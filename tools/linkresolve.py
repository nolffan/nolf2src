#!/usr/bin/env python3
"""Map a link's unresolved symbols onto the definitions they really mean.

The per-function oracle (exematch) never sees names: a function is verified
by its bytes with every relocation masked. So the reconstruction is full of
one shipped function or global reached under two spellings -- a caller's
declaration in one TU (often a stand-in or view class, `sub_XXXXXXXX`, an
address-named `g_Unknown...`) and the definition in another. Each TU is
byte-identical on its own; only a link notices the names disagree.

This recovers the pairing from the shipped image instead of guessing it from
names. For every function of ours that exematch places at ONE shipped
address, each relocation it carries is read back out of the shipped bytes:

  REL32 behind a `call`/`jmp`   -> the shipped callee address
  DIR32 (absolute)              -> the shipped address of a global or of a
                                   function taken by address

That gives every symbol we REFERENCE from a placed function the shipped
address it stands for. A symbol we DEFINE gets its address the same way (a
placed function is its own placement; a defined global is whatever address
its references read back). An unresolved symbol and a defined one at the same
address are the same thing, and the answer is an alias.

Only unique, agreeing evidence is used: a symbol read back at two different
addresses (a template modelled once for several instantiations, or a wrong
call) is reported, not aliased.

Usage:
  linkresolve.py <image> <link-output.txt> <obj|lib>... [--alias=out.txt]
                [--nears=<progress.py --nears output>] [--verbose] [--dups]
      --dups lists shipped data addresses that two of our definitions both
      stand for (a global defined twice: links, but is two objects).
      --alias writes one `/ALTERNATENAME:<unresolved>=<defined>` per line,
      ready for a linker response file.
"""
import collections
import glob
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exematch import find  # noqa: E402
from exedump import Pe  # noqa: E402

REL32 = 0x14
DIR32 = 0x06


