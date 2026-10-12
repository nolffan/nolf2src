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

# product ids seen in VC6-era images
PRODUCT = {
    0x00: "unmarked (linker-generated)",
    0x01: "import object",
    0x02: "linker (older)",
    0x03: "cvtomf / cvtres",
    0x04: "linker",
    0x05: "cvtomf",
    0x06: "masm (ml)",
    # 0x0c/0x0e at builds 7291/7299 are in EVERY Monolith image here and they
    # are NOT a barrier: server.dll carries 43 of them and is 65%
    # byte-identical, against lithtech.exe's 39. Reading the ~7xxx builds as
    # "VC5 objects that will never reproduce under our VC6" is wrong; the
    # per-image counts refute that outright. They come in with the statically
    # linked libraries, which this project already excludes from its
    # denominators, so a block that will not reproduce needs a different
    # explanation. (The standard published table calls 0x0c AliasObj60 and
    # 0x0e Masm613; neither is confirmed here, hence the label.)
    0x0c: "prebuilt library object (not a barrier — see comment)",
    0x0e: "prebuilt library object (not a barrier — see comment)",
    0x0a: "cl (C)",
    0x0b: "cl (C++)",
    0x0f: "cvtres",
    0x13: "linker (LTCG)",
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
