#!/usr/bin/env python3
"""Take what the build needs from the installed retail game.

  retailextract.py resources    <retaildir> <gamedir>  game DATA only (no binary)
  retailextract.py thirdparty   <retaildir> <gamedir>  Bink and the Microsoft
                                                       runtime, nothing else
  retailextract.py retailengine <retaildir> <gamedir>  the engine binaries we
                                                       do not build yet
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
build/package.sh packages: the game rewrites both). No file is
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
launcher import.

`retailengine` copies the engine -- Lithtech.exe, server.dll, ServerDir.dll
and snddrv.dll -- out of the retail game, because there is no source for it
yet: Monolith's release has the game, the launcher and the dedicated server,
not the engine. They are marked RETAIL in the manifest and in the audit, so
they are easy to find and to replace as the engine is reconstructed.
ltmsg.dll, the engine's message strings, is built (src/Engine/ltmsg/,
identical to the retail one apart from its timestamp), so it is not copied.

`reference` copies the retail engine images, launcher and dedicated server,
and the 1.3 game DLLs out of Update_v1x3.rez, to a reference directory
(build/reference.sh: out/reference/). They are what tools/progress.py and
the reconstruction tools compare our objects against; the build never reads
them, and nothing in that directory is ever run or goes into a game
directory.

Every file the steps write is recorded in <gamedir>/MANIFEST.txt
(`<origin>\\t<path>`); build/all.sh adds the binaries it built, and `audit`
lists every PE file in the directory with its origin, failing on any it
cannot account for -- or on any PE file still inside a .rez archive.
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

# RETAIL ENGINE: no source yet (see the docstring).
RETAIL_ENGINE = ["Lithtech.exe", "server.dll", "ServerDir.dll", "snddrv.dll"]

# Engine binaries built from our source (src/Engine/), identical to the
# retail ones apart from their timestamps: build/all.sh assembles ours, and
# `reference` still copies the retail ones to compare against.
BUILT_ENGINE = ["ltmsg.dll"]

# The retail images the checks compare against (`reference`), and the 1.3
# game DLLs, which the retail game holds only inside Update_v1x3.rez (the
# copies 1.3 runs, last in its rez stack, and what Monolith's source release
# builds), under the names our build gives them.
REFERENCE = RETAIL_ENGINE + BUILT_ENGINE + ["NOLF2.exe", "NOLF2Srv.exe"]
REFERENCE_REZ = "Update_v1x3.rez"
REFERENCE_GAME = [("CSHELL.dll", "CShell.dll"), ("OBJECT.lto", "Object.lto"),
                  ("CLIENTFX.fxd", "ClientFx.fxd"), ("CRES.dll", "CRes.dll"),
                  ("SRES.dll", "SRes.dll")]


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
        r.copy_if_changed(p, gamedir / p)
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
            r.copy(p, dest)
        for ename, _pos, sz in scrub_rez(dest):
            print(f"   {p}: retail binary {ename} ({sz} bytes) zeroed")
        man.add(p, f"data {r.name}:{p} (game binaries inside zeroed)")
    man.save()


def cmd_thirdparty(retaildir, gamedir):
    gamedir = Path(gamedir)
    man = Manifest(gamedir)
    r = Retail(retaildir)
    n = 0
    for p in r.files:
        if "/" in p or not is_third_party(p):
            continue
        r.copy_if_changed(p, gamedir / p)
        man.add(p, f"THIRD-PARTY {r.name}:{p}")
        n += 1
    man.save()
    print(f"== third-party runtime: {n} files (Bink, the Microsoft C++ and MFC runtime)")


def cmd_retailengine(retaildir, gamedir):
    gamedir = Path(gamedir)
    man = Manifest(gamedir)
    r = Retail(retaildir)
    for name in RETAIL_ENGINE:
        p = r.find(name)
        r.copy_if_changed(p, gamedir / p)
        man.add(p, f"RETAIL {r.name}:{p} (no source yet)")
    man.save()
    print(f"== retail engine: {', '.join(RETAIL_ENGINE)} (no source yet)")


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
                if origin == "UNKNOWN" or origin.startswith("data "):
                    bad += 1
                rows.append((origin, rel, full.stat().st_size))
            elif fn.lower().endswith(".rez"):
                for ename, _pos, sz in rez_pe_entries(full):
                    rows.append(("INSIDE A REZ ARCHIVE", f"{rel}:{ename}", sz))
                    bad += 1
    order = {"built": 0, "RETAIL": 1, "THIRD-PARTY": 2}
    rows.sort(key=lambda r: (order.get(r[0].split()[0], 3), r[1].lower()))
    print(f"{'size':>9}  {'file':<24} origin")
    for origin, rel, sz in rows:
        print(f"{sz:>9}  {rel:<24} {origin}")
    count = lambda kind: sum(1 for r in rows if r[0].startswith(kind))
    print(f"{len(rows)} PE files: {count('built')} built from our source, "
          f"{count('RETAIL')} retail engine (no source yet), "
          f"{count('THIRD-PARTY')} third-party runtime, {bad} unaccounted for")
    return 1 if bad else 0


def main():
    a = sys.argv[1:]
    cmds = {"resources": cmd_resources, "thirdparty": cmd_thirdparty,
            "retailengine": cmd_retailengine, "reference": cmd_reference}
    if len(a) == 3 and a[0] in cmds:
        cmds[a[0]](a[1], a[2])
    elif len(a) == 2 and a[0] == "audit":
        sys.exit(cmd_audit(a[1]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
