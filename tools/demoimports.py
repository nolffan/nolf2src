#!/usr/bin/env python3
"""The 1.3 multiplayer demo's engine as a key to retail Lithtech.exe's SecuROM.

Retail `Lithtech.exe` is SecuROM-wrapped (docs/engine/anatomy.md, section
2): every `call dword ptr [IAT]` (ff 15) in `.text` was rewritten to call
one dispatcher slot in `.cms_d` (0x607ec0), so which import each of those
1,514 sites calls cannot be read from retail; and `.text` 0x565000..0x56a000
(five pages) is encrypted. The multiplayer demo (`nolf2_mpdemo_en.exe`,
built 20 days after 1.3, Rich header identical) has an unprotected engine
whose IAT sits at the same addresses as retail's original one, and the
plaintext of those pages.

  demoimports.py extract   unpack the demo's Lithtech.exe and server.dll
                           into out/mpdemo/ from rez/'s artifact
                           (rez/assemble-artifacts.sh demos first), with
                           rez/tools/sfxcab.py and rez/tools/unshield
  demoimports.py map [--csv=progress/engine/Lithtech-iat-calls.csv]
                           pair every redirected retail call site with the
                           demo's instruction and name the import it calls;
                           checks the demo's import table against retail's
                           original one (.rdata) slot by slot
  demoimports.py plain [--out=out/mpdemo/Lithtech-readable.exe]
                           a copy of retail with the encrypted pages filled
                           in from the demo and every redirected call put
                           back on its IAT slot -- for reading with
                           tools/exedump.py / objdump only, never committed
                           (out/ is ignored) and never run

`plain` places the demo's bytes in three pieces (retail = demo + 0x40 for
0x565000..0x565250, + 0x30 to 0x5675e0, the end of the UI library; - 0x10
from 0x5675e0, msvcrt.lib's static code, the import thunks and D3DX), found
from retail's own calls into the pages; re-aims the branches that leave a
piece; and puts the IAT operands right. What it does not fix: absolute
addresses of data inside the filled bytes are the demo's (its .data and
vtables are laid out a little differently), and the initializer cut by
0x565000 has the demo's tail. Read it as the demo's code at retail's
addresses.

What is committed is the map (addresses and import names), not the demo's
code. Ten MSVCRT slots of the IAT hold different imports in the two images
(the same 230 imports, ordered differently), so the import is the demo's
and the slot is where retail's original import table has that name. server.dll is not protected (retail and demo both call their IAT
directly), so there is nothing to map for it.

How a site is paired. The demo's and retail's code are the same up to
object placement (retail = demo + a constant over long runs; other
constants where the demo links objects in another order), so both .text
sections are disassembled (objdump, linear sweep) and each instruction
normalized (addresses and branch targets -> `A`). A site's context is up to
12 instructions either side, cut at its function's edges; each retail site
is scored against the demo's `ff 15` sites, and among equal best the one at
a shift its unambiguous neighbours have wins. `exact`: the same normalized
instructions, and no site calling another import reads the same;
`context`: two thirds or more of them, and clearly this import. `twins` is
how many demo sites tie (identical template code); `shift_run` whether the
shift equals a neighbour's.
"""
import collections
import csv
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETAIL = os.path.join(ROOT, "out/reference/Lithtech.exe")
ARTIFACT = os.path.join(ROOT, "rez/artifacts/demos/nolf2_mpdemo_en.exe.tar.xz")
OUTDIR = os.path.join(ROOT, "out/mpdemo")
DEMO = os.path.join(OUTDIR, "Lithtech.exe")
CSV = os.path.join(ROOT, "progress/engine/Lithtech-iat-calls.csv")

# the demo's unprotected engine, as rez's artifact unpacks it
DEMO_SHA256 = {
    "Lithtech.exe": "5cdd539d4b625ea04a95f9754f7bc29549a3dc6740eccd14aaa365ba1b80d7b1",
    "server.dll": "2cb74ee9766b6649f0095d7a496a00bc66938aab42a601d16eedee4429956987",
}

