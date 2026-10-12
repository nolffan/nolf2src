#!/usr/bin/env python3
"""Does our reconstruction CALL what the shipped function calls, in order?

WHY THIS EXISTS. tools/callcheck.py answers the same question but only for a
function exematch can PLACE, which means a function that already matches. For
a large function reconstructed to be structurally right but not byte-exact --
a deliberate near -- placement fails and callcheck says nothing at all.

That is exactly where the question matters most. A 11K-byte function with 135
call sites, whose reconstruction issues the same 135 calls to the same
targets in the same order, is right about the control flow, the branch
structure and the callee set even if the register allocator disagrees
everywhere. Getting that sequence right by accident is not plausible; so this
is an acceptance test for work the byte oracle cannot yet score.

WHAT IT COMPARES. The shipped side is the ordered list of `call rel32`
targets read straight out of the image between two addresses. Our side is the
ordered list of REL32 call relocations in the named object symbol, with each
relocation's target symbol resolved to an address where the name carries one
(`sub_1004b720`) or where another of our objects places it. Indirect calls
(`ff /2`, a vtable slot) carry no relocation and are counted separately on
both sides: their COUNT and POSITION are compared, since a virtual call's
target is not knowable from the object.

Alignment is by longest common subsequence, so one missing or extra call
reports as one insertion rather than desynchronising everything after it --
which is what makes the output a worklist rather than a wall of noise.

Usage:
  callseq.py <image> <start> <end> <obj> <symbol-substr> [--verbose]
  callseq.py <image> <start> <end> --count      # calls and bytes-per-call

Exit status 0 if every resolvable target agrees and the counts match.
"""
import glob
import os
import subprocess
import tempfile
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exedump import Pe  # noqa: E402
from exematch import parse_obj_masked, find  # noqa: E402

REL32 = 0x14


def disasm_calls(blob, base):
    """Ordered (offset, target|None) for every call, via objdump.

    Byte-scanning for `e8` and `ff /2` does NOT work here and the control
    proves it: a byte-identical function reported an extra indirect call,
    because our object leaves relocated displacements as zero where the
    image holds a real address that happens to contain 0xff. Only a real
    decode gets the instruction boundaries right, so both sides go through
    objdump and are compared on equal terms.
    """
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(blob)
        tmp = f.name
    out = subprocess.run(
        ["objdump", "-D", "-b", "binary", "-m", "i386",
         f"--adjust-vma=0x{base:x}", tmp],
        capture_output=True, text=True).stdout
    os.unlink(tmp)
    calls = []
    for line in out.splitlines():
        m = re.match(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(\S+)\s*(.*)$",
                     line)
        if not m or m.group(3) != "call":
            continue
        off, arg = int(m.group(1), 16), m.group(4).strip()
        d = re.match(r"^(?:0x)?([0-9a-f]+)\s*$", arg)
        calls.append((off, int(d.group(1), 16) if d else None))
    return calls


def shipped_calls(pe, start, end):
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]
    return disasm_calls(text[start - tva:end - tva], start)


def our_calls(objpath, symsub):
    """Ordered (offset, callee-name) for the named symbol's REL32 calls."""
    data = open(objpath, "rb").read()
    machine, nsec, _ts, symoff, nsyms, optsz, _ch = struct.unpack_from(
        "<HHIIIHH", data, 0)
    strtab = data[symoff + nsyms * 18:]

    def symname(raw):
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            return strtab[off:strtab.find(b"\0", off)].decode("latin-1")
        return raw.rstrip(b"\0").decode("latin-1")

    entries, i = [None] * nsyms, 0
    while i < nsyms:
        e = symoff + i * 18
        name = symname(data[e:e + 8])
        value, secnum, typ, storage, naux = struct.unpack_from(
            "<IhHBB", data, e + 8)
        entries[i] = (name, value, secnum, typ, storage)
        i += 1 + naux

    for si in range(nsec):
        s = 20 + optsz + si * 40
        vsize, _va, rawsz, rawp, relp, _l, nrel, _n = struct.unpack_from(
            "<IIIIIIHH", data, s + 8)
        flags = struct.unpack_from("<I", data, s + 36)[0]
        if not flags & 0x20 or not rawsz:
            continue
        fsyms = sorted((v, n) for e in entries if e
                       for n, v, sn, typ, st in [e]
                       if sn == si + 1 and st in (2, 3) and typ == 0x20)
        # LARGEST match, not the first. icl emits outlined cold regions as
        # separate symbols with a `$$1` suffix -- `?f$$1@...` sorts before
        # `?f@...` and is often zero-length, so a first-match rule silently
        # compared an empty symbol and reported 50 shipped calls against 0.
        cands = [(j, v, n) for j, (v, n) in enumerate(fsyms) if symsub in n]
        if not cands:
            continue
        def _len(t):
            j, v, n = t
            return (fsyms[j + 1][0] if j + 1 < len(fsyms) else rawsz) - v
        j, v, n = max(cands, key=_len)
        if True:
            end = fsyms[j + 1][0] if j + 1 < len(fsyms) else rawsz
            code = data[rawp + v:rawp + end]
            names = {}
            for r in range(nrel):
                va, idx, typ = struct.unpack_from("<IIH", data, relp + r * 10)
                if v <= va < end and typ == REL32:
                    names[va - v - 1] = entries[idx][0]
            out = [(off, names.get(off)) for off, _t in disasm_calls(code, 0)]
            return n, out
    return None, None


