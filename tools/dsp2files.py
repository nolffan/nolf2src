#!/usr/bin/env python3
"""Extract the source-file list for one config from a VC6 .dsp project.

Usage: dsp2files.py <project.dsp> <config-name> [ext,ext,...]

Prints repo-style relative paths (as written in the .dsp, backslashes
converted), honouring per-config "Exclude_From_Build" properties.
Example config names: "Release", "Debug", "Final Release", "Final Debug".
"""
import sys


def parse(dsp_path, config):
    files = []  # (path, excluded)
    cur_source = None
    cur_excluded = False
    # Config scoping: inside a SOURCE block, !IF/!ELSEIF select a config.
    in_if = False
    if_matches = False
    saw_config_specific_exclude = False

    with open(dsp_path, "r", encoding="latin-1") as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith("SOURCE="):
                if cur_source is not None:
                    files.append((cur_source, cur_excluded))
                cur_source = line[len("SOURCE="):].strip().strip('"')
                cur_excluded = False
                in_if = False
                if_matches = False
            elif line.startswith(("!IF ", "!ELSEIF ")) and cur_source is not None:
                in_if = True
                if_matches = f'"$(CFG)" == "{cfg_full}"' in line
            elif line.startswith("!ENDIF") and cur_source is not None:
                in_if = False
                if_matches = False
            elif "# PROP Exclude_From_Build 1" in line and "BASE" not in line:
                if cur_source is not None and (not in_if or if_matches):
                    cur_excluded = True
    if cur_source is not None:
        files.append((cur_source, cur_excluded))
    return files


if __name__ == "__main__":
    dsp, config = sys.argv[1], sys.argv[2]
    exts = sys.argv[3].split(",") if len(sys.argv) > 3 else ["cpp", "c"]
    # Project name from the dsp header for full config string
    name = None
    with open(dsp, "r", encoding="latin-1") as fh:
        for line in fh:
            if line.startswith("# Microsoft Developer Studio Project File - Name="):
                name = line.split('Name="')[1].split('"')[0]
                break
    cfg_full = f"{name} - Win32 {config}"
    for path, excluded in parse(dsp, config):
        if excluded:
            continue
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext in exts:
            print(path.replace("\\", "/"))
