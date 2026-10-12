#!/usr/bin/env python3
"""Check our whole-linked image's vtables against the shipped ones, slot by slot.

Why: a constructor can be byte-identical (exematch masks the vptr store's
relocation) while the table it installs is a one- or two-slot stand-in.
The first interface call the game DLLs make past the end of such a table
jumps into whatever follows it in .rdata. Only a run notices -- or this.

How, with no symbols in the shipped image:
  * every function of ours that progress.py places at a shipped address is a
    Rosetta stone: each DIR32 relocation in it names a symbol of ours, and
    the shipped dword at the same offset is that symbol's shipped address.
    That gives `??_7Foo@@6B@` -> shipped vtable address.
  * our image's map gives the symbol's address in OUR link; the table is
    read out of both images.
  * each slot's target is translated our-VA -> symbol(s) -> shipped VA
    through the same placements (identical functions and progress.py's
    near pairings) and compared with the shipped slot.

Per table it prints OK, or the slots that are SHORT (our table ends early),
WRONG (our slot is a function placed at a different shipped address), or
UNKNOWN (our slot's function has no shipped placement). For each bad slot it
names our symbol(s) placed at the shipped target, when there are any.

With --spec=FILE it also writes, for every table with a problem, a draft
tools/mkvtabobj.py spec: the shipped table slot for slot, each slot the
symbol of ours placed at the shipped target (our own slot symbol where it
already agrees). A slot with nothing placed there is written as
`MISSING 0x<shipped>`, which mkvtabobj refuses -- each one is a function to
reconstruct (or, as a last resort, to carry as labelled shipped bytes).

Usage:
  vtabcheck.py [lithtech.exe|server.dll] [--all] [--sym=SUBSTR] [--spec=FILE]
"""
import collections
import glob
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import progress  # noqa: E402
from linkresolve import parse_obj  # noqa: E402
from exedump import Pe  # noqa: E402
from libextract import extract  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The CRT's _purecall in each shipped image (every abstract table's filler).
PURECALL = {"lithtech.exe": 0x004928e7}

# Stand-in tables that ARE an SDK interface: their slots must carry the
# header's names in order (tools/sdkvtab.py). Placement by bytes cannot tell
# same-shape one-line wrappers apart; their names can.
SDK_IFACE = {
    "lithtech.exe": {
        "??_7CLTClientQ404@@6B@": "ILTClient",
        "??_7ILTCSBaseQ404@@6B@": "ILTClient",
        "??_7CLTServer@@6B@": "ILTServer",
        "??_7LMessageImpl@@6B@": "ILTMessage",
        "??_7CMsgWriteQ18@@6B@": "ILTMessage",
        "??_7CSaveLoadMessage@@6B@": "ILTMessage",
        "??_7ClientCommonLTQ404@@6B@": "ILTCommon",
        "??_7ILTCommonQ404@@6B@": "ILTCommon",
        "??_7ServerCommonLT@@6B@": "ILTCommon",
        "??_7CPhysicsLTQ404@@6B@": "ILTClientPhysics",
        "??_7ClientModelLTQ404@@6B@": "ILTModel",
        "??_7ServerModelLT@@6B@": "ILTModel",
        "??_7ILTTransformQ404@@6B@": "ILTTransform",
        "??_7ClientLightAnimLTQ404@@6B@": "ILTLightAnim",
        "??_7LVideoMgrQ404@@6B@": "ILTVideoMgr",
        "??_7CUnknown3b8Q404@@6B@": "ILTCursor",
        "??_7ILTMathQ404@@6B@": "ILTMath",
        "??_7CCmgSoundMgr@@6B@": "ILTClientSoundMgr",
        "??_7CCmgMusicMgr@@6B@": "ILTDirectMusicMgr",
    },
}

# Where the shipped engine's interface had a virtual the LT2 SDK header does
# not: (index, name), inserted before the comparison. ILTServer's slot 102 is
# 0x0046ef80, which the reconstruction has as CLTServer::GetObjectName and
# after which every slot lines up with the header again.
SDK_EXTRA = {"ILTServer": [(102, "GetObjectName")]}
# Interfaces whose shipped table has one slot past the header's last: that
# slot is left to placement (ILTMessage's 36th is a `return 0`).
SDK_TAIL_EXTRA = {"ILTMessage"}

