#!/usr/bin/env python3
"""Take what the build needs from the installed retail game.

  retailextract.py resources    <retaildir> <gamedir>  game DATA only (no binary)
  retailextract.py thirdparty   <retaildir> <gamedir> [open]
                                                       Bink and the Microsoft
                                                       runtime, nothing else
                                                       ("open": the Microsoft
                                                       runtime only)
  retailextract.py openruntime  <extdir> <gamedir>     the modern build's
                                                       replacements for the
                                                       rest (build/ext.sh's
                                                       output)
  retailextract.py reference    <retaildir> <refdir>   the retail binaries, for
                                                       scoring only
  retailextract.py audit        <gamedir>              every PE file in a game
                                                       directory, with its
                                                       origin

<retaildir> is No One Lives Forever 2 (Europe) with the English 1.3 update,
as the rez/ submodule installs it (rez/install-games.sh nolf2-eu-1.3:
rez/games/nolf2-eu-1.3/, see build/retail.sh). It is only read: nothing in it
is run, and the build never writes to it.

`resources` is build/all.sh's first step. It copies the game's data: the
.rez archives, the movies, and the shipped autoexec.cfg and default player
profile (as autoexec.cfg.retail and Default.prf.retail, which build/all.sh
starts a game directory's autoexec.cfg and Profiles/Default.prf from, and
build/package.sh packages: the game rewrites both). A movie or an archive
that holds no binary is hard-linked rather than copied when it can be (the
same filesystem): it is the retail file unchanged, and four game
directories would otherwise take 7 GB. Nothing writes to it; were it
changed, build/retail.sh's check of the retail game would say so. No file is
copied that is a Windows executable image (recognised by its "MZ" header,
not its name). Two archives carry the retail game DLLs -- GAMEDLL.REZ the
1.0 ones and Update_v1x3.rez the 1.3 ones (CSHELL.dll, OBJECT.lto,
CLIENTFX.fxd, CRES.dll, SRES.dll) -- and those entries are overwritten with
zeros in our copy: the archive stays valid, the binary is gone, and the only
game code in the directory is what we compiled (in the custom/ rez
directory, last in the rez stack: build/nolf2cmds.sh). The setup's other
files (the Sierra updater, web links) are not copied.

`thirdparty` copies the licensed middleware we have no source for: Bink
(binkw32.dll), and the Microsoft C, C++ and MFC runtime DLLs setup installs
(MFC42.DLL, MFC42U.DLL, MSVCP60.DLL, Msvcrt.dll), which the engine and the
launcher import. With "open" (the modern build, NOLF2_MIDDLEWARE=open) it
leaves out what `openruntime` replaces.

`openruntime` is the modern build's other half of step 2: our Bink player,
binkw32.dll, which build/ext.sh built from src/modern/binkw32/ and
ext/ffmpeg into <extdir>, in place of RAD's (MANIFEST.txt origin `EXT`).
The Microsoft runtime DLLs stay the retail ones in both builds.

No engine binary is copied: Lithtech.exe, server.dll, snddrv.dll,
ServerDir.dll and ltmsg.dll are built from our source (src/Engine/,
src/Game/Libs/ServerDir/) and build/all.sh assembles them.

`reference` copies the retail engine images, launcher and dedicated server,
and the 1.3 game DLLs out of Update_v1x3.rez, to a reference directory
(build/reference.sh: out/reference/). They are what tools/progress.py and
the reconstruction tools compare our objects against; the build never reads
them, and nothing in that directory is ever run or goes into a game
directory.

Every file the steps write is recorded in <gamedir>/MANIFEST.txt
(`<origin>\\t<path>`); build/all.sh adds the binaries it built, and `audit`
lists every PE file in the directory with its origin, failing on any that
is neither built here, nor third-party runtime, nor the modern build's
open-source replacement (EXT) -- or on any PE file still
inside a .rez archive.
"""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rezextract import Rez  # noqa: E402

# The archives of the retail install, under their installed names (the rez
# stack is build/nolf2cmds.sh's).
REZ = ["Engine.REZ", "GAME.REZ", "GAME2.REZ", "GAMEDLL.REZ", "SOUND.REZ", "Update_v1x3.rez"]

# Data outside the archives, and the two files the game rewrites -- its
# settings and the default player profile -- kept as the retail copies
# (<name>.retail), which build/all.sh starts a new game directory from and
# build/package.sh packages.
DATA_DIRS = ["Movies"]
RETAIL_COPIES = [("autoexec.cfg", "autoexec.cfg.retail"), ("Profiles/Default.prf", "Default.prf.retail")]

# THIRD-PARTY RUNTIME: Bink, which the engine loads for the movies, and the
# Microsoft runtime DLLs setup installs beside the game.
THIRD_PARTY_NAMES = {"binkw32.dll", "mfc42.dll", "mfc42u.dll", "msvcp60.dll", "msvcrt.dll"}

