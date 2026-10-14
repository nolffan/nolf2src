#!/usr/bin/env python3
"""The install scripts of a game directory's public archive.

  mkinstall.py <gamedir> <outdir> [isodir]

A game directory holds the retail game's data as well as what we built: the
.rez archives (with the retail game DLLs inside them zeroed), the movies,
the shipped autoexec.cfg and default profile, and, as third-party runtime,
RAD's binkw32.dll (legacy builds only) and the Microsoft C++ and MFC DLLs
(MANIFEST.txt's `data` and `THIRD-PARTY` rows: tools/retailextract.py). The
public archive (build/package.sh) leaves all of that out, and two scripts
put it back from the player's own copies of the two discs of No One Lives
Forever 2 -- the European or the USA release, as .iso images or as redump's
.bin/.cue (or its .zip), which the scripts convert to the .iso first -- and
of Sierra's English 1.3 update, nolf2-update_1x3.exe:

  linux-install.sh       bash, coreutils and python3 (its zlib inflates)
  windows-install.bat    cmd running the PowerShell it carries (5.1, as every
                         Windows 10 and 11 has; .NET's DeflateStream inflates)

Nothing is installed or run from the discs or the update, and neither
script reads ISO 9660 or an InstallShield header. An image is recognised by
its size and SHA-256, and then every byte the game needs is known; this
works it out against the images and writes it as a list:

  D <id> <size> <sha256> <name>    a disc image (the .iso)
  R <id> <size>                    its redump .bin (2352-byte sectors)
  U <id> <size> <sha256> <name>    the update
  M <id> <of> <offset> <size> <sha256>
                                   the update's payload: the Microsoft
                                   cabinet at <offset> of <of>, its one
                                   folder unpacked (MSZIP: deflate blocks,
                                   each with the previous one's output as
                                   its dictionary)
  S <name> <id>...                 a set of images the game installs from:
                                   Europe, USA, USA with the other dump of
                                   its disc 2 (redump's "(Alt)"), each with
                                   the update
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
                                   retail file <n> by, in order:
  C <length>                       its next bytes, as they are
  Z <length>                       zeros in place of its next bytes (the
                                   retail game DLLs blanked inside the .rez
                                   archives: build/all.sh's `resources`)
  L <base64>                       bytes of ours in place of its next ones
                                   (none yet: room for data edits a modern
                                   build may make)
  E                                the end of the file: the script checks
                                   its size and SHA-256 before it moves it
                                   into place

A file's flag is `-`, or `once` for autoexec.cfg and Profiles/Default.prf
(the shipped settings, which the game rewrites: written only if there are
none). So the result is the game directory as built, byte for byte. The
list goes at the end of each script, after a marker line; the scripts' code
is build/game-scripts/linux-install.sh and windows-install.ps1 (the .bat's
header is written here).

Writes <outdir>/linux-install.sh, <outdir>/windows-install.bat and
<outdir>/disc-files.txt, the game directory's paths the scripts write (the
archive leaves them out). <isodir> is rez/isos/, which must hold the .iso of
both discs of both releases (rez/fetch-isos.sh nolf2-eu nolf2-usa); the
update is rez/'s (rez/artifacts/patches/, assembled if it is not there),
and the retail game rez/ installs, rez/games/nolf2-eu-1.3/, says which
retail file each of ours is made from. Every way is read back and checked
against that file's SHA-256 here. Exits 3 if an image is missing.
"""
import base64
import hashlib
import io
import os
import re
import struct
import subprocess
import sys
import tarfile
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "rez", "tools"))
from isoextract import Iso, SECTOR  # noqa: E402
from sfxcab import find_cabinet  # noqa: E402

REZ = os.path.join(REPO, "rez")
RETAIL = os.path.join(REZ, "games", "nolf2-eu-1.3")
UPDATE = "patches/nolf2-update_1x3.exe"
SCRIPTS = os.path.join(REPO, "build", "game-scripts")
MARKER = "__NOLF2_INSTALL_DATA__"
CHUNK = 1 << 20
BLOCK = 4096
RAW_SECTOR = 2352
LITERAL_LINE = 3 * 1024          # raw bytes per L record (4 KB of base64)
LITERAL_MAX = 1 << 20            # more than this of ours means a wrong source