# lithtech.exe has two copies of the allocator front end (0x004290b0/c0 over
# dalloc/dfree, 0x00435720/30 over 0x0041ec70/80) where our link has one; a
# relocation to either reads back "wrong" against the other. Not evidence.
TWINS = {"??2@YAPAXI@Z", "??3@YAXPAX@Z", "?dalloc@@YAPAXK@Z", "?dfree@@YAXPAX@Z"}
TWIN_ADDRS = {0x004290b0, 0x004290c0, 0x00435720, 0x00435730,
              0x00428fd0, 0x00429080, 0x0041ec70, 0x0041ec80}

TARGETS = {
    "lithtech.exe": ("out/reference/lithtech.exe", "src/engine/lithtech",
                     "lithtech.exe", "lithtech.map",
                     ["src/lithshared/out/Lith.lib", "src/lithshared/out/StdLith.lib"]),
    "server.dll": ("out/reference/server.dll", "src/engine/server",
                   "server.dll", "server.map",
                   ["src/lithshared/out/StdLith.lib", "src/lithshared/out/Lith.lib"]),
}


class Img:
    def __init__(self, path):
        self.pe = Pe(path)
        d = self.d = self.pe.d
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        n = struct.unpack_from("<H", d, pe + 6)[0]
        opt = struct.unpack_from("<H", d, pe + 20)[0]
        self.base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
        self.secs = []
        for i in range(n):
            s = pe + 24 + opt + i * 40
            name = d[s:s + 8].rstrip(b"\0").decode("latin-1")
            vs, va, rs, rp = struct.unpack_from("<IIII", d, s + 8)
            self.secs.append((name, self.base + va, vs, rs, rp))
            if name == ".text":
                self.tlo, self.thi = self.base + va, self.base + va + vs
                self.text = d[rp:rp + vs]

    def dword(self, va):
        for name, lo, vs, rs, rp in self.secs:
            if lo <= va < lo + min(vs, rs) - 3:
                return struct.unpack_from("<I", self.d, rp + va - lo)[0]
        return None

    def is_code(self, v):
        return v is not None and self.tlo <= v < self.thi


def load_map(path):
    """-> (sym -> VA, VA -> [syms])"""
    s2a, a2s = {}, collections.defaultdict(list)
    for line in open(path, errors="replace"):
        m = re.match(r"\s*[0-9a-f]{4}:[0-9a-f]{8}\s+(\S+)\s+([0-9a-f]{8})\s", line)
        if m:
            a = int(m.group(2), 16)
            s2a[m.group(1)] = a
            a2s[a].append(m.group(1))
    return s2a, a2s


def compiled_vtables(data):
    """{`??_7..` -> [slot symbol, ...]} as one object compiled them."""
    out = {}
    if len(data) < 20:
        return out
    machine, nsec, _ts, symoff, nsyms, optsz, _ch = struct.unpack_from(
        "<HHIIIHH", data, 0)
    if machine != 0x14C:
        return out
    strtab = data[symoff + nsyms * 18:]

    def symname(raw):
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            return strtab[off:strtab.find(b"\0", off)].decode("latin-1")
        return raw.rstrip(b"\0").decode("latin-1")

    names = {}
    tabs = []
    i = 0
    while i < nsyms:
        e = symoff + i * 18
        name = symname(data[e:e + 8])
        value, secnum, _t, storage, naux = struct.unpack_from("<IhHBB", data, e + 8)
        names[i] = name
        if storage == 2 and secnum > 0 and name.startswith("??_7"):
            tabs.append((name, secnum, value))
        i += 1 + naux
    for name, secnum, value in tabs:
        sh = 20 + optsz + (secnum - 1) * 40
        _vs, _va, rawsz, _rawp, relp, _l, nrel, _n = struct.unpack_from(
            "<IIIIIIHH", data, sh + 8)
        rels = {}
        for r in range(nrel):
            off, idx, typ = struct.unpack_from("<IIH", data, relp + r * 10)
            rels[off] = names.get(idx)
        slots = []
        o = value
        while o in rels and o < rawsz:
            slots.append(rels[o])
            o += 4
        out[name] = slots
    return out


