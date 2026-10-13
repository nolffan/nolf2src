#!/usr/bin/env python3
"""Put the source the release lacks into src/, from the LithTech Jupiter SDK.

  tools/jupitersrc.py <sdk-source> <src>

<sdk-source> is the SDK's "Source Code" file group as rez/ installs it
(rez/sdk/lithtech-jupiter-51/, checked against rez/sdk.sha256: see
build/jupiter.sh): the game code and libraries as Monolith gave them
to engine licensees in March 2002, laid out as the source release is
(Game/, Engine/, Libs/).

Monolith's release has ServerDir.dll's headers and import library only.
The SDK has its source: WONAPI (Game/Libs/WONAPI/, the WON/Titan client
library, the version retail ServerDir.dll is built from) and an earlier
CServerDir_Titan (Game/Libs/ServerDir/). This copies them into
<src>/Game/Libs/ as the release's own files are kept -- text with LF line
endings -- and applies the patches in src/nolf2src/jupiter/ (in name
order, `patch -p1` from the SDK's root, no fuzz), which bring the 2002
code to the 1.3 interface. Nothing of the SDK is committed: .gitignore
lists every path written here.

Not copied: the SDK's IServerDir.h (src/ has the 1.3 one) and ServerDir.dsp
(a static library; src/Game/Libs/ServerDir/ServerDir.dsp builds the DLL).

A file is written only when its content changes, so a rebuild redoes
nothing; a file of WONAPI/ that the SDK does not have is removed.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PATCHES = os.path.join(HERE, "..", "src", "nolf2src", "jupiter")

# (directory, files): every file of the directory when files is None
WANTED = [
    ("Game/Libs/WONAPI", None),
    ("Game/Libs/ServerDir", ["CServerDir_Titan.cpp", "CServerDir_Titan.h", "TitanTest.cpp",
                             "TitanTest.h", "WinSync.h", "stdafx.cpp", "stdafx.h"]),
]


def lf(data):
    """Text (no NUL byte) with LF line endings; anything else unchanged."""
    return data if b"\0" in data else data.replace(b"\r\n", b"\n")


def write_if_changed(path, data):
    try:
        with open(path, "rb") as f:
            if f.read() == data:
                return False
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # a new file renamed over the old one, never a write through it: the
    # old one may be a hard link shared with another worktree
    # (tools/agentwt.sh), whose copy must not change with ours
    tmp = path + ".jupitersrc-tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return True


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sdk, src = sys.argv[1], sys.argv[2]
    if not os.path.isfile(os.path.join(sdk, "Game", "Libs", "WONAPI", "WONAPI.dsp")):
        sys.exit(f"jupitersrc: {sdk} is not the SDK's source (rez/install-games.sh lithtech-jupiter-51 installs it)")
    with tempfile.TemporaryDirectory(prefix="jupitersrc.") as stage:
        rels = []
        for d, names in WANTED:
            if names is None:
                names = [os.path.relpath(os.path.join(r, f), os.path.join(sdk, d))
                         for r, _, fs in os.walk(os.path.join(sdk, d)) for f in fs]
            for n in sorted(names):
                rel = f"{d}/{n}"
                with open(os.path.join(sdk, rel), "rb") as f:
                    data = lf(f.read())
                os.makedirs(os.path.dirname(os.path.join(stage, rel)), exist_ok=True)
                with open(os.path.join(stage, rel), "wb") as f:
                    f.write(data)
                rels.append(rel)
        for p in sorted(os.listdir(PATCHES)):
            if not p.endswith(".patch"):
                continue
            with open(os.path.join(PATCHES, p), "rb") as f:
                r = subprocess.run(["patch", "-s", "-p1", "-F0", "--no-backup-if-mismatch", "-d", stage],
                                   stdin=f, capture_output=True, text=True)
            if r.returncode:
                sys.exit(f"jupitersrc: src/nolf2src/jupiter/{p} does not apply:\n{r.stdout}{r.stderr}")
        n = 0
        for rel in rels:
            with open(os.path.join(stage, rel), "rb") as f:
                n += write_if_changed(os.path.join(src, rel), f.read())
    # what WONAPI/ had and the SDK has not
    want = {r.lower() for r in rels}
    top = os.path.join(src, "Game", "Libs", "WONAPI")
    for r, _, fs in os.walk(top):
        for f in fs:
            p = os.path.join(r, f)
            if os.path.relpath(p, src).replace(os.sep, "/").lower() not in want:
                os.remove(p)
                n += 1
    print(f"jupitersrc: {len(rels)} files from the SDK in {src}/Game/Libs/ ({n} written or removed)")


if __name__ == "__main__":
    main()
