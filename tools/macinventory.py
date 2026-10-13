#!/usr/bin/env python3
"""The Mac NOLF2 engine's functions, each with the source file it belongs to.

    tools/macinventory.py --jupiter <Dev/Source> [--root <nolf2-mac-usa>] [--out progress/engine]

writes, deterministically (the same inputs give the same bytes):

  mac-functions.csv         the engine (NOLF2.app/Contents/MacOS/NOLF2)
  mac-server-functions.csv  the dedicated server's engine (NOLF2Srv.app's server.dll)
  mac-modules.md            per module and per file: functions and bytes; the
                            Jupiter files the Mac engine has nothing of; the
                            Mac classes the Jupiter tree has no file for

<Dev/Source> is the F.E.A.R. source tree's Dev/Source (its `runtime/` is
LithTech Jupiter, NOLF2's engine line: docs/engine/fear-mapping.md). The Mac
release comes from `rez/fetch-isos.sh nolf2-mac-usa && rez/install-games.sh
nolf2-mac-usa`; --root defaults to rez/games/nolf2-mac-usa.

Columns: addr, size (to the next symbol: includes alignment padding),
section (__text: in object order; __textcoal_nt: coalesced templates and
inlines; __StaticInit: one per __mod_init_func entry, unnamed and in link
order, left unattributed: each inlines its file's constructors), category,
file, evidence, name (demangled, as c++filt prints it), mangled.

category:
  engine   Monolith's engine code: a file of the Jupiter tree (or a path
           the binary names) defines it or contains it
  stl      libstdc++ instantiations (std::, __gnu_cxx::)
  omni     The Omni Group's port layer: their D3D8 / D3DX / DirectInput8 /
           DirectMusic / DirectSound / Win32 emulation (OD3D8::, ODM*, OGL*,
           Objective-C methods, functions in a `.mm` file by a path string)
  runtime  the Mach-O start-up code (start, dyld glue)
  unknown  none of the above could be shown: Monolith's Mac-only code
           (QTVideoMgr), classes the Jupiter tree no longer has, Omni code
           with Win32 names, libm

file: for Jupiter files, the path relative to `runtime/` (client/src/
clientmgr.cpp); a file of the Jupiter tree outside it starts `libs/` or
`sdk/`; a Monolith path the binary names that Jupiter does not have is as the
binary spells it below `Source/` (Engine/Runtime/...). Empty when unknown.

evidence (how the file was decided):
  defn       the Jupiter tree defines this name (Class::method, or a free
             function) in exactly one file -- after leaving out other
             platforms' copies (sys/linux, null drivers) -- or in several of
             which the neighbours (below) pick one
  path       the function references a source-path string the binary
             carries (an assert's __FILE__): `macho.py paths`
  neighbour  the functions on both sides of it in __text belong to the same
             file: the linker lays out each object's code together, so a run
             between two functions of one file is that file's
  none       no evidence
"""

import argparse
import collections
import csv
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import macho  # noqa: E402

LIBS = ["lith", "stdlith", "rezmgr", "ltmem", "zlib"]
# other platforms' copies, and kernel/toport (Jupiter's portable rewrite of
# kernel files whose sys/win versions the Mac binary names by path)
OTHER_PLATFORM = re.compile(r"/sys/(linux|null|nulldib|s_nul|xenon|xbox|ps3)/|/toport/")
CONTROL = {"if", "for", "while", "switch", "catch", "do", "else", "return",
           "sizeof", "__declspec", "defined", "throw", "new", "delete"}


# ---------------------------------------------------------------------------
# The Jupiter tree: which file defines which function

def _strip(src):
    """C/C++ source without comments, string/char literals, preprocessor
    lines (their contents kept as blanks), so braces and parens balance."""
    out, i, n = [], 0, len(src)
    line_start = True
    while i < n:
        c = src[i]
        if line_start and c == "#":
            j = i
            while j < n and src[j] != "\n":
                if src[j] == "\\" and j + 1 < n and src[j + 1] == "\n":
                    j += 1
                j += 1
            out.append(" ")
            i = j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
            continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            out.append('""' if c == '"' else "' '")
            i = j + 1
            continue
        if c == "\n":
            line_start = True
        elif not c.isspace():
            line_start = False
        out.append(c)
        i += 1
    return "".join(out)


