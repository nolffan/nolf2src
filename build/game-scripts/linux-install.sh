#!/usr/bin/env bash
# linux-install.sh -- install the game data from your NOLF2 discs.
#
#   ./linux-install.sh <disc image> <disc image> <update>
#   ./linux-install.sh                 (finds them in this directory or the
#                                       one above it)
#
# The images are the two discs of No One Lives Forever 2 -- the European or
# the USA release -- in either order, each as any of
#
#   .iso   a plain image (2048-byte sectors), e.g. your own rip
#   .bin   redump's raw image (2352-byte sectors), or its .cue
#   .zip   redump's download as archive.org serves it (the .cue and .bin)
#
# and <update> is Sierra's English 1.3 update, nolf2-update_1x3.exe, as it
# was published. A .bin, .cue or .zip is first converted to a temporary .iso
# in this directory (about 0.6 GB a disc, removed at the end). The script
# checks each file's SHA-256, then copies the game's data out of them into
# this directory -- the .rez archives (with the retail game DLLs inside them
# zeroed: the game DLLs here are built from source), the movies, the shipped
# settings, and Bink and the Microsoft runtime where this build uses them --
# and checks every file it writes. Nothing is installed or run from the
# discs or the update, and nothing else is changed. It can be run again: a
# file already in place is checked and kept. Then play with ./linux-run.sh
# (or ./linux-run-launcher.sh).
#
# NOLF2's setup stores its files compressed, in InstallShield cabinets that
# span both discs, and the update packs its own into a Microsoft cabinet:
# python3 (its zlib) unpacks them, with bash, sha256sum, stat and sed
# (GNU coreutils; a Steam Deck has them all). The list of files, at the end
# of this script, says for each one which bytes of which image it is made
# of (tools/mkinstall.py).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="$HERE/$(basename "${BASH_SOURCE[0]}")"
ME=linux-install.sh

for t in python3 sha256sum stat sed; do
    command -v "$t" >/dev/null || { echo "$ME: needs $t" >&2; exit 1; }
done

data() { sed -n '/^__NOLF2_INSTALL_DATA__$/,$p' "$SELF" | tail -n +2; }

# The images: their sizes and checksums, and the sets the game installs
# from, from the list.
declare -A SIZE SHA NAME RAW HAVE
SETS=()
while read -r tag id size sha name; do
    case "$tag" in
    D|U) SIZE[$id]=$size; SHA[$id]=$sha; NAME[$id]=$name ;;
    R)   RAW[$id]=$size ;;
    S)   SETS+=("$id $size $sha $name") ;;   # name, then its images
    esac
done < <(data)

