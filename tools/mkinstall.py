#!/usr/bin/env python3
"""The install scripts of a game directory's public archive.

  mkinstall.py <gamedir> <outdir> [retaildir]

A game directory holds the retail game's data as well as what we built: the
.rez archives (with the retail game DLLs inside them zeroed), the movies,
the shipped autoexec.cfg and default profile, and, as third-party runtime,
RAD's binkw32.dll (legacy builds only) and the Microsoft C++ and MFC DLLs
(MANIFEST.txt's `data` and `THIRD-PARTY` rows: tools/retailextract.py). The
public archive (build/package.sh) leaves all of that out, and two scripts
put it back from the player's own No One Lives Forever 2, installed from
their discs and updated to 1.3 (English; the European and the USA releases
install the same files):

  linux-install.sh       bash, dd, sha256sum, base64 (coreutils)
  windows-install.bat    cmd running the PowerShell it carries (5.1, as every
                         Windows 10 and 11 has)

They read the installed game, not the discs: NOLF2's setup packs its files
into InstallShield cabinets, compressed, and the 1.3 update into a
self-extractor, so only an install has them as they are. Every file is
then written from a list of byte ranges, worked out here against the
retail game rez/ installs (<retaildir>, rez/games/nolf2-eu-1.3/ by default)
--

  C <source> <offset> <length>   bytes of a file of the installed game
  Z <length>                     zeros (the retail game DLLs blanked inside
                                 the .rez archives: build/all.sh's
                                 `resources`)
  L <base64>                     bytes of ours (none yet: room for data
                                 edits a modern build may make)

-- and the file's size and SHA-256, which the script checks before it moves
the file into place. So the result is the game directory as built, byte for
byte. Each source is recorded with its path in the install, its size (the
scripts check it first: a wrong version fails at once), SHA-256 and the
flag of what is made from it. A written file is flagged:

  -      it must come out exactly
  opt    the Microsoft runtime: a Windows install keeps it in the system
         folder, where the game finds it, not in the game's; skipped,
         with a note, if the install's copy is missing or another version
  own    autoexec.cfg.retail, Default.prf.retail: the shipped settings. A
         game that has been played has rewritten them; the player's own
         are then taken as they are, with a note
  once   autoexec.cfg, Profiles/Default.prf: the same, written only if
         there is none

The list goes at the end of each script, after a marker line; the scripts'
code is build/game-scripts/linux-install.sh and windows-install.ps1 (the
.bat's header is written here).

Writes <outdir>/linux-install.sh, <outdir>/windows-install.bat and
<outdir>/retail-files.txt, the game directory's paths the scripts write
(the public archive leaves them out). Exits 3 if the retail game is not
installed.
"""
import base64
import hashlib
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETAIL = os.path.join(REPO, "rez", "games", "nolf2-eu-1.3")
SCRIPTS = os.path.join(REPO, "build", "game-scripts")
MARKER = "__NOLF2_INSTALL_DATA__"
CHUNK = 1 << 20
BLOCK = 4096
LITERAL_LINE = 3 * 1024          # raw bytes per L record (4 KB of base64)
LITERAL_MAX = 1 << 20            # more than this of ours means a wrong source

# The files the game rewrites, kept as their shipped copies (<name>.retail;
# tools/retailextract.py RETAIL_COPIES), and the live file each starts.
SETTINGS = {"autoexec.cfg.retail": "autoexec.cfg",
            "Default.prf.retail": "Profiles/Default.prf"}
