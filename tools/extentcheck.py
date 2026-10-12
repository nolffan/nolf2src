#!/usr/bin/env python3
"""Test whether an enumerated row is really ONE function, before decoding it.

Extent defects are the dominant error in the large-function work: four of one
recent batch of five rows were wrong, in four different shapes, each found by
the same hand-rolled checks. This runs them.

  python3 tools/extentcheck.py <image> <start> <size|end>

It reports, and every one of these has caught a real defect:

  * more than one `ret`               -- may be several functions, or may be
                                         one /O2 epilogue duplicated; the
                                         branch-target test separates them
  * more than one `push %ebp` frame   -- prologues behind lea-nop padding are
    setup                                where a row spans functions
  * branch targets outside the range  -- a function whose cold blocks branch
                                         back inside is still one function;
                                         targets leaving the range are not
  * a start that is a /Qip entry      -- `mov 0x4(%esp),%eax ; mov 0x8(%esp),
                                         %edx` falling into a `push %ebp` is
                                         the STACK entry, with the register
                                         entry a few bytes in. A row addressed
                                         AT the register entry has its real
                                         start earlier -- that is what made a
                                         6,456-byte row span two functions.
  * trailing lea-nop padding          -- the body ends before the row does
  * the last instruction overrunning  -- the row ends mid-instruction

It is a REPORT, not a verdict. It tells you where to look; the evidence still
has to be read.
"""
import os
import re
import subprocess
import sys