_CLASS_HEAD = re.compile(r"\b(class|struct|union|namespace)\s+(?:\w+\s+)*?(\w+)\s*"
                         r"(?:<[^{;]*>)?\s*(?::[^{;]*)?$")
_TARGS = r"<[^<>()]*(?:<[^<>()]*(?:<[^<>()]*>[^<>()]*)*>[^<>()]*)*>"
_FUNC_NAME = re.compile(r"((?:\b\w+\s*(?:" + _TARGS + r")?\s*::\s*)*"
                        r"(?:~\s*\w+|operator\s*(?:\(\s*\)|[^\w\s(]+|\w[\w\s\*&]*?)|\w+))"
                        r"\s*$")


_OPSYM = re.compile(r"operator\s*(<<=|>>=|<<|>>|<=|>=|->\*|->|<|>)")
_OPNAME = {"<<=": "lshift_eq", ">>=": "rshift_eq", "<<": "lshift", ">>": "rshift",
           "<=": "le", ">=": "ge", "->*": "arrowstar", "->": "arrow", "<": "lt",
           ">": "gt"}
_OPBACK = {v: k for k, v in _OPNAME.items()}


def _protect(s):
    """Operator names with angle brackets (`operator<`, `operator->`) as
    words, so template-depth counting is not thrown by them."""
    return _OPSYM.sub(lambda m: "operator_" + _OPNAME[m.group(1)] + "_", s)


def _unprotect(s):
    return re.sub(r"operator_(\w+?)_(?=\W|$)",
                  lambda m: "operator" + _OPBACK.get(m.group(1), m.group(1)), s)


def _norm(qual):
    """`CMoArray<T>::Foo` -> ['CMoArray', 'Foo']; `operator ==` -> 'operator=='."""
    parts, depth, cur = [], 0, ""
    for ch in _protect(qual):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif depth == 0:
            cur += ch
    parts = [p.strip() for p in cur.split("::")]
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p)
        if p.startswith("operator"):
            p = "operator" + re.sub(r"\s+", "", p[8:]) if not re.match(
                r"operator\s+\w", p) else "operator " + p[8:].strip()
        out.append(_unprotect(p.replace("~ ", "~")))
    return [p for p in out if p]


def definitions(text):
    """(qualified name parts) of every function this source defines with a
    body: out-of-class `A::B::f(...) {`, free functions, and functions
    defined inside a class body."""
    s = _strip(text)
    defs = []
    stack = []          # per '{': ('ns'|'class', name) or ('func'|'other', None)
    last = 0            # start of the current statement head
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in ";":
            last = i + 1
        elif c == "}":
            if stack:
                stack.pop()
            last = i + 1
        elif c == "{":
            head = s[last:i].strip()
            inside_func = any(k in ("func", "other") for k, _ in stack)
            kind = ("other", None)
            if not inside_func:
                m = _CLASS_HEAD.search(head)
                if m and "(" not in head.split(m.group(1))[-1]:
                    kind = ("class" if m.group(1) != "namespace" else "ns", m.group(2))
                elif "(" in head and not head.rstrip().endswith("="):
                    name = _func_name(head)
                    if name:
                        cls = [nm for k, nm in stack if k == "class"]
                        parts = _norm(name)
                        if parts:
                            defs.append((cls + parts) if cls else parts)
                    kind = ("func", None)
                elif head.startswith("extern") and head.endswith('""'):
                    kind = ("ns", None)
            stack.append(kind)
            last = i + 1
        i += 1
    return defs