SLOT = 0x607EC0                       # SecuROM's dispatcher slot in .cms_d
ENC = (0x565000, 0x56A000)            # retail's encrypted .text pages
ORIG_IMPDIR = 0x590CF0                # retail's original import directory


class PE:
    def __init__(self, path):
        self.path = path
        self.d = d = open(path, "rb").read()
        e = struct.unpack_from("<I", d, 0x3C)[0]
        n = struct.unpack_from("<H", d, e + 6)[0]
        osz = struct.unpack_from("<H", d, e + 20)[0]
        o = e + 24
        self.base = struct.unpack_from("<I", d, o + 28)[0]
        self.dirs = [struct.unpack_from("<II", d, o + 96 + 8 * i) for i in range(16)]
        so = o + osz
        self.secs = []
        for i in range(n):
            s = so + 40 * i
            name = d[s:s + 8].rstrip(b"\0").decode("latin1")
            vs, va, rs, ro = struct.unpack_from("<IIII", d, s + 8)
            self.secs.append((name, self.base + va, vs, ro, rs))

    def sec(self, name):
        return next(s for s in self.secs if s[0] == name)

    def off(self, va):
        for name, sva, vs, ro, rs in self.secs:
            if sva <= va < sva + max(vs, rs):
                return ro + va - sva if va - sva < rs else None
        return None

    def u32(self, va):
        return struct.unpack_from("<I", self.d, self.off(va))[0]

    def cstr(self, va):
        o = self.off(va)
        return self.d[o:self.d.index(b"\0", o)].decode("latin1")

    def text(self):
        name, va, vs, ro, rs = self.sec(".text")
        return va, self.d[ro:ro + min(vs, rs)]

    def imports(self, desc_va=None):
        """{iat slot va: (dll, name)} from an import directory (default:
        the PE header's)."""
        va = desc_va or (self.base + self.dirs[1][0])
        out = {}
        while True:
            ilt, ts, fwd, name, iat = struct.unpack_from("<IIIII", self.d, self.off(va))
            if not name:
                return out
            dll = self.cstr(self.base + name)
            t, j = ilt or iat, 0
            while True:
                v = self.u32(self.base + t + 4 * j)
                if not v:
                    break
                fn = "#%d" % (v & 0xFFFF) if v & 0x80000000 else self.cstr(self.base + v + 2)
                out[self.base + iat + 4 * j] = (dll, fn)
                j += 1
            va += 20


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def need_demo():
    if not os.path.exists(DEMO):
        sys.exit("demoimports: %s is missing -- run `tools/demoimports.py extract`" % os.path.relpath(DEMO, ROOT))
    if sha(DEMO) != DEMO_SHA256["Lithtech.exe"]:
        sys.exit("demoimports: %s is not the 1.3 MP demo's engine" % DEMO)
    return PE(DEMO)


# ---------------------------------------------------------------- extract

