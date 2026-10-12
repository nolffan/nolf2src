#!/usr/bin/env python3
"""Minimal Monolith REZ v1 archive reader/extractor. No dependencies.

Usage:
  rezextract.py list <file.rez> [filter]
  rezextract.py x    <file.rez> <outdir> [filter]

File entries get their extension restored from the 4-byte reversed type tag
(e.g. tag "LLD" -> ".dll"). Filter is a case-insensitive substring match.
"""
import struct
import sys
from pathlib import Path

HDR_TEXT = 127  # 2 + 60 + 2 + 60 + 2 + 1 (two title lines + CR/LFs + 0x1A)


class Rez:
    def __init__(self, path):
        # a path, or an open binary file positioned anywhere (it is read
        # from offset 0 of whatever it presents)
        self.f = path if hasattr(path, "read") else open(path, "rb")
        self.f.seek(0)
        hdr = self.f.read(HDR_TEXT)
        if b"RezMgr" not in hdr:
            raise RuntimeError("not a RezMgr file")
        (self.version, self.rootpos, self.rootsize) = struct.unpack(
            "<3I", self.f.read(12)
        )
        if self.version != 1:
            raise RuntimeError(f"unsupported REZ version {self.version}")

    def _read_cstr(self, data, off):
        end = data.index(b"\0", off)
        return data[off:end].decode("latin-1"), end + 1

    def walk(self, pos=None, size=None, prefix=""):
        """Yield (path, extent-pos, size) for all file entries."""
        if pos is None:
            pos, size = self.rootpos, self.rootsize
        self.f.seek(pos)
        data = self.f.read(size)
        off = 0
        dirs = []
        while off + 4 <= len(data):
            (etype,) = struct.unpack_from("<I", data, off)
            off += 4
            if etype == 1:  # directory
                dpos, dsize, _t = struct.unpack_from("<3I", data, off)
                off += 12
                name, off = self._read_cstr(data, off)
                dirs.append((name, dpos, dsize))
            else:  # file
                fpos, fsize, _t, _id = struct.unpack_from("<4I", data, off)
                off += 16
                tag = data[off : off + 4]
                off += 4
                (numkeys,) = struct.unpack_from("<I", data, off)
                off += 4
                name, off = self._read_cstr(data, off)
                off += 1  # trailing pad byte after file name
                off += 4 * numkeys
                ext = tag.rstrip(b"\0")[::-1].decode("latin-1").lower()
                fname = f"{name}.{ext}" if ext else name
                yield f"{prefix}{fname}", fpos, fsize
        for name, dpos, dsize in dirs:
            yield from self.walk(dpos, dsize, f"{prefix}{name}/")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    rez = Rez(path)
    if cmd == "list":
        want = sys.argv[3].lower() if len(sys.argv) > 3 else ""
        for p, _, sz in rez.walk():
            if want in p.lower():
                print(f"{sz:>12} {p}")
    elif cmd == "x":
        outdir = Path(sys.argv[3])
        want = sys.argv[4].lower() if len(sys.argv) > 4 else ""
        n = 0
        for p, pos, sz in rez.walk():
            if want not in p.lower():
                continue
            dest = outdir / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            rez.f.seek(pos)
            dest.write_bytes(rez.f.read(sz))
            n += 1
        print(f"extracted {n} files to {outdir}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