def _func_name(head):
    """The function name of a definition head `ret A::f(args) const : init`."""
    # the parameter list is the first '(' at template depth 0, except
    # `operator()(...)`
    head = _protect(re.sub(r"\s+", " ", head))
    m = re.search(r"operator\s*\(\s*\)\s*\(", head)
    if m:
        pre = head[:m.start()] + "operator()"
    else:
        depth, k = 0, -1
        for j, ch in enumerate(head):
            if ch == "<":
                depth += 1
            elif ch == ">":
                depth = max(0, depth - 1)
            elif ch == "(" and depth == 0:
                k = j
                break
        if k < 0:
            return None
        pre = head[:k]
    m = _FUNC_NAME.search(pre)
    if not m:
        return None
    name = m.group(1).strip()
    last = _norm(name)[-1:] or [""]
    if last[0] in CONTROL or not re.match(r"[A-Za-z_~]", last[0]):
        return None
    # a macro invocation at file scope (`IMPLEMENT_X(Foo) {`) has no return
    # type and no qualification: still a definition, keep it
    return name


def jupiter_index(source):
    """{key: set(files)} for keys 'Class::method' (last two components) and
    'func' (free functions), over runtime/, sdk/inc and the engine libs."""
    roots = [("runtime", "")]
    roots += [("libs/" + lib, "libs/" + lib) for lib in LIBS]
    roots += [("sdk/inc", "sdk/inc")]
    index = collections.defaultdict(set)
    files = []
    for sub, prefix in roots:
        top = os.path.join(source, sub)
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames.sort()
            for fn in sorted(filenames):
                if not re.search(r"\.(cpp|c|h|hpp|inl)$", fn, re.I):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, top).replace(os.sep, "/")
                rel = prefix + "/" + rel if prefix else rel
                files.append(rel)
                with open(full, "rb") as f:
                    text = f.read().decode("latin-1")
                for parts in definitions(text):
                    index[_key(parts)].add(rel)
    return index, files


def _key(parts):
    return "::".join(parts[-2:])


# ---------------------------------------------------------------------------
# Mac names -> keys and categories

def mac_key(dem):
    """'A::B<int>::f(int) const' -> 'B::f'; a template function's return
    type and its own template args are dropped."""
    s = dem
    if s.startswith(("vtable for", "typeinfo", "guard variable", "non-virtual thunk",
                     "virtual thunk", "<static init")):
        return None
    if s.endswith(" const"):
        s = s[:-6]
    s = _protect(s)
    # cut the parameter list: the last top-level '(...)'
    depth, k = 0, None
    for j in range(len(s) - 1, -1, -1):
        ch = s[j]
        if ch == ")":
            depth += 1
        elif ch == "(":
            depth -= 1
            if depth == 0:
                k = j
                break
    if k is None:
        return _key(_norm(s)) if re.match(r"^[\w:~]+$", s) else None
    s = s[:k]
    # drop a return type: the name is what follows the last space outside
    # <> -- before `operator`, when the name is an operator (`operator new`,
    # `operator char const*`)
    depth, spaces, op = 0, [], None
    for j, ch in enumerate(s):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif depth == 0:
            if ch == " ":
                spaces.append(j)
            elif op is None and s.startswith("operator", j) and \
                    (j == 0 or not (s[j - 1].isalnum() or s[j - 1] == "_")):
                op = j
    limit = op if op is not None else len(s)
    before = [j for j in spaces if j < limit]
    if before:
        s = s[before[-1] + 1:]
    parts = _norm(s)
    return _key(parts) if parts else None


OMNI = re.compile(r"^(OD3D8|ODM|ODI|ODS|OGL|OGP|Omni|OW32|ODX|OFS|OQT|ODInput)|"
                  r"^[-+]\[|^_?D3DX|^_OGL|^OBJC|^_objc|\bODM[A-Z]|"
                  r"^(IUnknownImpl|DataBufferDevice|MouseDevice8|KeyboardDevice8|"
                  r"JoystickDevice8|DirectInput8A|IDirect3D\w*8|Win32_|OSX|_?_?OS[A-Z])|"
                  r"\bNS[A-Z]\w+\*")