def cmd_extract(args):
    if not os.path.exists(ARTIFACT):
        sys.exit("demoimports: %s is missing -- run `rez/assemble-artifacts.sh demos`"
                 % os.path.relpath(ARTIFACT, ROOT))
    unshield = os.path.join(ROOT, "rez/tools/unshield/unshield")
    if not os.access(unshield, os.X_OK):
        sys.exit("demoimports: rez/tools/unshield/unshield is not built -- `make -C rez/tools/unshield`")
    work = os.path.join(OUTDIR, "work")
    os.makedirs(work, exist_ok=True)
    exe = os.path.join(work, "nolf2_mpdemo_en.exe")
    if not os.path.exists(exe):
        with tarfile.open(ARTIFACT) as t:
            m = t.getmember("nolf2_mpdemo_en.exe")
            with t.extractfile(m) as f, open(exe, "wb") as g:
                shutil.copyfileobj(f, g)
    disk = os.path.join(work, "sfx")
    if not os.path.exists(os.path.join(disk, "Disk1", "data1.hdr")):
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "rez/tools/sfxcab.py"), exe, disk], check=True,
                       stdout=subprocess.DEVNULL)
    xdir = os.path.join(work, "x")
    subprocess.run([unshield, "-o", "-g", "Resources", "-d", xdir, "x",
                    os.path.join(disk, "Disk1", "data1.cab")], check=True, stdout=subprocess.DEVNULL)
    for name, want in DEMO_SHA256.items():
        src = os.path.join(xdir, "Resources", name)
        got = sha(src)
        if got != want:
            sys.exit("demoimports: %s has sha256 %s, expected %s" % (name, got, want))
        shutil.copyfile(src, os.path.join(OUTDIR, name))
        print("out/mpdemo/%s" % name)


# ---------------------------------------------------------------- map

def sites(pe, pred):
    """[(va, operand)] of every `ff 15 <imm32>` in .text whose operand
    satisfies pred."""
    tva, code = pe.text()
    out, i = [], 0
    while True:
        i = code.find(b"\xff\x15", i)
        if i < 0 or i + 6 > len(code):
            return out
        v = struct.unpack_from("<I", code, i + 2)[0]
        if pred(v):
            out.append((tva + i, v))
        i += 1


def disasm(pe):
    """[(va, token)] of .text by a linear objdump sweep, each instruction
    normalized: numbers of 0x10000 and up (addresses) and branch targets
    become `A`, so code placed elsewhere reads the same."""
    tva, code = pe.text()
    tmp = os.path.join(OUTDIR, "work", "text-%08x.bin" % (hash(pe.path) & 0xFFFFFFFF))
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, "wb").write(code)
    p = subprocess.run(["objdump", "-D", "-b", "binary", "-m", "i386", "-M", "intel",
                        "--adjust-vma=%#x" % tva, tmp], capture_output=True, text=True, check=True)
    os.remove(tmp)
    out = []
    big = re.compile(r"0x[0-9a-f]{5,}")
    for line in p.stdout.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        ins = m.group(2).split("<")[0].strip()
        ins = big.sub("A", ins)
        if ins.startswith(("call", "j")):
            ins = re.sub(r"\b[0-9a-f]+$", "A", ins)
        out.append((int(m.group(1), 16), ins))
    return out


LINE = re.compile(r"^\s*([0-9a-f]+):\t[0-9a-f ]+\t(.*)$")
K = 12                                  # instructions of context, each side


PAD = ("nop", "int3", "xchg ax,ax", "lea esi,[esi", "lea edi,[edi", "mov edi,edi")


def contexts(ins, vas):
    """Per site, up to K instructions either side, cut at the function's
    edges (padding or a ret before it, a ret after it): the neighbouring
    function is not the same one in both images."""
    idx = {va: i for i, (va, _) in enumerate(ins)}
    out = {}
    for va in vas:
        i = idx.get(va)
        if i is None:
            out[va] = None                  # the sweep is out of step here
            continue
        pre = []
        for _, t in reversed(ins[max(0, i - K):i]):
            if t.startswith(PAD) or t.startswith("ret"):
                break
            pre.append(t)
        post = []
        for _, t in ins[i + 1:i + 1 + K]:
            if t.startswith(PAD):
                break
            post.append(t)
            if t.startswith("ret"):
                break
        out[va] = tuple(reversed(pre)) + ("|",) + tuple(post)
    return out


def score(a, b):
    """Equal instructions, aligned at the call, over the longer context
    (so a shorter or longer function costs what it lacks)."""
    pa, pb = a.index("|"), b.index("|")
    pre = sum(x == y for x, y in zip(reversed(a[:pa]), reversed(b[:pb])))
    post = sum(x == y for x, y in zip(a[pa + 1:], b[pb + 1:]))
    full = max(pa, pb) + max(len(a) - pa, len(b) - pb) - 1
    return pre + post - (full - (len(a) - 1))


