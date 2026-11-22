#!/usr/bin/env python3
"""Install the retail game, the SDK's source or the demo's engine from your
own images and installers, and check it.

  build/discs.py install <list> <outdir> [image ...]
  build/discs.py verify  <list> <outdir>
  build/discs.py find    <list> [image ...]

<list> is one of the lists in build/ (or its name):

  retail  build/retail-files.txt: No One Lives Forever 2 (Europe) with the
          English 1.3 update, as its setup and then the update install it:
          the two disc images and the update's installer,
          nolf2-update_1x3.exe. The build takes its data from it, and
          make progress compares against its binaries.
  sdk     build/sdk-files.txt: the WONAPI source of the LithTech Jupiter
          SDK (build 51), from the image of its CD. ServerDir.dll is
          built from it.
  demo    build/demo-files.txt: the engine of the NOLF2 multiplayer demo,
          from its installer, nolf2_mpdemo_en.exe. make progress reads it
          (ext/tools/demoimports.py).

No part of these is in this repository. Each list holds only metadata: for
each file its size, its SHA-256, and where its bytes are in which image.
This script uses that list and nothing else to install the files, as the
setup does. It runs no part of an image or installer.

The images are the files you give on the command line. If you give no
files, the script looks in $NOLF2_ISOS, or else in isos/ at the root of
the repository. Each image can be:

  .iso   a plain image, 2048-byte sectors (your own rip, for example)
  .bin   a raw image, 2352-byte MODE1 sectors (for example a redump dump)
  .cue   a cue sheet: the .bin it names is used
  .zip   a zip that holds one such .bin or .iso (it is read in place;
         nothing is unpacked to the disk)
  .exe   an installer (the update, the demo), as it was published

A disc is recognised by the volume label and the volume size in its file
system. Its image does not have to be identical to a known image: every
file that the install writes is checked against the list (its size and its
SHA-256). Thus any correct copy of the discs works. An installer is
recognised by its size and SHA-256.

The list's lines (the fields are separated by one TAB):

  D <id> <volume label> <volume blocks> <image size> <image SHA-256> <redump ID> <name>
      A disc. The image size and SHA-256 are those of the .iso of one known
      good image (its redump dump; the public install scripts recognise a
      disc by them). The redump ID is "-" for a disc that redump does not
      have.
  U <id> <size> <SHA-256> <name>
      An installer: a self-extracting Microsoft cabinet.
  M <id> <installer> <offset> <size> <SHA-256>
      The installer's payload: the one folder of the Microsoft cabinet at
      <offset> of the installer, unpacked (MSZIP: deflate blocks, each with
      the previous one's output as its dictionary).
  S <set> <id> ...
      A set of discs that the public install scripts accept.
  I <set> <id> ...
      The images that `install` needs.
  F <path> <size> <SHA-256>
      One file of the install ...
  W copy|is <id>:<offset>:<length> ...
      ... and one way to read it: those byte ranges, joined, are the file
      (copy), or the InstallShield 6 cabinet data that holds it (is: a run
      of chunks, each a 16-bit length and a raw deflate stream). A file
      split across cabinets has one range in each. The first way whose
      images are all found is used.

`install` writes every file of the list into <outdir>. A file that is
already correct stays. Each file is written to <name>.part, checked, and
then renamed. At the end the script writes <outdir>/.retail-files, a copy of
the list that it installed. `verify` checks every file of <outdir> against
the list: all the files must be there, with the correct size and SHA-256.
Exit status 0 if they are, 1 if not. `find` shows which image is which.

Exit status 3 if an image is missing: the message tells you what to supply.

build/mkinstall.py reads build/retail-files.txt too: the install scripts
of a public archive read the same byte ranges out of the player's disc
images.
"""
import hashlib
import os
import re
import struct
import sys
import zipfile
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTS = {"retail": "retail-files.txt", "sdk": "sdk-files.txt", "demo": "demo-files.txt"}
SECTOR = 2048
RAW_SECTOR = 2352
RAW_HEAD = 16                               # sync (12) + header (4), MODE1
SYNC = b"\x00" + b"\xff" * 10 + b"\x00"
CHUNK = 1 << 20
EXTS = (".iso", ".bin", ".cue", ".zip", ".exe")
STAMP = ".retail-files"


