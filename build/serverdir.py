#!/usr/bin/env python3
"""The committed ServerDir.dll, for a build without the LithTech Jupiter SDK.

  build/serverdir.py write              assets/serverdir/, from the last make
  build/serverdir.py check <built dll>  fail unless the compiled ServerDir.dll
                                        is the committed one (but its link time)
  build/serverdir.py install <built dll>
                                        the committed one where the compile
                                        puts its own

ServerDir.dll is built from Monolith's CServerDir_Titan
(src/Game/Libs/ServerDir/) and the WONAPI library of the LithTech Jupiter
SDK, whose source is not in this repository: build/discs.py installs it
from your image of the SDK's CD (build/jupiter.sh, ext/tools/jupitersrc.py).
A build without the SDK (NODISCS=1, as CI builds) cannot compile it. So
assets/serverdir/ holds the release build's ServerDir.dll and its link map,
as `make` built them, and that build uses them:

`write` (make serverdir) copies them from the release build's output,
src/Game/built/Final/libs/ServerDir/, into assets/serverdir/. It refuses a
ServerDir.dll that the compile did not make (one that `install` put
there: it has no command file, ServerDir.dll.cmd, beside it).

`check` (build/all.sh, step 3, in every release build with the SDK) fails
unless the compiled ServerDir.dll is the committed one but for the time of
the link: the TimeDateStamp of its COFF header, of its export directory and
of its debug directory entries, and the image checksum. For the link map,
the line with the time.

`install` (build/all.sh, step 2b, in a build without the SDK) copies the
committed ServerDir.dll and ServerDir.map to where the compile puts its own,
for step 4 and for make progress-ci, and removes the compile's command file
there, so that a later build with the SDK compiles ServerDir.dll again
(build/build.mk rebuilds an output whose command file is missing).
"""
import os
import shutil
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(REPO, "assets", "serverdir")
BUILT = os.path.join(REPO, "src", "Game", "built", "Final", "libs", "ServerDir", "ServerDir.dll")


def normal_dll(data):
    """The image with its link time and checksum as zeros."""
    b = bytearray(data)
    pe = struct.unpack_from("<I", b, 0x3C)[0]
    if b[pe:pe + 4] != b"PE\0\0":
        sys.exit("serverdir: not a PE image")
    struct.pack_into("<I", b, pe + 8, 0)                  # COFF TimeDateStamp
    opt = pe + 24
    struct.pack_into("<I", b, opt + 64, 0)                # CheckSum
    nsec = struct.unpack_from("<H", b, pe + 6)[0]
    optsz = struct.unpack_from("<H", b, pe + 20)[0]
    secs = []
    for i in range(nsec):
        o = opt + optsz + 40 * i
        vsz, va, rawsz, raw = struct.unpack_from("<IIII", b, o + 8)
        secs.append((va, max(vsz, rawsz), raw))

    def off(rva):
        for va, sz, raw in secs:
            if va <= rva < va + sz:
                return raw + rva - va
        return None

    exp_rva = struct.unpack_from("<I", b, opt + 96)[0]
    if exp_rva and off(exp_rva) is not None:
        struct.pack_into("<I", b, off(exp_rva) + 4, 0)    # export TimeDateStamp
    dbg_rva, dbg_size = struct.unpack_from("<II", b, opt + 96 + 6 * 8)
    if dbg_rva and off(dbg_rva) is not None:
        for i in range(dbg_size // 28):
            struct.pack_into("<I", b, off(dbg_rva) + 28 * i + 4, 0)
    return bytes(b)


def normal_map(text):
    return [line for line in text.splitlines() if "Timestamp is" not in line]


def pair(dll):
    return dll, os.path.splitext(dll)[0] + ".map"


def main():
    a = sys.argv[1:]
    if a == ["write"]:
        dll, mp = pair(BUILT)
        if not os.path.isfile(dll + ".cmd"):
            sys.exit(f"serverdir: {os.path.relpath(dll, REPO)} was not compiled here "
                     "(no .cmd beside it): build it with the SDK first (make)")
        os.makedirs(ASSETS, exist_ok=True)
        for f in (dll, mp):
            shutil.copyfile(f, os.path.join(ASSETS, os.path.basename(f)))
        print(f"== {os.path.relpath(os.path.dirname(dll), REPO)}/ServerDir.dll, ServerDir.map "
              "-> assets/serverdir/")
    elif len(a) == 2 and a[0] == "check":
        dll, mp = pair(a[1])
        cdll, cmp_ = pair(os.path.join(ASSETS, "ServerDir.dll"))
        same = normal_dll(open(dll, "rb").read()) == normal_dll(open(cdll, "rb").read()) and \
            normal_map(open(mp, errors="replace").read()) == normal_map(open(cmp_, errors="replace").read())
        if not same:
            sys.exit("serverdir: the compiled ServerDir.dll is not assets/serverdir/'s, which a "
                     "build without the SDK uses -- write it again: make serverdir")
        print("== ServerDir.dll: the committed one (assets/serverdir/), but the link time")
    elif len(a) == 2 and a[0] == "install":
        dll, mp = pair(a[1])
        os.makedirs(os.path.dirname(dll), exist_ok=True)
        for src, dest in zip(pair(os.path.join(ASSETS, "ServerDir.dll")), (dll, mp)):
            shutil.copyfile(src, dest)
        for stale in (dll + ".cmd", os.path.splitext(dll)[0] + ".lib.cmd"):
            if os.path.exists(stale):
                os.unlink(stale)
        print(f"   {os.path.relpath(dll, REPO)}, ServerDir.map  <-  assets/serverdir/")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