def build_map(ret, demo):
    dimp = demo.imports()
    lo, hi = min(dimp), max(dimp) + 4
    R = [va for va, _ in sites(ret, lambda v: v == SLOT)]
    D = sites(demo, lambda v: lo <= v < hi)
    dslot = dict(D)
    rctx = contexts(disasm(ret), R)
    dctx = contexts(disasm(demo), dslot)
    dlist = [d for d in dslot if dctx[d]]
    key = collections.defaultdict(list)
    for d in dlist:
        c = dctx[d]
        p = c.index("|")
        key[c[p - 3:p + 4]].append(d)
    # pass 1: every candidate's score
    scored = []
    for r in R:
        c = rctx[r]
        if c is None:
            scored.append((r, None, []))
            continue
        p = c.index("|")
        cand = set(key.get(c[p - 3:p + 4], ()))
        sc = sorted(((score(c, dctx[d]), d) for d in cand), reverse=True)
        if not sc or sc[0][0] < len(c) - 1:     # not exact: try them all
            sc = sorted(((score(c, dctx[d]), d) for d in dlist), reverse=True)
        scored.append((r, c, sc))
    # the shift of each site paired unambiguously (one best candidate)
    sure = {}
    for r, c, sc in scored:
        if sc and (len(sc) == 1 or sc[0][0] > sc[1][0]):
            sure[r] = r - sc[0][1]
    order = sorted(sure)

    def near_shifts(r):
        import bisect
        i = bisect.bisect_left(order, r)
        return [sure[order[j]] for j in (i - 1, i) if 0 <= j < len(order)]

    # pass 2: among equal best candidates, the one whose shift a paired
    # neighbour has (identical template code occurs many times over)
    rows = []
    for r, c, sc in scored:
        if c is None:
            rows.append(dict(site=r, demo=None, slot=None, score=0, second=0, conf="none", full=0, twins=0))
            continue
        best = sc[0][0]
        top = [d for s_, d in sc if s_ == best]
        ns = near_shifts(r)
        pref = [d for d in top if r - d in ns]
        d = (pref or top)[0]
        imp = dimp[dslot[d]]
        rival = [x[0] for x in sc if dimp[dslot[x[1]]] != imp]
        second = rival[0] if rival else -99
        full = len(c) - 1
        if best == full and (second < best or pref):
            conf = "exact"              # the same instructions, and no other import reads so
        elif best >= full * 2 // 3 and (best - second >= 2 or pref):
            conf = "context"            # most of them, and clearly this import
        else:
            conf = "weak"
        rows.append(dict(site=r, demo=d, slot=dslot[d], score=best, second=second, conf=conf, full=full,
                         twins=len(top)))
    for i, row in enumerate(rows):
        if row["demo"] is None:
            row["run"] = "no"
            continue
        s = row["site"] - row["demo"]
        nb = [rows[j]["site"] - rows[j]["demo"] for j in (i - 1, i + 1)
              if 0 <= j < len(rows) and rows[j]["demo"] is not None]
        row["run"] = "yes" if s in nb else "no"
    return rows, dimp, len(D)


