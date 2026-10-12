#!/usr/bin/env python3
"""Name a stripped image's functions from the error-tag literals they push.

Almost every engine interface method opens with a parameter check that reports
failure through a macro taking the method's own name as a string:

    RETURN_ERROR(1, "ILTPhysics::SetVelocity", LT_INVALIDPARAMS);

The literal survives the strip. So does the `push $addr-of-literal` that hands
it to the reporter — which means the *function that pushes it* is the function
the literal names. That is the cheapest naming oracle a symbol-less binary
has, and it is what turned server.dll's recon from guesswork into a worklist.

This finds every `Class::Method` literal, every push of its address, and the
enclosing function of each push (function bounds come from the enumeration in
out/reference/<target>-functions.csv, written by build/reference.sh with
tools/enumfuncs.py --csv).

Usage:
  tagmap.py <image> <functions.csv> [--class Foo] [--undone]

  tagmap.py out/reference/lithtech.exe out/reference/lithtech-functions.csv

--undone drops every name we have already reconstructed, leaving the actual
worklist, and groups what is left by class with the classes that carry the
most bytes first. Status comes from out/progress/functions.csv (regenerate it
with progress.py); a function counts as done unless its row says "todo", so
nears stay off the list -- they are near-match work, not decompilation work.
"""
import bisect
import csv
import os
import re
import struct
import sys


class Image:
    def __init__(self, path):
        d = self.d = open(path, "rb").read()
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        nsec = struct.unpack_from("<H", d, pe + 6)[0]
        optsz = struct.unpack_from("<H", d, pe + 20)[0]
        self.base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
        self.secs = []
        for i in range(nsec):
            s = pe + 24 + optsz + i * 40
            name = d[s:s + 8].rstrip(b"\0").decode("latin-1")
            vs, va, rs, rp = struct.unpack_from("<IIII", d, s + 8)
            self.secs.append((name, self.base + va, vs, rp, rs))

    def sec(self, name):
        for s in self.secs:
            if s[0] == name:
                return s
        return None

    def bytes_at(self, addr, n):
        for _, va, vs, rp, rs in self.secs:
            if va <= addr < va + vs:
                o = rp + (addr - va)
                return self.d[o:o + n]
        return b""


TAG = re.compile(rb"[A-Za-z_][A-Za-z0-9_]{1,40}::[A-Za-z_][A-Za-z0-9_]{1,48}\0")


def our_methods(image_path):
    """Method names our objects define, however we happened to class them.

    A tag says ILTPhysics::SetVelocity; our source calls the same function
    SPhysicsLT::SetVelocity, because the tag names the interface and we name
    the implementation. So the class half cannot be compared and the method
    half can: symbols are mangled ?Method@Class@@..., so the leading segment
    is the method name and that is what to look for.
    """
    rel = {"lithtech.exe": "src/engine/lithtech/Release",
           "server.dll": "src/engine/server/Release",
           "d3d.ren": "src/engine/d3d/Release"}
    target = os.path.basename(image_path)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(root, rel.get(target, ""))
    out = set()
    if not rel.get(target) or not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if not fn.endswith(".obj"):
            continue
        try:
            blob = open(os.path.join(d, fn), "rb").read()
        except OSError:
            continue
        for m in re.finditer(rb"\?([A-Za-z_][A-Za-z0-9_]*)@", blob):
            out.add(m.group(1).decode("latin-1"))
    return out


_TODO_CACHE = {}


