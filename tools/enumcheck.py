#!/usr/bin/env python3
"""Validate an enumerated function table against a real disassembly.

enumfuncs.py collects function starts from calls, vtables, push operands and
prologue heuristics, then takes each size as start-to-next-start. Both halves
of that can be wrong, and the two failures look nothing alike:

  a SPURIOUS start truncates the function before it -- the classic case is an
  address that is really an operand byte, so the "start" sits mid-instruction;

  a MISSING start makes the function before it swallow the next one whole.

Nine such defects were found by hand across one day's reconstruction, always
the same way: someone checked a worklist size against the disassembly and it
did not agree. This does that check for the whole table at once.

Each start is disassembled for exactly its claimed size. A row is sound when
the instruction stream lands exactly on start+size and the last instruction
is a terminator (ret/jmp/int3) or the tail is padding. Anything else is
reported with the reason.

Usage:
  enumcheck.py <image> <functions.csv> [--verbose]
"""
import csv
import os
import re
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exedump import Pe  # noqa: E402

TERM = ("ret", "jmp", "int3", "iret", "ud2")


def disasm(blob, base):
    """[(addr, length, mnemonic)] for one contiguous run of bytes."""
    f = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
    f.write(blob)
    f.close()
    out = subprocess.run(
        ["objdump", "-D", "-b", "binary", "-m", "i386", "-M", "att",
         f"--adjust-vma={base:#x}", f.name],
        capture_output=True, text=True).stdout
    os.unlink(f.name)
    rows = []
    for line in out.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\t([0-9a-f ]+)\t(\S+)", line)
        if m:
            nb = len(m.group(2).split())
            rows.append((int(m.group(1), 16), nb, m.group(3)))
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    verbose = "--verbose" in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    pe = Pe(args[0])
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]

    rows, source = [], {}
    for r in csv.DictReader(open(args[1])):
        a = int(r["addr"], 16)
        rows.append((a, int(r["size"])))
        source[a] = (r.get("source") or "").strip()
    rows.sort()
    starts = {a for a, _ in rows}

    bad = []
    for i, (a, n) in enumerate(rows):
        if n <= 0 or not (tva <= a < tva + tvs):
            continue
        blob = text[a - tva:a - tva + n]
        if len(blob) < n:
            continue
        ins = disasm(blob, a)
        if not ins:
            continue
        last_a, last_n, last_m = ins[-1]
        end = last_a + last_n
        # trailing padding is fine
        tail = blob.rstrip(b"\x90").rstrip(b"\xcc")
        if end != a + n:
            bad.append((a, n, "size is not an instruction boundary",
                        f"stream ends at 0x{end:08x}"))
            continue
        if not last_m.startswith(TERM) and len(tail) == n:
            nxt = rows[i + 1][0] if i + 1 < len(rows) else None
            # "Does not end in a terminator" was one bucket and is really
            # two, with opposite fixes. Decode a little PAST the claimed end
            # and see where the instruction boundaries actually fall: if the
            # next start is not one of them, an instruction straddles it and
            # the NEXT START IS SPURIOUS -- almost always an operand byte that
            # the call/push scan mistook for an address. If the next start is
            # a clean boundary, the row is genuinely short and a start is
            # missing inside it. Reporting the first as the second sends the
            # reader looking for a function that was never there.
            spurious = False
            if nxt is not None:
                over = text[a - tva:min(a - tva + n + 16, len(text))]
                bounds = {ia for ia, _il, _im in disasm(over, a)}
                spurious = nxt not in bounds
            if spurious:
                bad.append((a, n, "the NEXT start is spurious",
                            f"last is `{last_m}`; an instruction straddles "
                            f"0x{nxt:08x}, so that row is an operand byte and "
                            f"this function runs past it"))
            else:
                bad.append((a, n, "does not end in a terminator",
                            f"last is `{last_m}`; next start "
                            f"{'0x%08x' % nxt if nxt else 'none'}"
                            f" is a clean boundary, so a start is missing "
                            f"inside this row or the size is short"))
        # An interior `ret` followed by something that looks like a prologue
        # means a start is MISSING and this row has swallowed the function
        # after it. That is the other half of the defect and it does not
        # show up above, because a merged row still ends on a terminator at
        # the right address -- it simply contains two functions.
        for k, (ia, il, im) in enumerate(ins[:-1]):
            if not im.startswith("ret"):
                continue
            j = k + 1
            while j < len(ins) and ins[j][2] in ("nop", "int3"):
                j += 1
            if j >= len(ins):
                continue
            na, _nl, nm = ins[j]
            if na in starts:
                continue                       # already a known start
            nxt3 = [x[2] for x in ins[j:j + 3]]
            prologue = (nm == "push" and any(x in ("push", "mov", "sub") for x in nxt3[1:])) \
                or (nm == "sub" and "push" in nxt3[1:]) \
                or (nm == "mov" and nxt3[1:2] == ["push"])
            if prologue:
                bad.append((a, n, "contains an interior ret then a prologue",
                            f"start missing at 0x{na:08x} (+{na - a}); "
                            f"this row spans two functions"))
                break

        # A forwarder is a `jmp` in the first few bytes with nothing of its
        # own after it. If the row continues past that jmp, the row has
        # swallowed whatever follows -- the same missing-start defect, but
        # with a tail-jump where the loop above wanted a `ret`.
        run = 0
        for k, (ia, il, im) in enumerate(ins):
            run += il
            if im.startswith("jmp") and run <= 8 and k + 1 < len(ins):
                nxt = ins[k + 1][0]
                if nxt not in starts and ins[k + 1][2] not in ("nop", "int3"):
                    bad.append((a, n, "tail-jump forwarder, row continues past it",
                                f"start missing at 0x{nxt:08x} (+{nxt - a}); "
                                f"the function here is {run} bytes"))
                break
            if run > 8:
                break

        # any claimed start that this function's stream steps over is spurious
        boundaries = {x for x, _, _ in ins}
        for s in starts:
            if a < s < a + n and s not in boundaries:
                bad.append((s, 0, "start is mid-instruction (spurious)",
                            f"inside the function at 0x{a:08x} (+{s - a})"))

    # Third failure mode: a stretch of .text no row covers at all. enumfuncs
    # only finds a start if something references it, so a function reached
    # only through a register or a jump table can be missed entirely -- and
    # then it is not a wrong size, it is absent. 0x100135e0's "226-byte gap"
    # was two whole functions.
    cur = tva
    for a, n in rows:
        if a > cur:
            blob = text[cur - tva:a - tva]
            if blob.strip(b"\x90\xcc"):
                bad.append((cur, a - cur, "not covered by any row",
                            f"gap runs to 0x{a:08x}; "
                            f"{len(blob.strip(chr(0x90).encode() + chr(0xcc).encode()))}"
                            f" non-padding bytes"))
        cur = max(cur, a + n)

    # enumfuncs labels a row `gap` when it found the extent by elimination
    # rather than by a reference -- its own admission that the boundaries are
    # a guess. Those are exactly where two functions get merged, so report
    # them as suspect by default rather than waiting for one of the tests
    # above to fire. 0x100135e0 is a `gap` row of 226 bytes that is really
    # two functions, and none of the structural tests catches it.
    for a, n in rows:
        if source.get(a) == "gap" and n > 0 and tva <= a < tva + tvs:
            bad.append((a, n, "extent found by elimination (source=gap)",
                        "boundaries are unreferenced; confirm before trusting "
                        "the size"))

    seen = set()
    for a, n, why, detail in bad:
        if (a, why) in seen:
            continue
        seen.add((a, why))
        print(f"0x{a:08x}  {n:>5}  {why}\n              {detail}")
    print(f"\n{len(rows)} rows checked, {len(seen)} suspect")


if __name__ == "__main__":
    main()