# Apple's libgcc / libsupc++ / dyld glue linked into the image
RUNTIME = re.compile(
    r"^(start|_start|__?call_mod_init_funcs|__?dyld_\w+|dyld_stub_binding_helper|"
    r"__cxxabiv1::|__cxa_|___?cxa_|__gxx|___?gxx|_?_Unwind|___?(u?(mod|div)di3|"
    r"ashldi3|lshrdi3|ashrdi3|cmpdi2|ucmpdi2|fix\w*di|float\w*di\w*|muldi3)$|"
    r"___?darwin|__?keymgr|size_of_encoded_value|read_encoded_value|"
    r"base_of_encoded_value|parse_lsda_header|get_adjusted_ptr|"
    r"dl(open|close|sym|error)$|__?eh_|frame_dummy|_?_?(de)?register_frame|"
    r"init_object|search_object|fde_|classify_object_over_fdes|add_fdes|"
    r"linear_search_fdes|binary_search_\w*fdes|execute_cfa_program|uw_|"
    r"extract_cie_info|__terminate|__unexpected|___?terminate|"
    r"std::(terminate|unexpected|set_\w+|exception|bad_\w+|type_info|uncaught_exception))")
STL = re.compile(r"^(std::|__gnu_cxx::)|^[^(]*?\b(std|__gnu_cxx)::\S+ (std|__gnu_cxx)::|"
                 r"^[\w:<>,\*& ]+? (std|__gnu_cxx)::")
THUNK = re.compile(r"^(non-virtual thunk to |virtual thunk to |covariant return thunk to )")


def category_of(f, dem):
    raw = f.name.lstrip("_")
    if RUNTIME.search(dem) or RUNTIME.search(f.name) or RUNTIME.search(raw):
        return "runtime"
    if STL.search(dem):
        return "stl"
    if OMNI.search(dem) or OMNI.search(raw):
        return "omni"
    return None


def norm_mac_path(p):
    """A path string of the binary -> (tree-relative path, is_monolith)."""
    p = p.replace("\\", "/")
    m = re.search(r"Source/Engine/Runtime/(.*)$", p, re.I)
    if m:
        return m.group(1), True
    m = re.search(r"Source/(?:Engine/)?libs/(.*)$", p, re.I)
    if m:
        return "libs/" + m.group(1), True
    if re.search(r"/Omni/|\.mm?$|^O[A-Z]\w*\.h$", p):
        return None, False
    return p, True


# ---------------------------------------------------------------------------

