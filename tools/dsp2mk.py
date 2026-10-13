#!/usr/bin/env python3
"""Make rules for Monolith's Visual C++ 6 workspace, as Developer Studio
would build it.

  tools/dsp2mk.py [--have "<project>..."] <workspace.dsw> <config> <out.mk> <project>...

Reads the workspace and, for each named project and every project it
depends on (the workspace's Project_Dep_Name lines), its .dsp: the
configuration `<config>` ("Final", "Release", ...; a project without that
configuration builds its "Release" one, as the libraries have no "Final"),
its source files, the files excluded from that configuration, per-file
compiler settings and custom build steps. It writes build/build.mk's rules
for them, through build.mk's `compile` and `tool` macros:

  every .c/.cpp   cl (or the compiler in the make variable CL_<project>,
                  where build.mk sets one) <the project's ADD CPP, with the file's own ADD CPP
                  and SUBTRACT CPP applied, less /FD> /Fp"<intdir>\\<project>.pch"
                  (unless the file names its own /Fp)
                  /Fo"<intdir>\\" <source>, in the project's directory
  every .rc       rc <ADD RSC> /fo"<intdir>\\<name>.res" <source>
  custom builds   a source's custom build step (flex, bison) as its
                  commands, run by cmd.exe in the project's directory;
                  steps on the project's output (copies into a rez
                  directory) are left out
  a library       lib <ADD LIB32> <objects>
  a DLL or exe    link <ADD LINK32> /def:<the .def file the project lists
                  as a source, if any> <objects> <resources> <the .lib files
                  the project lists as sources> <the outputs of the library
                  projects it depends on, not already named>

Files excluded from the configuration (`# PROP Exclude_From_Build 1`) are
neither compiled nor linked. Projects named by --have (build.mk's PROJECTS:
those an earlier workspace's rules already build, such as the libraries
the game's and the engine's workspaces share) get no rules here, only
their outputs, to link.

Paths are as the .dsp spells them, relative to the project's directory; the
outputs land where its Output_Dir / Intermediate_Dir / /out: say. Every
project gets make variables P_<name>_OUT (its output, relative to the tree
root) and a phony target <name>. Projects the workspace names but the source
release lacks (ltmem) are skipped with a note on stderr.
"""
import ntpath
import os
import re
import shlex
import sys


# /YX compiles of a project run one at a time in its file order, the first
# one writing the precompiled header and the next using it if its headers
# start the same way (or writing its own). Where the retail binary was
# built from another order, its first object is named here:
# - ServerDir: CServerDir_Titan.cpp comes first in ServerDir.dsp, and
#   compiled first it writes a header of all its includes and compiles to
#   375,182 bytes; compiled after stdafx.cpp (stdafx.h's header) it is
#   377,910 bytes and six more of ServerDir.dll's functions are retail's
#   (0x10003cc0, 0x100043a0, 0x100044a0, 0x10008850, 0x10010060,
#   0x10010120). progress/identical.txt was recorded from such a rebuild.
YX_FIRST = {"serverdir": "stdafx.obj"}

_spelling = {}


def canon(path, leaf=True):
    """`path` (/-separated, relative to the tree root) as the disk spells it,
    matching each component case-insensitively as Windows does; a component
    that does not exist yet (a build directory) gets the spelling it was
    first given, so that `Built` and `built` are one directory to make too."""
    parts = path.split("/")
    out = []
    for i, comp in enumerate(parts):
        if not leaf and i == len(parts) - 1:
            out.append(comp)
            break
        here = "/".join(out) or "."
        key = (here.lower(), comp.lower())
        real = None
        if os.path.isdir(here):
            real = next((e for e in os.listdir(here) if e.lower() == comp.lower()), None)
        if real is None:
            real = _spelling.setdefault(key, comp)
        out.append(real)
    return "/".join(out)