def list_path(name):
    if name in LISTS:
        return os.path.join(REPO, "build", LISTS[name])
    return name


class Disc:
    def __init__(self, ident, label, blocks, size, sha, redump, name):
        self.id, self.label, self.blocks = ident, label, int(blocks)
        self.size, self.sha, self.redump, self.name = int(size), sha, redump, name


class Installer:
    def __init__(self, ident, size, sha, name):
        self.id, self.size, self.sha, self.name = ident, int(size), sha, name


class Payload:
    def __init__(self, ident, of, offset, size, sha):
        self.id, self.of, self.offset = ident, of, int(offset)
        self.size, self.sha = int(size), sha


class File:
    def __init__(self, path, size, sha):
        self.path, self.size, self.sha = path, int(size), sha
        self.ways = []                       # [(kind, [(id, offset, length)])]


class List:
    """A list of build/: its images and its files."""
    def __init__(self, path):
        self.path = path
        self.discs, self.installers, self.payloads = {}, {}, {}
        self.sets, self.need, self.files = [], [], []
        for line in open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            f = line.split("\t")
            if f[0] == "D":
                self.discs[f[1]] = Disc(*f[1:8])
            elif f[0] == "U":
                self.installers[f[1]] = Installer(*f[1:5])
            elif f[0] == "M":
                self.payloads[f[1]] = Payload(*f[1:6])
            elif f[0] == "S":
                self.sets.append((f[1], f[2].split()))
            elif f[0] == "I":
                self.need = f[2].split()
            elif f[0] == "F":
                self.files.append(File(f[1], f[2], f[3]))
            elif f[0] == "W" and self.files:
                ranges = []
                for r in f[2].split():
                    i, off, n = r.rsplit(":", 2)
                    ranges.append((i, int(off), int(n)))
                self.files[-1].ways.append((f[1], ranges))
            else:
                sys.exit(f"discs.py: {path}: a line it does not know: {line[:60]}")


def load(name="retail"):
    return List(list_path(name))


# --- disc images and installers ---------------------------------------------

