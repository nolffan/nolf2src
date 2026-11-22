#!/usr/bin/env python3
"""Take what the build needs from the installed retail game.

NOLF2's own copy of ext/tools/retailextract.py, which nolf2src used before
the retail game came from your own discs (build/discs.py).

  build/retailextract.py resources   <retaildir> <gamedir>   game DATA only (no binary)
  build/retailextract.py thirdparty  <retaildir> <gamedir> [open]
                                                             Bink and the Microsoft
                                                             runtime, nothing else
                                                             ("open": the Microsoft
                                                             runtime only)
  build/retailextract.py openruntime <extdir> <gamedir>      the modern build's
                                                             replacements for the
                                                             rest (build/ext.sh's
                                                             output)
  build/retailextract.py art install                         the committed art
                                                             (assets/art/) into the
                                                             directory the resource
                                                             script includes from
  build/retailextract.py art write|check <retaildir>         assets/art/, from the
                                                             retail binaries'
                                                             resources
  build/retailextract.py ranges write|check <retaildir>      build/retail-ranges.txt,
                                                             from the retail game
  build/retailextract.py reference   <retaildir> <refdir>    the retail binaries, for
                                                             scoring only
  build/retailextract.py audit       <gamedir>               every PE file in a game
                                                             directory, with its
                                                             origin

<retaildir> is No One Lives Forever 2 (Europe) with the English 1.3 update,
as build/discs.py installs it from your two disc images and the update's
installer (out/retail/nolf2-eu-1.3/, see build/retail.sh).
build/retail-files.txt lists its files. The directory is only read:
nothing in it is run, and the build never writes to it. For `resources`
and `thirdparty`, <retaildir> "-" means no retail game (NODISCS=1): they
then copy nothing and write only the manifest's rows of the files, the
same rows as with the retail game.

`resources` is build/all.sh's first step. It copies the game's data: the
.rez archives of the discs and the movies. A movie or an archive that holds
no binary is hard-linked rather than copied when it can be (the same
filesystem): it is the retail file unchanged, and four game directories
would otherwise take 7 GB. Nothing writes to it; were it changed,
build/retail.sh's check of the retail game would say so. No file is copied
that is a Windows executable image (recognised by its "MZ" header, not its
name). GAMEDLL.REZ carries the 1.0 game DLLs, and those entries are
overwritten with zeros in our copy: the archive stays valid, the binary is
gone, and the only game code in the directory is what we compiled (in the
custom/ rez directory, last in the rez stack: build/nolf2cmds.sh). The 1.3
update's data, the settings and the default profile come from assets/
(build/all.sh, step 1b), not from here; the update's own archive,
Update_v1x3.rez, is not copied. The setup's other files (the Sierra
updater, web links) are not copied either.

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

`art` is about the retail art that our binaries are compiled with: the
engine's icon, which lithtech.rc compiles into Lithtech.exe (IDR_MAINFRAME,
five images). It is committed, unchanged, in assets/art/lithtech/
(assets/README.md). `art install` (build/all.sh, step 2c, every build)
copies it into src/Engine/runtime/winbuild/lithtech/res/, where lithtech.rc
includes it from. `art write` (make art) writes assets/art/ again from the
retail Lithtech.exe's resources: the image is parsed in memory, never run,
and the icon group and its images are written back as the .ico file rc.exe
compiles. The .ico lists the images in the group's order, with the group
entry's fields, so rc.exe gives each image the same place. `art check`
(every build with the retail game, and make art-check) fails unless
assets/art/ is what the retail game gives. So our Lithtech.exe has the
retail icon in every build, with or without the discs.

`ranges` writes (or checks) build/retail-ranges.txt: metadata of the
retail game, which a build without it (NODISCS=1) and the public archive's
install scripts (build/mkinstall.py) use in place of it. It holds no game
data: the PE files of the install, and the retail game DLLs inside the
archives with each archive's SHA-256 after they are zeroed. `resources`
checks its list of PE files.

`reference` copies the retail engine images, launcher and dedicated server,
and the 1.3 game DLLs out of Update_v1x3.rez, to a reference directory
(build/reference.sh: out/reference/). They are what ext/tools/progress.py
and the reconstruction tools compare our objects against; the build never
reads them, and nothing in that directory is ever run or goes into a game
directory.

Every file the steps write is recorded in <gamedir>/MANIFEST.txt
(`<origin>\\t<path>`); build/all.sh adds the binaries it built, and `audit`
lists every PE file in the directory with its origin, failing on any that
is neither built here, nor third-party runtime, nor the modern build's
open-source replacement (EXT) -- or on any PE file still inside a .rez
archive.
"""
import hashlib
import os
import shutil
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# the shared helpers (rezextract.py) are ext/tools/'s
sys.path.insert(0, str(REPO / "ext" / "tools"))
sys.path.insert(0, str(REPO / "build"))
from rezextract import Rez  # noqa: E402

