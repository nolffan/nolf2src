#!/usr/bin/env python3
"""Compare the resource trees of two PE32 binaries.

Walks both .rsrc directories and compares each resource's data bytes
(keyed by type/name/language), ignoring the physical layout of the
section — the per-resource payload is what the loader hands out, so
byte-equal payloads mean identical runtime behavior.

Usage: rsrcdiff.py <ours.dll> <theirs.dll>
"""
import struct
import sys


def resources(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    so = pe + 24 + optsz
    rsrc = None
    for i in range(nsec):
        s = so + i * 40
        name = d[s : s + 8].rstrip(b"\0")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, s + 8)
        if name == b".rsrc":
            rsrc = (va, rp)
    if not rsrc:
        return {}
    va, rp = rsrc

    out = {}

    def walk(off, path_):
        _ch, _ts, _maj, _min, nnamed, nid = struct.unpack_from("<IIHHHH", d, rp + off)
        for i in range(nnamed + nid):
            e = rp + off + 16 + i * 8
            name, data = struct.unpack_from("<II", d, e)
            if name & 0x80000000:
                noff = name & 0x7FFFFFFF
                ln = struct.unpack_from("<H", d, rp + noff)[0]
                nm = d[rp + noff + 2 : rp + noff + 2 + ln * 2].decode("utf-16le")
            else:
                nm = name
            if data & 0x80000000:
                walk(data & 0x7FFFFFFF, path_ + (nm,))
            else:
                drva, dsz, _cp = struct.unpack_from("<III", d, rp + (data & 0x7FFFFFFF))
                out[path_ + (nm,)] = d[rp + (drva - va) : rp + (drva - va) + dsz]

    walk(0, ())
    return out


def main():
    a, b = resources(sys.argv[1]), resources(sys.argv[2])
    keys = sorted(set(a) | set(b), key=str)
    same = 0
    for k in keys:
        if k not in a:
            print(f"  MISSING in ours:  {k}")
        elif k not in b:
            print(f"  EXTRA in ours:    {k}")
        elif a[k] != b[k]:
            print(f"  DIFFERS:          {k}  ({len(a[k])} vs {len(b[k])} bytes)")
            x, y = a[k], b[k]
            for i in range(min(len(x), len(y))):
                if x[i] != y[i]:
                    print(f"    first diff at +0x{i:x}: {x[i]:02x} vs {y[i]:02x}")
                    break
        else:
            same += 1
    print(f"resources: {same}/{len(keys)} byte-identical")


if __name__ == "__main__":
    main()