def cmd_map(args):
    out = CSV
    for a in args:
        if a.startswith("--csv="):
            out = a[6:]
    ret, demo = PE(RETAIL), need_demo()
    rimp = ret.imports(ORIG_IMPDIR)
    rows, dimp, nd = build_map(ret, demo)
    # the two import tables, slot by slot
    agree = sum(1 for s in rimp if dimp.get(s) == rimp[s])
    print("retail original import table: %d slots; demo's: %d; same name at the same slot: %d"
          % (len(rimp), len(dimp), agree))
    for s in sorted(set(rimp) | set(dimp)):
        if rimp.get(s) != dimp.get(s):
            print("  slot 0x%08x retail %s demo %s" % (s, rimp.get(s), dimp.get(s)))
    conf = collections.Counter(r["conf"] for r in rows)
    print("retail redirected sites: %d; demo ff 15 sites: %d" % (len(rows), nd))
    print("paired: %s; shift agrees with a neighbour: %d"
          % (", ".join("%s %d" % kv for kv in sorted(conf.items())), sum(r["run"] == "yes" for r in rows)))
    used = collections.Counter(r["demo"] for r in rows if r["demo"])
    print("demo sites paired twice: %d" % sum(1 for n in used.values() if n > 1))
    shifts = collections.Counter(r["site"] - r["demo"] for r in rows if r["demo"])
    print("shifts (retail - demo):", ", ".join("%+#x x%d" % kv for kv in shifts.most_common(12)))
    # the import is the demo's; its slot in retail is where retail's own
    # import table has the same name (ten MSVCRT slots are ordered
    # differently in the two images)
    byname = {v: k for k, v in rimp.items()}
    miss = 0
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["retail_site", "iat_slot", "dll", "import", "demo_site", "demo_slot",
                    "confidence", "context", "twins", "shift_run"])
        for r in rows:
            if r["demo"] is None:
                miss += 1
                w.writerow(["0x%08x" % r["site"], "", "", "", "", "", "none", "", "", "no"])
                continue
            dll, fn = dimp[r["slot"]]
            rs = byname.get((dll, fn))
            if rs is None:
                miss += 1
            w.writerow(["0x%08x" % r["site"], "0x%08x" % rs if rs else "", dll, fn,
                        "0x%08x" % r["demo"], "0x%08x" % r["slot"], r["conf"],
                        "%d/%d" % (r["score"], r["full"]), r["twins"], r["run"]])
    print("sites without a retail slot: %d" % miss)
    print("wrote", os.path.relpath(os.path.abspath(out), ROOT))


def load_map(path=CSV):
    with open(path) as f:
        return {int(r["retail_site"], 16): int(r["iat_slot"], 16) for r in csv.DictReader(f) if r["iat_slot"]}


# ---------------------------------------------------------------- plain

def calls_into(ret, lo, hi):
    """{target: [sites]} of retail's `e8` calls from readable .text into
    [lo, hi)."""
    tva, code = ret.text()
    out = collections.defaultdict(list)
    for i in range(len(code) - 5):
        if code[i] != 0xE8:
            continue
        va = tva + i
        if ENC[0] <= va < ENC[1]:
            continue
        t = (va + 5 + struct.unpack_from("<i", code, i + 1)[0]) & 0xFFFFFFFF
        if lo <= t < hi:
            out[t].append(va)
    return out