# The name of the install (build/retail.sh), in the manifest's rows.
RETAIL_RELEASE = "nolf2-eu-1.3"

# The archives of the retail install the game directory takes (the discs';
# the rez stack is build/nolf2cmds.sh's). Update_v1x3.rez is the update's:
# its data is in assets/rez/ (nolf2src.rez), and the scoring takes its game
# DLLs (REFERENCE_REZ).
REZ = ["Engine.REZ", "GAME.REZ", "GAME2.REZ", "GAMEDLL.REZ", "SOUND.REZ"]

# Data outside the archives.
DATA_DIRS = ["Movies"]

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
    """The installed retail game, read only. build/retail-files.txt lists
    its files."""

    def __init__(self, root):
        import discs
        self.sizes = {f.path: f.size for f in discs.load("retail").files}
        self.files = sorted(self.sizes, key=str.lower)
        # "-": no retail game (NODISCS=1), only its lists: the files'
        # names, sizes and kinds, but no bytes
        self.nodiscs = root == "-"
        self.name = RETAIL_RELEASE
        if self.nodiscs:
            self.root = None
            self.pe = load_ranges().pe
            return
        self.root = Path(root)
        if not (self.root / discs.STAMP).exists():
            sys.exit(f"{self.root} is not an install of the retail game -- "
                     "install it first (make retail, build/retail.sh)")

    def find(self, path):
        for p in self.files:
            if p.lower() == path.lower():
                return p
        sys.exit(f"build/retail-files.txt: no {path}")

    def size(self, p):
        return self.sizes[p]

    def head(self, p, n=2):
        if self.nodiscs:
            return b"MZ" if p in self.pe else b""
        with open(self.root / p, "rb") as f:
            return f.read(n)

    def read(self, p):
        if self.nodiscs:
            sys.exit(f"retailextract: {p}: no retail game (NODISCS=1)")
        return (self.root / p).read_bytes()

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
    rez = Rez(str(path))
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
    # which files are PE images: what a build without the retail game
    # takes from build/retail-ranges.txt
    if not r.nodiscs and {p for p in r.files if r.head(p) == b"MZ"} != load_ranges().pe:
        sys.exit("retailextract: build/retail-ranges.txt's PE lines are not the retail game's "
                 "PE files -- write it again: make retail-ranges")
    for p in r.files:
        top = p.split("/", 1)[0]
        if top not in DATA_DIRS or "/" not in p:
            continue
        if r.head(p) == b"MZ":
            sys.exit(f"retailextract: {r.name}:{p} is a binary")
        if r.nodiscs:
            (gamedir / p).parent.mkdir(parents=True, exist_ok=True)   # (Movies/, as with it)
        else:
            r.link_if_changed(p, gamedir / p)
        man.add(p, f"data {r.name}:{p}")
    for name in REZ:
        p = r.find(name)
        dest = gamedir / p
        if not r.nodiscs:
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
    if r.nodiscs:
        print(f"== no retail game: only the manifest's rows of its data")


def cmd_thirdparty(retaildir, gamedir, middleware="retail"):
    gamedir = Path(gamedir)
    gamedir.mkdir(parents=True, exist_ok=True)
    man = Manifest(gamedir)
    r = Retail(retaildir)
    skip = {name for name, _ in OPEN_RUNTIME} if middleware == "open" else set()
    n = 0
    for p in r.files:
        if "/" in p or not is_third_party(p) or p.lower() in skip:
            continue
        if not r.nodiscs:
            r.copy_if_changed(p, gamedir / p)
        man.add(p, f"THIRD-PARTY {r.name}:{p}")
        n += 1
    man.save()
    print(f"== third-party runtime: {n} files ("
          + ("" if skip else "Bink, ") + "the Microsoft C++ and MFC runtime)"
          + (": no retail game, only their manifest rows" if r.nodiscs else ""))


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
    count = lambda kind: sum(1 for r in rows if r[0].startswith(kind))  # noqa: E731
    print(f"{len(rows)} PE files: {count('built')} built from our source, "
          + (f"{count('EXT')} open-source replacements (build/ext.sh), " if count('EXT') else "")
          + f"{count('THIRD-PARTY')} third-party runtime, {bad} unaccounted for")
    return 1 if bad else 0


# --- the art of the retail binaries -----------------------------------------

RT_CURSOR, RT_BITMAP, RT_ICON, RT_GROUP_CURSOR, RT_GROUP_ICON = 1, 2, 3, 12, 14


