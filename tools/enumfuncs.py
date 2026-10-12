#!/usr/bin/env python3
"""Enumerate every function in a symbol-less PE32 image.

Function starts are collected from three independent sources, because no
single one is complete:

  1. direct `call rel32` targets          — normal calls
  2. 4-byte values in other sections that point into .text
                                          — vtables, function tables, callbacks
  3. `push imm32` operands that land in .text
                                          — DLGPROCs and other API callbacks
  4. both targets of a `call rel32; jmp rel32` pair
                                          — global-initializer groups, whose
                                            atexit registration nothing else
                                            references
  5. code that follows a `ret` (past padding) with a recognizable prologue
     and that nothing else references
                                          — functions only reached indirectly
     (through a register, a jump table, or an exception handler)

plus the export table. Sizes are start-to-next-start, minus trailing padding.

Also reports coverage: the share of .text bytes that falls inside some
enumerated function. A number well below ~99% means starts are still missing.

Usage:
  enumfuncs.py <image.exe|dll> [--csv out.csv] [--names tagmap]
"""
import os
import struct
import sys


PROLOGUES = [
    b"\x55\x8b\xec",          # push ebp; mov ebp,esp
    b"\x8b\x4c\x24\x04",      # mov ecx,[esp+4]
    b"\x8b\x44\x24\x04",      # mov eax,[esp+4]
    b"\x8b\x54\x24\x04",      # mov edx,[esp+4]
    b"\x83\xec",              # sub esp,imm8
    b"\x81\xec",              # sub esp,imm32
]


class Image:
    """A PE image -- for the denominator, always a retail one
    (out/reference/, extracted from the retail game by `tools/retailextract.py reference`): an enumeration of
    anything else would drift with our own progress."""

    def __init__(self, path):
        self.path = path
        d = self.d = open(path, "rb").read()
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        self.nsec = struct.unpack_from("<H", d, pe + 6)[0]
        optsz = struct.unpack_from("<H", d, pe + 20)[0]
        self.base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
        self.pe = pe
        so = pe + 24 + optsz
        self.secs = []
        for i in range(self.nsec):
            s = so + i * 40
            name = d[s : s + 8].rstrip(b"\0").decode("latin-1")
            vs, va, rs, rp = struct.unpack_from("<IIII", d, s + 8)
            self.secs.append((name, va, vs, rs, rp))
        for name, va, vs, rs, rp in self.secs:
            if name == ".text":
                self.tlo = self.base + va
                self.thi = self.tlo + vs
                self.text = d[rp : rp + min(vs, rs)]

    def rva2off(self, rva):
        for name, va, vs, rs, rp in self.secs:
            if va <= rva < va + max(vs, rs):
                return rp + (rva - va)
        return None

    def cstr(self, va):
        o = self.rva2off(va - self.base)
        if o is None:
            return None
        e = self.d.find(b"\0", o)
        return self.d[o:e].decode("latin-1", "replace")

    def exports(self):
        erva = struct.unpack_from("<I", self.d, self.pe + 24 + 96)[0]
        out = {}
        if not erva:
            return out
        eo = self.rva2off(erva)
        nnam = struct.unpack_from("<I", self.d, eo + 24)[0]
        aof, anames, aord = struct.unpack_from("<III", self.d, eo + 28)
        for i in range(nnam):
            nrva = struct.unpack_from("<I", self.d, self.rva2off(anames) + i * 4)[0]
            ordn = struct.unpack_from("<H", self.d, self.rva2off(aord) + i * 2)[0]
            frva = struct.unpack_from("<I", self.d, self.rva2off(aof) + ordn * 4)[0]
            out[self.base + frva] = self.cstr(self.base + nrva)
        return out