# The Microsoft runtime: setup installs it into the system folder.
OPTIONAL = {"mfc42.dll", "mfc42u.dll", "msvcp60.dll", "msvcrt.dll"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


class Source:
    """A file of the installed retail game."""
    def __init__(self, n, root, rel):
        self.n, self.rel = n, rel
        self.path = os.path.join(root, rel)
        self.size = os.path.getsize(self.path)
        self.sha = sha256(self.path)


class Ops:
    def __init__(self):
        self.ops, self.literal = [], 0

    def copy(self, src, off, n):
        if n <= 0:
            return
        last = self.ops[-1] if self.ops else None
        if last and last[0] == "C" and last[1] == src.n and last[2] + last[3] == off:
            last[3] += n
        else:
            self.ops.append(["C", src.n, off, n])

    def zeros(self, n):
        if self.ops and self.ops[-1][0] == "Z":
            self.ops[-1][1] += n
        else:
            self.ops.append(["Z", n])

    def bytes(self, b):
        self.literal += len(b)
        if self.ops and self.ops[-1][0] == "L":
            self.ops[-1][1] += b
        else:
            self.ops.append(["L", bytearray(b)])

    def lines(self):
        for op in self.ops:
            if op[0] == "L":
                b = bytes(op[1])
                for i in range(0, len(b), LITERAL_LINE):
                    yield "L " + base64.b64encode(b[i:i + LITERAL_LINE]).decode()
            else:
                yield " ".join(str(x) for x in op)


def ops_for(src, path):
    """The file at `path` as ranges of `src` (the same size): the bytes it
    shares with it copied, zeros where they differ written as zeros (a
    blanked DLL's own zero bytes join the run), anything else as ours."""
    if os.path.getsize(path) != src.size:
        return None
    ops = Ops()
    with open(path, "rb") as f, open(src.path, "rb") as r:
        pos = 0
        while True:
            out = f.read(CHUNK)
            if not out:
                break
            ref = r.read(len(out))
            if out == ref:
                ops.copy(src, pos, len(out))
            else:
                for i in range(0, len(out), BLOCK):
                    o, a = out[i:i + BLOCK], ref[i:i + BLOCK]
                    zero = o.count(0) == len(o)
                    if o == a and not (zero and ops.ops and ops.ops[-1][0] == "Z"):
                        ops.copy(src, pos + i, len(o))
                    elif zero:
                        ops.zeros(len(o))
                    else:
                        for j in range(len(o)):
                            inzero = ops.ops and ops.ops[-1][0] == "Z"
                            if o[j] == 0 and (inzero or a[j] != 0):
                                ops.zeros(1)
                            elif o[j] == a[j]:
                                ops.copy(src, pos + i + j, 1)
                            else:
                                ops.bytes(o[j:j + 1])
            pos += len(out)
    return ops


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    game, outdir = sys.argv[1].rstrip("/"), sys.argv[2]
    retail = sys.argv[3] if len(sys.argv) == 4 else RETAIL
    if not os.path.isfile(os.path.join(retail, "MANIFEST.txt")):
        print(f"mkinstall: the retail game is not installed in {retail} -- "
              "rez/fetch-isos.sh nolf2-eu-1.3 && rez/install-games.sh nolf2-eu-1.3",
              file=sys.stderr)
        sys.exit(3)
    release = os.path.basename(os.path.normpath(retail))

    # What in the game directory came from the retail game, and from which
    # of its files (build/all.sh's MANIFEST.txt).
    wanted = {}                           # game path -> retail path
    for line in open(os.path.join(game, "MANIFEST.txt")):
        line = line.rstrip("\n")
        if line.startswith("#") or "\t" not in line:
            continue
        origin, rel = line.split("\t", 1)
        m = re.match(r"(data|THIRD-PARTY) ([^:]+):(.+?)( \(.*\))?$", origin)
        if not m:
            continue
        if m.group(2) != release:
            sys.exit(f"mkinstall: {rel} came from {m.group(2)}, not {release}")
        wanted[rel] = m.group(3)
    for rel in list(wanted) + list(wanted.values()):
        if re.search(r"[\s\"'`$\\%!]", rel):
            sys.exit(f"mkinstall: {rel}: a name the scripts do not quote")

    sources, kinds, records, literal = {}, {}, [], 0
    for rel in sorted(wanted, key=str.lower):
        rp = wanted[rel]
        if rp not in sources:
            sources[rp] = Source(len(sources) + 1, retail, rp)
        src = sources[rp]
        path = os.path.join(game, rel)
        ops = ops_for(src, path)
        if ops is None:
            sys.exit(f"mkinstall: {rel}: not made from {release}:{rp}")
        literal += ops.literal
        size, sha = os.path.getsize(path), sha256(path)
        flag = ("own" if rel in SETTINGS else
                "opt" if os.path.basename(rel).lower() in OPTIONAL else "-")
        kinds[rp] = flag
        records.append(f"F {rel} {size} {sha} {flag}")
        records.extend(ops.lines())
        records.append("E")
        if rel in SETTINGS:
            records.append(f"F {SETTINGS[rel]} {size} {sha} once")
            records.extend(ops.lines())
            records.append("E")
    if literal > LITERAL_MAX:
        sys.exit(f"mkinstall: {literal} bytes would ship as literal data")

    data = ["NOLF2INSTALL 1"]
    for rp, s in sorted(sources.items(), key=lambda kv: kv[1].n):
        data.append(f"S {s.n} {s.size} {s.sha} {kinds[rp]} {rp}")
    data += records

    os.makedirs(outdir, exist_ok=True)
    body = open(os.path.join(SCRIPTS, "linux-install.sh")).read()
    with open(os.path.join(outdir, "linux-install.sh"), "w", newline="\n") as f:
        f.write(body + MARKER + "\n" + "\n".join(data) + "\n")
    os.chmod(os.path.join(outdir, "linux-install.sh"), 0o755)

    ps = open(os.path.join(SCRIPTS, "windows-install.ps1")).read()
    if not ps.isascii() or "#__NOLF2_PS__" in ps or MARKER in ps:
        sys.exit("mkinstall: windows-install.ps1 must be ASCII, without the markers")
    bat = BAT_HEADER + ["#__NOLF2_PS__"] + ps.splitlines() + ["#__NOLF2_PS__", MARKER] + data
    with open(os.path.join(outdir, "windows-install.bat"), "w", newline="\r\n") as f:
        f.write("\n".join(bat) + "\n")

    written = sorted(set(wanted) | set(SETTINGS.values()), key=str.lower)
    with open(os.path.join(outdir, "retail-files.txt"), "w") as f:
        for rel in written:
            f.write(rel + "\n")
    print(f"   install scripts: {len(written)} files from {len(sources)} of the "
          f"installed game's, {literal} bytes of ours")


# cmd runs this; everything from the first #__NOLF2_PS__ line on is never
# parsed by it (`exit /b` comes first). The PowerShell between the markers is
# written to a temporary .ps1 and run with -File, which passes the dropped or
# typed paths through as they are.
BAT_HEADER = r"""@echo off
rem windows-install.bat -- install the game data from your own NOLF2.
rem
rem   Double-click it: it finds No One Lives Forever 2 where its setup
rem   installed it (the registry says where), or drop the folder you
rem   installed it in onto this file. The game must be updated to 1.3
rem   (English), as Sierra's update nolf2-update_1x3.exe does. Then start
rem   the game from this folder: Lithtech.exe -cmdfile nolf2cmds.txt
rem
rem It checks the installed files, copies the game's data out of them into
rem this folder and checks every file it writes. Nothing else is changed:
rem your installed game is only read.
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