def lcs(a, b, eq):
    """Longest common subsequence, as an alignment of index pairs."""
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            d[i][j] = (d[i + 1][j + 1] + 1 if eq(a[i], b[j])
                       else max(d[i + 1][j], d[i][j + 1]))
    out, i, j = [], 0, 0
    while i < n and j < m:
        if eq(a[i], b[j]):
            out.append((i, j)); i += 1; j += 1
        elif d[i + 1][j] >= d[i][j + 1]:
            out.append((i, None)); i += 1
        else:
            out.append((None, j)); j += 1
    out += [(i + k, None) for k in range(n - i)]
    out += [(None, j + k) for k in range(m - j)]
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {a for a in sys.argv[1:] if a.startswith("--")}

    # --count: just how many calls a shipped range makes, and its density.
    # This exists because ranking candidates by BYTE-SCANNING for 0xe8
    # overcounts badly -- 0xe8 occurs inside displacements, immediates and
    # data -- and a bad count sets the wrong expectation for a function. 0x10016324 was ranked at 69 calls and 93 B/call
    # that way; it actually makes 38, at 168 B/call, which is the difference
    # between this guide's "strong" and "weak" bands.
    if "--count" in opts and len(args) == 3:
        pe = Pe(args[0])
        lo, hi = int(args[1], 16), int(args[2], 16)
        c = shipped_calls(pe, lo, hi)
        direct = sum(1 for _o, t in c if t is not None)
        print(f"{hi - lo:,} bytes, {len(c)} calls "
              f"({direct} direct, {len(c) - direct} indirect), "
              f"{(hi - lo) / max(len(c), 1):.0f} bytes per call")
        return

    if len(args) != 5:
        sys.exit(__doc__)
    image, start, end, objpath, symsub = args
    pe = Pe(image)
    ship = shipped_calls(pe, int(start, 16), int(end, 16))
    name, ours = our_calls(objpath, symsub)
    if ours is None:
        sys.exit(f"symbol matching {symsub!r} not found in {objpath}")

    # Where does each of our callee symbols live? A name carrying an address
    # gives it directly; otherwise ask exematch to place the symbol.
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]
    placed = {}
    for o in sorted(glob.glob(os.path.join(os.path.dirname(objpath), "*.obj"))):
        try:
            fns = parse_obj_masked(open(o, "rb").read())
        except Exception:
            continue
        for n, (code, mask) in fns.items():
            if len(code) - len(mask) < 8:
                continue
            hits = list(find(text, tva, code, mask))
            if len(hits) == 1:
                placed.setdefault(n, hits[0])

    def addr_of(n):
        if n is None:
            return None
        m = re.search(r"(1[0-9a-f]{7})", n)
        if m:
            return int(m.group(1), 16)
        return placed.get(n)

    # /Qip emits a function as TWO entries: a stack entry at f that falls into
    # a register entry at f+4. A self-call or an internal call in the shipped
    # build reaches the register entry, while ours names the symbol at f. That
    # is the "/Qip two-entry offset" guides/11 already lists as benign, and
    # leaving it unmatched charged a spurious shipped-only AND ours-only row to
    # every such call -- 0x1007cc90's recursive descent, for one. Accept f+4
    # when f is a symbol we placed, and report how many were accepted so the
    # figure is never silently flattered.
    qip = []

    def eq(s, o):
        if (s[1] is None) != (o[1] is None):
            return False          # direct vs indirect never correspond
        if s[1] is None:
            return True           # both indirect: position is all we compare
        a = addr_of(o[1])
        if a is None:
            return True
        if a == s[1]:
            return True
        if s[1] - a == 4:
            qip.append((s[0], a))
            return True
        return False

    align = lcs(ship, ours, eq)
    agree = sum(1 for i, j in align if i is not None and j is not None)
    only_ship = [i for i, j in align if j is None]
    only_ours = [j for i, j in align if i is None]
    unresolved = sum(1 for i, j in align
                     if i is not None and j is not None
                     and ship[i][1] is not None and addr_of(ours[j][1]) is None)

    print(f"symbol {name}")
    print(f"  shipped calls {len(ship):>4}   ours {len(ours):>4}")
    print(f"  in agreement  {agree:>4}   "
          f"({agree - unresolved} by resolved target, {unresolved} by position "
          f"only -- callee not placed)")
    print(f"  shipped-only  {len(only_ship):>4}   ours-only {len(only_ours):>4}")
    if qip:
        # Never silent: a matched f+4 is a real difference in which entry the
        # call reaches, benign but not nothing.
        print(f"  of the agreements, {len(set(qip))} matched on the /Qip two-entry "
              f"offset (shipped calls f+4 where we call f):")
        for site, ours_a in sorted(set(qip)):
            print(f"    ~~ {site:#010x} -> {ours_a + 4:#010x} (we call "
                  f"{ours_a:#010x})")
    if "--verbose" in opts or only_ship or only_ours:
        for i, j in align:
            if i is not None and j is not None and "--verbose" not in opts:
                continue
            s = (f"{ship[i][0]:#010x} -> "
                 f"{'indirect' if ship[i][1] is None else '%#010x' % ship[i][1]}"
                 if i is not None else " " * 24)
            o = (f"+{ours[j][0]:<6x} {ours[j][1] or 'indirect'}"
                 if j is not None else "")
            flag = "  " if (i is not None and j is not None) else "!!"
            print(f"    {flag} {s:<26} {o}")
    ok = not only_ship and not only_ours
    if not ship and not ours:
        # 0 of 0 is not agreement, it is NO EVIDENCE, and saying "AGREES"
        # here would be the tool's own worst failure mode. 0x100051a0 is
        # 5,786 bytes with not one call in it -- the check is blind to the
        # entire function and must say so rather than print a pass.
        print("\nNO CALLS IN RANGE -- this check is VACUOUS here. The "
              "function must be pinned by other evidence (guide 11, "
              "'When the call sequence is nearly blind').")
        sys.exit(0)
    print("\nCALL SEQUENCE AGREES" if ok else "\nCALL SEQUENCE DIFFERS")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