def enumerate_functions(img):
    """Return (sorted starts, {start: source-tag})."""
    text, tlo, thi = img.text, img.tlo, img.thi
    src = {}

    def add(va, tag):
        if tlo <= va < thi:
            src.setdefault(va, tag)

    # 1. direct calls
    for off in range(len(text) - 5):
        if text[off] == 0xE8:
            add(tlo + off + 5 + struct.unpack_from("<i", text, off + 1)[0], "call")

    # 2. pointers into .text stored in other sections (vtables, tables)
    for name, va, vs, rs, rp in img.secs:
        if name == ".text":
            continue
        blob = img.d[rp : rp + min(vs, rs)]
        for o in range(0, len(blob) - 3, 4):
            add(struct.unpack_from("<I", blob, o)[0], "ptr")

    # 3. `push imm32` operands that land in .text — callbacks handed to the
    #    API (DLGPROCs, WNDPROCs, enumeration callbacks). These are neither
    #    call targets nor stored in a table, so nothing else finds them.
    for off in range(len(text) - 5):
        if text[off] == 0x68:
            add(struct.unpack_from("<I", text, off + 1)[0], "cb")

    # 3b. `movl $imm32, disp(%reg)` operands that land in .text -- a function
    #     address STORED INTO A TABLE AT RUN TIME rather than laid out in one.
    #     This is how both of this project's interface-setup functions work:
    #     lithtech.exe's ci_SetupInterface fills 208 ILTClient members this
    #     way, and d3d.ren's RenderDLLSetup fills 37 RenderStruct slots. Rule 2
    #     cannot see them (the table is in .data but is EMPTY in the file) and
    #     rule 1 only finds the ones that also happen to be called directly.
    #     Missing one costs a whole function: ci_SetOptimized2DColor at
    #     0x00409280 had no row at all, so a reconstructed function could not
    #     be credited, and its relocation-masked twin took its address instead.
    #
    #     Encodings, both with a 4-byte immediate last:
    #       c7 40 disp8  imm32   movl $imm,disp8(%eax..%edi)
    #       c7 80 disp32 imm32   movl $imm,disp32(%eax..%edi)
    for off in range(len(text) - 7):
        if text[off] != 0xC7:
            continue
        modrm = text[off + 1]
        if modrm & 0xC0 == 0x40 and (modrm & 0x07) != 4:          # disp8
            add(struct.unpack_from("<I", text, off + 3)[0], "setup")
        elif modrm & 0xC0 == 0x80 and (modrm & 0x07) != 4:        # disp32
            if off + 10 <= len(text):
                add(struct.unpack_from("<I", text, off + 6)[0], "setup")
        # 3c. the same store into a STACK local, `movl $imm32, disp(%esp)`:
        #     a function address written into a struct on the frame before
        #     the struct is handed on. The esp base needs a SIB byte (0x24),
        #     which 3b's `rm != 4` deliberately skips. cmodelload's
        #     0x00477460 stores 0x004451b0 (`mov $0x46,%eax ; ret`) this way
        #     and nothing else references it, so without this rule that
        #     6-byte function merged into phys_ResetMoveCounter's row
        #     (0x004451a0, 22 bytes for an 11-byte body) and neither could
        #     be credited. lithtech.exe gains 5 starts, server.dll none.
        #       c7 44 24 disp8  imm32   movl $imm,disp8(%esp)
        #       c7 84 24 disp32 imm32   movl $imm,disp32(%esp)
        elif modrm in (0x44, 0x84) and text[off + 2] == 0x24:
            i = off + (4 if modrm == 0x44 else 7)
            if i + 4 <= len(text):
                add(struct.unpack_from("<I", text, i)[0], "setup")

    # 4. the two halves of a global-initializer group. A `$E` thunk is exactly
    #    `call ??__E<var>; jmp <atexit registration>`, and the registration is
    #    reached only by that jmp — no call, no table, no padding-carve. Without
    #    it the constructor body and the registration merge into one span that
    #    matches neither COMDAT.
    #
    #    THE BYTE PATTERN ALONE IS NOT THE THUNK. `call f; jmp label` is also
    #    ordinary /O2 code -- a call in the tail position of an `if` arm or a
    #    loop body, where the jmp is the arm's exit or the loop's continue. Of
    #    the 42 pattern hits in lithtech.exe and 27 in server.dll, 33 are that.
    #    Each one minted a false function start in the MIDDLE of a real
    #    function, and three of them reached a worklist as unexamined
    #    "functions" of 714, 535 and 480 bytes: 0x0048618f and 0x004812dc are
    #    interior blocks of 0x00486040 and 0x00480d40, and 0x00486459 is the
    #    same defect in the same function.
    #
    #    The discriminator is what the thunk is FOR: it exists to be named by
    #    a `.CRT$XCU` slot, so its own address is stored as a dword somewhere
    #    outside .text. An `if` arm's tail call is not. Requiring that loses
    #    no real thunk -- one unreferenced by the CRT table would never run --
    #    and drops all 33. Note the call target is found by rule 1 regardless;
    #    the jmp target (the atexit registrar) is rule 4's only unique yield.
    data_ptrs = set()
    for _nm, _va, _vs, _rs, _rp in img.secs:
        if _nm == ".text":
            continue
        _blob = img.d[_rp : _rp + min(_vs, _rs)]
        for _o in range(0, len(_blob) - 3, 4):
            _v = struct.unpack_from("<I", _blob, _o)[0]
            if tlo <= _v < thi:
                data_ptrs.add(_v)

    for off in range(len(text) - 10):
        if text[off] == 0xE8 and text[off + 5] == 0xE9 and tlo + off in data_ptrs:
            add(tlo + off + 5 + struct.unpack_from("<i", text, off + 1)[0], "init")
            add(tlo + off + 10 + struct.unpack_from("<i", text, off + 6)[0], "init")

    # 4b. a THUNK's target. Rule 4 handles `call ??__E<var>; jmp <atexit>`,
    #     but the commonest `$E` in these images is the degenerate form: a
    #     bare `e9 00 00 00 00` -- `jmp $+5` -- because the linker placed the
    #     body COMDAT immediately after the thunk. There is no `call` in
    #     front, so rule 4 never fires and the 5-byte thunk and the body it
    #     jumps to merge into ONE row that matches neither COMDAT.
    #
    #     server.dll has 18 of these, 17 of them reached from the
    #     `.CRT$XCU` pointer run. Three of the merged rows had bodies that
    #     ALREADY reproduce byte-for-byte and could never be credited,
    #     because exematch skips a 5-byte symbol whose only four variable
    #     bytes are a relocation. The same failure hid CBaseCounter::ReadRaw
    #     behind the 5-byte `return Read();` thunk in front of it.
    #
    #     The rule is narrow on purpose: only a start ALREADY established by
    #     another rule, and only when its very first instruction is a
    #     `jmp rel32`. That is a thunk by construction, and its target is
    #     the function the thunk exists to reach.
    for va in list(src):
        off = va - tlo
        if 0 <= off < len(text) - 5 and text[off] == 0xE9:
            add(tlo + off + 5 + struct.unpack_from("<i", text, off + 1)[0],
                "thunk")

    # 4c. the `$E` initializer of a global CLASS object: `mov $&obj,%ecx;
    #     jmp ??0Class` (b9 imm32 e9 rel32), reached by 4b's bare `jmp $+5`
    #     from the `.CRT$XCU` slot. The constructor it tail-jumps to has no
    #     other reference, so without this the 10-byte thunk and the
    #     constructor merge into one row: server.dll 0x1003dd80 (53 bytes,
    #     really 10, g_Helpers -> CHelpers::CHelpers 0x1003dd90) and
    #     lithtech.exe 0x490c90 (-> 0x490ca0). Only a start that 4b itself
    #     found qualifies: the same byte pattern at a `call`/`cb` start is
    #     ordinary code (a thiscall tail jump) in all the other hits (21 in
    #     server.dll and lithtech.exe, 31 in NOLF.exe).
    for va in [v for v, t in list(src.items()) if t == "thunk"]:
        off = va - tlo
        if 0 <= off < len(text) - 10 and text[off] == 0xB9 \
                and text[off + 5] == 0xE9:
            add(tlo + off + 10 + struct.unpack_from("<i", text, off + 6)[0],
                "thunk")

    # 4d. what follows a complete one-store function. An atexit exit
    #     thunk for a global whose destructor only resets its vtable is
    #     exactly `movl $vtbl,abs32 ; ret` (c7 05 abs32 imm32 c3,
    #     11 bytes) -- decoded from its own start, so that `ret` is a real
    #     instruction boundary, not rule 6's any-offset C3. Past its padding
    #     the next COMDAT begins even when nothing references it: StdLith's
    #     unreferenced ??1LAlloc (`movl $vtbl,(%ecx) ; ret`) at server.dll
    #     0x1003d2e0 and lithtech.exe 0x491780, which otherwise merge into
    #     the thunk's row (0x1003d2d0 / 0x491770, 23 bytes, really 11).
    #     The shape is any one-store function, not only a thunk: lithtech.exe
    #     0x4451a0 (`movl $0,0x4b4064 ; ret`) is followed by an unreferenced
    #     `mov $0x46,%eax ; ret` at 0x4451b0 that had merged the same way.
    #     Across server.dll, lithtech.exe and NOLF.exe the rule adds exactly
    #     those three starts.
    for va in list(src):
        off = va - tlo
        if 0 <= off < len(text) - 12 and text[off] == 0xC7 \
                and text[off + 1] == 0x05 and text[off + 10] == 0xC3:
            p = off + 11
            while p < len(text) and text[p] in (0x90, 0xCC):
                p += 1
            if p > off + 11 and p < len(text) and (tlo + p) % 16 == 0:
                add(tlo + p, "stub")

    # 5. exports
    for va, nm in img.exports().items():
        src[va] = "export"

    # 6. unreferenced code following a ret, with a prologue
    #
    #    KNOWN DEFECT, measured but NOT fixed -- read this before trusting a
    #    `gap` row. The scan below looks for 0xC3 at EVERY BYTE OFFSET, not at
    #    instruction boundaries, so it also fires on the ModRM byte of any
    #    reg-to-reg instruction whose encoding ends in C3: `8b c3` is
    #    `mov eax,ebx`, `3b c3` is `cmp eax,ebx`, and both are everywhere. When
    #    the bytes after such a false `ret` happen to look like a prologue
    #    (`55 8b` = `push ebp ; mov ...` passes the test below), a start is
    #    minted in the MIDDLE of a live function.
    #
    #    Row 0x00478b4a/1547 is the
    #    `push ebp` TEN BYTES into the prologue of the real function at
    #    0x00478b40 (1557 bytes): 0x00478b48 is `8b c3`, so 0x00478b49 is the
    #    operand byte this rule read as a terminator. A full .text sweep finds
    #    ZERO references to 0x00478b4a from anywhere in the image.
    #
    #    Seven lithtech.exe `gap` rows sit behind a C3 that is preceded by such
    #    an opcode; three of those seven are nonetheless GENUINE (0x0040a6a0
    #    and 0x0040a7b0 follow `75 01 c3` -- a real `jne +1 ; ret` where the 01
    #    is the jump displacement, not an `add` -- and 0x0042cc00 follows
    #    `8b 01 c3`, a real `mov eax,[ecx] ; ret`). So the preceding byte is
    #    not a discriminator in either direction.
    #
    #    Requiring the candidate to be 16-byte aligned or preceded by padding
    #    was measured too and is WORSE: it would drop 120 of lithtech.exe's 184
    #    `gap` rows and 36 of server.dll's 41, because a function often follows
    #    a `ret` immediately and server.dll has almost no inter-function
    #    padding at all.
    #
    #    The only sound fix is to accept a `ret` only at a real instruction
    #    boundary, which needs a linear disassembly this module does not have.
    #    Until then: treat an unaligned `gap` row as a suspect, and check the
    #    five bytes in front of it before spending a run on it.
    def looks_prologue(o):
        for p in PROLOGUES:
            if text[o : o + len(p)] == p:
                return True
        if text[o] in (0x53, 0x55, 0x56, 0x57) and text[o + 1] in (
                0x8B, 0x53, 0x55, 0x56, 0x57, 0x83, 0x33, 0x8A):
            return True
        return False

    o = 0
    while o < len(text) - 8:
        b = text[o]
        end = o + 1 if b == 0xC3 else (o + 3 if b == 0xC2 else None)
        if end is None:
            o += 1
            continue
        p = end
        while p < len(text) and text[p] in (0x90, 0xCC):
            p += 1
        if p < len(text) - 4 and (tlo + p) not in src and looks_prologue(p):
            src[tlo + p] = "gap"
        o = end

    return sorted(src), src