def load_aliases(path):
    al = {}
    if os.path.exists(path):
        for line in open(path, errors="replace"):
            m = re.match(r"/ALTERNATENAME:(\S+?)=(\S+)", line.strip())
            if m:
                al.setdefault(m.group(1), m.group(2))
    return al


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict((a.split("=", 1) + [True])[:2] for a in sys.argv[1:]
                if a.startswith("--"))
    label = args[0] if args else "lithtech.exe"
    ship_path, d, ours, mapf, libs = TARGETS[label]
    objs = sorted(os.path.relpath(p, REPO)
                  for p in glob.glob(os.path.join(REPO, d, "Release/*.obj")))
    objs += libs
    os.chdir(REPO)
    progress.rows_for_image(label, ship_path, objs)

    sym2ship = {}
    for (lb, a), n in progress.PLACED_SYMS.items():
        if lb == label:
            sym2ship.setdefault(n.split(":", 1)[1], set()).add(a)
    for (lb, a), n in progress.SMALL_SYMS.items():
        if lb == label:
            sym2ship.setdefault(n.split(":", 1)[1], set()).add(a)
    for (lb, a, _sz, n, _our) in progress.NEAR_PAIRS:
        if lb == label:
            sym2ship.setdefault(n.split(":", 1)[1], set()).add(a)
    ship2sym = collections.defaultdict(set)
    for n, aa in sym2ship.items():
        for a in aa:
            ship2sym[a].add(n)

    ship = Img(os.path.join(REPO, ship_path))
    our = Img(os.path.join(REPO, d, "Release", ours))
    s2a, a2s = load_map(os.path.join(REPO, d, "Release", mapf))
    # `??_E` (vector deleting dtor) is a weak external onto `??_G` in the
    # objects that need it; naming it from another object does not resolve.
    for a in a2s:
        a2s[a].sort(key=lambda n: n.startswith("??_E"))
    aliases = load_aliases(os.path.join(REPO, d, "link/aliases.rsp"))

    # Rosetta: data symbols -> shipped address, from placed functions' DIR32s
    import tempfile
    tmp = tempfile.mkdtemp()
    paths = []
    # RezMgr.lib is linked in place of the Release rez*.obj (build/engine.sh);
    # it places nothing progress.py does not already place from those, but
    # it is what defines the rez symbols in the link.
    for o in objs + ["src/lithshared/out/RezMgr.lib"]:
        if o.endswith(".lib"):
            dd = os.path.join(tmp, os.path.basename(o))
            os.makedirs(dd, exist_ok=True)
            extract(o, dd)
            paths += sorted(glob.glob(dd + "/*"))
        else:
            paths.append(o)
    placed = {}
    for (lb, a), n in progress.PLACED_SYMS.items():
        if lb == label:
            placed[n.split(":", 1)[1]] = a
    seen = collections.defaultdict(set)
    funcrels = {}
    compiled = {}         # vtable -> slot symbols, as the source declares it
    shape_of, by_shape = {}, collections.defaultdict(list)
    code_of = {}
    defined = set()       # every external our link inputs define (the map
                          # lists only what /OPT:REF kept)
    excluded = re.compile(r"Release/(rezhash|rezdir|rezemu|rezfile|rezmgr|rezmgr2)\.obj$")
    for p in paths:
        try:
            f, dd_, _u = parse_obj(open(p, "rb").read())
        except Exception:                                  # noqa: BLE001
            continue
        if not excluded.search(p):
            for t, sl in compiled_vtables(open(p, "rb").read()).items():
                compiled.setdefault(t, sl)
            defined |= dd_
            for name, (_c, _m, rels) in f.items():
                funcrels.setdefault(name, rels)
                key = bytes(0 if i in _m else b for i, b in enumerate(_c))
                if name not in shape_of:
                    code_of[name] = (_c, _m)
                    shape_of[name] = key
                    by_shape[key].append(name)
        for name, (_c, _m, rels) in f.items():
            if name not in placed:
                continue
            base = placed[name]
            for off, kind, sym in rels:
                if kind != "abs":
                    continue
                v = ship.dword(base + off)
                if v is not None:
                    seen[sym].add(v)

    shipped_tabs = collections.defaultdict(dict)
    shipped_args = {}     # shipped function -> dwords its `ret` pops
    # build/reference.sh writes it (tools/vtabaudit.py --csv)
    vt = os.path.join(REPO, "out", "reference", label.split(".")[0] + "-vtables.csv")
    if os.path.exists(vt):
        import csv
        for r in csv.DictReader(open(vt)):
            shipped_tabs[int(r["table"], 16)][int(r["slot"])] = int(r["target"], 16)
            if r["args"].isdigit():
                shipped_args[int(r["target"], 16)] = int(r["args"])

    def resolve(sym):
        k = 0
        while sym not in s2a and sym not in defined and sym in aliases and k < 10:
            sym, k = aliases[sym], k + 1
        return s2a.get(sym, 0 if sym in defined else None)

    def our_to_ship(va):
        out = set()
        for n in a2s.get(va, []):
            out |= sym2ship.get(n, set())
        # aliases whose target lives at va
        return out

    def pick(st):
        """Our symbol for a shipped function address, best evidence first:
        placed there and nowhere else, then placed there among others."""
        if st == PURECALL.get(label):
            return "__purecall"
        c = [n for n in ship2sym.get(st, ()) if resolve(n) is not None]
        # Same masked bytes, other relocations (template instances, banks of
        # different element types): placement by bytes alone picks any of
        # them. Widen to every body of that shape and keep the ones whose
        # relocations read back right at `st`.
        wide = set(c)
        for n in c:
            wide.update(x for x in by_shape.get(shape_of.get(n), ())
                        if resolve(x) is not None)
        clean = [n for n in wide if not hard(n, st)]
        sure = [n for n in clean if not suspect(n, st)]
        if sure:
            clean = sure
        if os.environ.get("VTDEBUG") and st == int(os.environ["VTDEBUG"], 16):
            for n in sorted(wide):
                print("DEBUG", n, suspect(n, st), file=sys.stderr)
        if clean:
            c = clean
        # the argument pop is an ABI fact: never pick a body that pops a
        # different count from the shipped slot's
        want_args = shipped_args.get(st)
        if want_args is not None:
            agree = [n for n in c if our_args(n) in (None, want_args)]
            # vtabaudit reads the pop off the first `ret` it decodes, which
            # an early-out block can make wrong: only a filter, never a veto
            if agree:
                c = agree
        uniq = [n for n in c if sym2ship.get(n) == {st}]
        for group in (uniq, c):
            if group:
                # prefer a plain definition over an alias spelling
                group.sort(key=lambda n: (n.startswith("??_E"), n not in s2a, "?$" in n, n))
                return group[0]
        return None

    def fits(n, st):
        code, mask = code_of[n]
        o = st - ship.tlo
        t = ship.text
        if o < 0 or o + len(code) > len(t):
            return False
        return all(i in mask or t[o + i] == code[i] for i in range(len(code)))

    def method_of(n):
        if n.startswith("??_G") or n.startswith("??_E") or n.startswith("??1"):
            return "~"
        m = re.match(r"\?(\w+)@", n)
        return m.group(1) if m else n

    by_method = collections.defaultdict(list)
    for d_ in defined:
        by_method[method_of(d_)].append(d_)

    def sdk_fix(n, want, st):
        """(symbol, note): n if its method name is the header's; otherwise
        the best body of ours carrying that name -- one that fits the
        shipped target exactly, else one that resembles it."""
        if method_of(n) == want or n == "__purecall":
            return n, None
        best, score = None, 0
        for x in by_method.get(want, ()):
            if x.startswith("??_E"):
                continue
            cx = canon(x)
            if cx not in code_of:
                continue
            sc = 3 if fits(cx, st) and not hard(cx, st) else (
                2 if fits(cx, st) else (1 if resembles(cx, st) else 0))
            if sc > score or (sc == score and sc and len(x) < len(best)):
                best, score = x, sc
        if best:
            return best, None
        return n, "no %s of ours fits 0x%08x; kept" % (want, st)

    def resembles(n, st):
        """Our body and the shipped bytes at st, compared with relocation
        bytes ignored: 70% of the unmasked bytes in common (difflib) is the
        same function compiled slightly differently, not another one."""
        import difflib
        code, mask = code_of[n]
        o = st - ship.tlo
        t = ship.text[o:o + len(code) + 16] if o >= 0 else b""
        a = bytes(0 if i in mask else b for i, b in enumerate(code))
        if not t or len(a) < 8:
            return False
        r = difflib.SequenceMatcher(None, a, bytes(t[:len(a)]), autojunk=False).ratio()
        return r >= 0.7

    def canon(sym):
        k = 0
        while sym not in code_of and sym in aliases and k < 10:
            sym, k = aliases[sym], k + 1
        return sym

    def suspect(n, st, depth=2):
        """Relocations of our `n` that do not read back right at shipped
        `st`: the masked match placed a look-alike (same bytes, other
        globals or callees). A call is right when it reaches the callee's
        known address, or -- the callee's placement being as fallible as
        this one -- when our callee's body fits the bytes it reaches and is
        itself not suspect there (to `depth` levels). Entries starting with
        `?` are unverifiable (callee neither placed nor ours to compare)."""
        out = []
        for off, kind, sym in funcrels.get(n, ()):
            a = st + off
            v = ship.dword(a)
            if v is None:
                continue
            if kind == "rel" and sym in TWINS and \
                    (a + 4 + v) & 0xFFFFFFFF in TWIN_ADDRS:
                continue
            if kind == "rel":
                v = (a + 4 + v) & 0xFFFFFFFF
                want = sym2ship.get(sym)
                if want and v in want:
                    continue
                cs = canon(sym)
                if cs in code_of and ship.tlo <= v < ship.thi:
                    if fits(cs, v) and (depth == 0 or
                                        not [x for x in suspect(cs, v, depth - 1)
                                             if not x.startswith("?")]):
                        continue
                    if resembles(cs, v):
                        # a near reconstruction of the same function: not
                        # proof either way, so not a veto
                        out.append("?%s@+%x=0x%08x(near body)" % (sym[:40], off, v))
                    else:
                        out.append("%s@+%x=0x%08x(body does not fit)" % (sym[:40], off, v))
                elif want:
                    out.append("%s@+%x=0x%08x(want 0x%08x)" % (sym[:40], off, v, min(want)))
                else:
                    out.append("?%s@+%x=0x%08x(unverifiable)" % (sym[:40], off, v))
            else:
                want = sym2ship.get(sym) or seen.get(sym)
                if want and len(want) == 1 and v not in want:
                    out.append("%s@+%x=0x%08x(want 0x%08x)" % (sym[:40], off, v, next(iter(want))))
        return out

    def hard(n, st):
        return [x for x in suspect(n, st) if not x.startswith("?")]

    def norm(c):
        return "??_G" + c[4:] if c and c.startswith("??_E") else c

    def slot_fits(c, st):
        c = norm(c)
        if c == "__purecall" or st == PURECALL.get(label):
            return c == "__purecall" and st == PURECALL.get(label)
        c = canon(c)
        return c in code_of and fits(c, st) and not hard(c, st)

    def fitscore(cs, t):
        ss = [shipped_tabs[t][i] for i in sorted(shipped_tabs[t])]
        return sum(1 for k, c in enumerate(cs) if k < len(ss) and slot_fits(c, ss[k]))

    def our_args(c):
        c = canon(norm(c))
        if c not in code_of:
            return None
        code = code_of[c][0]
        if len(code) >= 3 and code[-3] == 0xC2:
            return (code[-2] | code[-1] << 8) // 4
        if code and code[-1] == 0xC3:
            return 0
        return None

    def args_clash(sym, t):
        """How many compiled slots pop a different argument count from the
        shipped slot at t, out of how many can be compared. The pops are an
        ABI fact no placement can confuse: a table whose slots disagree on
        them is the wrong table (CMessageObjectHelper's ctor placed as
        LTTexMod's)."""
        cs = compiled.get(sym, [])
        ss = [shipped_tabs[t][i] for i in sorted(shipped_tabs[t])]
        bad = known = 0
        for k, c in enumerate(cs):
            if k >= len(ss) or norm(c) == "__purecall":
                continue
            a, b = our_args(c), shipped_args.get(ss[k])
            if a is None or b is None:
                continue
            known += 1
            bad += a != b
        return bad, known

    def misfit_is_mapping(sym, sva):
        """A full-length compiled table that fits no shipped table well is
        left alone when its misfits are all slots our build has no shape
        evidence for either way (functions not reconstructed byte-for-byte):
        replacing those would trade the source's declaration for a guess."""
        cs = compiled[sym]
        ss = [shipped_tabs[sva][i] for i in sorted(shipped_tabs[sva])]
        for k, c in enumerate(cs):
            if k < len(ss) and not slot_fits(c, ss[k]) and pick(ss[k]):
                return False
        return True

    spec = [] if opts.get("--spec") else None
    # Tables already in the spec stay in it: once linked, our copy of them
    # IS the spec's, so they no longer show a problem to be re-found by.
    prev = set()
    if spec is not None and os.path.exists(opts["--spec"]):
        prev = {l.split()[1] for l in open(opts["--spec"]) if l.startswith("vtable ")}
    our_starts = sorted(a2s)
    import bisect
    want = opts.get("--sym")
    bad_tabs = 0
    def choose(sym):
        remapped_from = None
        sa = seen[sym]
        csl0 = compiled.get(sym)
        # The Rosetta mapping comes from placements, and two same-shape
        # constructors or bank functions can be placed either way round
        # (CTreeStream/CMemStream). Score each candidate shipped table by how
        # many compiled slots fit it; prefer the seen address, but take a
        # same-length table the compiled one fits PERFECTLY over a seen one
        # it does not, and settle an ambiguous mapping by best score.
        cands = sorted(a for a in sa if a in shipped_tabs)
        if csl0:
            same = [t for t in shipped_tabs if len(shipped_tabs[t]) == len(csl0)]
            sc = {t: fitscore(csl0, t) for t in set(cands) | set(same)}
            best = max(sc.values()) if sc else 0
            perfect = [t for t in sc if sc[t] == len(csl0)]
            # a remap needs real evidence -- six slots or more (four-slot banks are
            # all one shape, so any bank "fits" any other); matching _purecall slots say only
            # that both tables are abstract there (CServerWorldFull's all-pure
            # stand-in "fits" IDirectMusicGetLoader's abstract table)
            if len(cands) == 1 and len(shipped_tabs[cands[0]]) == len(csl0) >= 6 \
                    and sc.get(cands[0], 0) < len(csl0) and len(perfect) == 1 \
                    and sum(1 for c in csl0 if norm(c) != "__purecall") >= 3:
                print("%s: REMAP 0x%08x -> 0x%08x (compiled table fits it %d/%d, seen one %d)" % (
                    sym, cands[0], perfect[0], len(csl0), len(csl0), sc[cands[0]]))
                sa = {perfect[0]}
                remapped_from = cands[0]
            elif len(cands) > 1:
                top = [t for t in cands if sc.get(t, 0) == max(sc.get(c, 0) for c in cands)]
                if len(top) == 1:
                    print("%s: ambiguous %s, taking 0x%08x by fit" % (
                        sym, [hex(x) for x in cands], top[0]))
                    sa = {top[0]}
        if len(sa) != 1:
            print("%s: shipped address ambiguous %s" % (sym, sorted(hex(x) for x in sa)))
            return None, None
        t = next(iter(sa))
        if t in shipped_tabs:
            bad, known = args_clash(sym, t)
            if known >= 3 and bad * 2 > known:
                # look for the table it does belong to: same length, every
                # comparable pop agreeing, best shape fit, and only one such
                n = len(compiled.get(sym, []))
                ok = []
                for t2 in shipped_tabs:
                    if len(shipped_tabs[t2]) != n:
                        continue
                    b2, k2 = args_clash(sym, t2)
                    if b2 == 0 and k2 >= 3:
                        ok.append((fitscore(compiled[sym], t2), t2))
                ok.sort(reverse=True)
                if ok and (len(ok) == 1 or ok[0][0] > ok[1][0]):
                    print("%s: mapping 0x%08x REJECTED (%d of %d pops differ), REMAP -> 0x%08x by pops+fit" % (
                        sym, t, bad, known, ok[0][1]))
                    return ok[0][1], t
                print("%s: mapping 0x%08x REJECTED, %d of %d slots pop a different argument count" % (
                    sym, t, bad, known))
                return None, None
        return t, remapped_from

    chosen = {}
    for sym in sorted(s for s in seen if s.startswith("??_7")):
        if opts.get("--sym") and opts["--sym"] not in sym:
            continue
        chosen[sym] = choose(sym)
    # A remap is a swap: the table that was mapped where the remapped one
    # now goes takes the address it left (CTreeStream <-> CMemStream).
    for sym, (to, frm) in list(chosen.items()):
        if frm is None:
            continue
        for other, (t2, f2) in list(chosen.items()):
            if other != sym and t2 == to and f2 is None and \
                    len(compiled.get(other, [])) == len(shipped_tabs.get(frm, {})):
                print("%s: swapped with %s -> 0x%08x" % (other, sym, frm))
                chosen[other] = (frm, None)

    for sym in sorted(s for s in seen if s.startswith("??_7")):
        if want and want not in sym:
            continue
        sva = chosen.get(sym, (None, None))[0]
        if sva is None:
            continue
        ova = resolve(sym)
        if not ova:
            continue
        # shipped slots
        if sva in shipped_tabs:
            sslots = [shipped_tabs[sva][i] for i in sorted(shipped_tabs[sva])]
        else:
            sslots = []
            a = sva
            while ship.is_code(ship.dword(a)):
                sslots.append(ship.dword(a))
                a += 4
        # vtabaudit cuts a run at every address something references, and a
        # stray reference into a table splits it (CSaveLoadMessage's 36-slot
        # ILTMessage table was recorded as 6 + 30). An SDK interface says how
        # long the table is: read on through the image to that length.
        iface_ = SDK_IFACE.get(label, {}).get(sym)
        if iface_:
            from sdkvtab import virtuals
            want_n = len(virtuals(iface_)) + len(SDK_EXTRA.get(iface_, ())) + \
                (1 if iface_ in SDK_TAIL_EXTRA else 0)
            if len(sslots) < want_n:
                ext = []
                a = sva
                while len(ext) < want_n and ship.is_code(ship.dword(a)):
                    ext.append(ship.dword(a))
                    a += 4
                if len(ext) == want_n:
                    print("%s: shipped table 0x%08x read on to %d slots (%s)" % (
                        sym, sva, want_n, iface_))
                    sslots = ext
        # our slots: until the next symbol or a non-code dword
        i = bisect.bisect_right(our_starts, ova)
        nxt = our_starts[i] if i < len(our_starts) else ova + 4 * 1000
        oslots = []
        a = ova
        while a < nxt and our.is_code(our.dword(a)):
            oslots.append(our.dword(a))
            a += 4
        probs = []
        for k, st in enumerate(sslots):
            if k >= len(oslots):
                probs.append((k, "SHORT", None, st))
                continue
            got = our_to_ship(oslots[k])
            if st in got:
                continue
            probs.append((k, "WRONG" if got else "UNKNOWN", oslots[k], st))
        # Only STAND-INS go in the spec: a table the compiler emitted shorter
        # than the shipped one. A full-length compiled table is the source's
        # own declaration and stays as compiled even where this check
        # disagrees -- the disagreement is as likely to be the Rosetta
        # mapping (CTreeStream's and CMemStream's tables are installed by two
        # same-shape bank functions, which placement can swap) as the table.
        # A FULL-LENGTH compiled table is the source's own declaration and
        # is trusted slot for slot -- even where a slot does not "fit" the
        # shipped bytes, because the fit is judged through placements that
        # same-shape bodies make unreliable (ServerModelLT's SetCurAnim/
        # SetLooping/SetPlaying wrappers forward to three same-shape
        # CommonModelLT bodies that placement rotates; "correcting" the
        # table from them broke every model animation). The one exception
        # is a compiled _purecall where the shipped slot is concrete: a
        # class that never declared the override (CLTServer's ILTCSBase
        # slots), which can only crash.
        csl_ = compiled.get(sym, [])
        short = len(csl_) < len(sslots)
        pure_holes = [k for k, c in enumerate(csl_) if k < len(sslots)
                      and norm(c) == "__purecall" and sslots[k] != PURECALL.get(label)]
        if (short or pure_holes) and spec is not None:
            spec.append("vtable %s 0x%08x  # compiled with %d slots" % (sym, sva, len(compiled.get(sym, []))))
            csl = compiled.get(sym, [])
            sdk = None
            if SDK_IFACE.get(label, {}).get(sym):
                from sdkvtab import virtuals
                iface = SDK_IFACE[label][sym]
                sdk = virtuals(iface)
                for at, nm in SDK_EXTRA.get(iface, ()):
                    sdk.insert(at, nm)
                if len(sdk) != len(sslots) and not (len(sdk) == len(sslots) - 1
                                                    and iface in SDK_TAIL_EXTRA):
                    print("%s: %s has %d virtuals, the shipped table %d slots; "
                          "names not applied" % (sym, iface, len(sdk), len(sslots)))
                    sdk = None
            for k, st in enumerate(sslots):
                n = None
                c = csl[k] if k < len(csl) else None
                if c and c.startswith("??_E"):
                    # ??_E is a weak external onto ??_G in the compiling
                    # object only; name the ??_G from here
                    c = "??_G" + c[4:]
                # The compiled slot is the source's own declaration: keep it
                # unless the evidence says it is wrong (its bytes do not fit
                # the shipped target, or its relocations read back wrong).
                # Placement alone is not evidence -- two same-shape bodies
                # (CRezDirHash/CRezTypeHash::HashFunc) are placed either way.
                if c == "__purecall" or st == PURECALL.get(label):
                    if c == "__purecall" and st == PURECALL.get(label):
                        n = c
                elif c and resolve(c) is not None and \
                        (not short or canon(c) not in code_of or slot_fits(c, st)):
                    n = c
                n = n or pick(st)
                if not n and c and resolve(c) is not None:
                    spec.append("    %s  # UNVERIFIED slot %d: nothing placed at 0x%08x, our own slot kept" % (c, k, st))
                    continue
                if not n:
                    spec.append("    MISSING 0x%08x" % st)
                    continue
                if sdk and k < len(sdk):
                    n2, why = sdk_fix(n, sdk[k], st)
                    if n2 != n:
                        spec.append("    %s  # SDK slot %d is %s (was %s)" % (n2, k, sdk[k], n[:70]))
                        continue
                    if why:
                        spec.append("    %s  # SDK slot %d is %s -- %s" % (n, k, sdk[k], why))
                        continue
                sus = suspect(n, st)
                tag = "SUSPECT" if [x for x in sus if not x.startswith("?")] else "SOFT"
                spec.append("    %s%s" % (n, ("  # %s slot %d 0x%08x: " % (tag, k, st) + " ".join(sus[:3])) if sus else ""))
        if not probs and not opts.get("--all"):
            continue
        bad_tabs += bool(probs)
        print("%s  ours 0x%08x (%d slots)  shipped 0x%08x (%d slots)  %s" % (
            sym, ova, len(oslots), sva, len(sslots),
            "OK" if not probs else "%d bad" % len(probs)))
        for k, kind, ot, st in probs:
            names = sorted(ship2sym.get(st, ()))
            print("   slot %2d %-7s ours=%s  shipped=0x%08x  have: %s" % (
                k, kind, ("0x%08x %s" % (ot, ",".join(a2s.get(ot, [])[:2]))) if ot else "-",
                st, " ".join(names[:3]) or "(none)"))
    print("tables with problems:", bad_tabs)

    if opts.get("--calls"):
        # The link-level wiring check: for every function progress.py places
        # byte-identically, follow each relocation in OUR linked image and in
        # the shipped one. A call or an address that reaches a different
        # function (or datum) than the shipped one did is a wiring bug the
        # masked per-function match cannot see -- typically an alias in
        # link/aliases.rsp onto the wrong definition, or a stand-in symbol
        # resolving to a sibling of the same shape.
        nbad = 0
        dataof = collections.defaultdict(set)    # our data VA -> shipped VAs
        for sym2, aa in seen.items():
            va = resolve(sym2)
            if va:
                dataof[va] |= aa
        for name, sa_ in sorted(sym2ship.items()):
            if name not in placed or len(sa_) != 1 or name not in funcrels:
                continue
            st = next(iter(sa_))
            ova = s2a.get(name)
            if not ova:
                continue
            for off, kind, sym2 in funcrels[name]:
                o = our.dword(ova + off)
                v = ship.dword(st + off)
                if o is None or v is None:
                    continue
                if kind == "rel":
                    o = (ova + off + 4 + o) & 0xFFFFFFFF
                    v = (st + off + 4 + v) & 0xFFFFFFFF
                    if v in our_to_ship(o):
                        continue
                    ok = False
                    for x in a2s.get(o, []):
                        cx = canon(x)
                        if cx in code_of and fits(cx, v) and not hard(cx, v):
                            ok = True
                            break
                    if ok or not our_to_ship(o) and not any(canon(x) in code_of for x in a2s.get(o, [])):
                        continue        # nothing to compare against
                    nbad += 1
                    print("CALL  %s+0x%x (shipped 0x%08x): reaches %s, shipped reaches 0x%08x [%s]" % (
                        name[:60], off, st, ",".join(a2s.get(o, ["0x%08x" % o])[:2])[:90], v,
                        " ".join(sorted(ship2sym.get(v, ()))[:2])[:90]))
                else:
                    if not (ship.tlo <= v < ship.thi) and o in dataof and dataof[o] and v not in dataof[o]:
                        nbad += 1
                        print("DATA  %s+0x%x (shipped 0x%08x): our 0x%08x %s stands for %s, shipped uses 0x%08x" % (
                            name[:60], off, st, o, ",".join(a2s.get(o, [])[:1])[:60],
                            ",".join("0x%08x" % x for x in sorted(dataof[o])[:3]), v))
        print("wiring problems:", nbad)
    if spec is not None:
        open(opts["--spec"], "w").write("\n".join(spec) + "\n")
        print("spec: %d tables, %d MISSING slots -> %s" % (
            sum(1 for l in spec if l.startswith("vtable")),
            sum(1 for l in spec if "MISSING" in l), opts["--spec"]))


if __name__ == "__main__":
    main()
