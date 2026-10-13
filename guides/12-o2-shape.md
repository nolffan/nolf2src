# 12 · Fixing /O2 shape in already-correct source

Read this before working any `tools/o2gap.py` row. Everything here was learned
from measured builds in nolfsrc, on NOLF1's engine (whose `server.dll` was
also `/O1` and whose `lithtech.exe` was `/O2`); none of it is theory. The
function names, addresses and the "server/lithtech" counts below are NOLF1's.

## What the job is

NOLF2's `server.dll` is the exe's server, shared, kernel, net and world
objects compiled a second time (`docs/engine/anatomy.md`, section 4), so the
shared translation units under `src/Engine/runtime/` compile TWICE:

    /O1 = /Og /Os /Oy /Ob1      -> server.dll
    /O2 = /Og /Oi /Ot /Oy /Ob1  -> Lithtech.exe

(`/O1` for NOLF2's `server.dll` is inferred from its function alignment, and
`/Ob1` for both is NOLF1's; confirm both once files match.) The gap is real:
only 7.1% of the dll's instructions occur verbatim in the exe.

A function that is byte-identical in server.dll and not in Lithtech.exe is
built from source we have ALREADY PROVEN CORRECT. The semantics are right; only
the `/O2`-visible SHAPE is wrong. That is far cheaper than reconstructing from
raw bytes, and server.dll acts as a built-in regression check: an edit that
breaks `/O1` changed semantics rather than placement.

`tools/o2gap.py` lists these functions. Work them with both loops:

```sh
build/engine.sh server-one   <file.cpp> <symbol>
build/engine.sh Lithtech-one <file.cpp> <symbol>     # the same file, as the client
```

Two mechanisms produce the whole pool:

* **Both builds are `/Ob1`**, so only in-class, `inline`-marked, or TEMPLATE
  functions are ever expansion candidates. But `/Os` DECLINES expansions that
  `/Ot` ACCEPTS, on size. One source, two outcomes.
* **`/O1` tail-merges duplicated epilogues** that `/O2` preserves, so an early
  `return X` and a nested positive guard with a trailing `return X` give the
  same `/O1` bytes and different `/O2` bytes.

## The rules, in the order they pay

**1. Positive guards, and they NEST.** If the shipped `/O2` conditional jump
goes FORWARD to a block sitting past every other return, that block is a
TRAILING STATEMENT and the guard above it is positive:

    if (!p) RETURN_ERROR(...);      ->   if (p) { ...body... }
    ...body...                           RETURN_ERROR(...);

The shared answer need not be one instruction; a 25-instruction
`RETURN_ERROR` expansion counts. After fixing the outer guard, look inside the
body again; one function needed the move at two levels before it closed.

**2. One instruction differing only in an IMMEDIATE is a struct offset or
size.** Examples: `add $0x11a0` vs `$0x119c` (a missing dword), `push $0x2c4`
vs `$0x20c` (`sizeof` 184 bytes short, read straight off `operator new`),
`mov 0x1534` vs `0x1530` (`LTList` is 0x10 bytes, not 0x14). **Check this
FIRST on any size-exact near.** `tools/layoutscan.py` and `tools/nearpos.py`
find this class mechanically.

**3. Inline visibility, in both directions.** A helper the shipped `/O2`
EXPANDS and we CALL wants `inline` (and hoisting, see rule 4). A helper the
shipped `/O2` CALLS and we EXPAND wants its body moved OUT. The one construct
`/Ob1` NEVER expands is a **non-template function declared out-of-class**; that
shape, in a hand-written stand-in class, has been the real cause several
times.

**4. VC6's inliner is FORWARD-ONLY.** A function defined BELOW its caller is
not a candidate at any `/Ob` setting. Hoisting AND `inline` are both required;
hoisting alone does nothing.

## The four ways this bites back (measured on NOLF1)

**A. `inline` (or `static`) COSTS that function's own match.** When every
caller expands it, the COMDAT stops being emitted, and if one of our objects
was matching that standalone body in server.dll, that match is gone. Measured:

    CWorldTable::SetSizeInit2          server -2, lithtech +0   reverted
    ModelWalker::ModelWalker           server  0, lithtech +1   kept
    CConnList::Alloc/FreeItems 24/32b  server -2, lithtech -1   reverted
    LThreadMessageBank::Allocate 28b   server -1, lithtech -1   reverted
    static sav_WriteVector             server -1, lithtech +0   reverted
    inline sm_AllocateObject           server -1, lithtech +0   reverted

**Every `inline` is a bet on BOTH images. Apply one at a time and rebuild
both.** And never take an enabling fix on its own: measure it WITH the
dependent function in place, or you pay the cost and collect nothing.

**B. Below about 32 bytes, do not mark anything.** `/Os` DOES expand at 24, 28
and 32 bytes, so the spelling cannot be what distinguishes the images, and
marking it is ACTIVELY NEGATIVE: it perturbs the caller's allocation for
nothing. The 28-byte case above cost a function in each image.

**C. The decision is CALLER-CONTEXT-DEPENDENT.** VC6 `/O2 /Ob1` decides per
CALL SITE, not per function. The same helper, same header, same image, is
expanded at one site and called at another: `LTMatrix::Init` (114 bytes)
expanded in a 196-byte caller and called in an 1182-byte one;
`Mat_InverseTransformation` expanded in `wm_BuildTransforms` (which matches)
and called in `sub_10017517`. Depth, callee size and source order each fail to
predict at least one. **So a HEADER keyword cannot separate two call sites**,
which is why `.cpp`-level work has paid many times better than header-level
work. Before betting on suppressing an over-inline, grep the image for calls
to the helper's address: if any currently matching function expands it,
suppression is a guaranteed loss.

**D. Templates are already candidates.** VC6 at `/Ob1` treats function
TEMPLATES as inline candidates with or without the keyword. Adding `inline` to
a template is a no-op, proved by a 50-byte `GenRemoveAll` instantiation in our
own object, with no call relocation, that matches the shipped image.

## Measuring

**`exematch` counts SYMBOLS; `progress.py` counts ADDRESSES.** A per-object
`matched N` drop is not a regression until the address count says so; one
edit read as -34 and was actually -1. `make progress` is the final word, and
fails if anything recorded as identical stopped matching.

A symbol that STOPS being emitted (because every caller now expands it) makes
`o2gap` shrink by more than the score rises. That is correct, not a loss:
those functions have no address in the shipped client at all.

**Do not run a full build while someone else is editing the same tree.**
Build per file as each edit lands, or give each worker its own worktree
(`tools/agentwt.sh`).

## The census proves the CALLEE, not the CALLERS

A census showing server.dll calls the helper out of line at every site proves
**the helper's own standalone body survives**. It says nothing about whether
the CALLERS' bytes change.

`sm_FreeObject` passed the census cleanly and looked a safe bet. Making it
`inline` still moved `si_CreateObjectProps` and three others at `/O1`, because
the expansion changed those functions, not the helper. Net: server -4,
lithtech +1.

**So: bisect per edit, and bisect against the CURRENT tree.** Edits interact:
reverting one changes what another is worth in the same file. One batch
measured whole was lithtech +8 / server -6; bisected, it was +6 / -2, keeping
seven of nine edits. And intuition about which edit is risky is unreliable in
both directions: the edit that looked riskiest was free, and the one that
looked safest cost the most.

## Proving an edit is `/O1`-safe before making it: THE CENSUS IS NOT A PROOF

The argument runs: **scan every `e8` in both images for calls to the helper's
address.** If server.dll calls it out of line at EVERY site, `/Os` declined it
at that size with the true source, so making it `inline` cannot change server
codegen. That closed three helpers at once in `lthread.h` with no regression.

**It has also failed, and you must treat it as a hypothesis, not a proof.**

* `sm_CanDeactivate`: the census said both server sites call out of line.
  After the move, NO object emitted the symbol at all: `/Os` expanded it.
  Server happened not to move, so it cost nothing, but the prediction was
  wrong.
* `obj_MaybeRetransformWorldModel` + `CWMMoveSetup::Setup`: the census said
  all thirteen and all three server sites call out of line. Marking them
  `inline` and hoisting gained lithtech 0x00450fc0 and took
  `wm_SetObjectDims` from 26 bytes short to 2 over, and **lost server.dll
  THREE addresses**. Net -2. Reverted.

**Why it fails.** The census tells you what the SHIPPED compiler did with the
TRUE source. It does not tell you what OUR compiler will do with OUR source,
and the two differ whenever our body is not byte-for-byte the original: a
different body has a different inline cost, and `/Os`'s threshold is a size
test. The argument is sound about the original and silent about ours.

**So: build both images and measure before keeping any `inline`/hoist edit.**
The run takes minutes; a silent `-3` on the other image is not visible any
other way. Keep the census for CHOOSING which helper to try, never for
skipping the measurement.

## The best evidence that a body belonged in-class is a FOLD, not a size

A size difference between the two images tells you an expansion happened. It
does not tell you the expansion is the one the shipped source asked for, and
chasing sizes alone produces 4-byte near-misses.

The decisive evidence is a **fold**: an optimisation that becomes available
only once the callee's body is visible at the call site, and which therefore
could not appear at any optimisation level with an out-of-line definition.

The worked case is `CMsgSpaceView::GetSpaceLeft`, whose body floors a
subtraction at zero, called by a site that then tests the result against
`0x16`. Moved in-class, lithtech's `/Ot` expands it and 0x00463055 reads:

    sub eax,0x7
    js  0x463070        <- straight into the guarded block
    cmp eax,0x16
    jg  0x463091

The callee's `if (nLeft < 0) nLeft = 0;` has been folded INTO the caller's
comparison: a negative count is certainly `<= 0x16`, so the clamp degenerates
into a branch to the same place, and the assignment vanishes. An out-of-line
callee must materialise the zero. So the fold proves the in-class spelling by
itself, before any byte is counted.

When you are deciding whether a helper belonged in a header, **look for a
constant that disappeared, a branch that merged, or a clamp that turned into a
jump**. Those are proof. A size that moved in the right direction is a hint.

## Two returns of the same constant are ONE BLOCK

This is the first thing to check on a near that is a handful of bytes over
with the right instruction count.

Written as two early returns:

    p = Find(...);  if (!p) return FALSE;
    q = p->First(); if (!q) return FALSE;
    return q->Get(...);

VC6 emits `jne` + `ret` at EACH guard. The shipped code almost always has `je`
from both guards onto ONE shared `xor %eax,%eax ; ret $N` tail. Nesting puts
them there:

    p = Find(...);
    if (p) { q = p->First(); if (q) return q->Get(...); }
    return FALSE;

The same rule covers a merge the optimiser can prove rather than see. In
`w_FindPolyAtPoint` an early `return LTNULL` and a later `if (nIndex ==
0xffff) return LTNULL` became one block, because nIndex is provably still
0xffff on the early path, so the shipped code jumps straight PAST the
comparison. Seven bytes, one block; guarding the traversal instead of
returning early closed it.

**Symptom to recognise:** a diff whose only block is `S jne X` against
`O je X ; xor %eax,%eax ; jmp X`, or an instruction count 2-3 high with the
excess all in epilogues.

### And it runs both ways: read the diff, do not assume

The rule above is not "always nest the guards". `/O1` TAIL-MERGES duplicated
epilogues and **`/O2` PRESERVES them**, so in the exe an early return in
the source stays duplicated. `cis_CreateSurfaceFromDIB` was three bytes SHORT
with the mirror-image diff (shipped `jne ; pop %edi ; pop %esi ; ret` against
our `je` onto a shared exit), and writing it as a genuine early return closed
it:

    if (!pSurface)            // shipped duplicates the epilogue here
        return LTNULL;
    cis_DrawDIBToSurface(...);
    return pSurface;

So the question is never "should exits merge" in the abstract. **Look at which
side has the extra `ret`.** Shipped sharing a tail where we duplicate means
nest the guards; shipped duplicating where we share means write the early
return. Both cost a handful of bytes and both are one edit.

## Hoist a subexpression to fix evaluation order

A near that is SIZE-EXACT with the same instruction count and a register
rotation through one call is usually operand evaluation order, not allocation.
`WantsTree` was 212/212 bytes and 72/72 instructions, with the shipped code
computing the ARGUMENT before loading the object where we did the reverse;
assigning the argument to a local first reordered it and the function closed.
The same lever fixed an allocator that the shipped code kept in `%ecx` and we
shuffled through `%eax` and `%ebx`.

## A counting `for` and a countdown `do/while` are different code

The shipped code tests the trip count ONCE and closes the loop with `dec`; a
`for (i = 0; i < n; i++)` counts up and closes with a compare plus `jbe`.
Across two arms of one function that was six instructions and eight bytes.

    if (nCount)                       // one entry test
    {
        do { ... } while (--nCount);  // closes with `dec`
    }

Recognise it by a `dec` closing the shipped loop with no separate compare, and
by the trip count being tested once above the loop rather than at the top of
each iteration.

## Fingerprints worth knowing

* An unmatched destructor short by exactly ONE vptr store means a member class
  has a destructor you have not written. The constant tells you which class;
  put it on the MOST-DERIVED one, because only that table is stored and a
  base-level destructor's store loses dead-store elimination.
* A `ptr` row that is unaligned and has no caller may be an ASCII ACCIDENT
  (NOLF1's addresses below; the shape is any exe's at base 0x400000).
  Not just PE import names (`"GetStartupInfoA\0"` contains 0x00416f66,
  `"LoadCursorA\0"` contains 0x0041726f): ordinary `.data` literals do it too
  (`"SYNTHSAMPLERATE\0"` -> 0x00455441, `"WSAEMSGSIZE\0"` -> 0x00455a49). The
  window is the last three characters plus the NUL. Read the address back as
  text before disassembling it.
* Enumeration SIZES are unreliable above about 1 KB: one row said 2,593 bytes
  against a real 4,613. Verify extents with `tools/extentcheck.py` and by
  sweeping `e8`/`e9` displacements into the body.
* `exematch` MASKS every relocated byte, so changing a call's callee SYMBOL
  cannot affect matching. It CAN break the whole link (`build/engine.sh
  Lithtech`): a renamed callee needs its definition (nolfsrc used alias
  objects, `tools/mkaliasobj.py`, as a stopgap), and a second definition is a
  duplicate-COMDAT error. Check the link, not just the score.
* A `+` suffix on an exematch address means those bytes occur more than once.
  When two functions differ ONLY inside a masked relocation, exematch will name
  the wrong one: `DistSqr` was reported matching where the shipped callee was
  `Dist`, the whole difference being one `fsqrt`.
* `gap` and `ptr` rows (the `source` column of
  `out/reference/<image>-functions.csv`) are the unreliable ones. A cluster of
  clean `call` rows had all eight extents sound.
