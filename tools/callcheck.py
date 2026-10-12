#!/usr/bin/env python3
"""Check that our calls go where the shipped calls go.

exematch masks every byte a relocation covers, so a `call rel32` is compared
as one opcode byte and four holes. A function wired to the WRONG callee is
therefore byte-identical to a function wired to the right one, and this
project has shipped that mistake more than once -- CRateController::Update and
CNetMgr::DebugPrint both called a tail-jump thunk in front of CBaseCounter::Read
instead of Read itself, and stayed "byte-identical" for months.

This closes that hole. For every function exematch places at a unique shipped
address, it reads the four bytes behind each masked `call`/`jmp rel32`,
resolves the shipped target, resolves OUR relocation's symbol, and reports
three kinds of disagreement:

  WRONG     our callee symbol is itself placed at address A, and the shipped
            call goes to B. Definite: the source names the wrong function.

  SPLIT     one symbol of ours is called from several sites and the shipped
            targets are not all the same address. At least one site is wrong,
            even though no address for the symbol is known.

  MERGED    two different symbols of ours reach one shipped address. Either
            one is wrong, or the two are the same function under two names --
            which is worth knowing either way.

SPLIT and MERGED need no knowledge of where the callee lives, which is what
makes them useful: most callees are still unreconstructed.

ONE EXPECTED FALSE POSITIVE, and it is most of the raw output on this
codebase: where the shipped image has several template instantiations with
identical bodies, our source deliberately models them with ONE symbol --
`CMoArray<void*, NoCache>` stands in for the whole four-byte-element family.
Every such symbol is genuinely called from sites that reach different shipped
addresses, so it SPLITs, and a caller placed at one instantiation's address
reports WRONG against another's. Filter on `?$` in the callee's mangled name
to set those aside. What is left -- CRT entry points, engine allocators, named
member functions -- is where the real findings are, because those have exactly
one shipped address each.

Found on its first run, all four invisible to every other oracle:
  * twenty string compares with the wrong case sensitivity (`strcmp` is at
    0x1003e1f0 and `stricmp` at 0x10047080; w_ReadWorldLights alone had twelve)
  * CBaseCounter::ReadRaw dividing signed where the shipped build divides
    unsigned (__alldiv 0x1003e940 vs __aulldiv 0x1003e8d0)
  * se_LoadModelData calling dalloc where the shipped build calls the
    `operator new` forwarder in front of it

Usage:
  callcheck.py <image> <obj>...            [--verbose] [--csv=out.csv]

Exit status is 1 if anything was reported, so it can gate a build.
"""
import collections
import csv
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exematch import find  # noqa: E402
from exedump import Pe  # noqa: E402

REL32 = 0x14  # IMAGE_REL_I386_REL32