def winjoin(base, rel, leaf=True):
    """A Windows path relative to directory `base` (a Windows path relative
    to the tree root), normalised, with / separators for make, as the disk
    spells it (canon; with leaf=False only its directories: a file a build
    step makes keeps the name the step gives it)."""
    p = ntpath.normpath(ntpath.join(base, rel))
    return canon(p.replace("\\", "/"), leaf)


def split_flags(s):
    """cl/link flags as Developer Studio writes them: /D "X" is two words,
    /I "..\\x" two words, /Yu"stdafx.h" one; quotes dropped."""
    out = []
    for tok in shlex.split(s.replace("\\", "\x00"), posix=True):
        out.append(tok.replace("\x00", "\\"))
    return out


class Config:
    def __init__(self):
        self.outdir = self.intdir = ""
        self.cpp, self.rsc, self.link, self.lib = [], [], [], []
        self.sub_cpp, self.sub_link = [], []


class SourceFile:
    def __init__(self, path):
        self.path = path
        self.excluded = False
        self.add_cpp, self.sub_cpp = [], []
        self.custom = None          # [command lines]
        self.custom_outputs = []


def parse_dsp(path, want, exact=None):
    """(project name, type, chosen config name, Config, [SourceFile]). The
    configuration is `exact` if given, else the one named `want`, else
    Release."""
    text = open(path, encoding="latin-1").read().replace("\r\n", "\n")
    lines = text.split("\n")
    name = re.search(r'Project File - Name="([^"]+)"', text).group(1)
    ttype = re.search(r'# TARGTYPE "[^"]*\) ([^"]+)"', text).group(1)
    configs = re.findall(r'!(?:IF|ELSEIF)\s+"\$\(CFG\)" == "([^"]+)"', text)
    full = [c for c in dict.fromkeys(configs) if c.endswith(" " + want)]
    if not full:
        full = [c for c in dict.fromkeys(configs) if c.endswith(" Release")]
    cfgname = exact or full[0]
    if ttype == "External Target":
        # Developer Studio runs Cmd_Line: here, always another configuration
        # of a project (`msdev X.dsp /MAKE "X - Win32 Final MFC DLL"`)
        block = text.split(f'"$(CFG)" == "{cfgname}"', 1)[1].split("!E", 1)[0]
        m = re.search(r'# PROP Cmd_Line "msdev (\S+) /MAKE "([^"]+)""', block)
        if not m:
            sys.exit(f"dsp2mk: {path}: an external target that is not msdev /MAKE")
        sub = winjoin(os.path.dirname(path).replace("/", "\\"), m.group(1))
        return parse_dsp(sub, want, m.group(2))

    cfg = Config()
    files = []
    cur_cfg = None              # the config the current !IF block is about
    in_target = False
    sf = None
    custom = None
    for raw in lines:
        line = raw.strip()
        m = re.match(r'!(?:IF|ELSEIF)\s+"\$\(CFG\)" == "([^"]+)"', line)
        if m:
            cur_cfg = m.group(1)
            continue
        if line == "!ENDIF":
            cur_cfg = None
            continue
        if line == "# Begin Target":
            in_target = True
            continue
        mine = cur_cfg is None or cur_cfg == cfgname
        if custom is not None:
            if line == "# End Custom Build":
                if mine and sf is not None:
                    sf.custom = custom
                custom = None
            else:
                custom.append(raw)
            continue
        if line == "# Begin Custom Build":
            custom = []
            continue
        if not mine:
            continue
        if not in_target:
            for key, attr in (("# PROP Output_Dir ", "outdir"), ("# PROP Intermediate_Dir ", "intdir")):
                if line.startswith(key):
                    setattr(cfg, attr, line[len(key):].strip().strip('"'))
            for key, attr in (("# ADD CPP ", "cpp"), ("# ADD RSC ", "rsc"), ("# ADD LINK32 ", "link"),
                              ("# ADD LIB32 ", "lib"), ("# SUBTRACT CPP ", "sub_cpp"),
                              ("# SUBTRACT LINK32 ", "sub_link")):
                if line.startswith(key):
                    getattr(cfg, attr).extend(split_flags(line[len(key):]))
            continue
        if line == "# Begin Source File":
            sf = SourceFile(None)
            continue
        if line.startswith("SOURCE=") and sf is not None:
            sf.path = line[len("SOURCE="):].strip().strip('"')
            continue
        if line == "# End Source File":
            if sf is not None and sf.path:
                files.append(sf)
            sf = None
            continue
        if sf is None:
            continue
        if line.startswith("# PROP Exclude_From_Build"):
            sf.excluded = line.split()[-1] == "1"
        elif line.startswith("# ADD CPP "):
            sf.add_cpp.extend(split_flags(line[len("# ADD CPP "):]))
        elif line.startswith("# SUBTRACT CPP "):
            sf.sub_cpp.extend(split_flags(line[len("# SUBTRACT CPP "):]))
    return name, ttype, cfgname, cfg, files


