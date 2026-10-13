#!/usr/bin/env python3
"""Per-target facts for the tools, from progress/targets.py.

The reconstruction tools came from nolfsrc with NOLF's binaries written into
them (`lithtech.exe`, `src/engine/server/Release`, APP_REGION tables). This
module is what they ask instead, so that, like progress.py, they know no
binary by name: a target is found from whatever the user typed (its label,
its stem, or the path of the shipped or built image, in any case), and its
regions, its build, its link inputs and its tables come from targets.py.

  find(name)        the target dict, or exit with the list of labels
  find_or_none(name)
  app_span(t)       (lo, hi) spanning every `app` range
  region(t, a)      "app" / "middleware" / "encrypted" / "crt" (progress.py's)
  built(t)          our image (repository-relative), or None while unbuilt
  objs(t)           the .obj/.lib inputs of our link (its .rsp), [] if none
  objdirs(t)        the directories of those objects, link order, no repeats
  ourmap(t)         our link's .map, or None
  funcs_csv(t)      out/reference/<stem>-functions.csv
  vtabs_csv(t)      out/reference/<stem>-vtables.csv
  cited_src(t)      source roots whose 0x... comments cite this image
  data(t, suffix)   progress/<stem><suffix> (for the evidence CSVs)
  obj_path(t, mod)  the object file behind progress.py's module key (`x.obj`,
                    or `Lib(member.obj)`: the member is unpacked under out/)
  require_built(t)  built(t), or exit with a message naming what builds it

`python3 tools/tgt.py` lists the targets and what each resolves to.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import progress  # noqa: E402

REPO = progress.REPO
cfg = progress.cfg


def _keys(t):
    ks = {t["label"].lower(), t["stem"].lower()}
    for p in (t.get("shipped"), t.get("built")):
        if p:
            ks.add(os.path.basename(p).lower())
            ks.add(os.path.splitext(os.path.basename(p))[0].lower())
    return ks


def find_or_none(name):
    if isinstance(name, dict):
        return name
    n = os.path.basename(str(name).rstrip("/\\")).lower()
    for cand in (n, os.path.splitext(n)[0]):
        for t in cfg.TARGETS:
            if cand in _keys(t):
                return t
    return None


def find(name):
    t = find_or_none(name)
    if t is None:
        sys.exit("%s: not a target of progress/targets.py (%s)" % (
            name, ", ".join(t["label"] for t in cfg.TARGETS)))
    return t


def app_span(t):
    rs = t.get("app") or []
    if not rs:
        return None
    return (min(lo for lo, _ in rs), max(hi for _, hi in rs))


def region(t, a):
    return progress.region(t, a)


def in_app(t, a):
    return progress.in_app(t, a)


def built(t):
    return progress.built_image(t)


def require_built(t, what=""):
    b = built(t)
    if b:
        return b
    sys.exit("%s: no build of ours yet (%s)%s -- build it first (make)" % (
        t["label"], t.get("built") or "no source", what))


def objs(t):
    b = built(t)
    if not b:
        return []
    return progress.link_inputs(b) or []


def objdirs(t):
    out = []
    for o in objs(t):
        if o.lower().endswith(".obj"):
            d = os.path.dirname(o)
            if d not in out:
                out.append(d)
    if not out and built(t):
        out.append(os.path.dirname(built(t)))
    return out


def libs(t):
    third = {x.lower() for x in t.get("third_party") or ()}
    return [o for o in objs(t) if o.lower().endswith(".lib")
            and os.path.basename(o).lower() not in third]


def ourmap(t):
    b = built(t)
    return progress.our_map(b) if b else None


def funcs_csv(t):
    return "%s/%s-functions.csv" % (cfg.REFERENCE, t["stem"])


def vtabs_csv(t):
    return "%s/%s-vtables.csv" % (cfg.REFERENCE, t["stem"])


def data(t, suffix):
    return "%s/%s%s" % (cfg.DATA, t["stem"], suffix)


def obj_path(t, mod):
    """The file behind a module key of progress.py's near list or placements:
    `name.obj` (one of the link's objects) or `lib(member)` (a member of one
    of its libraries, extracted to out/tgt-lib/<lib>/). None if not found."""
    import re
    from libextract import extract
    m = re.match(r"(.+)\((.+)\)$", mod)
    if not m:
        for o in objs(t):
            if os.path.basename(o).lower() == mod.lower():
                return o
        return None
    lib, member = m.group(1).lower(), m.group(2)
    for o in objs(t):
        if o.lower().endswith(".lib") and \
                os.path.splitext(os.path.basename(o))[0].lower() == lib:
            dest = os.path.join(REPO, "out", "tgt-lib", os.path.basename(o))
            if not os.path.isdir(dest) or \
                    os.path.getmtime(dest) < os.path.getmtime(os.path.join(REPO, o)):
                os.makedirs(dest, exist_ok=True)
                extract(os.path.join(REPO, o), dest)
                os.utime(dest)
            p = os.path.join(dest, member)
            return os.path.relpath(p, REPO) if os.path.exists(p) else None
    return None


def cited_src(t):
    """Where comments cite this image's addresses: the target's own
    `cited_src`, else the global CITED_SRC; [] unless the target `cites`."""
    if not t.get("cites"):
        return []
    return list(t.get("cited_src") or cfg.CITED_SRC)


def main():
    os.chdir(REPO)
    for t in cfg.TARGETS:
        span = app_span(t)
        print("%-14s stem=%-10s shipped=%s built=%s" % (
            t["label"], t["stem"], t["shipped"], built(t) or "-"))
        if span:
            print("%14s app 0x%08x..0x%08x  objdirs=%s" % (
                "", span[0], span[1], ",".join(objdirs(t)) or "-"))


if __name__ == "__main__":
    main()