# The images: id -> redump's name (rez/isos/<name>.iso).
NOLF2 = "No One Lives Forever 2 - A Spy in H.A.R.M.'s Way"
DISCS = {
    "eu1": f"{NOLF2} (Europe) (Disc 1)",
    "eu2": f"{NOLF2} (Europe) (Disc 2)",
    "us1": f"{NOLF2} (USA) (Disc 1)",
    "us2": f"{NOLF2} (USA) (Disc 2)",
}
# redump's other dump of the USA disc 2, which rez/ does not fetch: its
# .iso's size and SHA-256, and the disc whose cabinet it has at the same
# offset (checked here whenever the image is in <isodir>).
ALIASES = {
    "us2alt": (f"{NOLF2} (USA) (Disc 2) (Alt)", 464687104,
               "46e4d552f14f8ca052f6b023aba71adadc575232863d2ca9832ebebf4d63384a", "us2"),
}
REGIONS = {"Europe": ("eu1", "eu2"), "USA": ("us1", "us2")}
SETS = [("Europe", ["eu1", "eu2"]), ("USA", ["us1", "us2"]), ("USA-alt", ["us1", "us2alt"])]

# The files the game rewrites, kept as their shipped copies (<name>.retail;
# tools/retailextract.py RETAIL_COPIES), and the live file each starts.
SETTINGS = {"autoexec.cfg.retail": "autoexec.cfg",
            "Default.prf.retail": "Profiles/Default.prf"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


class Image:
    """A file the scripts read: a disc's .iso, or the update (in memory)."""
    def __init__(self, ident, name, path=None, data=None):
        self.id, self.name = ident, name
        if data is None:
            self.size, self.sha = os.path.getsize(path), sha256(path)
            self.f = open(path, "rb")
        else:
            self.size, self.sha = len(data), hashlib.sha256(data).hexdigest()
            self.f = io.BytesIO(data)

    def read(self, off, n):
        self.f.seek(off)
        b = self.f.read(n)
        if len(b) != n:
            sys.exit(f"mkinstall: {self.name}: short read at {off}")
        return b


class Disc(Image):
    def __init__(self, ident, name, path):
        super().__init__(ident, name, path)
        self.files = {p.lower(): (ext * SECTOR, sz) for p, ext, sz in Iso(path).walk()}


# --- InstallShield 6 cabinets (what tools/unshield reads; its lib/file.c) ---

FILE_SPLIT, FILE_OBFUSCATED, FILE_COMPRESSED, FILE_INVALID = 1, 2, 4, 8


class Cabinets:
    """An InstallShield 6 cabinet set: data1.hdr and the volumes dataN.cab,
    each a range of an image. files: [(name, flags, expanded size, md5,
    [(image, offset, length), ...])], the ranges holding each file's data."""
    def __init__(self, hdr, volumes):
        self.volumes = volumes            # n -> (Image, offset, size)
        sig, _ver, _info, cdo = struct.unpack_from("<4sIII", hdr, 0)
        if sig != b"ISc(":
            sys.exit("mkinstall: not an InstallShield cabinet header")
        ftoff, = struct.unpack_from("<I", hdr, cdo + 0x0c)
        count, ftoff2 = struct.unpack_from("<II", hdr, cdo + 0x28)
        base = cdo + ftoff
        self.files = []
        for i in range(count):
            p = base + ftoff2 + i * 0x57
            flags, exp, comp, doff = struct.unpack_from("<HQQQ", hdr, p)
            md5 = hdr[p + 26:p + 42]
            name_off, = struct.unpack_from("<I", hdr, p + 58)
            vol, = struct.unpack_from("<H", hdr, p + 0x55)
            if flags & FILE_INVALID or doff == 0:
                continue
            name = hdr[base + name_off:hdr.index(b"\0", base + name_off)].decode("latin-1")
            stored = comp if flags & FILE_COMPRESSED else exp
            self.files.append((name, flags, exp, md5, self.ranges(i, flags, stored, doff, vol)))

    def volume_header(self, n):
        img, off, _size = self.volumes[n]
        v = struct.unpack("<16I", img.read(off + 20, 64))
        return {"first": v[2], "last": v[3], "first_off": v[4], "first_comp": v[8],
                "last_off": v[10], "last_comp": v[14]}

    def ranges(self, index, flags, stored, doff, vol):
        out, left = [], stored
        while left > 0:
            if vol not in self.volumes:
                sys.exit(f"mkinstall: cabinet file {index} runs past the last volume")
            img, base, _size = self.volumes[vol]
            if flags & FILE_SPLIT:
                h = self.volume_header(vol)
                if index == h["last"] and h["last_off"] != 0x7FFFFFFF:
                    off, n = h["last_off"], h["last_comp"]
                elif index == h["first"]:
                    off, n = h["first_off"], h["first_comp"]
                else:
                    sys.exit(f"mkinstall: cabinet file {index}: not in volume {vol}")
            else:
                off, n = doff, stored
            n = min(n, left)
            out.append((img, base + off, n))
            left -= n
            vol += 1
        return out


def read_ranges(ranges):
    for img, off, n in ranges:
        while n:
            k = min(n, CHUNK)
            yield img.read(off, k)
            off += k
            n -= k


def digest(ranges):
    h = hashlib.sha256()
    for b in read_ranges(ranges):
        h.update(b)
    return h.hexdigest()


def inflate_chunks(ranges):
    """The data of an InstallShield 6 compressed file: chunks of a 16-bit
    length and a raw deflate stream."""
    buf, gen = b"", read_ranges(ranges)
    while True:
        while len(buf) < 2:
            more = next(gen, None)
            if more is None:
                if buf:
                    sys.exit("mkinstall: a chunk's length is cut off")
                return
            buf += more
        n, = struct.unpack_from("<H", buf)
        while len(buf) < 2 + n:
            more = next(gen, None)
            if more is None:
                sys.exit("mkinstall: a chunk is cut off")
            buf += more
        z = zlib.decompressobj(-15)
        out = z.decompress(buf[2:2 + n])
        if not z.eof:
            sys.exit("mkinstall: a chunk is not a whole deflate stream")
        yield out
        buf = buf[2 + n:]


def unpack_folder(exe, base):
    """The one folder of the Microsoft cabinet at `base` of `exe`, unpacked,
    and its files: {name: (offset in the folder, size)}."""
    files_off, = struct.unpack_from("<I", exe, base + 16)
    nfolders, nfiles, flags = struct.unpack_from("<HHH", exe, base + 26)
    if nfolders != 1 or flags & 4:
        sys.exit("mkinstall: the update's cabinet is not one folder without reserve fields")
    off, nblocks, kind = struct.unpack_from("<IHH", exe, base + 36)
    if kind & 0xF not in (0, 1):
        sys.exit("mkinstall: the update's cabinet is neither MSZIP nor stored")
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
            sys.exit("mkinstall: an MSZIP block of the wrong size")
        out += piece
        window = bytes(piece[-32768:])
    files, pos = {}, base + files_off
    for _ in range(nfiles):
        size, foff, _folder = struct.unpack_from("<IIH", exe, pos)
        end = exe.index(b"\0", pos + 16)
        files[exe[pos + 16:end].decode("latin-1").replace("\\", "/").lstrip("/").lower()] = \
            (foff, size)
        pos = end + 1
    return bytes(out), files


# --- what each of ours is made of ---

class Ops:
    def __init__(self):
        self.ops, self.literal = [], 0

    def add(self, kind, n, b=None):
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


def ops_for(src, path):
    """The file at `path` against the retail file `src` (the same size), byte
    for byte: shared bytes copied, zeros where they differ written as zeros
    (a blanked DLL's own zero bytes join the run), anything else as ours."""
    if os.path.getsize(path) != os.path.getsize(src):
        return None
    ops = Ops()
    with open(path, "rb") as f, open(src, "rb") as r:
        while True:
            out = f.read(CHUNK)
            if not out:
                break
            ref = r.read(len(out))
            if out == ref:
                ops.add("C", len(out))
                continue
            for i in range(0, len(out), BLOCK):
                o, a = out[i:i + BLOCK], ref[i:i + BLOCK]
                zero = o.count(0) == len(o)
                inzero = ops.ops and ops.ops[-1][0] == "Z"
                if o == a and not (zero and inzero):
                    ops.add("C", len(o))
                elif zero:
                    ops.add("Z", len(o))
                else:
                    for j in range(len(o)):
                        inzero = ops.ops and ops.ops[-1][0] == "Z"
                        if o[j] == 0 and (inzero or a[j] != 0):
                            ops.add("Z", 1)
                        elif o[j] == a[j]:
                            ops.add("C", 1)
                        else:
                            ops.add("L", 1, o[j:j + 1])
    return ops


def way_line(kind, ranges):
    return f"W {kind} " + " ".join(f"{img.id}:{off}:{n}" for img, off, n in ranges)


def check_way(kind, ranges, size, sha, what):
    h, total = hashlib.sha256(), 0
    for b in (read_ranges(ranges) if kind == "copy" else inflate_chunks(ranges)):
        h.update(b)
        total += len(b)
    if total != size or h.hexdigest() != sha:
        sys.exit(f"mkinstall: {what} does not read back as the retail file")


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    game, outdir = sys.argv[1].rstrip("/"), sys.argv[2]
    isodir = sys.argv[3] if len(sys.argv) == 4 else os.path.join(REZ, "isos")
    paths = {i: os.path.join(isodir, n + ".iso") for i, n in DISCS.items()}
    missing = [p for p in paths.values() if not os.path.isfile(p)]
    if missing or not os.path.isfile(os.path.join(RETAIL, "MANIFEST.txt")):
        print("mkinstall: no disc images (%s) or no rez/games/nolf2-eu-1.3/ -- "
              "rez/fetch-isos.sh nolf2-eu nolf2-usa && rez/install-games.sh nolf2-eu-1.3"
              % ", ".join(missing or paths.values()), file=sys.stderr)
        sys.exit(3)
    discs = {i: Disc(i, DISCS[i], p) for i, p in paths.items()}

    # The other dump of a disc: the same cabinet at the same offset.
    aliases = {}
    for i, (name, size, sha, same) in ALIASES.items():
        p = os.path.join(isodir, name + ".iso")
        if os.path.isfile(p):
            d = Disc(i, name, p)
            if (d.size, d.sha) != (size, sha) or any(
                    d.files.get(k) != v or digest([(d,) + v]) != digest([(discs[same],) + v])
                    for k, v in discs[same].files.items() if k.startswith("data")):
                sys.exit(f"mkinstall: {name}.iso is not the image recorded in ALIASES")
        aliases[i] = (name, size, sha, same)

    # The update: its payload, unpacked; its own InstallShield cabinets.
    archive = os.path.join(REZ, "artifacts", UPDATE + ".tar.xz")
    if not os.path.isfile(archive):
        subprocess.run([os.path.join(REZ, "assemble-artifacts.sh"), os.path.basename(UPDATE)],
                       check=True, stdout=subprocess.DEVNULL)
    with tarfile.open(archive, "r:xz") as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        exe = tar.extractfile(members[0]).read()
    upd = Image("upd", os.path.basename(UPDATE), data=exe)
    cab_at = find_cabinet(exe)
    payload, pfiles = unpack_folder(exe, cab_at)
    pay = Image("pay", "the update's cabinet", data=payload)

    def cabset(find, prefix=""):
        """The cabinet set whose files find(name) -> (image, offset, size)."""
        img, off, size = find(prefix + "data1.hdr")
        hdr, vols, n = img.read(off, size), {}, 1
        while True:
            try:
                vols[n] = find(prefix + f"data{n}.cab")
            except KeyError:
                break
            n += 1
        return Cabinets(hdr, vols)

    cabs = {}
    for region, ids in REGIONS.items():
        def find(name, ids=ids):
            for i in ids:
                if name in discs[i].files:
                    return (discs[i],) + discs[i].files[name]
            raise KeyError(name)
        cabs[region] = cabset(find)
    ucabs = cabset(lambda name: (pay,) + pfiles[name], "disk1/")

    # Where each retail file came from (rez/install-games.sh's record).
    origin = {}
    for line in open(os.path.join(RETAIL, "MANIFEST.txt"), errors="replace"):
        if line.startswith("#") or "\t" not in line:
            continue
        rel, frm = line.rstrip("\n").split("\t", 1)
        origin[rel] = frm

    # What in the game directory came from the retail game, and from which
    # of its files (build/all.sh's MANIFEST.txt).
    wanted = {}                           # game path -> retail path
    for line in open(os.path.join(game, "MANIFEST.txt")):
        line = line.rstrip("\n")
        if line.startswith("#") or "\t" not in line:
            continue
        frm, rel = line.split("\t", 1)
        m = re.match(r"(data|THIRD-PARTY) ([^:]+):(.+?)( \(.*\))?$", frm)
        if not m:
            continue
        if m.group(2) != "nolf2-eu-1.3":
            sys.exit(f"mkinstall: {rel} came from {m.group(2)}, not nolf2-eu-1.3")
        wanted[rel] = m.group(3)
    for rel in list(wanted) + list(wanted.values()):
        if re.search(r"[\s\"'`$\\%!]", rel):
            sys.exit(f"mkinstall: {rel}: a name the scripts do not quote")

    def in_cabs(cs, path, size, md5, what):
        for name, flags, exp, fmd5, ranges in cs.files:
            if exp == size and fmd5 == md5:
                if flags & FILE_OBFUSCATED:
                    sys.exit(f"mkinstall: {what}: obfuscated in its cabinet")
                return ("is" if flags & FILE_COMPRESSED else "copy"), ranges
        sys.exit(f"mkinstall: {what}: not in the cabinets")

    # Each retail file, and the ways to read it.
    sources, vlines = {}, []
    for rp in sorted(set(wanted.values()), key=str.lower):
        path = os.path.join(RETAIL, rp)
        data_md5, size = hashlib.md5(), os.path.getsize(path)
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(CHUNK), b""):
                data_md5.update(b)
        md5, sha = data_md5.digest(), sha256(path)
        frm = origin.get(rp, "")
        ways = []
        if frm.startswith(UPDATE + ":"):
            ways.append(in_cabs(ucabs, path, size, md5, rp))
        else:
            for region, ids in REGIONS.items():
                if ".iso:" in frm:            # stored as it is on disc 1
                    disc = discs[ids[0]]
                    off, n = disc.files[frm.split(".iso:", 1)[1].lower()]
                    ways.append(("copy", [(disc, off, n)]))
                else:
                    ways.append(in_cabs(cabs[region], path, size, md5, f"{rp} ({region})"))
        lines = []
        for kind, ranges in ways:
            check_way(kind, ranges, size, sha, rp)
            line = way_line(kind, ranges)
            if line not in lines:
                lines.append(line)
            # the other dump of a disc: the same ranges, read from it
            for i, (_name, _size, _sha, same) in aliases.items():
                alt = line.replace(f" {same}:", f" {i}:")
                if alt != line and alt not in lines:
                    lines.append(alt)
        n = len(sources) + 1
        sources[rp] = n
        vlines.append(f"V {n} {size} {sha} {rp}")
        vlines += lines

    records, literal = [], 0
    for rel in sorted(wanted, key=str.lower):
        rp = wanted[rel]
        path = os.path.join(game, rel)
        ops = ops_for(os.path.join(RETAIL, rp), path)
        if ops is None:
            sys.exit(f"mkinstall: {rel}: not made from nolf2-eu-1.3:{rp}")
        literal += ops.literal
        size, sha = os.path.getsize(path), sha256(path)
        records.append(f"F {rel} {size} {sha} - {sources[rp]}")
        records.extend(ops.lines())
        records.append("E")
        if rel in SETTINGS:
            records.append(f"F {SETTINGS[rel]} {size} {sha} once {sources[rp]}")
            records.extend(ops.lines())
            records.append("E")
    if literal > LITERAL_MAX:
        sys.exit(f"mkinstall: {literal} bytes would ship as literal data")

    data = ["NOLF2INSTALL 2"]
    for i, d in discs.items():
        data.append(f"D {i} {d.size} {d.sha} {d.name}")
        data.append(f"R {i} {d.size // SECTOR * RAW_SECTOR}")
    for i, (name, size, sha, _same) in aliases.items():
        data.append(f"D {i} {size} {sha} {name}")
        data.append(f"R {i} {size // SECTOR * RAW_SECTOR}")
    data.append(f"U {upd.id} {upd.size} {upd.sha} {upd.name}")
    data.append(f"M {pay.id} {upd.id} {cab_at} {pay.size} {pay.sha}")
    for name, ids in SETS:
        data.append(f"S {name} {' '.join(ids)} {upd.id}")
    data += vlines + records

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
    with open(os.path.join(outdir, "disc-files.txt"), "w") as f:
        for rel in written:
            f.write(rel + "\n")
    print(f"   install scripts: {len(written)} files from {len(sources)} retail files "
          f"on the discs and in the update, {literal} bytes of ours")


# cmd runs this; everything from the first #__NOLF2_PS__ line on is never
# parsed by it (`exit /b` comes first). The PowerShell between the markers is
# written to a temporary .ps1 and run with -File, which passes the dropped or
# typed paths through as they are.
BAT_HEADER = r"""@echo off
rem windows-install.bat -- install the game data from your NOLF2 discs.
rem
rem   Drop the images of both discs of No One Lives Forever 2 (the European
rem   or the USA release) and Sierra's English 1.3 update,
rem   nolf2-update_1x3.exe, onto this file -- or put them in this folder or
rem   the one above it and double-click it. Then start the game with
rem   NOLF2.exe. An image is a plain .iso, redump's .bin (or its .cue), or
rem   redump's .zip download; a .bin or .zip is first converted to a
rem   temporary .iso in this folder (about 0.6 GB a disc, removed at the end).
rem
rem It checks each file's SHA-256, copies the game's data out of them into
rem this folder and checks every file it writes. Nothing is installed or run
rem from them, and nothing else is changed.
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
