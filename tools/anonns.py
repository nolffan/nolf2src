#!/usr/bin/env python3
"""Pin the names VC6 gives anonymous namespaces in a COFF object.

VC6 names an anonymous namespace `?%<source as spelled><number>`, and the
number is different on every compile (it is not derived from the source:
the same file compiled twice in a row gets two numbers, 8 to 10 digits).
The name is part of every symbol declared in the namespace, so its length
moves where the linker puts things: WONAPI's three anonymous namespaces
(QueueSocket.cpp, CDKey.cpp, CRC.cpp) decide whether six functions of
ServerDir.dll come out byte-identical to retail. A build that is scored
has to be reproducible, so the library build (build/build.mk, `library`)
rewrites each such number, for the libraries PINNED_LIBS names, to a fixed
one: the numbers of the WONAPI.lib the recorded score
(progress/identical.txt) was measured on, and for any other source a
number derived from its name.

Only the object's string table changes (the long symbol and section
names); the code and data are not touched. A name found anywhere else in
the object (a type name in RTTI data, a debug record) would change length
there too, so the tool refuses such an object rather than half-pin it.

  tools/anonns.py <object>...       rewrite in place (no change: not written)
"""
import re
import struct
import sys
import zlib

# the numbers in the WONAPI.lib progress/identical.txt was recorded from
FIXED = {
    rb".\WONAuth\CDKey.cpp": b"503414755",
    rb".\WONCommon\CRC.cpp": b"3249328598",
    rb".\WONSocket\QueueSocket.cpp": b"1557412994",
}

ANON = re.compile(rb"\?%([^@?]*?\.(?:cpp|c|cxx))(\d+)", re.I)


def pinned(m):
    src = m.group(1)
    num = FIXED.get(src)
    if num is None:
        num = b"%d" % (100000000 + zlib.crc32(src.lower()) % 900000000)
    return b"?%" + src + num


def pin_sections(path, data):
    """The names in section data: the RTTI type names (".?AV<class>@?%...@@")
    of classes in an anonymous namespace. Each is the end of its own small
    COMDAT section, so the section grows or shrinks by the difference, and
    every file offset after it moves."""
    changed = False
    while True:
        machine, nsect, _, symptr, nsym = struct.unpack_from("<HHIII", data, 0)
        opt = struct.unpack_from("<H", data, 16)[0]
        edit = None
        for m in ANON.finditer(bytes(data[:symptr])):
            if m.group(0) != pinned(m):
                edit = m
        if edit is None:
            return changed
        p, delta = edit.start(), len(pinned(edit)) - len(edit.group(0))
        owner = None
        for i in range(nsect):
            h = 20 + opt + 40 * i
            size, raw, rel, lines, nrel = struct.unpack_from("<IIIIH", data, h + 16)
            if raw <= p < raw + size:
                owner = i
                for r in range(nrel):
                    va = struct.unpack_from("<I", data, rel + 10 * r)[0]
                    if va > p - raw:
                        sys.exit(f"anonns: {path}: a relocation after a pinned name")
                size += delta
            raw += delta if raw > p else 0
            rel += delta if rel > p else 0
            lines += delta if lines > p else 0
            struct.pack_into("<IIII", data, h + 16, size, raw, rel, lines)
        if owner is None:
            sys.exit(f"anonns: {path}: an anonymous-namespace name outside the sections")
        symptr += delta
        struct.pack_into("<I", data, 8, symptr)
        data[p:edit.end()] = pinned(edit)
        # the section's definition symbol: its auxiliary record has the length
        i = 0
        while i < nsym:
            off = symptr + 18 * i
            sect, typ, cls, naux = struct.unpack_from("<hHBB", data, off + 12)
            if sect == owner + 1 and cls == 3 and naux and \
                    struct.unpack_from("<I", data, off + 8)[0] == 0:
                ln = struct.unpack_from("<I", data, off + 18)[0]
                struct.pack_into("<I", data, off + 18, ln + delta)
            i += 1 + naux
        changed = True


def pin(path):
    data = bytearray(open(path, "rb").read())
    machine, nsect, _, symptr, nsym = struct.unpack_from("<HHIII", data, 0)
    if machine != 0x14C or symptr == 0:
        return False                      # not an i386 COFF object
    changed = pin_sections(path, data)
    machine, nsect, _, symptr, nsym = struct.unpack_from("<HHIII", data, 0)
    strtab = symptr + 18 * nsym
    (strsize,) = struct.unpack_from("<I", data, strtab)
    if strtab + strsize != len(data):
        sys.exit(f"anonns: {path}: the string table is not at the end")
    old = bytes(data[strtab + 4:strtab + strsize])
    if not ANON.search(old):
        if changed:
            open(path, "wb").write(data)
        return changed
    # rebuild the string table, string by string, keeping the order; a name
    # may be the tail of another's string (the compiler shares them)
    spans, new, pos = [], bytearray(), 0
    while pos < len(old):
        end = old.index(b"\0", pos)
        s = ANON.sub(pinned, old[pos:end])
        spans.append((pos + 4, end + 4, len(new) + 4, s))
        new += s + b"\0"
        pos = end + 1
    if bytes(new) == old:
        if changed:
            open(path, "wb").write(data)
        return changed

    def moved(soff):
        for a, b, n, s in spans:
            if a <= soff <= b:
                tail = ANON.sub(pinned, old[soff - 4:b - 4])
                if not s.endswith(tail):
                    sys.exit(f"anonns: {path}: a name starts inside a pinned number")
                return n + len(s) - len(tail)
        sys.exit(f"anonns: {path}: a name outside the string table")
    # the symbols' long names (a symbol's auxiliary records follow it, and
    # are not names)
    i = 0
    while i < nsym:
        off = symptr + 18 * i
        zero, soff = struct.unpack_from("<II", data, off)
        if zero == 0:
            struct.pack_into("<I", data, off + 4, moved(soff))
        i += 1 + data[off + 17]
    # the sections' long names ("/<offset>")
    opt = struct.unpack_from("<H", data, 16)[0]
    for i in range(nsect):
        off = 20 + opt + 40 * i
        name = bytes(data[off:off + 8]).rstrip(b"\0")
        if name.startswith(b"/") and name[1:].isdigit():
            data[off:off + 8] = (b"/%d" % moved(int(name[1:]))).ljust(8, b"\0")
    data[strtab:] = struct.pack("<I", len(new) + 4) + new
    open(path, "wb").write(data)
    return True


if __name__ == "__main__":
    for p in sys.argv[1:]:
        if pin(p):
            print(f"anonns: {p}: anonymous namespaces pinned")