def segments(ret, demo, rows):
    """[(lo, hi, shift)] covering the encrypted pages: retail va = demo va +
    shift. Each retail call from readable code into the pages is found in
    the demo (at the shift of the nearest paired import call, `map`), and
    the demo's call there says where the target is in the demo: one shift
    per target, by majority of its callers. Pieces change shift at the first
    target that needs a new one; the bytes just below such a target are the
    uncertain part (where exactly the piece before it ends)."""
    import bisect
    pairs = sorted((r["site"], r["site"] - r["demo"]) for r in rows if r["demo"] and r["run"] == "yes")
    keys = [p[0] for p in pairs]
    dva, dcode = demo.text()
    votes = collections.defaultdict(collections.Counter)
    def demo_call(dc):
        o = dc - dva
        if 0 <= o < len(dcode) - 5 and dcode[o] == 0xE8:
            return (dc + 5 + struct.unpack_from("<i", dcode, o + 1)[0]) & 0xFFFFFFFF
        return None

    for t, callers in calls_into(ret, ENC[0], ENC[1]).items():
        for c in callers:
            # the demo's site: at the shift of a neighbouring import call,
            # else wherever the bytes either side of the call recur
            i = bisect.bisect_left(keys, c)
            near = [c - pairs[j][1] for j in (i - 1, i) if 0 <= j < len(pairs)]
            found = [demo_call(dc) for dc in near]
            found = [dt for dt in found if dt is not None and abs(t - dt) < 0x400]
            if not found:
                co = ret.off(c)
                for pat, rel in ((ret.d[co - 12:co + 1], 12), (ret.d[co + 5:co + 17], -5)):
                    hits = []
                    k = dcode.find(pat)
                    while k >= 0 and len(hits) < 2:
                        hits.append(dva + k + rel)
                        k = dcode.find(pat, k + 1)
                    if len(hits) == 1:          # only a unique recurrence
                        dt = demo_call(hits[0])
                        if dt is not None and abs(t - dt) < 0x400:
                            found = [dt]
                            break
            if found:
                votes[t][t - found[0]] += 1
    anchors = sorted((t, v.most_common(1)[0][0]) for t, v in votes.items())
    pieces = []
    for i, (t, sh) in enumerate(anchors):
        if pieces and pieces[-1][1] == sh:
            continue
        nxt = [x[1] for x in anchors[i + 1:i + 4]]
        if pieces and nxt and sh not in nxt:
            continue                        # one odd target: the shift holds
        pieces.append((t, sh))
    segs = []
    for i, (t, sh) in enumerate(pieces):
        lo = ENC[0] if i == 0 else t
        hi = pieces[i + 1][0] if i + 1 < len(pieces) else ENC[1]
        segs.append((lo, hi, sh))
    return segs, anchors


def remap_iat(img, ret, demo, lo, hi, rimp, dimp):
    """In [lo, hi) of the image (demo bytes), point `ff 15` / `ff 25` at
    retail's slot for the same import: ten MSVCRT slots are ordered
    differently in the two images."""
    byname = {v: k for k, v in rimp.items()}
    n = 0
    a = ret.off(lo)
    for o in range(a, a + hi - lo - 6):
        if img[o] == 0xFF and img[o + 1] in (0x15, 0x25):
            v = struct.unpack_from("<I", img, o + 2)[0]
            if v in dimp and byname.get(dimp[v], v) != v:
                struct.pack_into("<I", img, o + 2, byname[dimp[v]])
                n += 1
    return n


