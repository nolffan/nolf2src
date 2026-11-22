#!/usr/bin/env python3
"""The install scripts of a game directory's public archive.

NOLF2's own copy of ext/tools/mkinstall.py, which read the disc images and
the installed retail game. This one reads neither: only the lists in
build/.

  build/mkinstall.py <gamedir> <outdir>

A game directory holds the retail game's data as well as what we built: the
.rez archives of the discs (with the retail game DLLs inside them zeroed),
the movies, and, as third-party runtime, RAD's binkw32.dll (legacy builds
only) and the Microsoft C++ and MFC DLLs (MANIFEST.txt's `data` and
`THIRD-PARTY` rows: build/retailextract.py). The public archive
(build/package.sh) leaves all of that out, and two scripts put it back from
the player's own copies of the two discs of No One Lives Forever 2 -- the
European or the USA release, as .iso images or as raw .bin/.cue images (or
a .zip of one), which the scripts convert to the .iso first. The 1.3
update's data ships with the release (assets/), so the scripts ask only for
the discs:

  linux-install.sh       bash, coreutils and python3 (its zlib inflates)
  windows-install.bat    cmd running the PowerShell it carries (5.1, as every
                         Windows 10 and 11 has; .NET's DeflateStream inflates)

Nothing is installed or run from the discs, and neither script reads ISO
9660 or an InstallShield header. An image is recognised by its size and
SHA-256, and then every byte the game needs is known; this writes it as a
list:

  D <id> <size> <sha256> <name>    a disc image (the .iso)
  R <id> <size>                    its raw .bin (2352-byte sectors)
  S <name> <id>...                 a set of images the game installs from:
                                   Europe, USA, USA with the other dump of
                                   its disc 2 (redump's "(Alt)")
  V <n> <size> <sha256> <name>     a retail file (as installed) ...
  W copy|is <id>:<offset>:<length>...
                                   ... and a way to read it: those byte
                                   ranges, joined, are the file (copy), or
                                   the InstallShield 6 cabinet data it is
                                   stored as (is: a run of chunks, each a
                                   16-bit length and a raw deflate stream
                                   of up to 32 KB). A file split across
                                   cabinets has one range in each. One W
                                   per set it differs in; the script takes
                                   the first whose images it has.
  F <path> <size> <sha256> <flag> <n>
                                   a file of the game directory, made from
                                   retail file <n> (`-`: from none, only
                                   L records) by, in order:
  C <length>                       its next bytes, as they are
  Z <length>                       zeros in place of its next bytes (the
                                   retail game DLLs blanked inside the .rez
                                   archives: build/all.sh's `resources`)
  L <base64>                       bytes of ours in place of its next ones
                                   (of a file from none: its bytes)
  E                                the end of the file: the script checks
                                   its size and SHA-256 before it moves it
                                   into place

A file's flag is `-`, or `once` for autoexec.cfg and Profiles/Default.prf:
the 1.3 update's shipped settings and default profile (assets/game/, in the
game directory as autoexec.cfg.retail and Default.prf.retail), which the
game rewrites. The archive does not carry them, so that a release unpacked
over an installed game keeps the player's; the scripts write them, from
our bytes, only if there are none. So the result is the game directory as
built, byte for byte. The list goes at the end of each script,
after a marker line; the scripts' code is build/game-scripts/linux-install.sh
and windows-install.ps1 (the .bat's header is written here).

The ranges come from two lists: build/retail-files.txt (each retail file's
size and SHA-256, and where its bytes are on the European and the USA
discs) and build/retail-ranges.txt (the zeroed DLLs in each archive, and
the archive's SHA-256 after that). A game directory built with the retail
game is checked against them: each file the scripts write must be in it as
they write it. One built without it (NODISCS=1: it has the file
NOT-PLAYABLE.txt) has no game data to check, and gives the same scripts.

Writes <outdir>/linux-install.sh, <outdir>/windows-install.bat,
<outdir>/disc-files.txt, the game directory's paths the scripts write (the
archive leaves them out), and <outdir>/disc-sums.txt, the SHA-256 of each of
those but the `once` files (build/package.sh puts them in the archive's
SHA256SUMS).
"""
import base64
import hashlib
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "build"))
import discs as disclist  # noqa: E402
import retailextract as rx  # noqa: E402