class Image:
    """The 2048-byte user data of one disc image, read from any of the
    accepted formats. Reads that go forward are cheap in all of them; a
    .zip goes back to the start of its member for a read that goes back."""

    def __init__(self, path):
        self.path, self.label = path, os.path.basename(path)
        self.zip = self.f = None
        src = path
        if path.lower().endswith(".cue"):
            src = self._cue(path)
        if zipfile.is_zipfile(src):
            self.zip = zipfile.ZipFile(src)
            members = [i for i in self.zip.infolist()
                       if i.filename.lower().endswith((".bin", ".iso"))]
            if len(members) != 1:
                raise ValueError("not one .bin or .iso in the zip")
            self.member = members[0]
            self.f = self.zip.open(self.member)
            self.length = self.member.file_size
        else:
            self.f = open(src, "rb")
            self.length = os.path.getsize(src)
        head = self.f.read(len(SYNC))
        self.raw = head == SYNC and self.length % RAW_SECTOR == 0
        self._rewind()

    @staticmethod
    def _cue(path):
        text = open(path, encoding="latin-1").read()
        m = re.search(r'^\s*FILE\s+"([^"]+)"', text, re.M | re.I)
        if not m or not re.search(r"TRACK\s+01\s+MODE1/(2352|2048)", text, re.I):
            raise ValueError("not a cue sheet of one MODE1 data track")
        return os.path.join(os.path.dirname(path), m.group(1))

    def _rewind(self):
        if self.zip:
            self.f.close()
            self.f = self.zip.open(self.member)
        else:
            self.f.seek(0)
        self.pos = 0

    def _seek(self, raw_off):
        if raw_off < self.pos:
            self._rewind()
        if self.zip:
            while self.pos < raw_off:      # forward: read and drop
                n = len(self.f.read(min(CHUNK, raw_off - self.pos)))
                if not n:
                    raise EOFError
                self.pos += n
        else:
            self.f.seek(raw_off)
            self.pos = raw_off

    def _read(self, n):
        b = self.f.read(n)
        self.pos += len(b)
        return b

    def chunks(self, off, n):
        """The user data bytes off .. off + n, in chunks."""
        if not self.raw:
            self._seek(off)
            while n:
                b = self._read(min(CHUNK, n))
                if not b:
                    raise EOFError
                n -= len(b)
                yield b
            return
        sec, within = divmod(off, SECTOR)
        self._seek(sec * RAW_SECTOR)
        per = CHUNK // SECTOR
        while n:
            buf = self._read(RAW_SECTOR * per)
            if not buf or len(buf) % RAW_SECTOR and len(buf) < RAW_SECTOR:
                raise EOFError
            while len(buf) % RAW_SECTOR:
                more = self._read(RAW_SECTOR - len(buf) % RAW_SECTOR)
                if not more:
                    raise EOFError
                buf += more
            data = b"".join(buf[i + RAW_HEAD:i + RAW_HEAD + SECTOR]
                            for i in range(0, len(buf), RAW_SECTOR))
            data = data[within:within + n]
            within = 0
            n -= len(data)
            yield data

    def read(self, off, n):
        return b"".join(self.chunks(off, n))

    def volume(self):
        """(volume label, volume size in blocks) of its ISO 9660 file system."""
        pvd = self.read(16 * SECTOR, SECTOR)
        if pvd[1:6] != b"CD001" or pvd[0] != 1:
            return None
        return pvd[40:72].decode("ascii", "replace").rstrip(), struct.unpack_from("<I", pvd, 80)[0]


class Memory:
    """An installer's payload, unpacked in memory."""
    def __init__(self, data, label):
        self.data, self.label = data, label

    def chunks(self, off, n):
        if off + n > len(self.data):
            raise EOFError
        for i in range(off, off + n, CHUNK):
            yield self.data[i:min(i + CHUNK, off + n)]


def unpack_folder(exe, base):
    """The one folder of the Microsoft cabinet at `base` of `exe`, unpacked."""
    if exe[base:base + 4] != b"MSCF":
        raise ValueError("no Microsoft cabinet at the offset of the list")
    nfolders, _nfiles, flags = struct.unpack_from("<HHH", exe, base + 26)
    if nfolders != 1 or flags & 4:
        raise ValueError("the cabinet is not one folder without reserve fields")
    off, nblocks, kind = struct.unpack_from("<IHH", exe, base + 36)
    if kind & 0xF not in (0, 1):
        raise ValueError("the cabinet is neither MSZIP nor stored")
    p, out, window = base + off, bytearray(), b""
    for _ in range(nblocks):
        _csum, cb, cu = struct.unpack_from("<IHH", exe, p)
        block = exe[p + 8:p + 8 + cb]
        p += 8 + cb
        if kind & 0xF == 0:
            piece = block
        else:
            z = zlib.decompressobj(-15, zdict=window) if window else zlib.decompressobj(-15)
            piece = z.decompress(block[2:]) + z.flush()
        if len(piece) != cu:
            raise ValueError("an MSZIP block of the wrong size")
        out += piece
        window = bytes(piece[-32768:])
    return bytes(out)


def candidates(args):
    """The image files to look at: the arguments, or the files in
    $NOLF2_ISOS or isos/ (and the directories given)."""
    if args:
        out = []
        for a in args:
            if os.path.isdir(a):
                out += candidates_in(a)
            else:
                out.append(a)
        return out
    d = os.environ.get("NOLF2_ISOS") or os.path.join(REPO, "isos")
    return candidates_in(d)


