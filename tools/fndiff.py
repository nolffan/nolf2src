#!/usr/bin/env python3
"""One-shot function diff for the reconstruction loop.

Compares a shipped function against our compiled object and reports, in
order of severity: byte identity (relocations masked), the mnemonic diff,
the best register-renaming of ours (to separate allocation lottery from
structure), and pattern hints matched against the codegen fingerprints this
project has already proven (guides/09-codegen-patterns.md).

Usage:
  fndiff.py <ship-addr> <obj> <symbol-substr> [--image=out/reference/server.dll]
            [--end=0xADDR] [--csv=out/reference/server-functions.csv]

The shipped size comes from --end if given, else from the csv's (addr,size)
row. Typical loop:

  build/engine.sh server-one smgr.cpp PlaySound     # 3s rebuild+verify
  tools/fndiff.py 0x10034037 src/engine/server/Release/smgr.obj PlaySound
"""
import csv
import struct
import difflib
import itertools
import re
import subprocess
import sys

HERE = __file__.rsplit("/", 1)[0]


def run(args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def parse_listing(text):
    """[(offset, [bytes...], 'op', 'args')] from exedump/dumpfn output.

    objdump wraps any instruction longer than SEVEN bytes onto a second line
    carrying only an offset and the remaining bytes -- no mnemonic field:

          1f:\tc7 85 04 ff ff ff 00 \tmovl   $0x0,-0xfc(%ebp)
          26:\t00 00 00

    The mnemonic-matching pattern below cannot match that line, so for a long
    time those trailing bytes were simply DROPPED and every size this tool
    printed was short by three bytes per wrapped instruction. It reported
    ws_MoveBox as 2122/2023 where the real figures are 2134/2038, which is
    enough to make a function look closer than it is, or to make an edit look
    size-neutral when it was not. Continuation bytes are now appended to the
    instruction they belong to.
    """
    out = []
    for line in text.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\t([0-9a-f ]+)\t(\S+)\s*(.*)", line)
        if m:
            args = m.group(4).split(";")[0].strip()
            out.append((m.group(1), m.group(2).split(), m.group(3), args))
            continue
        # The trailing `;` comment is dumpfn's relocation annotation, and a
        # continuation line can carry one: `618:\t00    ; ?g_pServerMgr...`.
        # Requiring end-of-line after the bytes missed exactly those, so the
        # first version of this fix still under-reported by three bytes per
        # relocated long instruction.
        c = re.match(r"\s*([0-9a-f]+):\t((?:[0-9a-f]{2} )+)\s*(?:;.*)?$", line)
        if c and out:
            out[-1][1].extend(c.group(2).split())
    return out


def norm(ins, regmap=None):
    """'op X-masked-args' stream, optionally renaming callee-saved regs."""
    out = []
    for _, _, op, args in ins:
        a = re.sub(r"0x[0-9a-f]+", "X", args)
        if regmap:
            a = re.sub(r"%(ebx|esi|edi)", lambda m: "%" + regmap[m.group(1)], a)
            a = re.sub(r"%(bx|si|di)\b",
                       lambda m: "%" + regmap["e" + m.group(1)][1:], a)
        out.append(op + " " + a)
    return out


def opblocks(a, b):
    sm = difflib.SequenceMatcher(None, a, b)
    return [(t, a[i1:i2], b[j1:j2])
            for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]


HINTS = [
    (lambda S, O: any("pop %ecx" in x for x in O) and any(x.startswith("add") and "%esp" in x for x in S),
     "ours pops where ship batches an add esp: the call site is varargs for us, "
     "fixed-prototype for ship. Declare a fixed second prototype for this site "
     "(the dsi_PrintStat / net_DebugPrint5 trick). Note 12.00.8804 also never "
     "merges pending cleanup into a varargs add (proven)."),
    (lambda S, O: any(x.startswith("lea") for x in S) and not any(x.startswith("lea") for x in O),
     "ship has a lea ours lacks: usually a pointer local whose indexed uses "
     "folded back to absolute addressing (float* p = &obj->field), leaving "
     "only the initialization behind."),
    (lambda S, O: any(x.startswith("lea") for x in O) and not any(x.startswith("lea") for x in S),
     "ours materializes an address ship reads by displacement. NOT a revision "
     "difference - that claim was falsified: 8168, 8447 and 8966 all form the "
     "temp here. The trigger is a single tail-hosted exit; with the return "
     "written inline the lea disappears (sm_RemoveObjectFromSky near class). "
     "Try an early return, or a value temp."),
    (lambda S, O: any(x.startswith("not ") for x in S) and not any(x.startswith("not ") for x in O),
     "ship tests a complement: the source wrote a literal ~ ( `if (~flags & BIT)` )."),
    (lambda S, O: any(x.startswith("incl X(%ebp)") or x.startswith("incl -X(%ebp)") for x in S)
                  and not any(x.startswith("incl") for x in O),
     "ship keeps a memory-homed counter ours folds away: write it through a "
     "volatile pointer aliased into a dead parameter slot (CServerMgr::Update's "
     "loop counter); keep the loop-condition READ a plain cast so FP stores can "
     "still sink past the compare."),
    (lambda S, O: any(re.match(r"mov %\w+,-?X?\(?%e(bx|si|di)x?\)?$", x) is None and x.startswith("mov X(%e") and x.endswith("%ax") for x in S)
                  or any(x.startswith("movzwl") for x in O) and any(re.search(r"mov X\(%e\w\w\),%.?x$", x) for x in S),
     "ship loads a partial register (mov ax/cx) where ours zero-extends: the "
     "parameter or field is uint16 at that site."),
    (lambda S, O: any(x.startswith("fldz") or x.startswith("fsts") or x.startswith("fstps") for x in S + O),
     "FP store scheduling: 8804 will not move stores across volatile accesses "
     "and sinks them past plain compares; check LTCLAMP-in-st, value-kept-in-st "
     "chains, and the two-statement clamp form."),
    (lambda S, O: any("push" in x for x in O) and any(x.startswith("jmp") for x in S) and len(O) > len(S),
     "ours tail-duplicates a loop head ship jumps back to: 8168 preserves the "
     "loop shape; 8804 rotates whatever the source (while/do/goto all tried in "
     "CNetMgr::GetPacket). Likely an 8168-TU near if everything else matches."),
]


def reloc_offsets(obj, sym):
    """Byte offsets within `sym` that carry a relocation, from the COFF itself.

    Returns an empty set if the object or symbol cannot be read, in which
    case the caller's zero-byte heuristic still applies -- a missing mask is
    a false difference report, never a false match.
    """
    try:
        sys.path.insert(0, HERE)
        from exematch import parse_obj_masked
        fns = parse_obj_masked(open(obj, "rb").read())
    except Exception:
        return set()
    for name, (code, mask) in fns.items():
        if sym in name:
            return set(mask)
    return set()



def _trim_trailing_table(image, start, end):
    """Drop a trailing jump table from a shipped extent. See the call site."""
    try:
        sys.path.insert(0, HERE)
        from enumfuncs import Image
        img = Image(image)
    except Exception:
        return end
    lo, hi = img.tlo, img.thi
    n = 0
    while end - 4 >= start:
        off = (end - 4) - lo
        if off < 0 or off + 4 > len(img.text):
            break
        v = struct.unpack_from("<I", img.text, off)[0]
        if not (lo <= v < hi):
            break
        end -= 4
        n += 1
    if n >= 4:
        print(f"note: trimmed {n} trailing dwords ({n * 4} bytes) that are all "
              f".text addresses -- a jump table, not code", file=sys.stderr)
        return end
    return end + n * 4


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) if "=" in a else (a, True)
                for a in sys.argv[1:] if a.startswith("--"))
    if len(args) != 3:
        sys.exit(__doc__)
    addr, obj, sym = args
    image = opts.get("--image", "out/reference/server.dll")
    csvpath = opts.get("--csv")
    if csvpath is None:
        stem = image.rsplit("/", 1)[-1].split(".")[0]
        # The function table build/reference.sh writes from the current
        # enumeration. fndiff takes a function's extent from it, so a stale
        # table makes a whole function look like a near-miss that is really
        # the next function's bytes counted against it.
        csvpath = f"out/reference/{stem}-functions.csv"

    start = int(addr, 16)
    if "--end" in opts:
        end = int(opts["--end"], 16)
    else:
        end = None
        try:
            for r in csv.DictReader(open(csvpath)):
                if int(r["addr"], 16) == start:
                    end = start + int(r["size"])
                    break
        except OSError:
            pass
        if end is None:
            sys.exit(f"size for {addr} not in {csvpath}; pass --end")

    # A row's extent often INCLUDES the function's jump tables, which sit
    # after the last `ret` and are data. exedump decodes them as instructions,
    # so the shipped side comes out longer than the real code and every
    # comparison below is measured against a number that is too big.
    # net_LogPacket's row carries 140 bytes of table that decode as 52 fake
    # instructions -- enough to report a 14-byte gap as 154.
    #
    # A table is a run of dwords that are all valid .text addresses. Trim from
    # the END only, require at least four in a row so a coincidental pointer
    # cannot shorten a real function, and say so rather than doing it silently.
    end = _trim_trailing_table(image, start, end)

    ship = parse_listing(run(["python3", f"{HERE}/exedump.py", image, addr, hex(end)]))
    ours = parse_listing(run(["python3", f"{HERE}/dumpfn.py", obj, sym]))
    if not ship or not ours:
        sys.exit("empty listing (bad address, obj, or symbol)")

    ship_len = sum(len(b) for _, b, _, _ in ship)
    ours_len = sum(len(b) for _, b, _, _ in ours)
    print(f"ship {ship_len} bytes / {len(ship)} instructions;"
          f" ours {ours_len} bytes / {len(ours)} instructions")

    # 1. byte identity, relocations masked.
    #
    # Masking on "our byte is zero" is not enough: a relocation with a
    # non-zero addend (`flds g_vIsectDir+4` leaves 04 00 00 00 in the
    # unrelocated object) has no zero byte to spot, so it reads as a real
    # difference and the function looks like a near that exematch calls
    # identical. Two functions were misreported that way before this was
    # found. So take the actual relocated offsets out of the COFF instead,
    # and keep the zero rule as a fallback for when that lookup fails.
    relmask = reloc_offsets(obj, sym)
    if ship_len == ours_len and len(ship) == len(ours):
        bad = []
        pos = 0
        for (sa, sb, _, _), (oa, ob, _, _) in zip(ship, ours):
            masked = {i - pos for i in relmask if pos <= i < pos + len(ob)}
            if len(sb) != len(ob) or any(
                    x != y and y != "00" and i not in masked
                    for i, (x, y) in enumerate(zip(sb, ob))):
                bad.append((sa, sb, oa, ob))
            pos += len(ob)
        if not bad:
            print("VERDICT: byte-identical modulo relocations. Run exematch to confirm.")
            return
        print(f"{len(bad)} instruction(s) differ at byte level:")
        for sa, sb, oa, ob in bad[:10]:
            print(f"  ship {sa}: {' '.join(sb)}   ours {oa}: {' '.join(ob)}")

    # 2. mnemonic diff
    a, b = norm(ship), norm(ours)
    blocks = opblocks(a, b)
    print(f"\nmnemonic diff: {len(blocks)} block(s)")
    for t, S, O in blocks[:25]:
        print(f"[{t}]")
        for x in S:
            print("  S", x)
        for x in O:
            print("  O", x)

    # 3. best register renaming of ours
    if blocks:
        best, bestmap = blocks, None
        for perm in itertools.permutations(["ebx", "esi", "edi"]):
            m = dict(zip(["ebx", "esi", "edi"], perm))
            bl = opblocks(a, norm(ours, m))
            if sum(len(S) + len(O) for _, S, O in bl) < \
               sum(len(S) + len(O) for _, S, O in best):
                best, bestmap = bl, m
        if bestmap and bestmap != {"ebx": "ebx", "esi": "esi", "edi": "edi"}:
            print(f"\nbest register renaming {bestmap}: "
                  f"{len(best)} residual block(s)")
            if not best:
                print("PURE REGISTER LOTTERY: try decl/init order, "
                      "pListHead-first, the cursor-alias walk, or accept as "
                      "the FreeUnusedModels near class.")
            for t, S, O in best[:15]:
                print(f"[{t}]")
                for x in S:
                    print("  S", x)
                for x in O:
                    print("  O", x)
            blocks = best

    # 4. fingerprint hints
    S = [x for _, ss, _ in blocks for x in ss]
    O = [x for _, _, oo in blocks for x in oo]
    hints = [h for cond, h in HINTS if cond(S, O)]
    if hints:
        print("\nhints (proven fingerprints, see guides/09-codegen-patterns.md):")
        for h in hints:
            print("  *", h)
    if ship_len == ours_len and abs(len(ship) - len(ours)) <= 2 and len(blocks) <= 3:
        print("\nsize-exact with <=3 residual blocks: if shapes are exhausted, "
              "suspect a cl-8168 TU (server.dll is a mixed 8168/8447 build - "
              "see richhdr.py) and document as a near.")


if __name__ == "__main__":
    main()
