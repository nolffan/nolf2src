#!/usr/bin/env python3
"""Decode the MSVC "Rich" header: which tools built a PE, and how much of it.

Between the DOS stub and the PE signature, link.exe leaves an XOR-obfuscated
record of every tool that contributed to the image, as (product id, build
number, object count) triples. For a reconstruction project this is the
ground truth for "which toolchain do we need" — it names the exact compiler
and linker builds, not just the marketing service-pack level.

Usage: richhdr.py <image.exe|dll> [...]
"""
import struct
import sys

# Product ids: the names are those of Microsoft's own list (prodid values
# as published by the Rich-header research: Linker600, Utc12_CPP, ...);
# what each means in this project's images is checked where it says
# "here". progress/COMPILERS.md has the evidence.
PRODUCT = {
    # objects with no @comp.id at all: here, every Intel C/C++ object (icl
    # 4.0, 4.5, 5.0.1, 6.0, 8.0 and 9.0 all emit none) and the eight
    # unmarked members of the DirectX 8.1 SDK's d3dx8.lib; any compiler
    # older than the symbol (VC5 and before) too
    0x00: "object without @comp.id (Intel C/C++, pre-VC6, ...)",
    0x01: "import (Import0: one per imported function)",
    0x02: "linker 5.10 (Linker510)",
    0x03: "cvtomf 5.10",
    # link/lib 6.00: import-library descriptors (msvcrt.lib's and
    # msvcprt.lib's are 0x04/8047 here) and the exports objects of DLLs
    0x04: "link/lib 6.00 (Linker600): import descriptors, exports",
    0x05: "cvtomf 6.00",
    # cvtres 5.00.1735, VC6's: the one .res object of an image with
    # resources (CRes.dll and SRes.dll have one and nothing else of the
    # kind). Not MASM, as this table once said.
    0x06: "cvtres 5.00 (Cvtres500): the resources",
    0x07: "Basic 11",
    0x08: "cl 11.00 (VC5) C",
    0x09: "Basic 12",
    0x0a: "cl 12.00 (VC6) C",
    0x0b: "cl 12.00 (VC6) C++",
    # 0x0c/7291 and 0x0e/7299 come in with VC6's own libraries: libcmt.lib
    # has 73 members of 0x0e/7299, its assembly files (ml 6.13.7299)
    0x0c: "AliasObj 6.0 (VC6 libraries)",
    0x0d: "Visual Basic 6",
    0x0e: "masm 6.13 (Masm613; VC6's CRT assembly)",
    0x0f: "masm 7.10",
    0x10: "linker 5.11",
    0x11: "cvtomf 5.11",
    # ml 6.14.8444: here, the one assembly member of d3dx8.lib
    0x12: "masm 6.14 (Masm614)",
    # lib 5.12.8034: here, the import libraries of VC6's Platform SDK
    # (kernel32.lib, user32.lib, ...)
    0x13: "linker 5.12 (Linker512): import libraries",
    0x14: "cvtomf 5.12",
    0x15: "cl 12.00 C (Standard)",
    0x16: "cl 12.00 C++ (Standard)",
    0x17: "cl 12.00 C (Learning)",
    0x18: "cl 12.00 C++ (Learning)",
    # lib 7.00.9210: here, the import descriptors of the DirectX 8.1 SDK's
    # import libraries (dinput8.lib, ...)
    0x19: "implib 7.00 (Implib700): import descriptors",
    0x1a: "cvtomf 7.00",
    0x1b: "Basic 13",
    # cl 13.00 (the VC .NET 2002 generation), build 9178: here, the DirectX
    # 8.1 SDK's static libraries -- d3dx8.lib (C++, 133 members), dxguid.lib,
    # dinput8.lib's data formats (C) -- which Lithtech.exe and snddrv.dll
    # link
    0x1c: "cl 13.00 C (Utc13_C)",
    0x1d: "cl 13.00 C++ (Utc13_CPP)",
}


def rich(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    blob = d[:pe]
    i = blob.rfind(b"Rich")
    if i < 0:
        return None
    key = struct.unpack_from("<I", blob, i + 4)[0]
    # walk back to the "DanS" marker, which is 0x536E6144 ^ key
    j = i
    dans = struct.pack("<I", 0x536E6144 ^ key)
    start = blob.rfind(dans, 0, i)
    if start < 0:
        return None
    out = []
    for o in range(start + 16, i, 8):
        v, cnt = struct.unpack_from("<II", blob, o)
        v ^= key
        cnt ^= key
        out.append((v >> 16, v & 0xFFFF, cnt))
    return out


def main():
    for p in sys.argv[1:]:
        print(p)
        r = rich(p)
        if r is None:
            print("   no Rich header")
            continue
        for pid, build, cnt in r:
            print(f"   id 0x{pid:02x}  build {build:<6} x{cnt:<4} "
                  f"{PRODUCT.get(pid, '?')}")


if __name__ == "__main__":
    main()