SCRIPTS = os.path.join(REPO, "build", "game-scripts")
TAG = "NOLF2"
MARKER = f"__{TAG}_INSTALL_DATA__"
CHUNK = 1 << 20
SECTOR = 2048
RAW_SECTOR = 2352
LITERAL_LINE = 3 * 1024          # raw bytes per L record (4 KB of base64)
LITERAL_MAX = 1 << 20            # more than this of ours means a wrong source
NODISCS_MARK = "NOT-PLAYABLE.txt"   # build/all.sh, NOLF2_NODISCS=1
# The settings the game rewrites: their shipped copies in the game
# directory (from assets/game/), and the file each starts.
SETTINGS = {"autoexec.cfg.retail": "autoexec.cfg",
            "Default.prf.retail": "Profiles/Default.prf"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


class Ops:
    def __init__(self):
        self.ops, self.literal = [], 0

    def add(self, kind, n, b=None):
        if n <= 0:
            return
        last = self.ops[-1] if self.ops else None
        if last and last[0] == kind:
            last[1] += n
            if b:
                last[2] += b
        else:
            self.ops.append([kind, n, bytearray(b or b"")])
        if kind == "L":
            self.literal += n

    def lines(self):
        for kind, n, b in self.ops:
            if kind == "L":
                b = bytes(b)
                for i in range(0, len(b), LITERAL_LINE):
                    yield "L " + base64.b64encode(b[i:i + LITERAL_LINE]).decode()
            else:
                yield f"{kind} {n}"


def retail_ops(f, ranges):
    """(ops, size, SHA-256) of the game directory's copy of a retail file:
    the whole file, or an archive with its game DLLs as zeros."""
    ops = Ops()
    if f.path not in ranges.zsum:
        ops.add("C", f.size)
        return ops, f.size, f.sha
    size, sha = ranges.zsum[f.path]
    if size != f.size:
        sys.exit(f"mkinstall: {f.path}: build/retail-ranges.txt and retail-files.txt "
                 "do not agree on its size")
    pos = 0
    for off, n, _entry in sorted(ranges.zero.get(f.path, [])):
        ops.add("C", off - pos)
        ops.add("Z", n)
        pos = off + n
    ops.add("C", f.size - pos)
    return ops, size, sha


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    game, outdir = sys.argv[1].rstrip("/"), sys.argv[2]
    nodiscs = os.path.isfile(os.path.join(game, NODISCS_MARK))
    lst = disclist.load("retail")
    ranges = rx.load_ranges()
    retail = {f.path.lower(): f for f in lst.files}

    # What in the game directory came from the discs, and from which file
    # (build/all.sh's MANIFEST.txt).
    wanted = {}                           # game path -> File
    for line in open(os.path.join(game, "MANIFEST.txt")):
        line = line.rstrip("\n")
        if line.startswith("#") or "\t" not in line:
            continue
        frm, rel = line.split("\t", 1)
        m = re.match(r"(data|THIRD-PARTY) ([^:]+):(.+?)( \(.*\))?$", frm)
        if not m:
            continue
        if m.group(2) != rx.RETAIL_RELEASE:
            sys.exit(f"mkinstall: {rel} came from {m.group(2)}, not {rx.RETAIL_RELEASE}")
        f = retail.get(m.group(3).lower())
        if f is None:
            sys.exit(f"mkinstall: {rel}: {m.group(3)} is not in build/retail-files.txt")
        wanted[rel] = f
    for rel in list(wanted) + [f.path for f in wanted.values()]:
        if re.search(r"[\s\"'`$\\%!]", rel):
            sys.exit(f"mkinstall: {rel}: a name the scripts do not quote")

    # Each retail file, and the ways to read it from the discs (not the
    # update's: what the game directory takes from it ships in assets/).
    disc_ids = set(lst.discs)
    sources, vlines, used = {}, [], set()
    for f in sorted({id(f): f for f in wanted.values()}.values(), key=lambda f: f.path.lower()):
        ways = [(k, r) for k, r in f.ways if all(i in disc_ids for i, _o, _n in r)]
        if not ways:
            sys.exit(f"mkinstall: {f.path}: on none of the discs (build/retail-files.txt)")
        n = len(sources) + 1
        sources[f.path] = n
        vlines.append(f"V {n} {f.size} {f.sha} {f.path}")
        for kind, r in ways:
            vlines.append(f"W {kind} " + " ".join(f"{i}:{o}:{c}" for i, o, c in r))
            used.update(i for i, _o, _c in r)

    records, sums, literal, wanted_once = [], [], 0, []
    for rel in sorted(wanted, key=str.lower):
        f = wanted[rel]
        ops, size, sha = retail_ops(f, ranges)
        path = os.path.join(game, rel)
        if not nodiscs and (not os.path.isfile(path) or os.path.getsize(path) != size
                            or sha256(path) != sha):
            sys.exit(f"mkinstall: {rel} in {game} is not what the scripts would write "
                     "(build/retail-files.txt, build/retail-ranges.txt)")
        literal += ops.literal
        records.append(f"F {rel} {size} {sha} - {sources[f.path]}")
        sums.append(f"{sha}  {rel}")
        records.extend(ops.lines())
        records.append("E")
    # The shipped settings and default profile (assets/game/, the 1.3
    # update's): the game rewrites both, so the archive does not carry them
    # -- a release unpacked over an installed game keeps the player's -- and
    # the scripts write them only if there are none, from these bytes of
    # ours (L records, from no retail file: source "-").
    for copy, live in SETTINGS.items():
        data = open(os.path.join(game, copy), "rb").read()
        ops = Ops()
        ops.add("L", len(data), data)
        literal += ops.literal
        records.append(f"F {live} {len(data)} {hashlib.sha256(data).hexdigest()} once -")
        records.extend(ops.lines())
        records.append("E")
        wanted_once.append(live)
    if literal > LITERAL_MAX:
        sys.exit(f"mkinstall: {literal} bytes would ship as literal data")

    data = [f"{TAG}INSTALL 2"]
    for i, d in lst.discs.items():
        if i in used:
            data.append(f"D {i} {d.size} {d.sha} {d.name}")
            data.append(f"R {i} {d.size // SECTOR * RAW_SECTOR}")
    for name, ids in lst.sets:
        if all(i in used for i in ids):
            data.append(f"S {name} {' '.join(ids)}")
    data += vlines + records

    os.makedirs(outdir, exist_ok=True)
    body = open(os.path.join(SCRIPTS, "linux-install.sh")).read()
    with open(os.path.join(outdir, "linux-install.sh"), "w", newline="\n") as fh:
        fh.write(body + MARKER + "\n" + "\n".join(data) + "\n")
    os.chmod(os.path.join(outdir, "linux-install.sh"), 0o755)

    ps = open(os.path.join(SCRIPTS, "windows-install.ps1")).read()
    psm = f"#__{TAG}_PS__"
    if not ps.isascii() or psm in ps or MARKER in ps:
        sys.exit("mkinstall: windows-install.ps1 must be ASCII, without the markers")
    bat = BAT_HEADER + [psm] + ps.splitlines() + [psm, MARKER] + data
    with open(os.path.join(outdir, "windows-install.bat"), "w", newline="\r\n") as fh:
        fh.write("\n".join(bat) + "\n")

    with open(os.path.join(outdir, "disc-files.txt"), "w") as fh:
        for rel in sorted(list(wanted) + wanted_once, key=str.lower):
            fh.write(rel + "\n")
    with open(os.path.join(outdir, "disc-sums.txt"), "w", newline="\n") as fh:
        fh.write("".join(line + "\n" for line in sums))
    print(f"   install scripts: {len(wanted)} files from {len(sources)} retail files "
          f"on the discs, {literal} bytes of ours")


# cmd runs this; everything from the first #__NOLF2_PS__ line on is never
# parsed by it (`exit /b` comes first). The PowerShell between the markers is
# written to a temporary .ps1 and run with -File, which passes the dropped or
# typed paths through as they are.
BAT_HEADER = r"""@echo off
rem windows-install.bat -- install the game data from your NOLF2 discs.
rem
rem   Drop the images of both discs of No One Lives Forever 2 (the European
rem   or the USA release) onto this file -- or put them in this folder or
rem   the one above it and double-click it. Then start the game with
rem   NOLF2.exe. (The 1.3 update's data comes with the release.) An image is
rem   a plain .iso, a raw .bin (or its .cue), or a .zip of one; a .bin or
rem   .zip is first converted to a temporary .iso in this folder (about
rem   0.6 GB a disc, removed at the end).
rem
rem First it checks that this folder is the release unpacked and nothing
rem else (SHA256SUMS: not copied over another installation or an older
rem release). It checks each file's SHA-256, copies the game's data out of them into
rem this folder and checks every file it writes. Nothing is installed or run
rem from them. In the legacy build it then registers the game as the
rem original installer did (the registry values the retail launcher reads:
rem this folder, the 1.3 update's data): for all users when run as an
rem administrator, else for this Windows user. The modern build's launcher
rem needs no registry.
setlocal
set "NOLF2_SELF=%~f0"
set "NOLF2_PS1=%TEMP%\nolf2-install-%RANDOM%%RANDOM%.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:NOLF2_SELF); $m='#'+'__NOLF2_PS__'; $a=$t.IndexOf($m); $b=$t.IndexOf($m,$a+1); [IO.File]::WriteAllText($env:NOLF2_PS1,$t.Substring($a,$b-$a))"
if errorlevel 1 goto failed
powershell -NoProfile -ExecutionPolicy Bypass -File "%NOLF2_PS1%" "%~f0" %*
set "NOLF2_RC=%errorlevel%"
del "%NOLF2_PS1%" 2>nul
pause
exit /b %NOLF2_RC%
:failed
echo Could not start PowerShell.
pause
exit /b 1""".splitlines()

if __name__ == "__main__":
    main()