def inventory(path, index, jfiles):
    m = macho.MachO(path)
    funcs = m.functions()
    lower = {}
    for jf in jfiles:
        lower.setdefault(jf.lower(), jf)
        lower.setdefault("base:" + jf.rsplit("/", 1)[-1].lower(), jf)

    # path evidence
    paths = dict(m.source_paths())
    path_of = {}
    for f in funcs:
        for _, t, k in m.refs(f):
            if t in paths and k != "call":
                rel, monolith = norm_mac_path(paths[t])
                if rel is None:
                    path_of.setdefault(f.addr, ("", "omni"))
                    continue
                jf = lower.get(rel.lower()) or (lower.get("base:" + rel.lower())
                                                if "/" not in rel else None)
                if jf is None and "/" not in rel:
                    jf = None
                path_of.setdefault(f.addr, (jf or ("Engine/Runtime/" + rel
                                                   if "/" in rel and not rel.startswith("libs/")
                                                   else rel), None))

    rows = []
    for f in funcs:
        dem = macho.demangle(f.name)
        if dem == f.name and dem.startswith("_"):
            dem = dem[1:]               # a C name: Mach-O prefixes an underscore
        base = THUNK.sub("", dem)
        cat = category_of(f, base)
        key = mac_key(base) if cat is None else None
        cands = sorted(index.get(key, ())) if key else []
        if len(cands) > 1:
            main = [c for c in cands if not OTHER_PLATFORM.search("/" + c)]
            cands = main or cands
        row = dict(addr=f.addr, size=f.size, section=f.section, category=cat or "",
                   file="", evidence="none", name=dem, mangled=f.name, cands=cands)
        if len(cands) == 1:
            row.update(file=cands[0], evidence="defn")
        if f.addr in path_of:
            pf, pcat = path_of[f.addr]
            if pcat == "omni":
                row.update(category="omni")
            elif not row["file"]:
                row.update(file=pf, evidence="path")
        rows.append(row)

    # ambiguous definitions: pick the candidate a neighbour has
    text = [r for r in rows if r["section"] == "__text"]
    for i, r in enumerate(text):
        if not r["file"] and len(r["cands"]) > 1:
            near = _neighbour_files(text, i)
            pick = [c for c in r["cands"] if c in near]
            if len(pick) == 1:
                r.update(file=pick[0], evidence="defn")
    # neighbour runs in __text
    for _ in range(2):
        for i, r in enumerate(text):
            if r["file"] or r["category"] in ("omni", "stl", "runtime"):
                continue
            prev = next((x for x in reversed(text[:i]) if x["file"]), None)
            nxt = next((x for x in text[i + 1:] if x["file"]), None)
            if prev and nxt and prev["file"] == nxt["file"]:
                r.update(file=prev["file"], evidence="neighbour")
    # categories by neighbours: an unattributed function between two of
    # Omni's (or the runtime's) in __text is theirs
    for i, r in enumerate(text):
        if r["category"] or r["file"]:
            continue
        prev = next((x for x in reversed(text[:i]) if x["category"] or x["file"]), None)
        nxt = next((x for x in text[i + 1:] if x["category"] or x["file"]), None)
        if prev and nxt and prev["category"] == nxt["category"] and \
                prev["category"] in ("omni", "runtime"):
            r["category"] = prev["category"]
    for r in rows:
        if not r["category"]:
            r["category"] = "engine" if r["file"] or r["cands"] else "unknown"
    return m, rows


def _neighbour_files(text, i, reach=8):
    out = set()
    for j in range(max(0, i - reach), min(len(text), i + reach + 1)):
        if j != i and text[j]["file"]:
            out.add(text[j]["file"])
    return out


def write_csv(rows, path):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["addr", "size", "section", "category", "file", "evidence",
                "name", "mangled"])
    for r in rows:
        w.writerow(["0x%08x" % r["addr"], r["size"], r["section"], r["category"],
                    r["file"], r["evidence"], r["name"], r["mangled"]])
    with open(path, "w", newline="") as f:
        f.write(buf.getvalue())


def module_of(path):
    if not path:
        return "(none)"
    p = path.split("/")
    if p[0] in ("libs", "sdk"):
        return "/".join(p[:2])
    if p[0] == "kernel" and len(p) > 1 and p[1] in ("io", "mem", "net"):
        return "kernel/" + p[1]
    if p[0] == "Engine":
        return "(Monolith path, not in Jupiter)"
    return p[0]