# The engine: built from our source (src/Engine/, and ServerDir.dll from
# src/Game/Libs/ServerDir/); build/all.sh assembles ours, and `reference`
# copies the retail ones to compare against.
BUILT_ENGINE = ["Lithtech.exe", "server.dll", "ServerDir.dll", "snddrv.dll", "ltmsg.dll"]

# The retail images the checks compare against (`reference`), and the 1.3
# game DLLs, which the retail game holds only inside Update_v1x3.rez (the
# copies 1.3 runs, last in its rez stack, and what Monolith's source release
# builds), under the names our build gives them.
REFERENCE = BUILT_ENGINE + ["NOLF2.exe", "NOLF2Srv.exe"]
REFERENCE_REZ = "Update_v1x3.rez"
REFERENCE_GAME = [("CSHELL.dll", "CShell.dll"), ("OBJECT.lto", "Object.lto"),
                  ("CLIENTFX.fxd", "ClientFx.fxd"), ("CRES.dll", "CRes.dll"),
                  ("SRES.dll", "SRes.dll")]


# The modern build's replacements (build/ext.sh), and where each comes from.
OPEN_RUNTIME = [
    ("binkw32.dll", "src/modern/binkw32 + ext/ffmpeg: our Bink player"),
]


def is_third_party(name):
    return name.lower() in THIRD_PARTY_NAMES