def apply_cpp(base, add, sub):
    """The project's cl flags with a file's ADD CPP and SUBTRACT CPP."""
    flags = list(base)
    for f in add:
        if f[:3] in ("/Yc", "/Yu", "/YX"):
            flags = [g for g in flags if g[:3] not in ("/Yc", "/Yu", "/YX")]
        flags.append(f)
    for s in sub:
        flags = [g for g in flags if not g.startswith(s)]
    return flags


def without(flags, prefixes):
    return [f for f in flags if not any(f.lower().startswith(p) for p in prefixes)]


def parse_dsw(path):
    """{project: (dsp path relative to the workspace's directory, [deps])}."""
    text = open(path, encoding="latin-1").read().replace("\r\n", "\n")
    out = {}
    for m in re.finditer(r'Project: "([^"]+)"=(\S+) - Package Owner=<4>(.*?)(?=\n#{20,})', text, re.S):
        deps = re.findall(r"Project_Dep_Name\s+(\S+)", m.group(3))
        out[m.group(1).lower()] = (m.group(1), m.group(2), deps)
    return out


def q(w):
    """A word inside build.mk's `$(call compile,...)` arguments."""
    return w.replace("$", "$$").replace(",", "$(comma)")


def main():
    have = set()
    if len(sys.argv) > 2 and sys.argv[1] == "--have":
        have = {re.sub(r"\W", "_", n).lower() for n in sys.argv[2].replace(",", " ").split()}
        del sys.argv[1:3]
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    dsw, want, out_mk = sys.argv[1], sys.argv[2], sys.argv[3]
    wsdir = os.path.dirname(dsw)                    # relative to the tree root
    projects = parse_dsw(dsw)

    order, seen = [], set()

    def visit(n):
        key = n.lower()
        if key in seen:
            return
        seen.add(key)
        if key not in projects:
            print(f"dsp2mk: {n}: not in the workspace, skipped", file=sys.stderr)
            return
        for d in projects[key][2]:
            visit(d)
        order.append(key)
    for n in sys.argv[4:]:
        visit(n)

    mk = [f"# Generated by tools/dsp2mk.py from {dsw} ({want}); do not edit", ""]
    outputs = {}
    pch_makers = {}             # library project -> the object that makes its .pch
    for key in order:
        pname, rel, deps = projects[key]
        dsp = winjoin(wsdir, rel)
        if not os.path.exists(dsp):
            print(f"dsp2mk: {pname}: {dsp} is not in the source release, skipped", file=sys.stderr)
            continue
        pdir = os.path.dirname(dsp)
        mark = len(mk)
        name, ttype, cfgname, cfg, files = parse_dsp(dsp, want)
        wdir = pdir.replace("/", "\\")
        intdir = cfg.intdir or "."
        outdir = cfg.outdir or "."
        var = re.sub(r"\W", "_", pname)
        objs, ress, libs = [], [], []
        defs = []                   # the .def file, as the project dir sees it
        pch_objs = []               # (object, c|u|x for /Yc, /Yu, /YX) in file order
        generated = []              # the outputs of custom build steps
        # /FD (the minimal-rebuild dependency file) writes vc60.idb in the
        # project directory, which parallel compiles would fight over; it
        # does not change the code
        # /Zm1000 (ten times the memory for the precompiled header, which VC6
        # must reserve at the address it was made at) fails about every other
        # compile under Wine with C1060 "out of heap space"; /Zm200 never
        # does, and gives the same objects (the headers need far less).
        cflags = ["/Zm200" if f == "/Zm1000" else f for f in cfg.cpp if f not in ("/c", "/FD")]
        cflags = apply_cpp(cflags, [], cfg.sub_cpp)
        for sf in files:
            if sf.excluded:
                continue
            src = sf.path
            low = src.lower()
            ext = os.path.splitext(low)[1]
            if sf.custom and ext in (".l", ".y"):
                body = [ln for ln in sf.custom if ln.strip()]
                outs, cmds = [], []
                for ln in body:
                    m = re.match(r'"([^"]+)"\s*:', ln.strip())
                    if m:
                        outs.append(m.group(1))
                    elif ln.startswith("\t") and not ln.strip().startswith("$("):
                        cmds.append(ln.strip())
                if any(ln.lstrip().startswith("BuildCmds=") for ln in body):
                    cmds, grab = [], False
                    for ln in body:
                        if ln.lstrip().startswith("BuildCmds="):
                            grab = True
                            continue
                        if grab:
                            if not ln.startswith("\t"):
                                break
                            c = ln.strip().rstrip("\\").strip()
                            if c:
                                cmds.append(c)
                outs_rel = [winjoin(wdir, o, leaf=False) for o in outs]
                generated += outs_rel
                # one cmd.exe line, each command in parentheses: `if exist X
                # del X & ren ...` would make the ren part of the if
                mk.append(f"$(eval $(call custom,{' '.join(outs_rel)},{winjoin(wdir, src)},{pdir},"
                          f"{q(' & '.join('(' + c + ')' for c in cmds))}))")
                continue
            if ext in (".c", ".cpp", ".cxx"):
                flags = apply_cpp(cflags, sf.add_cpp, sf.sub_cpp)
                pch = any(f[:3] in ("/Yc", "/Yu", "/YX") for f in flags)
                cmd = [f for f in flags]
                if pch and not any(f[:3] == "/Fp" for f in cmd):
                    cmd.append(f"/Fp{intdir}\\{name}.pch")
                cmd += [f"/Fo{intdir}\\", "/c"]
                base = os.path.splitext(ntpath.basename(src))[0]
                obj = winjoin(wdir, f"{intdir}\\{base}.obj")
                objs.append(obj)
                mk.append(f"$(eval $(call compile,{obj},{pdir},{q(src)},$(ENV_GAME),$(or $(CL_{var}),$(CL)),"
                          f"{q(' '.join(cmd))},wine-drives))")
                if pch:
                    kind = next(f[2] for f in flags if f[:3] in ("/Yc", "/Yu", "/YX")).lower()
                    pch_objs.append((obj, kind))
            elif ext == ".rc":
                base = os.path.splitext(ntpath.basename(src))[0]
                res = winjoin(wdir, f"{intdir}\\{base}.res")
                ress.append(res)
                mk.append(f"$(eval $(call rcfile,{res},{pdir},{q(src)},{winjoin(wdir, src)},"
                          f"{q(' '.join(cfg.rsc + [f'/fo{intdir}' + chr(92) + base + '.res']))}))")
            elif ext == ".lib":
                libs.append(winjoin(wdir, src))
            elif ext == ".def":
                defs.append(src)
        # Sources include what the custom build steps generate (AnimationLex.cpp
        # includes AnimationLex.o), which tools/mkdeps.py cannot find before
        # it exists: every compile of the project waits for them.
        if generated:
            mk.append(f"{' '.join(objs)}: {' '.join(generated)}")
        # The compiles that use the precompiled header (/Yu) wait for the one
        # that makes it (/Yc). With /YX any compile may write it, so those
        # run one at a time, in the project's file order, as Developer
        # Studio runs them.
        makers = [o for o, kind in pch_objs if kind == "c"]
        for o, kind in pch_objs:
            if kind == "u" and makers and o != makers[0]:
                mk.append(f"{o}: {makers[0]}")
        yx = [o for o, kind in pch_objs if kind == "x"]
        first = YX_FIRST.get(pname.lower())
        if first:
            yx.sort(key=lambda o: ntpath.basename(o).lower() != first)
        for prev, nxt in zip(yx, yx[1:]):
            mk.append(f"{nxt}: {prev}")
        if makers:
            pch_makers[key] = makers[0]
        # the output
        if ttype == "Static Library":
            outspec = next((f[5:] for f in cfg.lib if f.lower().startswith("/out:")), f"{outdir}\\{name}.lib")
        else:
            default = f"{outdir}\\{name}.{'exe' if ttype == 'Application' else 'dll'}"
            outspec = next((f[5:] for f in cfg.link if f.lower().startswith("/out:")), default)
        out = winjoin(wdir, outspec)
        outputs[key] = out
        if re.sub(r"\W", "_", pname).lower() in have:
            del mk[mark:]
            pch_makers.pop(key, None)
            print(f"dsp2mk: {pname}: built by an earlier workspace's rules -> {out}", file=sys.stderr)
            continue
        # Developer Studio links the outputs of the library projects this one
        # depends on, after the libraries it lists as sources -- unless the
        # link line already names the library (linked through /libpath).
        # Every one of them is a prerequisite either way.
        deplibs = [outputs[d.lower()] for d in deps if outputs.get(d.lower(), "").endswith(".lib")]
        named = {f.lower() for f in cfg.link if f.lower().endswith(".lib")}
        for o in deplibs:
            if o.lower() not in [l.lower() for l in libs] and os.path.basename(o).lower() not in named:
                libs.append(o)
        prereqs = objs + ress + libs + [o for o in deplibs if o not in libs] + [winjoin(wdir, d) for d in defs]
        rel = lambda p: ntpath.relpath(p.replace("/", "\\"), wdir)
        mk.append(f"P_{var}_OUT := {out}")
        mk.append(f"P_{var}_OBJS := {' '.join(objs)}")
        if ttype == "Static Library":
            flags = without(cfg.lib, ["/out:"]) + [f"/out:{outspec}"]
            mk.append(f"$(eval $(call library,{out},{pdir},{q(' '.join(flags))},"
                      f"{' '.join(objs)},{' '.join(rel(o) for o in objs)}))")
        else:
            flags = without(apply_cpp(cfg.link, [], cfg.sub_link), ["/out:", "/pdb", "/debug"])
            flags.append(f"/out:{outspec}")
            flags += [f"/def:{d}" for d in defs]
            ins = objs + ress + libs
            # Compiled with /Z7 (the debug builds), an object that uses a
            # precompiled header refers to the type information in the
            # object that made it, which a link takes out of a library only
            # if something else needs it (LNK1211): build.mk links those of
            # the libraries explicitly then.
            pchs = [pch_makers[d.lower()] for d in deps if d.lower() in pch_makers]
            mk.append(f"$(eval $(call binary,{out},{pdir},{q(' '.join(flags))},"
                      f"{' '.join(prereqs)},{' '.join(rel(o) for o in ins)},{' '.join(rel(o) for o in pchs)}))")
        mk.append(f".PHONY: {var}")
        mk.append(f"{var}: {out}")
        mk.append(f"PROJECTS += {var}")
        mk.append("")
        print(f"dsp2mk: {pname}: {cfgname}, {len(objs)} objects -> {out}", file=sys.stderr)
    data = "\n".join(mk) + "\n"
    if not os.path.exists(out_mk) or open(out_mk).read() != data:
        with open(out_mk, "w") as f:
            f.write(data)


if __name__ == "__main__":
    main()