def summary(sets, jfiles):
    out = []
    w = out.append
    w("# The Mac NOLF2 engine, by module and file\n")
    w("Generated by `tools/macinventory.py` from the Mac release's engine and "
      "server (`tools/macho.py`) and the LithTech Jupiter tree. Functions "
      "and bytes per module and per file; the evidence for each function is "
      "in the CSVs beside this file.\n")
    used = set()
    for label, rows in sets:
        used |= {r["file"] for r in rows if r["file"]}
        w("## %s\n" % label)
        cat = collections.Counter()
        catb = collections.Counter()
        ev = collections.Counter()
        for r in rows:
            cat[r["category"]] += 1
            catb[r["category"]] += r["size"]
            if r["category"] == "engine":
                ev[r["evidence"]] += 1
        w("| Category | Functions | Bytes |\n|---|---:|---:|")
        for c in sorted(cat, key=lambda c: -catb[c]):
            w("| %s | %d | %d |" % (c, cat[c], catb[c]))
        w("| total | %d | %d |\n" % (len(rows), sum(catb.values())))
        eng = cat["engine"]
        w("Engine functions by evidence: " + ", ".join(
            "%s %d (%.1f%%)" % (k, ev[k], 100.0 * ev[k] / max(1, eng))
            for k in ("defn", "path", "neighbour", "none")) + ".\n")
        mods = collections.defaultdict(lambda: [0, 0, set()])
        files = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            if r["category"] != "engine":
                continue
            md = mods[module_of(r["file"])]
            md[0] += 1
            md[1] += r["size"]
            if r["file"]:
                md[2].add(r["file"])
                files[r["file"]][0] += 1
                files[r["file"]][1] += r["size"]
        w("| Module | Files | Functions | Bytes |\n|---|---:|---:|---:|")
        for md in sorted(mods, key=lambda k: -mods[k][1]):
            w("| %s | %d | %d | %d |" % (md, len(mods[md][2]), mods[md][0], mods[md][1]))
        w("")
        w("<details><summary>Per file</summary>\n")
        w("| File | Functions | Bytes |\n|---|---:|---:|")
        for fn in sorted(files):
            w("| %s | %d | %d |" % (fn, files[fn][0], files[fn][1]))
        w("\n</details>\n")
        # Mac classes with no Jupiter file: no function of the class is
        # attributed anywhere
        known, cls = set(), collections.Counter()
        for r in rows:
            k = mac_key(THUNK.sub("", r["name"]))
            if k and "::" in k and r["file"]:
                known.add(k.split("::")[0])
        for r in rows:
            if r["category"] == "unknown" and r["mangled"].startswith("__Z"):
                k = mac_key(THUNK.sub("", r["name"]))
                if k and "::" in k and k.split("::")[0] not in known:
                    cls[k.split("::")[0]] += 1
        w("Classes the Jupiter tree has no file for (no function of theirs is "
          "attributed), with their function counts:\n")
        w(", ".join("%s (%d)" % (c, n) for c, n in sorted(cls.items())) + "\n")
    cpp = [f for f in jfiles if f.endswith((".cpp", ".c")) and "/" in f
           and not f.startswith(("sdk/", "libs/zlib"))
           and not OTHER_PLATFORM.search("/" + f)]
    missing = [f for f in cpp if f not in used]
    w("## Jupiter files the Mac engine has nothing of\n")
    w("%d of the %d Jupiter `.cpp`/`.c` files (other platforms' left out) have "
      "no function attributed in either binary: mostly what Jupiter added after "
      "2002, or code the Mac build did not use.\n" % (len(missing), len(cpp)))
    bymod = collections.defaultdict(list)
    for f in missing:
        bymod[module_of(f)].append(f)
    for md in sorted(bymod):
        w("- **%s**: %s" % (md, ", ".join("`%s`" % x for x in bymod[md])))
    w("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--jupiter", required=True,
                    help="the F.E.A.R. tree's Dev/Source (runtime/, libs/, sdk/)")
    ap.add_argument("--root", default=os.environ.get("NOLF2_MAC", macho.ROOT_DEFAULT),
                    help="the nolf2-mac-usa install")
    ap.add_argument("--out", default="progress/engine")
    a = ap.parse_args()
    index, jfiles = jupiter_index(a.jupiter)
    os.makedirs(a.out, exist_ok=True)
    sets = []
    for label, which, name in (("Engine (NOLF2.app)", "engine", "mac-functions.csv"),
                               ("Server (NOLF2Srv.app's server.dll)", "server",
                                "mac-server-functions.csv")):
        _, rows = inventory(macho.resolve(which, a.root), index, jfiles)
        write_csv(rows, os.path.join(a.out, name))
        sets.append((label, rows))
    with open(os.path.join(a.out, "mac-modules.md"), "w") as f:
        f.write(summary(sets, jfiles))


if __name__ == "__main__":
    main()
