#!/usr/bin/env python3
"""Extract object members from an MS COFF .lib (ar) archive.

Usage: libextract.py <lib> <outdir>

Handles the MS long-name table ("//" member) and flattens any path
prefixes in member names (e.g. "./Release/foo.obj" -> "foo.obj").
"""
import os
import sys


def extract(libpath, outdir):
    data = open(libpath, "rb").read()
    assert data[:8] == b"!<arch>\n", "not an ar archive"
    os.makedirs(outdir, exist_ok=True)
    longnames = b""
    off = 8
    n = 0
    while off + 60 <= len(data):
        hdr = data[off : off + 60]
        name = hdr[0:16].decode("latin-1").rstrip()
        size = int(hdr[48:58].decode().strip() or "0")
        body = data[off + 60 : off + 60 + size]
        if name == "//":
            longnames = body
        elif name.startswith("/") and name[1:].isdigit():
            ln_off = int(name[1:])
            # MS .lib long names are NUL-terminated; GNU uses newline
            end = longnames.find(b"\x00", ln_off)
            if end < 0:
                end = longnames.find(b"\n", ln_off)
            real = longnames[ln_off:end].decode("latin-1").rstrip("/").rstrip("\\")
            _write(outdir, real, body)
            n += 1
        elif name not in ("/", ""):
            _write(outdir, name.rstrip("/"), body)
            n += 1
        off += 60 + size + (size & 1)
    return n


def _write(outdir, member, body):
    base = member.replace("\\", "/").rsplit("/", 1)[-1]
    with open(os.path.join(outdir, base), "wb") as f:
        f.write(body)


if __name__ == "__main__":
    n = extract(sys.argv[1], sys.argv[2])
    print(f"extracted {n} members to {sys.argv[2]}")