def disasm(image, start, end):
    out = subprocess.run(
        ["objdump", "-d", f"--start-address={hex(start)}",
         f"--stop-address={hex(end)}", image],
        capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\t([0-9a-f ]+)\t(.*)", line)
        if m:
            rows.append((int(m.group(1), 16),
                         len(m.group(2).split()),
                         m.group(3).strip()))
    return rows


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    image, start = sys.argv[1], int(sys.argv[2], 16)
    arg = int(sys.argv[3], 16) if sys.argv[3].startswith("0x") else int(sys.argv[3])
    end = arg if arg > start else start + arg
    size = end - start

    # Disassemble PAST the end so the padding and the next start are visible.
    rows = disasm(image, start, end + 64)
    inside = [r for r in rows if r[0] < end]
    if not inside:
        sys.exit("nothing disassembled -- wrong image or address?")
    print(f"0x{start:08x}..0x{end:08x}  {size:,} bytes  "
          f"{len(inside)} instructions")
    # The /Qip checks below are Intel-specific. On an MSVC target they cannot
    # fire, and their silence must not be read as "the extent is verified" --
    # they were the two commonest defects in d3d.ren (nine register-entry rows
    # and sixteen overlapping ones) and they simply do not exist here.
    if "d3d" not in os.path.basename(image):
        print("NOTE: this is not d3d.ren, so the /Qip register-entry and "
              "overlap checks cannot fire.\n      Their silence is not "
              "evidence. Only the ret/prologue/branch-target/padding checks "
              "apply here.")
    print()

    boundaries = {a for a, _, _ in rows}

    rets = [a for a, _, t in inside if t.startswith("ret")]
    print(f"ret               {len(rets)}"
          + ("" if len(rets) < 2 else "   <-- check: several functions, or "
                                      "one /O2 epilogue duplicated?"))
    for a in rets:
        print(f"                    0x{a:08x}")

    pro = [a for i, (a, _, t) in enumerate(inside)
           if t.startswith("push   %ebp")
           and i + 1 < len(inside) and "mov    %esp,%ebp" in inside[i + 1][2]]
    # ZERO prologues is NOT a defect. icl emits plenty of large functions
    # entirely %esp-relative with no frame pointer -- 0x1004b720 (11,204 b)
    # and 0x10043e10 (4,452 b) are both frameless and both decoded correctly
    # from their rows as given. A first version of this sweep flagged 14 rows
    # on that basis and every one was a false positive, so it is reported as
    # information, not a warning.
    note = ("" if len(pro) >= 2 else
            "   (frameless: normal for icl, not a defect)" if not pro else "")
    print(f"\npush %ebp frames  {len(pro)}"
          + ("   <-- ROW LIKELY SPANS FUNCTIONS" if len(pro) >= 2 else note))
    for a in pro:
        pad = [t for pa, _, t in inside if pa < a and "nop" in t or
               (pa < a and "lea" in t and "%eiz" in t)]
        print(f"                    0x{a:08x}"
              + ("   (lea-nop padding precedes it)" if pad and a != start else ""))

    # A /Qip stack entry loads its arguments off the stack and falls through
    # into the register entry's own prologue.
    head = inside[:3]
    if head and re.match(r"mov\s+0x4\(%esp\),%eax", head[0][2]):
        reg = next((a for a, _, t in inside if t.startswith("push   %ebp")), None)
        print(f"\n/Qip              start is the STACK entry; register entry "
              f"at 0x{reg:08x}" if reg else "")
    else:
        # NOT gated on the row starting with `push %ebp`. It used to be, and
        # that blinded the check to every FRAMELESS function: 0x10024024's row
        # opens `sub $0xc,%esp`, so the walk-back never ran and the 216-row
        # sweep missed it -- the sweep could only ever have caught register
        # entries belonging to functions that keep a frame pointer. The
        # preceding bytes being argument loads is the whole test; what the row
        # itself starts with is irrelevant.
        pre = disasm(image, start - 24, start + 4)
        prev = [(a, t) for a, _, t in pre if a < start]
        # Walk back over the CONSECUTIVE argument loads that make up the stack
        # entry, so the corrected start is computed rather than assumed to be
        # start-4. A two-argument entry is 8 bytes, not 4.
        k = len(prev)
        while k and re.match(r"mov\s+0x[0-9a-f]+\(%esp\),%e", prev[k - 1][1]):
            k -= 1
        if k < len(prev):
            fixed = prev[k][0]
            print(f"\n/Qip              !! THIS ROW STARTS AT A REGISTER "
                  f"ENTRY. The stack entry, and the real function, starts at "
                  f"0x{fixed:08x} ({start - fixed} bytes earlier, "
                  f"{len(prev) - k} argument load(s)). Re-address the row and "
                  f"add {start - fixed} to its size.")

    # A SECOND FUNCTION AFTER THE RET, even a frameless one. Counting
    # `push %ebp` prologues cannot see one that opens `push %ebx` -- which is
    # how 0x10073140 hid inside the 0x100729c0 row. The reliable signal is
    # independent of the prologue shape: a `ret`, then alignment padding, then
    # an instruction that NOTHING in the range branches to. A real function's
    # sunk cold blocks are always branched to from above their ret, so they do
    # not trip this.
    def is_pad_t(t):
        return ("nop" in t or t == "mov    %esi,%esi"
                or ("lea" in t and "%eiz" in t)
                or re.match(r"lea\s+0x0\(%e(si|di)[,)]", t) is not None)

    # target -> the LOWEST address that branches to it. A second function that
    # loops back to its own entry makes its head a branch target, which
    # suppressed the flag for 0x10038f50; only a branch from BEFORE the
    # candidate can mean it belongs to the preceding function.
    targets = {}
    for a, _, t in inside:
        m = re.search(r"\b(j\w+)\s+0x([0-9a-f]+)", t)
        if m:
            tg = int(m.group(2), 16)
            targets[tg] = min(targets.get(tg, a), a)
    # Not "after a ret" -- after ANY run of alignment padding. 0x10073140 sits
    # after the last of its neighbour's twelve sunk cold blocks, not after the
    # ret, so requiring a ret immediately before missed it. Intra-function
    # padding before a sunk block is excluded for free: that block is always a
    # branch target.
    second = []
    i = 0
    while i < len(inside):
        if is_pad_t(inside[i][2]):
            k = i
            while k < len(inside) and is_pad_t(inside[k][2]):
                k += 1
            # STRICT: nothing in the range branches to it at all, forwards
            # or backwards. The looser "nothing EARLIER branches to it" was
            # tried and flagged every aligned LOOP HEAD -- icl pads those too,
            # and a loop head reached only from the bottom of its loop is
            # indistinguishable from a function head by this test alone. It
            # produced thirteen false positives on 0x1005dca0 and one on
            # 0x10040e10, both known-correct rows. The cost of strictness is
            # that a second function which loops back to its own entry is
            # missed here -- 0x10038f50 does, and the `push %ebp` prologue
            # count catches that one instead. Two narrow checks with no false
            # positives beat one broad one that cries wolf.
            if k < len(inside) and inside[k][0] not in targets:
                second.append(inside[k][0])
            i = k
        else:
            i += 1
    if second:
        print(f"\nsecond function    !! after alignment padding, and nothing "
              f"EARLIER in the range branches to:")
        for a in second:
            print(f"                    0x{a:08x}   <-- a SEPARATE function, "
                  f"whatever its prologue looks like")

    out = []
    for a, _, t in inside:
        m = re.search(r"\b(j\w+|call)\s+0x([0-9a-f]+)", t)
        if not m:
            continue
        tgt = int(m.group(2), 16)
        if m.group(1) == "call":
            continue
        if not (start <= tgt < end):
            out.append((a, tgt))
        elif tgt not in boundaries:
            out.append((a, tgt))
    print(f"\nbranch targets    {len(out)} outside the range or mid-instruction"
          + ("" if not out else "   <-- EXTENT IS WRONG"))
    for a, t in out[:12]:
        print(f"                    0x{a:08x} -> 0x{t:08x}")

    # The mirror of the register-entry defect. Nine large rows are addressed
    # at a /Qip register entry, which means the four to eight bytes of the
    # stack entry were attributed to the PREVIOUS row -- so that row overlaps
    # the next function. 0x10048180's row runs to 0x10049bb4 and the function
    # after it starts at 0x10049bb0.
    tail = [(a, t) for a, _, t in rows if end - 12 <= a < end + 4]
    for i, (a, t) in enumerate(tail):
        if re.match(r"mov\s+0x[0-9a-f]+\(%esp\),%e", t) and a < end:
            nxt = [x for x in tail[i:] if x[1].startswith("push   %ebp")]
            if nxt and nxt[0][0] >= end - 4:
                print(f"\noverlap           !! THE ROW'S LAST BYTES ARE THE "
                      f"NEXT FUNCTION'S /Qip STACK ENTRY: 0x{a:08x} is an "
                      f"argument load falling into a prologue at "
                      f"0x{nxt[0][0]:08x}. This row is {end - a} bytes too "
                      f"long; the next function starts at 0x{a:08x}.")
                break

    last = inside[-1]
    lend = last[0] + last[1]
    if lend > end:
        print(f"\nlast instruction  0x{last[0]:08x} ends at 0x{lend:08x}, "
              f"PAST the stated end -- the row ends mid-instruction")
    elif lend < end:
        tail = [(a, t) for a, _, t in rows if lend <= a < end]
        pad = all("nop" in t or ("lea" in t and "%eiz" in t) or t == "mov    %esi,%esi"
                  for _, t in tail)
        print(f"\nlast instruction  0x{last[0]:08x} ends at 0x{lend:08x}; "
              f"{end - lend} bytes follow"
              + ("  (alignment padding -- body ends early)" if pad and tail
                 else "  <-- NOT padding; check what is there"))
    else:
        # objdump decodes lea-nop padding as instructions, so a row that ends
        # flush can still be padded: 0x1000e0e0's body ends 9 bytes before its
        # row does and the tail looked exact. Walk back over the padding.
        def is_pad(t):
            return ("nop" in t or t == "mov    %esi,%esi"
                    or ("lea" in t and "%eiz" in t)
                    or re.match(r"lea\s+0x0\(%e(si|di)[,)]", t) is not None)
        k = len(inside)
        while k > 0 and is_pad(inside[k - 1][2]):
            k -= 1
        if k < len(inside):
            body_end = inside[k - 1][0] + inside[k - 1][1]
            print(f"\nlast instruction  ends flush at the stated end, BUT the "
                  f"final {end - body_end} bytes are alignment padding -- the "
                  f"body ends at 0x{body_end:08x}")
        else:
            print(f"\nlast instruction  ends exactly at the stated end")


main()