def fix_branches(img, ret, demo, segs, rows):
    """The filled bytes are the demo's, so a `call`/`jmp rel32` in them
    reaches where the demo's target would be under its own piece's shift.
    Re-aim each whose target lies elsewhere: in another piece, or outside
    the pages (at the shift of the nearest paired import call). Returns
    (re-aimed, left alone because no shift is known for the target)."""
    import bisect
    pairs = sorted((r["demo"], r["site"] - r["demo"]) for r in rows if r["demo"] and r["run"] == "yes")
    keys = [p[0] for p in pairs]
    shifts = [sh for sh, _ in collections.Counter(p[1] for p in pairs).most_common()]

    def to_retail(dt):
        for lo, hi, sh in segs:
            if lo - sh <= dt < hi - sh:
                return dt + sh
        if ENC[0] - 0x400 <= dt < ENC[0]:
            return dt + segs[0][2]
        if ENC[1] <= dt < ENC[1] + 0x400:
            return dt + segs[-1][2]
        # elsewhere: the shift (a nearby import call's first, then any
        # seen) under which retail's bytes there are the demo's
        i = bisect.bisect_left(keys, dt)
        near = [pairs[j][1] for j in range(max(0, i - 3), min(len(pairs), i + 3))]
        do = demo.off(dt)
        if do is None:
            return None
        want = demo.d[do:do + 16]
        best = None
        for sh in near + shifts:
            ro = ret.off(dt + sh)
            if ro is None or ENC[0] <= dt + sh < ENC[1]:
                continue
            n = sum(x == y for x, y in zip(want, ret.d[ro:ro + 16]))
            if n >= 13 and (best is None or n > best[0]):
                best = (n, sh)
                if n == 16:
                    break
        return dt + best[1] if best else None

    tmp = os.path.join(OUTDIR, "work", "filled.bin")
    fixed = unknown = 0
    for lo, hi, sh in segs:
        a = ret.off(lo)
        open(tmp, "wb").write(bytes(img[a:a + hi - lo]))
        p = subprocess.run(["objdump", "-D", "-b", "binary", "-m", "i386", "--adjust-vma=%#x" % lo, tmp],
                           capture_output=True, text=True, check=True)
        for line in p.stdout.splitlines():
            m = re.match(r"^\s*([0-9a-f]+):\t((?:[0-9a-f]{2} )+)", line)
            if not m:
                continue
            va, ops = int(m.group(1), 16), m.group(2).split()
            if ops[0] in ("e8", "e9") and len(ops) == 5:
                at, n = va + 1, 5
            elif ops[0] == "0f" and len(ops) == 6 and 0x80 <= int(ops[1], 16) <= 0x8F:
                at, n = va + 2, 6
            else:
                continue
            o = ret.off(at)
            t = (va + n + struct.unpack_from("<i", img, o)[0]) & 0xFFFFFFFF
            if lo <= t < hi:
                continue                    # inside its own piece: already right
            rt = to_retail(t - sh)
            if rt is None:
                unknown += 1
                continue
            if rt != t:
                struct.pack_into("<i", img, o, rt - (va + n))
                fixed += 1
    os.remove(tmp)
    return fixed, unknown


def cmd_plain(args):
    out = os.path.join(OUTDIR, "Lithtech-readable.exe")
    for a in args:
        if a.startswith("--out="):
            out = a[6:]
    ret, demo = PE(RETAIL), need_demo()
    if not os.path.exists(CSV):
        sys.exit("demoimports: run `tools/demoimports.py map` first")
    rimp, dimp = ret.imports(ORIG_IMPDIR), demo.imports()
    rows = build_map(ret, demo)[0]
    segs, anchors = segments(ret, demo, rows)
    img = bytearray(ret.d)
    nre = 0
    for lo, hi, s in segs:
        a, b = ret.off(lo), demo.off(lo - s)
        img[a:a + hi - lo] = demo.d[b:b + hi - lo]
        nre += remap_iat(img, ret, demo, lo, hi, rimp, dimp)
    fixed, unknown = fix_branches(img, ret, demo, segs, rows)
    m = load_map()
    for site, slot in m.items():
        struct.pack_into("<I", img, ret.off(site) + 2, slot)
    # the PE header's import directory back on the original one, so a
    # disassembler names the IAT slots
    e = struct.unpack_from("<I", img, 0x3C)[0]
    va = ORIG_IMPDIR
    while struct.unpack_from("<I", img, ret.off(va) + 12)[0]:
        va += 20
    struct.pack_into("<II", img, e + 24 + 96 + 8, ORIG_IMPDIR - ret.base, va + 20 - ORIG_IMPDIR)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "wb").write(img)
    for lo, hi, s in segs:
        print("0x%08x..0x%08x  from demo 0x%08x..0x%08x  (retail = demo %+#x)" % (lo, hi, lo - s, hi - s, s))
    print("%d call targets in the pages, each found through its callers in the demo, placed the pieces"
          % len(anchors))
    print("%d branches out of the filled pieces re-aimed, %d left (no shift known for the target)" % (fixed, unknown))
    print("%d redirected call sites restored, %d IAT operands in the filled pages renumbered" % (len(m), nre))
    print("wrote", os.path.relpath(os.path.abspath(out), ROOT), "(for reading only: never run or committed)")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("extract", "map", "plain"):
        sys.exit(__doc__)
    {"extract": cmd_extract, "map": cmd_map, "plain": cmd_plain}[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