TAG = __import__("re").compile(r"^[A-Za-z_][A-Za-z0-9_]*::[A-Za-z_][A-Za-z0-9_]*$")


def tag_functions(img, starts):
    """Map function start -> the `Class::Method` string it pushes.

    The engine's argument checks end in a macro that reports the failing call
    by name (`RETURN_ERROR_PARAM("ILTPhysics::IntersectSegment")`), so the tag
    a function pushes *is* that function's name. server.dll has no symbols and
    no RTTI; this is the only naming information in the image.
    """
    import bisect

    text, tlo = img.text, img.tlo
    out = {}

    def tag_at(off):
        # `push imm32` — the literal itself
        if text[off] == 0x68:
            return img.cstr(struct.unpack_from("<I", text, off + 1)[0])
        # `push [imm32]` — a global char*. The shared client/server files use a
        # different error macro that holds the name in a variable rather than
        # passing the literal, so a third of the tags are only reachable this
        # way; without the indirection ILTModel and SharedCommonLT come out
        # almost entirely anonymous.
        if text[off] == 0xFF and text[off + 1] == 0x35:
            o = img.rva2off(struct.unpack_from("<I", text, off + 2)[0] - img.base)
            # rva2off can land past the end of the FILE: a section's virtual
            # size may exceed its raw size (d3d.ren's .data is 107,808 virtual
            # against a shorter tail on disk), and the dword this reads is a
            # pointer stored in that uninitialised part.
            if o is None or o + 4 > len(img.d):
                return None
            return img.cstr(struct.unpack_from("<I", img.d, o)[0])
        return None

    for off in range(len(text) - 6):
        s = tag_at(off)
        if not s or not TAG.match(s):
            continue
        i = bisect.bisect_right(starts, tlo + off) - 1
        if i >= 0:
            out.setdefault(starts[i], s)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    img = Image(args[0])
    starts, src = enumerate_functions(img)
    text, tlo, thi = img.text, img.tlo, img.thi

    # sizes = start -> next start, minus trailing padding
    sizes = {}
    for i, a in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else thi
        lo, hi = a - tlo, min(end - tlo, len(text))
        while hi > lo and text[hi - 1] in (0x90, 0xCC):
            hi -= 1
        sizes[a] = hi - lo

    covered = sum(sizes.values())
    from collections import Counter
    tally = Counter(src.values())
    print(f"{img.path}: .text {tlo:#x}-{thi:#x} ({thi-tlo} bytes)")
    print(f"functions enumerated : {len(starts)}")
    for k in ("call", "ptr", "cb", "setup", "init", "export", "gap"):
        if tally.get(k):
            print(f"   via {k:<7}: {tally[k]}")
    print(f"bytes in functions   : {covered} / {thi-tlo}  ({100*covered/(thi-tlo):.1f}%)")

    if "--csv" in sys.argv:
        out = sys.argv[sys.argv.index("--csv") + 1]
        exp = img.exports()
        tags = tag_functions(img, starts)
        with open(out, "w") as f:
            f.write("addr,size,source,name\n")
            for a in starts:
                f.write(f"0x{a:08x},{sizes[a]},{src[a]},{exp.get(a) or tags.get(a,'')}\n")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