def parse_obj_calls(data):
    """Per function symbol: (code, maskset, [(offset, callee_symbol), ...]).

    The call list holds every REL32 relocation whose opcode byte is a direct
    `call` (0xe8) or `jmp` (0xe9) -- the two forms that name a function and
    that exematch masks. Indirect calls through a vtable carry no relocation
    and are not this tool's business; a wrong vtable SLOT is a different bug
    and shows up as a mnemonic difference.
    """
    if len(data) < 20:
        return {}
    machine, nsec, _ts, symoff, nsyms, optsz, _ch = struct.unpack_from(
        "<HHIIIHH", data, 0)
    if machine != 0x14C:
        return {}
    strtab = data[symoff + nsyms * 18:]

    def symname(raw):
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            return strtab[off:strtab.find(b"\0", off)].decode("latin-1")
        return raw.rstrip(b"\0").decode("latin-1")

    secs = []
    for i in range(nsec):
        s = 20 + optsz + i * 40
        vsize, _va, rawsz, rawp, relp, _lnp, nrel, _nln = struct.unpack_from(
            "<IIIIIIHH", data, s + 8)
        flags = struct.unpack_from("<I", data, s + 36)[0]
        secs.append((rawsz, rawp, relp, nrel, flags))

    # The symbol table is indexed by ENTRY, not by symbol: an entry with aux
    # records occupies naux+1 slots and a relocation's index counts those.
    # Getting this wrong silently attributes every call to the wrong callee,
    # which is exactly the failure this tool exists to catch, so it is built
    # as a flat list with the aux slots left in place.
    entries = [None] * nsyms
    i = 0
    while i < nsyms:
        e = symoff + i * 18
        raw = data[e:e + 18]
        name = symname(raw[:8])
        value, secnum, typ, storage, naux = struct.unpack_from("<IhHBB", raw, 8)
        entries[i] = (name, value, secnum, typ, storage)
        i += 1 + naux

    out = {}
    for si, (rawsz, rawp, relp, nrel, flags) in enumerate(secs, 1):
        if not flags & 0x20 or rawsz == 0 or rawp == 0:
            continue
        code = data[rawp:rawp + rawsz]
        masks = set()
        rels = []
        for r in range(nrel):
            va, idx, typ = struct.unpack_from("<IIH", data, relp + r * 10)
            masks.update(range(va, min(va + 4, rawsz)))
            if typ == REL32 and va >= 1 and code[va - 1] in (0xE8, 0xE9):
                ent = entries[idx] if idx < nsyms else None
                if ent:
                    rels.append((va - 1, ent[0]))
        fsyms = sorted(
            (v, n) for i, e in enumerate(entries) if e
            for n, v, sn, typ, st in [e]
            if sn == si and st in (2, 3) and typ == 0x20)
        for j, (v, n) in enumerate(fsyms):
            end = fsyms[j + 1][0] if j + 1 < len(fsyms) else rawsz
            fcode = code[v:end]
            while fcode and fcode[-1] in (0x90, 0xCC):
                fcode = fcode[:-1]
            fmask = {m - v for m in masks if v <= m < v + len(fcode)}
            fcalls = [(o - v, s) for o, s in rels if v <= o < v + len(fcode)]
            out[n] = (fcode, fmask, fcalls)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) if "=" in a else (a, True)
                for a in sys.argv[1:] if a.startswith("--"))
    if len(args) < 2:
        sys.exit(__doc__)
    image, objs = args[0], args[1:]
    expanded = []
    for o in objs:
        expanded.extend(sorted(glob.glob(o)) if "*" in o else [o])

    pe = Pe(image)
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]

    # Pass one: where does each of our function symbols live in the image?
    # Only UNIQUE placements are usable. A function whose masked bytes occur
    # twice tells us nothing about which copy a call reaches, and the generic
    # template bodies in this codebase occur many times over.
    placed = {}
    ambiguous = set()
    parsed = {}
    for obj in expanded:
        try:
            fns = parse_obj_calls(open(obj, "rb").read())
        except Exception as exc:
            print(f"  skipped {obj}: {exc}", file=sys.stderr)
            continue
        parsed[obj] = fns
        for name, (code, mask, _calls) in fns.items():
            if len(code) - len(mask) < 8:
                continue
            hits = list(find(text, tva, code, mask))
            if len(hits) == 1:
                if name in placed and placed[name] != hits[0]:
                    ambiguous.add(name)
                placed[name] = hits[0]
            elif len(hits) > 1:
                ambiguous.add(name)
    for name in ambiguous:
        placed.pop(name, None)

    # Pass two: read the shipped target behind every masked call we can site.
    sites = []                                  # (caller, off, sym, target)
    for obj, fns in parsed.items():
        tu = os.path.basename(obj)
        for name, (code, mask, calls) in fns.items():
            if name not in placed or not calls:
                continue
            base = placed[name]
            for off, callee in calls:
                i = base - tva + off
                if i + 5 > len(text) or text[i] not in (0xE8, 0xE9):
                    continue      # our call landed on a byte that is not one
                rel = struct.unpack_from("<i", text, i + 1)[0]
                sites.append((tu, name, off, callee, base + off + 5 + rel))

    by_sym = collections.defaultdict(set)
    by_addr = collections.defaultdict(set)
    for tu, name, off, callee, tgt in sites:
        by_sym[callee].add(tgt)
        by_addr[tgt].add(callee)

    rows = []
    for tu, name, off, callee, tgt in sorted(sites):
        if callee in placed and placed[callee] != tgt:
            rows.append(("WRONG", tu, name, off, callee, tgt, placed[callee]))
    for callee, tgts in sorted(by_sym.items()):
        if len(tgts) > 1:
            rows.append(("SPLIT", "", "", 0, callee, sorted(tgts)[0], 0))
    # Two of our symbols reaching one shipped address is only interesting when
    # the two are actually different code. Identical COMDAT bodies under two
    # names -- a base class's method and a view class's copy of it, the same
    # template instantiated twice -- reach one address because they ARE one
    # function, and reporting those buries the real finding in noise.
    bodies = {}
    for fns in parsed.values():
        for n, (code, mask, _c) in fns.items():
            bodies.setdefault(n, (code, tuple(sorted(mask))))
    for tgt, names in sorted(by_addr.items()):
        if len(names) < 2:
            continue
        seen = {bodies[n] for n in names if n in bodies}
        if len(seen) <= 1 and all(n in bodies for n in names):
            continue
        rows.append(("MERGED", "", "", 0, "; ".join(sorted(names)), tgt, 0))

    print(f"{len(placed)} function(s) placed uniquely, "
          f"{len(sites)} direct call site(s) resolved, "
          f"{len(ambiguous)} symbol(s) ambiguous and skipped")
    if opts.get("--verbose"):
        for tu, name, off, callee, tgt in sorted(sites):
            print(f"  {placed[name]:#010x}+{off:<5} {name[:60]:<60} "
                  f"-> {tgt:#010x}  {callee}")

    for r in rows:
        kind, tu, name, off, callee, tgt, want = r
        if kind == "WRONG":
            print(f"WRONG  {tu} {name}+{off}: source calls {callee}, which is "
                  f"at {want:#010x}, but the shipped call goes to {tgt:#010x}")
        elif kind == "SPLIT":
            addrs = " ".join(f"{a:#010x}" for a in sorted(by_sym[callee]))
            print(f"SPLIT  {callee} is called from several of our functions "
                  f"and the shipped targets differ: {addrs}")
        else:
            print(f"MERGED {tgt:#010x} is reached by more than one of our "
                  f"symbols: {callee}")

    out = opts.get("--csv")
    if out:
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["kind", "tu", "caller", "offset", "callee",
                        "shipped_target", "expected"])
            for kind, tu, name, off, callee, tgt, want in rows:
                w.writerow([kind, tu, name, off, callee,
                            f"0x{tgt:08x}", f"0x{want:08x}" if want else ""])
        print(f"\nwrote {out}")

    if not rows:
        print("no disagreement found")
    sys.exit(1 if rows else 0)


if __name__ == "__main__":
    main()
