# 02 · The verification loop

The whole method rests on a strict oracle: tools that tell you, per function,
whether your machine code equals the retail machine code. You never guess
whether you are right -- you diff.

## The tools

All live in `tools/` and are plain Python 3 (the disassemblers also need
`objdump` from binutils, which the build image has). [`tools/README.md`](../tools/README.md)
describes every tool; these are the core of the loop.

| Tool | What it does | Use when |
|---|---|---|
| `dumpfn.py` | Disassemble one function from a `.obj` in isolation | Inspecting your output |
| `exedump.py` | Annotated disassembly of a PE `.text` range (imports and strings resolved) | Reading a retail exe/dll with no symbols |
| `exematch.py` | Search a retail image for each function of our objects, relocations masked | Verifying engine reconstructions |
| `fndiff.py` | One-shot retail-vs-ours function diff: bytes, mnemonics, best register renaming, fingerprint hints | The engine iteration loop |
| `bindiff.py` | Segment-level code compare of two whole PE files (relocation-normalised) | Whole-DLL sanity |
| `rsrcdiff.py` | Compare PE resource trees payload by payload | Resource targets (`ltmsg.dll`, `CRes.dll`, the engine's `.rc`) |
| `progress.py` | Per-function scoreboard across all targets | Tracking; picking work |

The fast engine loop is these two commands, a few seconds a cycle (in
`make shell`):

```sh
build/engine.sh server-one <file.cpp> [symbol]      # recompile ONE file, match it
python3 tools/fndiff.py <shipped-addr> src/Engine/built/Final/server/<file>.obj <symbol> \
    --image=out/reference/server.dll
```

`build/engine.sh` (`Lithtech|server [verify]`, `Lithtech-one|server-one
<file.cpp> [symbol]`) rebuilds through `build/build.mk`'s engine pass, so the
object gets exactly the compiler and flags the project file gives it; the
object directory is the project's under `src/Engine/built/Final/`.

One thing about `fndiff.py` bites everybody once: its options need an
equals sign -- `--end=0x...`, `--image=out/reference/Lithtech.exe`,
`--csv=...`; written with a space it prints the usage text instead. Say which
image you mean every time.

`fndiff.py` reads the retail function's size from the image's function table
(`out/reference/<stem>-functions.csv`, written by `build/reference.sh`),
checks byte identity with relocations masked, shows the mnemonic diff, then
retries it under every renaming of `ebx`/`esi`/`edi` (separating
register-allocation noise from structural differences), and prints hints
matched against the codegen fingerprints catalogued in
[09-codegen-patterns](09-codegen-patterns.md). Its byte-level view also
catches what opcode-masked diffs cannot: two same-shaped instructions with
*swapped field offsets* look identical once immediates are masked -- that
exact blind spot hid a crossed pair of struct fields in NOLF1's
`CNetMgr::Update`.

The whole-target checks are the same tools run over every object:

```sh
build/engine.sh server verify          # exematch over every server.dll object
build/engine.sh Lithtech verify        # the same for Lithtech.exe
make progress                          # the scoreboard, held to the recorded baseline
```

`exematch.py`'s own totals are not the ones to quote: it scores each of our
functions independently, so two of ours with identical code both "match" the
same retail address. `tools/progress.py` gives every retail function to at
most one of ours; its numbers are the authoritative ones.

## Why relocations are masked

A `call` to another function, or a `mov` of a global's address, encodes an
address the linker fills in -- it differs between our build and theirs for
reasons that have nothing to do with correctness. So the diff tools blank the
4 bytes each relocation covers before comparing. Two functions that match
after masking are the same code; the linker will place the addresses.

**This is also a blind spot:** a `call` to the *wrong* function of the same
shape still masks to a match, and so does a load of the wrong float constant
(`tools/fpconst.py` checks those). `objdiff`/`exematch` cannot catch a
miswired call -- `tools/callcheck.py` can, and so can *linking* (an
unresolved external) or running the game.

In `Lithtech.exe` there is a third blind spot: SecuROM rewrote every
`call dword ptr [IAT]` (1,514 sites) to call its own dispatcher slot at
0x607ec0, so the retail bytes no longer say which import a site calls. The
masked comparison does not notice (the operand is an address), but reading
the code does: `progress/engine/Lithtech-iat-calls.csv` (from
`tools/demoimports.py` and the 1.3 multiplayer demo, whose IAT is at the
same addresses) names the real import of each site.

## Libraries

NOLF1's source release came with Monolith's prebuilt static libraries, which
kept their COFF symbols, so nolfsrc matched them object by object
(`objdiff.py`, `libextract.py`, `libfndiff.py`). NOLF2's release ships none:
`rezmgr`, `stdlith`/`lith`, `ltmem`, the UI library and the renderer
libraries are built from source here and scored inside the images that link
them, by address, like any other code. The library tools are still useful
on our own objects (two of our builds of one `.lib`, before and after a
change) and on the DirectX SDK's `.lib`s (`libscan.py`).

## Reading a diff

`objdiff` prints, per common function, `identical` or `differing (X vs Y
bytes)`. When sizes match but bytes differ, it is usually register allocation
or instruction scheduling -- a small source change (statement order, a temp
variable, a `>>` vs `/`) flips it. When sizes differ, you have a structural
mismatch (an extra branch, a wrong loop form, a missing or extra statement).

A useful trick for large functions -- normalise away register names and stack
offsets so only *structural* differences remain:

```sh
norm() { sed -E 's/%e[a-ds][ipx]/%R/g; s/0x[0-9a-f]+\(%esp[^)]*\)/SLOT/g'; }
diff <(python3 tools/dumpfn.py ours.obj Sym | norm) \
     <(python3 tools/dumpfn.py theirs.obj Sym | norm)
```

If the normalised diff is empty, all that is left is register and slot
assignment. If it is not, there is a real source difference to find.

Frame size is a free checksum along the way: add up the locals your source
declares and compare with the retail `sub esp,N`. A shortfall of twelve bytes
is almost always a vector operator's return temporary you wrote out by hand.

## When to stop at "near"

Leave a function `near` only when the normalised diff is empty or reduces to
one of the [known near classes](09-codegen-patterns.md#known-near-classes) --
tail merge, cross-jump host, shared-exit host, callee-saved rotation,
shrink-wrapping, FPU stack bookkeeping or term ordering. Note which class, in
a comment next to the function.

Before you do, two cheap checks that have both turned a "near" back into a
match in nolfsrc: confirm the file's flags (`/O1` against `/O2`, `/GX`,
`/Ob`; a per-file exception is a finding for `progress/COMPILERS.md`), and
confirm every call in the function pushes exactly what the retail call
pushes. NOLF1's third check, rebuilding under another compiler revision,
does not apply: every Monolith object in NOLF2's binaries is cl 8966. Anything else is a real difference -- keep
going, and add what you learn to
[09-codegen-patterns](09-codegen-patterns.md).

## Ghidra as a reading aid (optional)

For `Lithtech.exe`, decompile a copy with the encrypted pages and the
redirected import calls restored from the demo (`tools/demoimports.py`
`plain`, into `out/`); Ghidra on the retail file sees five pages of noise
and 1,514 calls to one SecuROM slot.


For a large or unfamiliar function, a decompiled C draft saves real reading
time. `tools/ghidra/decomp.sh` batch-decompiles a binary's app region:

```sh
tools/ghidra/decomp.sh out/reference/server.dll 0x10001000 0x1004d1d0 out/ghidra/server-app.c
```

It runs on the host, not in the build container: it needs
`ghidra.analyzeHeadless` on `PATH` (the Ghidra snap provides it) and about
2 GB of free RAM (the JVM is killed without it). Keep the output under `out/`
-- it is derived from the retail binary, and takes a few minutes to
regenerate.

**It is a reading aid, never the source.** The decompiler normalises away
precisely the things byte-matching depends on:

| the bytes distinguish | Ghidra prints both as |
|---|---|
| `while (*p)` vs `if (*p) do {…} while (*p)` | `while (*p)` |
| `HIWORD(w)==n` vs `(w>>16)==n` | `(w >> 16) == n` |
| `CString cs = x;` vs `CString cs; cs = x;` | `cs = x` |
| declaration order (which local takes a dead register) | any order |
| `?:` vs `if/else` returning two calls | a `?:` |

What it *is* good for: control flow at a glance, struct field offsets,
argument counts, and spotting an argument you misread -- in NOLF1's launcher
it correctly typed `PaintSplash`'s second parameter as `SelectPalette`'s `bForceBackground`
flag.

Three uses beyond a first draft, all of which turned a near match into an
exact one in NOLF1's launcher:

- **Its function-ID database names CRT calls.** It identified 0x40b3b0 as
  `_mbscpy`, which settled a "register tie-break" that was really a source
  difference: `strcpy` is an intrinsic and expands inline, `_mbscpy` is not
  and calls. `Save3DSoundDlg` had been 18 bytes over for that reason alone.
- **Its `goto LAB_...` marks a genuinely shared block.** Where the retail
  code reaches one body from two places, writing the bodies out twice and
  hoping the compiler merges them is not the same code -- VC6 merges one pair
  and not the next. `CustomizeDlgProc` was 56 bytes over until the gotos went
  in.
- **Its if/else nesting shows branch polarity**, which is source, not
  codegen: `if (!p) { a } else { b }` and `if (p) { b } else { a }` differ.
  That was worth 217 bytes in `InitGameDlg`, 32 in `CustomizeDlgProc`, and
  re-ordered every call site in `SetDefaultModes`.

**Seed the function starts.** Ghidra misses functions reached only through a
`push imm32` handed to the API -- DLGPROCs, WNDPROCs -- and silently folds
them into whatever precedes them. Pass a file of function starts as the fifth
argument (the first column of `out/reference/<stem>-functions.csv`) and it
creates a function at each, splitting any over-extended one. On NOLF1's
`NOLF.exe` that was the difference between having and not having the preview and display
dialog procs.

**It reads our objects too.** `analyzeHeadless` imports a COFF `.obj` and
keeps the COMDAT symbol names, so a near match can be checked semantically:
decompile the retail function and our own object, and if the C differs, the
diagnosis of "compiler-revision variance" is wrong and there is still a
source fix to find.

Read the draft, then derive the real source from `tools/exedump.py` as usual.
