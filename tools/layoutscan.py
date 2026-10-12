"""Find NEARS that are STRUCT LAYOUT errors rather than codegen.

The signature, found the hard way on soundinst2.cpp's CSndInstance*J::Init:
a near that is SIZE-EXACT, has ZERO mnemonic differences, and whose every
differing byte is a field displacement off the same base, all shifted by the
same constant. That is not register allocation or scheduling -- it is a
missing (or surplus) field in our class declaration, and ONE line of source
closes every function that touches the struct.

Reports, per object, the functions showing the signature and the constant
shift, so the fix can be made once at the header rather than per function.

Usage: layoutscan.py [--image=lithtech.exe] [--min-hits=1]
"""
import re, subprocess, sys, collections, os

def nears(target):
    out = subprocess.run([sys.executable, "tools/progress.py", "--nears=" + target],
                         capture_output=True, text=True).stdout
    rows = []
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 6 and p[1].startswith("0x") and int(p[4]) == 0:   # size-exact only
            obj, _, sym = p[5].partition(":")
            rows.append((p[1], int(p[2]), obj, sym))
    return rows

def analyse(addr, obj, sym, image, objdir):
    """Return (shift, nhits) if the layout signature holds, else None."""
    r = subprocess.run([sys.executable, "tools/fndiff.py", addr,
                        os.path.join(objdir, obj), sym, "--image=" + image],
                       capture_output=True, text=True).stdout
    if "mnemonic diff: 0 block(s)" not in r:
        return None                      # structure differs -> not a layout error
    deltas = []
    for m in re.finditer(r"^\s*ship \S+:\s*((?:[0-9a-f]{2}\s)+?)\s+ours \S+:\s*((?:[0-9a-f]{2}\s*)+?)\s*$",
                         r, re.M):
        a = [int(x, 16) for x in m.group(1).split()]
        b = [int(x, 16) for x in m.group(2).split()]
        if len(a) != len(b) or len(a) < 3:
            return None                  # different instruction lengths -> not it
        # the displacement is the trailing little-endian tail that differs
        da = [i for i in range(len(a)) if a[i] != b[i]]
        if not da:
            continue
        # rebuild both displacements from the differing tail onward
        lo = da[0]
        va = int.from_bytes(bytes(a[lo:]), "little")
        vb = int.from_bytes(bytes(b[lo:]), "little")
        deltas.append(va - vb)
    if not deltas:
        return None
    return (deltas, len(deltas))

def main():
    opts = dict(x.split("=", 1) for x in sys.argv[1:] if "=" in x)
    target = opts.get("--image", "lithtech.exe")
    image = "out/reference/%s" % target
    objdir = "src/engine/%s/Release" % ("lithtech" if "lithtech" in target else "server")
    hits = collections.defaultdict(list)
    rows = nears(target)
    print(f"scanning {len(rows)} size-exact nears in {target}\n")
    for addr, size, obj, sym in rows:
        res = analyse(addr, obj, sym, image, objdir)
        if res:
            deltas, n = res
            uniq = sorted(set(deltas))
            hits[obj].append((addr, size, sym, uniq, n))
    total = sum(len(v) for v in hits.values())
    print(f"{total} functions show the signature, in {len(hits)} objects\n")
    # A TRUE layout error has ONE uniform shift across every displacement.
    # Mixed shifts are frame-slot swaps or independent field differences and
    # are NOT fixed by a single padding change -- rank them apart.
    uni = {o: [r for r in v if len(r[3]) == 1] for o, v in hits.items()}
    uni = {o: v for o, v in uni.items() if v}
    nuni = sum(len(v) for v in uni.values())
    print(f"  of those, {nuni} have a SINGLE UNIFORM SHIFT -- the true layout signature")
    print(f"  the rest have mixed shifts and are not one-padding fixes\n")
    print("=" * 62)
    print("UNIFORM-SHIFT HITS (fix the header once, close every function)")
    print("=" * 62)
    for o in sorted(uni, key=lambda o: -len(uni[o])):
        sh = sorted({d for _, _, _, u, _ in uni[o] for d in u})
        print(f"\n### {o}   {len(uni[o])} function(s), shift {sh}")
        for addr, size, sym, u, n in sorted(uni[o], key=lambda r: r[1]):
            print(f"    {addr} {size:>5}  +{u[0]:<4} ({n} disp)  {sym[:58]}")
    print("\n" + "=" * 62)
    print("MIXED-SHIFT (not layout errors; frame or field differences)")
    print("=" * 62)
    for obj in sorted(hits, key=lambda o: -len(hits[o])):
        rows_ = hits[obj]
        allshift = sorted({d for _, _, _, u, _ in rows_ for d in u})
        print(f"=== {obj}   {len(rows_)} function(s), shifts {allshift}")
        for addr, size, sym, uniq, n in sorted(rows_, key=lambda r: r[1]):
            print(f"      {addr} {size:>5}  shift={uniq} ({n} disp)  {sym[:60]}")
        print()

main()