def todo_addrs(image_path):
    """Addresses progress.py last classified "todo" for this image.

    The status file names each unreconstructed function sub_<addr>, which is
    the only key the two tools share -- tagmap works from the shipped image
    and progress.py from our objects, so neither knows the other's symbols.
    """
    target = os.path.basename(image_path)
    if target in _TODO_CACHE:
        return _TODO_CACHE[target]
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "out", "progress", "functions.csv")
    out = set()
    try:
        with open(path, newline="") as fh:
            for r in csv.reader(fh):
                if len(r) == 4 and r[0] == target and r[1].startswith("sub_"):
                    if r[3].strip() == "todo":
                        out.add(int(r[1][4:], 16))
    except OSError:
        sys.exit(f"tagmap: --undone needs {path}; run tools/progress.py first")
    if not out:
        sys.exit(f"tagmap: {path} has no todo rows for {target} -- either the "
                 f"target name is wrong or the file is stale; rerun progress.py")
    _TODO_CACHE[target] = out
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) if "=" in a else (a, True)
                for a in sys.argv[1:] if a.startswith("--"))
    if len(args) != 2:
        sys.exit(__doc__)
    img = Image(args[0])

    # every Class::Method literal, by address
    lit = {}
    for _, va, vs, rp, rs in img.secs:
        blk = img.d[rp:rp + rs]
        for m in TAG.finditer(blk):
            lit[va + m.start()] = m.group(0)[:-1].decode("latin-1")

    # function bounds
    funcs = sorted((int(r["addr"], 16), int(r["size"]))
                   for r in csv.DictReader(open(args[1])))
    starts = [a for a, _ in funcs]
    size = dict(funcs)

    # every push imm32 / mov $imm32,reg of a literal address, in .text
    text = img.sec(".text")
    tv, tp, ts = text[1], text[3], text[4]
    blk = img.d[tp:tp + ts]
    hits = {}
    for addr, name in lit.items():
        pat = struct.pack("<I", addr)
        for m in re.finditer(re.escape(pat), blk):
            i = m.start()
            if i >= 1 and blk[i - 1] == 0x68:            # push imm32
                site = tv + i - 1
            elif i >= 1 and 0xB8 <= blk[i - 1] <= 0xBF:  # mov $imm32,r32
                site = tv + i - 1
            else:
                continue
            k = bisect.bisect_right(starts, site) - 1
            if k < 0:
                continue
            f = starts[k]
            if site >= f + size[f]:
                continue
            hits.setdefault(f, set()).add(name)

    # A literal pushed from more than one function does not name a function:
    # it names an *inlined* method, and the pushes are its call sites. Split
    # those out or they swamp the worklist — CPacket::ReadType alone appears
    # in sixty-nine of lithtech.exe's functions.
    where = {}
    for f, names in hits.items():
        for n in names:
            where.setdefault(n, []).append(f)

    want = opts.get("--class")
    rows, inlined = [], []
    for n, fs in where.items():
        if want and not n.startswith(want + "::"):
            continue
        if len(fs) == 1:
            rows.append((n, fs[0], size[fs[0]]))
        else:
            inlined.append((n, len(fs)))
    rows.sort()
    named = len(rows)
    all_named = list(rows)
    if opts.get("--undone"):
        todo = todo_addrs(args[0])
        rows = [r for r in rows if r[1] in todo]
        # "todo" is an address-level verdict: a function we wrote whose near
        # pairing did not land leaves its shipped address unclaimed and so
        # shows up here as though no source existed. Splitting on whether we
        # define a method of that name keeps the flag from under-reporting
        # the way the unimplemented one over-reported.
        mine = our_methods(args[0])
        def have(tag):
            meth = tag.split("::", 1)[1]
            # the engine's free functions wear an si_/sm_/ci_/cm_ prefix on
            # the same name, so a suffix hit counts as ours too
            return meth in mine or any(
                m.endswith(meth) and m[:-len(meth)].endswith("_") for m in mine)

        fresh = [r for r in rows if not have(r[0])]
        written = [r for r in rows if have(r[0])]
        by_class = {}
        for n, f, s in fresh:
            by_class.setdefault(n.split("::")[0], []).append((n, f, s))
        for cls, v in sorted(by_class.items(),
                             key=lambda kv: -sum(x[2] for x in kv[1])):
            print(f"\n{cls}  ({len(v)} functions, {sum(x[2] for x in v)} bytes)")
            for n, f, s in sorted(v, key=lambda x: -x[2]):
                print(f"   {n.split('::', 1)[1]:<46} 0x{f:08x} {s:>6}")
        print(f"\n{len(fresh)} of {named} named functions have no source yet")
        if written:
            print(f"\n{len(written)} more are unclaimed addresses whose method "
                  f"name we already define — an unpaired near, not new work; "
                  f"confirm with progress.py --nears before writing anything:")
            for n, f, s in sorted(written, key=lambda x: -x[2]):
                print(f"   {n:<52} 0x{f:08x} {s:>6}")
    else:
        print(f"{'name':<52} {'addr':<12} {'size':>6}")
        for n, f, s in rows:
            print(f"{n:<52} 0x{f:08x} {s:>6}")
        print(f"\n{named} functions named, {len(lit)} literals in the image")
    if inlined:
        print(f"\n{len(inlined)} literals appear in more than one function — "
              f"inlined methods, whose pushes are call sites, not definitions:")
        for n, k in sorted(inlined, key=lambda r: -r[1]):
            print(f"   {n:<48} in {k} functions")
    # from the full naming, not the filtered worklist -- a name we have
    # already reconstructed is still a name that was pushed somewhere.
    unpushed = (set(lit.values()) - {r[0] for r in all_named}
                - {n for n, _ in inlined})
    if unpushed and not want:
        print(f"\n{len(unpushed)} literals with no push found (the reporter "
              f"call was inlined away, or the address is register-loaded):")
        for n in sorted(unpushed)[:12]:
            print("   ", n)


if __name__ == "__main__":
    main()