def pe_resources(img):
    """{(type, name): data} of a PE image's resources, the first language of
    each. A string type or name is upper case, as rc.exe stores it."""
    pe = struct.unpack_from("<I", img, 0x3C)[0]
    nsec = struct.unpack_from("<H", img, pe + 6)[0]
    optsz = struct.unpack_from("<H", img, pe + 20)[0]
    rva = struct.unpack_from("<I", img, pe + 24 + 96 + 2 * 8)[0]   # directory 2
    if not rva:
        return {}
    secs = []
    for i in range(nsec):
        o = pe + 24 + optsz + 40 * i
        vsz, va, rawsz, raw = struct.unpack_from("<IIII", img, o + 8)
        secs.append((va, max(vsz, rawsz), raw))

    def off(r):
        for va, sz, raw in secs:
            if va <= r < va + sz:
                return raw + r - va
        raise ValueError(f"resource RVA {r:#x} outside every section")

    base = off(rva)

    def name(v):
        if v & 0x80000000:
            o = base + (v & 0x7FFFFFFF)
            n = struct.unpack_from("<H", img, o)[0]
            return img[o + 2:o + 2 + 2 * n].decode("utf-16-le").upper()
        return v

    def entries(o):
        nn, ni = struct.unpack_from("<HH", img, o + 12)
        for i in range(nn + ni):
            yield struct.unpack_from("<II", img, o + 16 + 8 * i)

    out = {}
    for t, tsub in entries(base):
        for n, nsub in entries(base + (tsub & 0x7FFFFFFF)):
            for _lang, leaf in entries(base + (nsub & 0x7FFFFFFF)):
                drva, dsz = struct.unpack_from("<II", img, base + leaf)
                out[(name(t), name(n))] = img[off(drva):off(drva) + dsz]
                break
    return out


def icon_file(res, group):
    """An RT_GROUP_ICON and its images as an .ico file."""
    g = res[(RT_GROUP_ICON, group)]
    n = struct.unpack_from("<H", g, 4)[0]
    head, body, at = struct.pack("<HHH", 0, 1, n), b"", 6 + 16 * n
    for i in range(n):
        w, h, cc, rsv, planes, bpp, _size, rid = struct.unpack_from("<BBBBHHIH", g, 6 + 14 * i)
        data = res[(RT_ICON, rid)]
        head += struct.pack("<BBBBHHII", w, h, cc, rsv, planes, bpp, len(data), at + len(body))
        body += data
    return head + body


def lithtech_art(r):
    p = r.find("Lithtech.exe")
    res = pe_resources(r.read(p))
    return p, {"lithtech.ico": icon_file(res, 128)}      # IDR_MAINFRAME


# The extractions: the directory of assets/art/ that holds the files, the
# directory our resource script includes them from, what they are, and the
# function.
ARTS = [
    ("lithtech", "src/Engine/runtime/winbuild/lithtech/res", "the engine's icon", lithtech_art),
]
ART = REPO / "assets" / "art"


def committed_art(name):
    """{file name: bytes} of assets/art/<name>/."""
    d = ART / name
    if not d.is_dir():
        sys.exit(f"retailextract: no {d.relative_to(REPO)}/ -- the art is committed there")
    return {f.name: f.read_bytes() for f in sorted(d.iterdir()) if f.is_file()}


def write_res(resdir, out, origin):
    """Write {file name: bytes} into resdir, leaving files already right
    untouched (so make sees no change)."""
    resdir = Path(resdir)
    resdir.mkdir(parents=True, exist_ok=True)
    for name, data in out.items():
        dest = resdir / name
        if not dest.exists() or dest.read_bytes() != data:
            dest.write_bytes(data)
    print(f"== {origin} -> {resdir}/ ({', '.join(out)})")


def cmd_art(mode, retaildir=None):
    """write: assets/art/ from the retail game; check: fail unless it is
    what the retail game gives; install: assets/art/ into the directories
    the resource scripts include from (every build)."""
    if mode == "install":
        for name, resdir, what, _make in ARTS:
            write_res(REPO / resdir, committed_art(name), f"{what} (assets/art/{name}/)")
        return
    r = Retail(retaildir)
    bad = []
    for name, _resdir, what, make in ARTS:
        label, out = make(r)
        d = ART / name
        if mode == "write":
            d.mkdir(parents=True, exist_ok=True)
            for f in d.iterdir():
                if f.is_file() and f.name not in out:
                    f.unlink()
            write_res(d, out, f"{what}: {r.name}:{label}")
        elif committed_art(name) != out:
            bad.append(f"assets/art/{name}/")
    if bad:
        sys.exit(f"retailextract: {', '.join(bad)} not what the retail game gives -- "
                 "write it again: make art")
    if mode == "check":
        print("== assets/art/: the retail game's art, unchanged")