def candidates_in(d):
    if not os.path.isdir(d):
        return []
    names = sorted(n for n in os.listdir(d) if n.lower().endswith(EXTS))
    # .iso first (no conversion), and a .bin before the .cue that names it
    order = {e: i for i, e in enumerate(EXTS)}
    names.sort(key=lambda n: order[os.path.splitext(n)[1].lower()])
    return [os.path.join(d, n) for n in names]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def identify(lst, paths, quiet=False):
    """{id: Image or Memory} for the images among `paths` that the list
    names: the first image found for each, and the payload of each
    installer found."""
    found, seen = {}, set()
    want = set(lst.need)
    for p in paths:
        if want <= set(found):
            break
        try:
            real = os.path.realpath(Image._cue(p) if p.lower().endswith(".cue") else p)
        except (OSError, ValueError):
            real = p
        if real in seen:
            continue
        seen.add(real)
        name = os.path.basename(p)
        if p.lower().endswith(".exe"):
            size = os.path.getsize(p)
            hits = [u for u in lst.installers.values()
                    if u.id not in found and u.size == size]
            if hits and sha256_file(p) == hits[0].sha:
                found[hits[0].id] = p
                if not quiet:
                    print(f"   {name}: {hits[0].name}")
            elif not quiet and lst.installers:
                print(f"   {name}: not an installer of this list")
            continue
        if not lst.discs:
            continue
        try:
            img = Image(p)
            vol = img.volume()
        except (OSError, ValueError, EOFError, zipfile.BadZipFile) as e:
            if not quiet:
                print(f"   {name}: not read ({e})")
            continue
        ids = [d.id for d in lst.discs.values()
               if d.id not in found and vol == (d.label, d.blocks)]
        for i in ids:
            found[i] = img
        if not quiet:
            print(f"   {name}: " + (f"disc {', '.join(ids)} ({vol[0]})" if ids
                                    else "not a disc of this list"))
    # each installer's payload, unpacked (and checked)
    for m in lst.payloads.values():
        if m.of not in found or isinstance(found[m.of], Memory):
            continue
        with open(found[m.of], "rb") as f:
            exe = f.read()
        try:
            data = unpack_folder(exe, m.offset)
        except (ValueError, struct.error) as e:
            raise SystemExit(f"error: {found[m.of]}: {e}")
        if len(data) != m.size or hashlib.sha256(data).hexdigest() != m.sha:
            raise SystemExit(f"error: {found[m.of]}: its cabinet is not the one of the list")
        found[m.id] = Memory(data, os.path.basename(found[m.of]))
    return found


WHAT = {
    "retail": "No One Lives Forever 2 (Europe) and its English 1.3 update",
    "sdk": "the LithTech Jupiter SDK (build 51)",
    "demo": "the NOLF2 multiplayer demo",
}


def missing_message(lst, found, name):
    lines = [f"error: images of {WHAT.get(name, name)} are missing. Bring your own:"]
    for i in lst.need:
        if i in found:
            continue
        if i in lst.discs:
            d = lst.discs[i]
            rid = (f", redump ID {d.redump}" if d.redump != "-" else
                   f" (as a .iso: {d.size} bytes, SHA-256 {d.sha})")
            lines.append(f"  the disc with the volume label \"{d.label}\": {d.name}{rid}")
        else:
            u = lst.installers[i]
            lines.append(f"  the installer {u.name} ({u.size} bytes, SHA-256 {u.sha})")
    lines += [
        "Put them in isos/ at the root of the repository (a hard link is good:",
        "ln <image> isos/), or set NOLF2_ISOS=<directory>. A disc image can be a",
        ".iso, a .bin with its .cue, or a .zip that holds one of them; an",
        "installer is the .exe as it was published.",
        "See docs/BUILDING.md, \"What you need\".",
    ]
    return "\n".join(lines)


# --- reading a file -------------------------------------------------------------

def read_ranges(found, ranges):
    for i, off, n in ranges:
        yield from found[i].chunks(off, n)