def parse_obj(data):
    """-> (funcs, defined, undefined).

    funcs: name -> (code, maskset, [(off, kind, symbol)]) for code sections.
    defined: external symbols this object defines (any section).
    undefined: external symbols it references but does not define.
    """
    machine, nsec, _ts, symoff, nsyms, optsz, _ch = struct.unpack_from(
        "<HHIIIHH", data, 0)
    if machine != 0x14C:
        return {}, set(), set()
    strtab = data[symoff + nsyms * 18:]

    def symname(raw):
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            return strtab[off:strtab.find(b"\0", off)].decode("latin-1")
        return raw.rstrip(b"\0").decode("latin-1")

    secs = []
    for i in range(nsec):
        s = 20 + optsz + i * 40
        _vs, _va, rawsz, rawp, relp, _lnp, nrel, _nln = struct.unpack_from(
            "<IIIIIIHH", data, s + 8)
        flags = struct.unpack_from("<I", data, s + 36)[0]
        secs.append((rawsz, rawp, relp, nrel, flags))

    entries = [None] * nsyms
    defined, undefined = set(), set()
    i = 0
    while i < nsyms:
        e = symoff + i * 18
        raw = data[e:e + 18]
        name = symname(raw[:8])
        value, secnum, typ, storage, naux = struct.unpack_from(
            "<IhHBB", raw, 8)
        entries[i] = (name, value, secnum, typ, storage)
        if storage == 2:                       # IMAGE_SYM_CLASS_EXTERNAL
            if secnum > 0:
                defined.add(name)
            elif secnum == 0 and value == 0:
                undefined.add(name)
        i += 1 + naux

    funcs = {}
    for si, (rawsz, rawp, relp, nrel, flags) in enumerate(secs, 1):
        if not flags & 0x20 or rawsz == 0 or rawp == 0:
            continue
        code = data[rawp:rawp + rawsz]
        masks, rels = set(), []
        for r in range(nrel):
            va, idx, typ = struct.unpack_from("<IIH", data, relp + r * 10)
            masks.update(range(va, min(va + 4, rawsz)))
            ent = entries[idx] if idx < nsyms else None
            if not ent:
                continue
            if ent[4] == 3 and typ == DIR32 and ent[2] > 0 \
                    and not ent[0].startswith((".", "$")) and ent[3] != 0x20:
                # a file-scope static datum: named per object by the caller,
                # so two TUs' statics of one name stay apart
                rels.append((va, "abs", "static:" + ent[0]))
                continue
            if ent[4] not in (2,):              # externals only
                continue
            if typ == REL32 and va >= 1 and code[va - 1] in (0xE8, 0xE9):
                rels.append((va, "rel", ent[0]))
            elif typ == DIR32:
                rels.append((va, "abs", ent[0]))
        fsyms = sorted(
            (v, n) for e in entries if e
            for n, v, sn, typ, st in [e]
            if sn == si and st in (2, 3) and typ == 0x20)
        for j, (v, n) in enumerate(fsyms):
            end = fsyms[j + 1][0] if j + 1 < len(fsyms) else rawsz
            fcode = code[v:end]
            while fcode and fcode[-1] in (0x90, 0xCC):
                fcode = fcode[:-1]
            fmask = {m - v for m in masks if v <= m < v + len(fcode)}
            frels = [(o - v, k, s) for o, k, s in rels
                     if v <= o < v + len(fcode)]
            funcs[n] = (fcode, fmask, frels)
    return funcs, defined, undefined


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) if "=" in a else (a, True)
                for a in sys.argv[1:] if a.startswith("--"))
    if len(args) < 3:
        sys.exit(__doc__)
    image, linkout, objs = args[0], args[1], []
    import tempfile
    from libextract import extract
    tmp = tempfile.mkdtemp()
    for o in args[2:]:
        for p in (sorted(glob.glob(o)) if "*" in o else [o]):
            if p.lower().endswith(".lib"):
                d = os.path.join(tmp, os.path.basename(p))
                os.makedirs(d, exist_ok=True)
                extract(p, d)
                objs.extend(sorted(glob.glob(d + "/*")))
            else:
                objs.append(p)

    unresolved = {}
    for line in open(linkout, errors="replace"):
        m = re.search(r"unresolved external symbol (.*?) \((\S+)\)", line)
        if m:
            unresolved[m.group(2)] = m.group(1)
            continue
        # C linkage: the linker prints the decorated name alone
        m = re.search(r"unresolved external symbol (\S+)\s*$", line)
        if m:
            unresolved[m.group(1)] = m.group(1)

    pe = Pe(image)
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]

    parsed, defined_all = {}, set()
    for obj in objs:
        try:
            f, d, _u = parse_obj(open(obj, "rb").read())
        except Exception as exc:                          # noqa: BLE001
            print(f"  skipped {obj}: {exc}", file=sys.stderr)
            continue
        base = os.path.basename(obj)
        for name, (code, mask, rels) in f.items():
            rels[:] = [(o, k, base + "::" + sy[7:] if sy.startswith("static:")
                        else sy) for o, k, sy in rels]
            d |= {sy for _o, _k, sy in rels if sy.startswith(base + "::")}
        parsed[obj] = f
        defined_all |= d

    placed, ambiguous = {}, set()
    for obj, fns in parsed.items():
        for name, (code, mask, _r) in fns.items():
            if len(code) - len(mask) < 8:
                continue
            hits = list(find(text, tva, code, mask))
            if len(hits) == 1:
                if name in placed and placed[name] != hits[0]:
                    ambiguous.add(name)
                placed[name] = hits[0]
            elif len(hits) > 1:
                ambiguous.add(name)
    for n in ambiguous:
        placed.pop(n, None)

    seen = collections.defaultdict(set)       # symbol -> shipped addresses
    for obj, fns in parsed.items():
        for name, (_code, _mask, rels) in fns.items():
            if name not in placed:
                continue
            base = placed[name]
            for off, kind, sym in rels:
                i = base - tva + off
                if i + 4 > len(text):
                    continue
                v = struct.unpack_from("<i" if kind == "rel" else "<I",
                                       text, i)[0]
                seen[sym].add(base + off + 4 + v if kind == "rel" else v)

    addr_of = {}                                # defined symbol -> address
    for n, a in placed.items():
        addr_of[n] = a
    # Nears: written, not byte-identical, but paired to one address by
    # progress.py (--nears=<pairs.txt>, the output of progress.py --nears).
    if opts.get("--nears"):
        for line in open(opts["--nears"]):
            m = re.match(r"\S+\s+(0x[0-9a-f]+)\s+\d+\s+\d+\s+\S+\s+\S+?:(\S+)",
                         line)
            if m and m.group(2) not in addr_of:
                addr_of[m.group(2)] = int(m.group(1), 16)
    # Functions whose bytes occur several times: a candidate at each copy.
    multi = collections.defaultdict(set)
    for obj, fns in parsed.items():
        for name, (code, mask, _r) in fns.items():
            if name in addr_of or len(code) - len(mask) < 8:
                continue
            hits = list(find(text, tva, code, mask))
            if 1 < len(hits) <= 16:
                for h in hits:
                    multi[h].add(name)
    for n, addrs in seen.items():
        if n in defined_all and n not in addr_of and len(addrs) == 1:
            addr_of[n] = next(iter(addrs))
    by_addr = collections.defaultdict(set)
    for n, a in addr_of.items():
        by_addr[a].add(n)

    if opts.get("--dups"):
        # One shipped global defined twice links cleanly and breaks the DLL at
        # run time: each spelling is its own object. Functions sharing an
        # address are fine (/OPT:ICF folds identical bodies); data is not.
        data = collections.defaultdict(set)
        for n, addrs in seen.items():
            if n in defined_all and n not in placed and len(addrs) == 1:
                data[next(iter(addrs))].add(n)
        dups = {a: ns for a, ns in data.items() if len(ns) > 1}
        print(f"shipped data addresses with more than one definition: "
              f"{len(dups)}")
        for a in sorted(dups):
            print(f"  DUP  {a:#x}  {'  '.join(sorted(dups[a]))}")

    aliases, conflict, nodef, noev = [], [], [], []
    for u, dem in sorted(unresolved.items(), key=lambda x: x[1]):
        addrs = seen.get(u, set())
        if not addrs:
            noev.append((u, dem))
            continue
        if len(addrs) > 1:
            conflict.append((u, dem, sorted(addrs)))
            continue
        a = next(iter(addrs))
        cands = sorted(by_addr.get(a, ()))
        if not cands and len(multi.get(a, ())) == 1:
            cands = sorted(multi[a])
        if len(cands) == 1:
            aliases.append((u, cands[0], a, dem))
        elif cands:
            conflict.append((u, dem, [a] + cands))
        else:
            nodef.append((u, dem, a))

    print(f"unresolved {len(unresolved)}: aliasable {len(aliases)}, "
          f"no definition at its address {len(nodef)}, "
          f"conflicting evidence {len(conflict)}, "
          f"no evidence (only referenced from unplaced code) {len(noev)}")
    if opts.get("--verbose"):
        for u, d, a, dem in aliases:
            print(f"  ALIAS  {a:#x}  {dem}  ->  {d}")
        for u, dem, a in nodef:
            print(f"  NODEF  {a:#x}  {dem}")
        for u, dem, x in conflict:
            print(f"  CONFL  {dem}  {[hex(v) if isinstance(v, int) else v for v in x]}")
        for u, dem in noev:
            print(f"  NOEV   {dem}")
    if opts.get("--alias"):
        with open(opts["--alias"], "w") as f:
            for u, d, _a, _dem in aliases:
                f.write(f"/ALTERNATENAME:{u}={d}\n")


if __name__ == "__main__":
    main()