# --- build/retail-ranges.txt --------------------------------------------------

RANGES_HEAD = """\
## Where the retail game's bytes go in a game directory, beyond the files
## that the build copies whole (build/retail-files.txt lists those). This
## list holds no game data: only names, offsets, sizes and SHA-256 values.
## build/retailextract.py writes it from the installed retail game (`make
## retail-ranges`). A build with the retail game checks it. A build without
## the retail game (NODISCS=1) and the install scripts of a public archive
## (build/mkinstall.py) use it in place of the retail game.
##
## PE <path>
##   A file of the install that is a PE image (the build does not copy it
##   as game data).
## ZERO <archive> <offset> <size> <entry>
##   A retail game DLL in one of the archives: the build writes zeros over
##   its data in the game directory's copy. The offset is in the archive.
## ZSUM <archive> <size> <SHA-256>
##   The game directory's copy of that archive, with those zeros.
## The fields are separated by one TAB.
"""


class Ranges:
    def __init__(self):
        self.pe = set()
        self.zero = {}        # archive -> [(offset, size, entry)]
        self.zsum = {}        # archive -> (size, sha)


def load_ranges(path=None):
    path = path or REPO / "build" / "retail-ranges.txt"
    g = Ranges()
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if f[0] == "PE":
            g.pe.add(f[1])
        elif f[0] == "ZERO":
            g.zero.setdefault(f[1], []).append((int(f[2]), int(f[3]), f[4]))
        elif f[0] == "ZSUM":
            g.zsum[f[1]] = (int(f[2]), f[3])
        else:
            sys.exit(f"retailextract: {path}: an unknown line: {line[:60]}")
    return g


def zeroed_sha(path, zeros):
    """The SHA-256 of a file with the (offset, size) ranges as zeros."""
    h = hashlib.sha256()
    pos = 0
    with open(path, "rb") as f:
        for off, size, *_ in sorted(zeros) + [(os.path.getsize(path), 0)]:
            while pos < off:
                b = f.read(min(1 << 20, off - pos))
                h.update(b)
                pos += len(b)
            h.update(bytes(size))
            f.seek(size, 1)
            pos += size
    return h.hexdigest()


def make_ranges(r):
    """The lines of build/retail-ranges.txt, from the installed retail game."""
    lines = []
    for p in r.files:
        if r.head(p) == b"MZ":
            lines.append(f"PE\t{p}")
    for name in REZ:
        p = r.find(name)
        hits = rez_pe_entries(r.root / p)
        for ename, pos, sz in hits:
            lines.append(f"ZERO\t{p}\t{pos}\t{sz}\t{ename}")
        lines.append(f"ZSUM\t{p}\t{r.size(p)}\t{zeroed_sha(r.root / p, [(pos, sz) for _e, pos, sz in hits])}")
    return lines


def cmd_ranges(retaildir, mode):
    """write: build/retail-ranges.txt from the retail game; check: fail
    unless it is what the retail game gives."""
    r = Retail(retaildir)
    text = RANGES_HEAD + "".join(line + "\n" for line in make_ranges(r))
    path = REPO / "build" / "retail-ranges.txt"
    if mode == "write":
        path.write_text(text)
        print(f"== {path.relative_to(REPO)} written ({text.count(chr(10))} lines)")
    elif not path.exists() or path.read_text() != text:
        sys.exit(f"retailextract: {path.relative_to(REPO)} is not what the retail game gives -- "
                 "write it again: make retail-ranges")
    else:
        print(f"== {path.relative_to(REPO)}: as the retail game gives it")


def main():
    a = sys.argv[1:]
    cmds = {"resources": cmd_resources, "thirdparty": cmd_thirdparty,
            "openruntime": cmd_openruntime, "reference": cmd_reference}
    if a == ["art", "install"]:
        cmd_art("install")
    elif len(a) == 3 and a[0] == "art" and a[1] in ("write", "check"):
        cmd_art(a[1], a[2])
    elif len(a) == 3 and a[0] == "ranges" and a[1] in ("write", "check"):
        cmd_ranges(a[2], a[1])
    elif len(a) == 4 and a[0] == "thirdparty" and a[3] in ("retail", "open"):
        cmd_thirdparty(a[1], a[2], a[3])
    elif len(a) == 3 and a[0] in cmds:
        cmds[a[0]](a[1], a[2])
    elif len(a) == 2 and a[0] == "audit":
        sys.exit(cmd_audit(a[1]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