def inflate_chunks(gen):
    """The data of an InstallShield 6 compressed file: chunks of a 16-bit
    length and a raw deflate stream."""
    buf = b""
    while True:
        while len(buf) < 2:
            more = next(gen, None)
            if more is None:
                if buf:
                    raise ValueError("a chunk's length is cut off")
                return
            buf += more
        n, = struct.unpack_from("<H", buf)
        while len(buf) < 2 + n:
            more = next(gen, None)
            if more is None:
                raise ValueError("a chunk is cut off")
            buf += more
        z = zlib.decompressobj(-15)
        out = z.decompress(buf[2:2 + n])
        if not z.eof:
            raise ValueError("a chunk is not a whole deflate stream")
        yield out
        buf = buf[2 + n:]


def file_data(found, kind, ranges):
    """The bytes of a file, in chunks, read the way the W line says."""
    gen = read_ranges(found, ranges)
    return gen if kind == "copy" else inflate_chunks(gen)


def way_for(found, f):
    for kind, ranges in f.ways:
        if all(i in found for i, _o, _n in ranges):
            return kind, ranges
    return None


# --- install and verify -------------------------------------------------------

def correct(path, f):
    return os.path.isfile(path) and os.path.getsize(path) == f.size and \
        sha256_file(path) == f.sha


def install(name, outdir, args):
    lst = load(name)
    found = identify(lst, candidates(args))
    if not set(lst.need) <= set(found):
        print(missing_message(lst, found, name), file=sys.stderr)
        return 3
    os.makedirs(outdir, exist_ok=True)
    stamp = os.path.join(outdir, STAMP)
    if os.path.exists(stamp):
        os.unlink(stamp)                   # not whole until the end
    plan = []
    for f in lst.files:
        w = way_for(found, f)
        if w is None:
            print(f"error: {lst.path}: no way to read {f.path} from the images found",
                  file=sys.stderr)
            return 1
        plan.append((f, w))
    written = kept = 0
    # forward through each image (a .zip is read once)
    for f, (kind, ranges) in sorted(plan, key=lambda p: (p[1][1][0][0], p[1][1][0][1])):
        dest = os.path.join(outdir, f.path)
        if correct(dest, f):
            kept += 1
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        part = dest + ".part"
        h, size = hashlib.sha256(), 0
        where = found[ranges[0][0]].label
        try:
            with open(part, "wb") as out:
                for b in file_data(found, kind, ranges):
                    h.update(b)
                    size += len(b)
                    out.write(b)
        except (EOFError, ValueError, zlib.error) as e:
            os.unlink(part)
            print(f"error: {where} does not hold {f.path} as the list says "
                  f"({e or 'it ends too soon'}): it is not a whole, correct copy", file=sys.stderr)
            return 1
        if size != f.size or h.hexdigest() != f.sha:
            os.unlink(part)
            print(f"error: {f.path} from {where} is not the retail file "
                  f"(SHA-256 {h.hexdigest()}, the list has {f.sha}): the image is not "
                  "a correct copy", file=sys.stderr)
            return 1
        os.replace(part, dest)
        written += 1
    with open(lst.path, "rb") as src, open(stamp, "wb") as out:
        out.write(src.read())
    print(f"   {written} files written, {kept} already correct -> {outdir}")
    return 0


def verify(name, outdir):
    lst = load(name)
    bad = []
    for f in lst.files:
        p = os.path.join(outdir, f.path)
        if not os.path.isfile(p):
            bad.append(f"missing  {f.path}")
        elif os.path.getsize(p) != f.size or sha256_file(p) != f.sha:
            bad.append(f"changed  {f.path}")
    for line in bad:
        print(f"   {line}")
    if bad:
        return 1
    print(f"   all {len(lst.files)} files match {os.path.relpath(lst.path, REPO)}")
    return 0


def main():
    a = sys.argv[1:]
    if a[:1] == ["install"] and len(a) >= 3:
        return install(a[1], a[2], a[3:])
    if a[:1] == ["verify"] and len(a) == 3:
        return verify(a[1], a[2])
    if a[:1] == ["find"] and len(a) >= 2:
        lst = load(a[1])
        found = identify(lst, candidates(a[2:]))
        if not set(lst.need) <= set(found):
            print(missing_message(lst, found, a[1]), file=sys.stderr)
            return 3
        return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