# complete: is there a set every image of which is found?
complete() {
    local s i ok
    for s in "${SETS[@]}"; do
        ok=1
        for i in ${s#* }; do [ -n "${HAVE[$i]:-}" ] || ok=0; done
        [ $ok = 0 ] || return 0
    done
    return 1
}

# Converted images, removed however the script ends.
TEMPS=()
cleanup() { [ ${#TEMPS[@]} -eq 0 ] || rm -f "${TEMPS[@]}"; }
trap cleanup EXIT

# raw <cmd> <file> [out]: a redump image's raw (2352-byte sector) data.
#   raw size <.bin|.zip>          its size (a .zip's one .bin)
#   raw iso  <.bin|.zip> <out>    the 2048 bytes of user data of each sector
#                                 (after the 16-byte sync and header, and
#                                 on a MODE2 track its 8-byte subheader)
raw() {
    python3 - "$@" <<'PY'
import sys, zipfile
cmd, src = sys.argv[1], sys.argv[2]
try:
    z = zipfile.ZipFile(src) if zipfile.is_zipfile(src) else None
except (zipfile.BadZipFile, OSError):    # not a disc: matches no size
    z = None
    if src.lower().endswith(".zip"):
        print(0)
        sys.exit(0)
if z:
    bins = [i for i in z.infolist() if i.filename.lower().endswith(".bin")]
    if len(bins) != 1:                    # not a disc: matches no size
        print(0)
        sys.exit(0)
    size, f = bins[0].file_size, (z.open(bins[0]) if cmd == "iso" else None)
else:
    import os
    size, f = os.path.getsize(src), (open(src, "rb") if cmd == "iso" else None)
if cmd == "size":
    print(size)
    sys.exit(0)
S, B, k = 2352, 512, None
with open(sys.argv[3], "wb") as out:
    while True:
        buf = f.read(S * B)
        if not buf:
            break
        while len(buf) % S:               # a zip stream can read short
            more = f.read(S - len(buf) % S)
            if not more:
                sys.exit(f"linux-install.sh: {src}: not whole 2352-byte sectors")
            buf += more
        # the user data: after the 16-byte sync and header (MODE1, the
        # European discs), and the 8-byte subheader of MODE2 (the USA ones),
        # the track's mode as its first sector's header gives it
        if k is None:
            k = 24 if buf[15] == 2 else 16
        out.write(b"".join(buf[i + k:i + k + 2048] for i in range(0, len(buf), S)))
PY
}

# take <file> <label>: which image a file is, if any (by size, then SHA-256)
take() {
    local f=$1 label=$2 size id sum=
    size=$(stat -L -c %s "$f")
    for id in "${!SIZE[@]}"; do
        [ -z "${HAVE[$id]:-}" ] && [ "$size" = "${SIZE[$id]}" ] || continue
        if [ -z "$sum" ]; then
            echo "checking $label ..."
            sum=$(sha256sum < "$f" | cut -d' ' -f1)
        fi
        if [ "$sum" = "${SHA[$id]}" ]; then
            HAVE[$id]=$f
            echo "  ${NAME[$id]}"
            return 0
        fi
    done
    [ -z "$sum" ] || echo "  the size of an image, but not its contents (a bad copy?)"
    return 1
}

CANDIDATES=("$@")
if [ ${#CANDIDATES[@]} -eq 0 ]; then
    # .iso first: one is used as it is, the others need converting.
    shopt -s nullglob nocaseglob
    CANDIDATES=("$HERE"/*.iso "$HERE"/../*.iso "$HERE"/*.exe "$HERE"/../*.exe
                "$HERE"/*.bin "$HERE"/../*.bin "$HERE"/*.zip "$HERE"/../*.zip)
    shopt -u nullglob nocaseglob
fi
for f in "${CANDIDATES[@]}"; do
    complete && break
    [ -f "$f" ] || { echo "$ME: $f: no such file" >&2; exit 1; }
    label=$(basename "$f")
    case "${f,,}" in
    *.cue)
        bin=$(sed -n 's/^[[:space:]]*FILE[[:space:]]*"\(.*\)"[[:space:]].*/\1/p' "$f" | head -1)
        grep -qi 'TRACK[[:space:]]*01[[:space:]]*MODE[12]/2352' "$f" && [ -n "$bin" ] || {
            echo "  $label: not a one-track MODE1/2352 or MODE2/2352 cue sheet; skipped"; continue; }
        f="$(dirname "$f")/$bin"
        [ -f "$f" ] || { echo "$ME: $label names $bin, which is not beside it" >&2; exit 1; }
        ;& # on as the .bin
    *.bin|*.zip)
        size=$(raw size "$f")
        for id in "${!RAW[@]}"; do
            [ -z "${HAVE[$id]:-}" ] && [ "$size" = "${RAW[$id]}" ] || continue
            tmp="$HERE/.disc-${#TEMPS[@]}.iso.part"
            TEMPS+=("$tmp")
            echo "converting $label to an .iso ..."
            raw iso "$f" "$tmp"
            take "$tmp" "$label (converted)" || rm -f "$tmp"
            break
        done ;;
    *)  take "$f" "$label" || true ;;
    esac
done
if ! complete; then
    echo "$ME: these are needed, and not all were found:" >&2
    for s in "${SETS[@]}"; do
        echo "  ${s%% *}:" >&2
        for id in ${s#* }; do
            if [ -n "${HAVE[$id]:-}" ]; then echo "    found:   ${NAME[$id]}" >&2
            else echo "    missing: ${NAME[$id]} (${SIZE[$id]} bytes, SHA-256 ${SHA[$id]})" >&2; fi
        done
    done
    echo "  (a disc as an .iso, or redump's .bin/.cue or .zip of it)" >&2
    exit 1
fi

# The files: python3 reads the list and the images, writes each file beside
# its place, checks it and moves it there.
ARGS=()
for id in "${!HAVE[@]}"; do ARGS+=("$id=${HAVE[$id]}"); done
python3 - "$SELF" "$HERE" "${ARGS[@]}" <<'PY'
import base64, hashlib, os, struct, sys, zlib
self_path, here = sys.argv[1], sys.argv[2]
have = dict(a.split("=", 1) for a in sys.argv[3:])
text = open(self_path, "rb").read().decode("latin-1")
lines = text[text.index("\n__NOLF2_INSTALL_DATA__\n") + 24:].splitlines()
CHUNK = 1 << 20

def fail(msg):
    sys.exit(f"linux-install.sh: {msg}")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()

# The update's payload: the one folder of its Microsoft cabinet, unpacked.
memory = {}
for l in lines:
    p = l.split(" ")
    if p[0] == "M" and p[2] in have:
        ident, base, size, sha = p[1], int(p[3]), int(p[4]), p[5]
        exe = open(have[p[2]], "rb").read()
        files_off, = struct.unpack_from("<I", exe, base + 16)
        off, nblocks, kind = struct.unpack_from("<IHH", exe, base + 36)
        pos, out, window = base + off, bytearray(), b""
        for _ in range(nblocks):
            _csum, cb, cu = struct.unpack_from("<IHH", exe, pos)
            block = exe[pos + 8:pos + 8 + cb]
            pos += 8 + cb
            if kind & 15 == 0:
                piece = block
            else:            # MSZIP: "CK", deflate with the last 32 KB as history
                z = zlib.decompressobj(-15, zdict=window) if window else zlib.decompressobj(-15)
                piece = z.decompress(block[2:]) + z.flush()
            out += piece
            window = bytes(piece[-32768:])
        if len(out) != size or hashlib.sha256(out).hexdigest() != sha:
            fail(f"{os.path.basename(have[p[2]])}: its cabinet did not unpack right")
        memory[ident] = bytes(out)

files = {}
def read_ranges(ranges):
    for ident, off, n in ranges:
        if ident in memory:
            yield memory[ident][off:off + n]
            continue
        f = files.get(ident) or files.setdefault(ident, open(have[ident], "rb"))
        f.seek(off)
        while n:
            b = f.read(min(n, CHUNK))
            if not b:
                fail(f"{have[ident]} ended early")
            yield b
            n -= len(b)

def inflate(ranges):
    """InstallShield 6: chunks of a 16-bit length and a raw deflate stream."""
    buf, gen = b"", read_ranges(ranges)
    def need(n):
        nonlocal buf
        while len(buf) < n:
            more = next(gen, None)
            if more is None:
                return False
            buf += more
        return True
    while need(2):
        n, = struct.unpack_from("<H", buf)
        if not need(2 + n):
            fail("a compressed file ends early")
        yield zlib.decompress(buf[2:2 + n], -15)
        buf = buf[2 + n:]

class Reader:
    """A retail file's bytes, in order."""
    def __init__(self, kind, ranges):
        self.gen = read_ranges(ranges) if kind == "copy" else inflate(ranges)
        self.buf = b""
    def take(self, n):
        out = []
        while n:
            if not self.buf:
                self.buf = next(self.gen, b"")
                if not self.buf:
                    fail("a retail file ends early")
            b, self.buf = self.buf[:n], self.buf[n:]
            out.append(b)
            n -= len(b)
        return out

ways, vid = {}, None
for l in lines:
    p = l.split(" ")
    if p[0] == "V":
        vid = p[1]
    elif p[0] == "W" and vid not in ways:
        ranges = [(r.split(":")[0], int(r.split(":")[1]), int(r.split(":")[2])) for r in p[2:]]
        if all(i in have or i in memory for i, _, _ in ranges):
            ways[vid] = (p[1], ranges)

def ok(path, size, sha):
    return os.path.isfile(path) and os.path.getsize(path) == size and sha256(path) == sha

written = kept = 0
skip, out = True, None
for l in lines:
    p = l.split(" ")
    tag = p[0]
    if tag == "F":
        name, size, sha, flag, vid = p[1], int(p[2]), p[3], p[4], p[5]
        dest = os.path.join(here, name)
        skip = (flag == "once" and os.path.exists(dest)) or ok(dest, size, sha)
        if skip:
            kept += 1
            continue
        print(name, flush=True)
        if vid not in ways:
            fail(f"{name}: none of the images found has it")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        part = dest + ".part"
        out, src = open(part, "wb"), Reader(*ways[vid])
    elif skip or tag not in ("C", "Z", "L", "E"):
        continue
    elif tag == "C":
        for b in src.take(int(p[1])):
            out.write(b)
    elif tag == "Z":
        n = int(p[1])
        src.take(n)
        while n:
            k = min(n, CHUNK)
            out.write(bytes(k))
            n -= k
    elif tag == "L":
        b = base64.b64decode(p[1])
        src.take(len(b))
        out.write(b)
    elif tag == "E":
        out.close()
        if not ok(part, size, sha):
            os.remove(part)
            fail(f"{name} came out wrong (a disk error?); the files before it are in place")
        os.replace(part, dest)
        written += 1
os.makedirs(os.path.join(here, "Save"), exist_ok=True)
print(f"done: {written} files written, {kept} already in place. Play with ./linux-run.sh")
PY
exit 0