class Retail:
    """The installed retail game, read only; rez/'s MANIFEST.txt lists its
    files (`<path>\\t<origin>`)."""

    def __init__(self, root):
        self.root = Path(root)
        man = self.root / "MANIFEST.txt"
        if not man.exists():
            sys.exit(f"missing {man} -- install the retail game first (build/retail.sh)")
        self.name = self.root.name
        self.files = []
        for line in man.read_text().splitlines():
            if "\t" in line and not line.startswith("#"):
                self.files.append(line.split("\t", 1)[0])

    def find(self, path):
        for p in self.files:
            if p.lower() == path.lower():
                return p
        sys.exit(f"{self.root}: no {path}")

    def size(self, p):
        return (self.root / p).stat().st_size

    def head(self, p, n=2):
        with open(self.root / p, "rb") as f:
            return f.read(n)

    def copy(self, p, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        shutil.copyfile(self.root / p, tmp)
        tmp.replace(dest)

    def copy_if_changed(self, p, dest):
        if not dest.exists() or dest.stat().st_size != self.size(p):
            self.copy(p, dest)

    def link_if_changed(self, p, dest):
        """The retail file itself in the game directory, hard-linked, or
        copied where it cannot be (another filesystem)."""
        if dest.exists() and dest.stat().st_size == self.size(p):
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        tmp.unlink(missing_ok=True)
        try:
            os.link(self.root / p, tmp)
        except OSError:
            shutil.copyfile(self.root / p, tmp)
        tmp.replace(dest)


class Manifest:
    def __init__(self, gamedir):
        self.path = Path(gamedir) / "MANIFEST.txt"
        self.rows = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if "\t" in line and not line.startswith("#"):
                    origin, p = line.split("\t", 1)
                    self.rows[p] = origin

    def add(self, relpath, origin):
        self.rows[relpath] = origin

    def save(self):
        with open(self.path, "w") as f:
            f.write("# origin<TAB>path, one row per file build/all.sh put here\n")
            for p in sorted(self.rows, key=str.lower):
                f.write(f"{self.rows[p]}\t{p}\n")


def rez_pe_entries(path):
    """(name, pos, size) of every entry in a .rez that is a PE image."""
    rez = Rez(path)
    out = []
    for name, pos, sz in list(rez.walk()):
        if sz < 2:
            continue
        rez.f.seek(pos)
        if rez.f.read(2) == b"MZ":
            out.append((name, pos, sz))
    rez.f.close()
    return out


def scrub_rez(path):
    """Overwrite every PE entry of a .rez with zeros. Idempotent."""
    hits = rez_pe_entries(path)
    with open(path, "r+b") as f:
        for _name, pos, sz in hits:
            f.seek(pos)
            f.write(b"\0" * sz)
    return hits


def cmd_resources(retaildir, gamedir):
    gamedir = Path(gamedir)
    gamedir.mkdir(parents=True, exist_ok=True)
    man = Manifest(gamedir)
    r = Retail(retaildir)
    for p in r.files:
        top = p.split("/", 1)[0]
        if top not in DATA_DIRS or "/" not in p:
            continue
        if r.head(p) == b"MZ":
            sys.exit(f"retailextract: {r.name}:{p} is a binary")
        r.link_if_changed(p, gamedir / p)
        man.add(p, f"data {r.name}:{p}")
    for name, copy in RETAIL_COPIES:
        p = r.find(name)
        r.copy_if_changed(p, gamedir / copy)
        man.add(copy, f"data {r.name}:{p}")
    for name in REZ:
        p = r.find(name)
        dest = gamedir / p
        if not dest.exists() or dest.stat().st_size != r.size(p):
            print(f"== {r.name}:{p} -> {p}")
            if rez_pe_entries(r.root / p):
                r.copy(p, dest)
            else:
                r.link_if_changed(p, dest)
        for ename, _pos, sz in scrub_rez(dest):
            print(f"   {p}: retail binary {ename} ({sz} bytes) zeroed")
        man.add(p, f"data {r.name}:{p} (game binaries inside zeroed)")
    man.save()


def cmd_thirdparty(retaildir, gamedir, middleware="retail"):
    gamedir = Path(gamedir)
    man = Manifest(gamedir)
    r = Retail(retaildir)
    skip = {name for name, _ in OPEN_RUNTIME} if middleware == "open" else set()
    n = 0
    for p in r.files:
        if "/" in p or not is_third_party(p) or p.lower() in skip:
            continue
        r.copy_if_changed(p, gamedir / p)
        man.add(p, f"THIRD-PARTY {r.name}:{p}")
        n += 1
    man.save()
    print(f"== third-party runtime: {n} files ("
          + ("" if skip else "Bink, ") + "the Microsoft C++ and MFC runtime)")


def cmd_openruntime(extdir, gamedir):
    gamedir = Path(gamedir)
    gamedir.mkdir(parents=True, exist_ok=True)
    man = Manifest(gamedir)
    for name, origin in OPEN_RUNTIME:
        # (over a retail copy an earlier build left, whatever its case)
        for f in gamedir.iterdir():
            if f.is_file() and f.name.lower() == name and f.name != name:
                f.unlink()
                man.rows.pop(f.name, None)
        shutil.copyfile(Path(extdir) / name, gamedir / name)
        man.add(name, f"EXT {origin} (build/ext.sh)")
        print(f"   {name}  <-  {origin}")
    man.save()
    print(f"== open runtime: {len(OPEN_RUNTIME)} file(s) (Bink on FFmpeg)")


def cmd_reference(retaildir, refdir):
    refdir = Path(refdir)
    refdir.mkdir(parents=True, exist_ok=True)
    r = Retail(retaildir)
    for name in REFERENCE:
        p = r.find(name)
        r.copy(p, refdir / name)
        print(f"== {r.name}:{p} -> {refdir / name}")
    p = r.find(REFERENCE_REZ)
    rez = Rez(str(r.root / p))
    found = {path.lower(): (pos, size) for path, pos, size in rez.walk()}
    for name, out in REFERENCE_GAME:
        if name.lower() not in found:
            sys.exit(f"retailextract: no {name} in {r.name}:{p}")
        pos, size = found[name.lower()]
        rez.f.seek(pos)
        (refdir / out).write_bytes(rez.f.read(size))
        print(f"== {r.name}:{p}:{name} -> {refdir / out}")
    rez.f.close()


def cmd_audit(gamedir):
    gamedir = Path(gamedir)
    man = Manifest(gamedir)
    bad = 0
    rows = []
    for root, _dirs, files in os.walk(gamedir, followlinks=True):
        for fn in files:
            full = Path(root) / fn
            rel = str(full.relative_to(gamedir))
            with open(full, "rb") as f:
                head = f.read(2)
            if head == b"MZ":
                origin = man.rows.get(rel, "UNKNOWN")
                # only what we built and the third-party runtime belong
                # in a game directory (a RETAIL row is a stale manifest's)
                if not origin.startswith(("built ", "THIRD-PARTY ", "EXT ")):
                    bad += 1
                rows.append((origin, rel, full.stat().st_size))
            elif fn.lower().endswith(".rez"):
                for ename, _pos, sz in rez_pe_entries(full):
                    rows.append(("INSIDE A REZ ARCHIVE", f"{rel}:{ename}", sz))
                    bad += 1
    order = {"built": 0, "EXT": 1, "THIRD-PARTY": 2}
    rows.sort(key=lambda r: (order.get(r[0].split()[0], 3), r[1].lower()))
    print(f"{'size':>9}  {'file':<24} origin")
    for origin, rel, sz in rows:
        print(f"{sz:>9}  {rel:<24} {origin}")
    count = lambda kind: sum(1 for r in rows if r[0].startswith(kind))
    print(f"{len(rows)} PE files: {count('built')} built from our source, "
          + (f"{count('EXT')} open-source replacements (build/ext.sh), " if count('EXT') else "")
          + f"{count('THIRD-PARTY')} third-party runtime, {bad} unaccounted for")
    return 1 if bad else 0


def main():
    a = sys.argv[1:]
    cmds = {"resources": cmd_resources, "thirdparty": cmd_thirdparty,
            "openruntime": cmd_openruntime, "reference": cmd_reference}
    if len(a) == 4 and a[0] == "thirdparty" and a[3] in ("retail", "open"):
        cmd_thirdparty(a[1], a[2], a[3])
    elif len(a) == 3 and a[0] in cmds:
        cmds[a[0]](a[1], a[2])
    elif len(a) == 2 and a[0] == "audit":
        sys.exit(cmd_audit(a[1]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
