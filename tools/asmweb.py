#!/usr/bin/env python3
"""Render a shipped binary's disassembly as one scrollable, annotated page.

The reconstruction knows two things the raw bytes do not: which byte ranges
are functions, and what each reconstructed function is called. This puts them
together -- 80,000 instructions of server.dll with every function we have
recovered labelled by its demangled signature, its status, and the translation
unit it lives in, so the machine code can be read the way the project actually
thinks about it.

WHERE EACH FACT COMES FROM, because the point is that the labels are earned:

  * the disassembly is objdump over the image's own bytes, annotated the way
    tools/exedump.py annotates it (imports by name, C strings inline, other
    sections as section+offset);
  * function extents come from the same enumeration the scoreboard counts,
    tools/progress.py's `rows_for_image`, so this page and the scoreboard
    cannot disagree about what a function is;
  * `identical` means exematch placed one of our COMDATs at that exact
    address -- the same oracle the scoreboard uses, not a guess;
  * `near` means progress.py PAIRED one of our unmatched functions to that
    address by length and byte agreement. That is a heuristic, and it is
    labelled as one on the page;
  * signatures are tools/msvcdemangle.py over the mangled COMDAT name, which
    refuses anything it cannot parse safely rather than inventing a signature.

Call and jump targets that land on a known function are annotated with that
function's name, which is what makes the page readable as a call graph rather
than as a wall of hex.

The page virtualises its own scrolling: 80,000 rows of DOM would crawl, so the
instructions ship as one newline-separated blob and only the visible slice is
built. That keeps it responsive and the file near 4MB.

Usage:
  asmweb.py <image> <objdir> [--label=server.dll] [--out=FILE] [--stats]

  asmweb.py out/reference/server.dll src/engine/server/Release --out=out/asm.html
"""
import glob
import html
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import progress                                            # noqa: E402
from exedump import Pe                                     # noqa: E402
from msvcdemangle import demangle                           # noqa: E402

REPO = progress.REPO


def disassemble(pe, lo, hi):
    """[(addr, hexbytes, text)] over [lo, hi), annotated like exedump.py."""
    tva, tvs, trp = pe.secs[".text"]
    imp = pe.imports()
    blob = pe.d[trp + (lo - tva):trp + (hi - tva)]
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(blob)
        tmp = f.name
    try:
        out = subprocess.run(
            ["objdump", "--insn-width=16", "-D", "-b", "binary", "-m", "i386",
             "--adjust-vma=0x%x" % lo, tmp],
            capture_output=True, text=True).stdout
    finally:
        os.unlink(tmp)

    memref = re.compile(r"0x([0-9a-f]{6,8})")
    row = re.compile(r"^\s*([0-9a-f]+):\t([0-9a-f ]+?)\s*\t(.*)$")
    rows = []
    for line in out.splitlines():
        m = row.match(line)
        if not m:
            continue
        addr, raw, text = int(m.group(1), 16), m.group(2), m.group(3)
        text = re.sub(r"\s+", " ", text).strip()
        note = []
        for r in memref.finditer(text):
            va = int(r.group(1), 16)
            if va in imp:
                note.append(imp[va])
                continue
            s = pe.cstr(va)
            if s is not None:
                note.append('"%s"' % s[:60])
                continue
            sec, off = pe.sec_of(va)
            if sec and sec != ".text":
                note.append("%s+0x%x" % (sec, off))
        rows.append((addr, raw.replace(" ", ""), text, note))
    return rows


def classify(label, image, objdir):
    """(blocks, stats). One block per enumerated function, in address order."""
    objs = sorted(os.path.relpath(p, REPO)
                  for p in glob.glob(os.path.join(REPO, objdir, "*.obj")))
    if not objs:
        sys.exit("no objects under " + objdir)
    rows = progress.rows_for_image(label, image, objs)

    near = {a: sym for (lb, a, _sz, sym, _our) in progress.NEAR_PAIRS
            if lb == label}
    placed = {a: sym for (lb, a), sym in progress.PLACED_SYMS.items()
              if lb == label}

    blocks = []
    for (_lb, name, size, status) in rows:
        if not name.startswith("sub_"):
            continue                    # a symbol-keyed near, no address
        addr = int(name[4:], 16)
        sym = placed.get(addr) or near.get(addr) or ""
        tu, _, mangled = sym.partition(":")
        blocks.append({
            "addr": addr, "size": size, "status": status,
            "tu": tu, "sym": mangled,
            "sig": (demangle(mangled) if mangled else "") or "",
        })
    blocks.sort(key=lambda b: b["addr"])
    return blocks


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict((a.split("=", 1) + [True])[:2] for a in sys.argv[1:]
                if a.startswith("--"))
    if len(args) != 2:
        sys.exit(__doc__)
    image, objdir = args
    label = opts.get("--label", os.path.basename(image))
    out = opts.get("--out", "out/asmweb.html")

    pe = Pe(os.path.join(REPO, image))
    tva, tvs, _ = pe.secs[".text"]
    lo, hi = progress.APP_REGION.get(label, (tva, tva + tvs))

    blocks = [b for b in classify(label, image, objdir) if lo <= b["addr"] < hi]
    insns = [r for r in disassemble(pe, lo, hi) if lo <= r[0] < hi]

    at = lo
    for (addr, raw, _t, _n) in insns:
        if addr != at:
            sys.exit("disassembly is not contiguous at %#x (accumulated %#x); "
                     "the page derives addresses by accumulating byte lengths "
                     "and would be wrong" % (addr, at))
        at += len(raw) // 2
    if at != hi:
        sys.exit("disassembly ends at %#x, region ends at %#x" % (at, hi))
    by_addr = {b["addr"]: b for b in blocks}
    names = {b["addr"]: (b["sig"].split("(")[0].split()[-1] if b["sig"]
                         else b["sym"] or "sub_%x" % b["addr"])
             for b in blocks}

    # Every instruction must belong to exactly one block, or the page would
    # silently drop code. Enumerated extents run start-to-next-start and so
    # normally tile the region; anything left over becomes an explicit
    # "unenumerated" block rather than disappearing.
    bounds = sorted(by_addr)
    owner, gaps, bi = [], [], -1
    for (addr, _raw, _t, _n) in insns:
        while bi + 1 < len(bounds) and bounds[bi + 1] <= addr:
            bi += 1
        if bi < 0:
            gaps.append(addr)
            owner.append(None)
        else:
            owner.append(bounds[bi])
    if gaps:
        lead = {"addr": gaps[0], "size": 0, "status": "gap", "tu": "",
                "sym": "", "sig": ""}
        blocks.insert(0, lead)
        owner = [g if g is not None else gaps[0] for g in owner]

    # ---- compact payload -------------------------------------------------
    # One newline-separated blob for the instruction stream and one for the
    # annotations; the address of a row is derivable from the block it sits in
    # plus the byte lengths before it, so it is not stored.
    body = "\n".join("%s\t%s" % (raw, text) for (_a, raw, text, _n) in insns)
    notes = "\n".join(" ".join(n) for (_a, _r, _t, n) in insns)

    counts = {}
    first = {}
    for i, a in enumerate(owner):
        counts[a] = counts.get(a, 0) + 1
        first.setdefault(a, i)

    # A block whose start is not an instruction boundary is a SPURIOUS
    # enumeration start -- the disassembler walked straight through it, so it
    # sits inside the previous function rather than beginning a new one. That
    # is a real defect in the enumeration, and flagging it here
    # turns this page into a way of finding more of them rather than a page
    # that quietly mislabels a few rows.
    boundary = {a for (a, _r, _t, _n) in insns}

    fns = []
    for b in blocks:
        a = b["addr"]
        fns.append({
            "a": a, "n": b["size"], "s": b["status"], "tu": b["tu"],
            "sym": b["sym"], "sig": b["sig"],
            "i0": first.get(a, 0), "ni": counts.get(a, 0),
            "off": 0 if a in boundary else 1,
        })
    fns = [f for f in fns if f["ni"] or f["n"]]

    if "--stats" in opts:
        import collections
        c = collections.Counter(f["s"] for f in fns)
        print("region %#x..%#x  %d instructions  %d blocks" % (
            lo, hi, len(insns), len(fns)))
        print("  " + "  ".join("%s=%d" % kv for kv in sorted(c.items())))
        print("  body %.1f KB   notes %.1f KB   named %d   signatures %d" % (
            len(body) / 1024, len(notes) / 1024,
            sum(1 for f in fns if f["sym"]),
            sum(1 for f in fns if f["sig"])))
        return

    import json
    page = TEMPLATE.replace("__LABEL__", html.escape(label))
    page = page.replace("__LO__", "%#x" % lo).replace("__HI__", "%#x" % hi)
    page = page.replace("__NINSN__", str(len(insns)))
    page = page.replace("__FNS__", json.dumps(fns, separators=(",", ":")))
    page = page.replace("__BODY__", json.dumps(body))
    page = page.replace("__NOTES__", json.dumps(notes))
    page = page.replace("__NAMES__", json.dumps(
        {("%x" % k): v for k, v in names.items()}, separators=(",", ":")))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write(page)
    print("wrote %s (%.1f MB)" % (out, os.path.getsize(out) / 1048576))


TEMPLATE = r"""<title>__LABEL__ Disassembly</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
  :root{
    --bg:#f3f1ea; --panel:#fbfaf6; --raised:#ffffff; --line:#e2ded2; --line2:#eceae0;
    --ink:#1b2028; --muted:#6d7688; --faint:#9aa1b0;
    --brand:#2f6fa8; --brand-soft:#dbe8f2;
    --ok:#2f9268; --near:#b7842a; --small:#6f7f96; --todo:#b0563f;
    --ok-bg:#e2efe8; --near-bg:#f2e9d5; --small-bg:#e6eaef; --todo-bg:#f1ddd6;
    --hex:#8d94a3; --imm:#2f6fa8; --str:#2f9268; --reg:#1b2028;
    --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
    --sans:'IBM Plex Sans',-apple-system,BlinkMacSystemFont,sans-serif;
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --bg:#13161c; --panel:#191d25; --raised:#20252f; --line:#2b313d; --line2:#242a34;
      --ink:#e8eaef; --muted:#98a1b2; --faint:#69707e;
      --brand:#59a3dc; --brand-soft:#1f3346;
      --ok:#55bb8a; --near:#d7a648; --small:#8496ad; --todo:#cf6f57;
      --ok-bg:#183026; --near-bg:#322a17; --small-bg:#222a34; --todo-bg:#331f19;
      --hex:#5f6775; --imm:#79b6e8; --str:#63c096; --reg:#e8eaef;
    }
  }
  :root[data-theme="dark"]{
      --bg:#13161c; --panel:#191d25; --raised:#20252f; --line:#2b313d; --line2:#242a34;
      --ink:#e8eaef; --muted:#98a1b2; --faint:#69707e;
      --brand:#59a3dc; --brand-soft:#1f3346;
      --ok:#55bb8a; --near:#d7a648; --small:#8496ad; --todo:#cf6f57;
      --ok-bg:#183026; --near-bg:#322a17; --small-bg:#222a34; --todo-bg:#331f19;
      --hex:#5f6775; --imm:#79b6e8; --str:#63c096; --reg:#e8eaef;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
       font-size:13px;overflow:hidden}
  a{color:var(--brand)}

  header{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;
          padding:12px 18px 11px;border-bottom:1px solid var(--line);
          background:var(--panel)}
  header h1{margin:0;font-size:15px;font-weight:700;letter-spacing:-.01em}
  header h1 code{font-family:var(--mono);font-weight:600;color:var(--brand)}
  .region{font-family:var(--mono);font-size:11.5px;color:var(--muted)}
  .legend{display:flex;gap:14px;margin-left:auto;flex-wrap:wrap}
  .lg{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--muted);
      white-space:nowrap}
  .sw{width:9px;height:9px;border-radius:2px;flex:none}
  .lg b{color:var(--ink);font-variant-numeric:tabular-nums}

  main{display:flex;height:calc(100% - 46px);min-height:0}
  aside{width:330px;flex:none;border-right:1px solid var(--line);
        background:var(--panel);display:flex;flex-direction:column;min-height:0}
  .find{padding:9px 10px;border-bottom:1px solid var(--line2)}
  .find input{width:100%;padding:6px 8px;border:1px solid var(--line);
    border-radius:5px;background:var(--raised);color:var(--ink);
    font-family:var(--mono);font-size:12px}
  .find input:focus{outline:2px solid var(--brand-soft);border-color:var(--brand)}
  .idx{overflow-y:auto;flex:1;min-height:0;padding:4px 0 40px}
  .idx .row{display:flex;gap:8px;align-items:baseline;padding:3px 10px;
    cursor:pointer;border-left:3px solid transparent}
  .idx .row:hover{background:var(--raised)}
  .idx .row.on{background:var(--brand-soft);border-left-color:var(--brand)}
  .idx .ad{font-family:var(--mono);font-size:11px;color:var(--faint);flex:none}
  .idx .nm{font-family:var(--mono);font-size:11.5px;overflow:hidden;
    text-overflow:ellipsis;white-space:nowrap}
  .idx .row.s-todo .nm{color:var(--muted)}
  .none{padding:14px 12px;color:var(--muted);font-size:12px}

  .pane{flex:1;min-width:0;display:flex;flex-direction:column;min-height:0}
  .now{padding:8px 16px;border-bottom:1px solid var(--line);background:var(--raised);
       display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;min-height:34px}
  .now .nname{font-family:var(--mono);font-size:12.5px;font-weight:600}
  .now .nsig{font-family:var(--mono);font-size:11.5px;color:var(--muted);
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:120px}
  .now .ntu{font-family:var(--mono);font-size:11px;color:var(--faint)}
  .scroll{overflow-y:auto;flex:1;min-height:0;position:relative;
          font-family:var(--mono);font-size:12px;line-height:18px}
  .virt{position:relative;width:100%}
  .slice{position:absolute;left:0;right:0;top:0;will-change:transform}
  .ins{display:flex;gap:0;white-space:pre;height:18px;padding:0 16px}
  .ins:hover{background:var(--raised)}
  .ins .a{width:78px;flex:none;color:var(--faint)}
  .ins .b{width:200px;flex:none;color:var(--hex);overflow:hidden}
  .ins .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
  .ins .t i{font-style:normal;color:var(--imm)}
  .ins .t s{text-decoration:none;color:var(--str)}
  .ins .t u{text-decoration:none;color:var(--brand);cursor:pointer;
    border-bottom:1px dotted var(--brand)}
  .fh{padding:14px 16px 6px;border-top:1px solid var(--line2);margin:0}
  .fh .l1{display:flex;gap:10px;align-items:baseline;flex-wrap:nowrap;
    overflow:hidden;white-space:nowrap}
  .fh .fa{font-family:var(--mono);font-size:11px;color:var(--faint)}
  .fh .fn{font-family:var(--mono);font-size:13px;font-weight:600}
  .fh .fsz{font-size:11px;color:var(--faint);font-variant-numeric:tabular-nums}
  .fh .ftu{font-family:var(--mono);font-size:11px;color:var(--faint);
    margin-left:auto;overflow:hidden;text-overflow:ellipsis}
  .fh .sig{font-family:var(--mono);font-size:11.5px;color:var(--muted);
    margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .pill{font-family:var(--sans);font-size:10px;font-weight:600;padding:1px 6px;
    border-radius:9px;letter-spacing:.02em;text-transform:uppercase}
  .p-identical{background:var(--ok-bg);color:var(--ok)}
  .p-near{background:var(--near-bg);color:var(--near)}
  .p-small{background:var(--small-bg);color:var(--small)}
  .p-todo{background:var(--todo-bg);color:var(--todo)}
  .p-gap{background:var(--small-bg);color:var(--small)}
  .p-off{background:var(--todo-bg);color:var(--todo);cursor:help}
  .note{font-family:var(--sans);font-size:11px;color:var(--faint);
    padding:10px 16px 26px;max-width:76ch;line-height:1.5}
  @media (max-width:820px){ aside{display:none} }
</style>

<header>
  <h1>Annotated disassembly &mdash; <code>__LABEL__</code></h1>
  <span class="region">__LO__ &ndash; __HI__ &middot; __NINSN__ instructions</span>
  <div class="legend" id="legend"></div>
</header>

<main>
  <aside>
    <div class="find"><input id="q" placeholder="filter by name, signature or address" spellcheck="false"></div>
    <div class="idx" id="idx"></div>
  </aside>
  <div class="pane">
    <div class="now" id="now"></div>
    <div class="scroll" id="scroll">
      <div class="virt" id="virt"><div class="slice" id="slice"></div></div>
    </div>
    <div class="note" id="foot"></div>
  </div>
</main>

<script>
const FNS   = __FNS__;
const BODY  = __BODY__;
const NOTES = __NOTES__;
const NAMES = __NAMES__;
const NINSN = __NINSN__;
const LO    = parseInt("__LO__", 16);

const INS = BODY.split("\n");
const ANN = NOTES.split("\n");

// Absolute address per instruction. The region is contiguous, so accumulating
// each instruction's own byte length from the region base gives every address
// without storing 80,000 of them in the page.
const ADDR = new Int32Array(NINSN);
{
  let a = LO;
  for (let i = 0; i < NINSN; i++) {
    ADDR[i] = a;
    const t = INS[i].indexOf("\t");
    a += (t < 0 ? 0 : t) >> 1;
  }
}

// Headers and instruction rows are different heights, so the scroll maps
// through a running PIXEL offset per block rather than a uniform row height.
// Every emitted box must then be exactly RH or HH tall, margins included.
const RH = 18, HH = 62;
const PY = new Float64Array(FNS.length + 1);
for (let i = 0; i < FNS.length; i++) {
  PY[i + 1] = PY[i] + HH + FNS[i].ni * RH;
}
const TOTPX = PY[FNS.length];

const scroll = document.getElementById("scroll");
const virt   = document.getElementById("virt");
const slice  = document.getElementById("slice");
const nowEl  = document.getElementById("now");
virt.style.height = TOTPX + "px";

function blockAtPx(y) {
  let lo = 0, hi = FNS.length - 1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (PY[m] <= y) lo = m; else hi = m - 1; }
  return lo;
}
const esc = s => s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

// Colour the operands, and turn a call/jump target that lands on a known
// function into a link. Done at render time, for the visible rows only.
function paint(text, note) {
  let out = esc(text).replace(/0x[0-9a-f]+/g, m => {
    const key = m.slice(2);
    if (NAMES[key] !== undefined) return '<u data-a="' + key + '">' + m + "</u>";
    return "<i>" + m + "</i>";
  });
  if (note) out += '   <s>; ' + esc(note) + "</s>";
  return out;
}

function fname(f) {
  if (f.sig) { const h = f.sig.split("("); return h[0].split(" ").pop(); }
  return f.sym || ("sub_" + f.a.toString(16));
}

function headerHTML(i) {
  const f = FNS[i];
  const nm = fname(f);
  const full = f.sig || f.sym || "";
  const sig = full ? '<div class="sig" title="' + esc(full) + '">'
                     + esc(full) + "</div>" : "";
  return '<div class="fh" style="height:' + HH + 'px;overflow:hidden">'
       + '<div class="l1"><span class="fa">0x' + f.a.toString(16) + "</span>"
       + '<span class="fn">' + esc(nm) + "</span>"
       + '<span class="pill p-' + f.s + '">' + f.s + "</span>"
       + (f.n ? '<span class="fsz">' + f.n + " b</span>" : "")
       + (f.off ? '<span class="pill p-off" title="the disassembler decodes '
            + 'straight through this address, so this start is inside the '
            + 'previous function and not the beginning of a new one">'
            + "not an instruction boundary</span>" : "")
       + (f.tu ? '<span class="ftu">' + esc(f.tu) + "</span>" : "")
       + "</div>" + sig + "</div>";
}

let curBlock = -1;
function render() {
  const top = scroll.scrollTop, view = scroll.clientHeight;
  let i = blockAtPx(top), y = PY[i], html = "", startY = y;
  while (i < FNS.length && y < top + view + 400) {
    html += headerHTML(i);
    y += HH;
    const f = FNS[i];
    for (let k = 0; k < f.ni; k++) {
      if (y + RH >= top - 200 && y <= top + view + 400) {
        const j = f.i0 + k, tab = INS[j].indexOf("\t");
        html += '<div class="ins"><span class="a">'
             + ADDR[j].toString(16) + '</span><span class="b" title="'
             + INS[j].slice(0, tab) + '">'
             + INS[j].slice(0, tab) + '</span><span class="t">'
             + paint(INS[j].slice(tab + 1), ANN[j]) + "</span></div>";
      } else {
        html += '<div class="ins" style="height:' + RH + 'px"></div>';
      }
      y += RH;
    }
    i++;
  }
  slice.style.transform = "translateY(" + startY + "px)";
  slice.innerHTML = html;

  const b = blockAtPx(top + 1);
  if (b !== curBlock) { curBlock = b; showNow(b); markIdx(b); }
}

function showNow(i) {
  const f = FNS[i];
  nowEl.innerHTML = '<span class="nname">' + esc(fname(f)) + "</span>"
    + '<span class="pill p-' + f.s + '">' + f.s + "</span>"
    + '<span class="nsig" title="' + esc(f.sig || f.sym || "") + '">'
      + esc(f.sig || f.sym || "") + "</span>"
    + (f.tu ? '<span class="ntu">' + esc(f.tu) + "</span>" : "");
}

// ---- index -------------------------------------------------------------
const idx = document.getElementById("idx");
function buildIdx(filter) {
  const f = (filter || "").toLowerCase();
  let html = "";
  for (let i = 0; i < FNS.length; i++) {
    const fn = FNS[i];
    if (f) {
      const hay = (fname(fn) + " " + (fn.sig || "") + " " + (fn.sym || "")
                   + " " + fn.a.toString(16) + " " + fn.tu).toLowerCase();
      if (hay.indexOf(f) < 0) continue;
    }
    html += '<div class="row s-' + fn.s + '" data-i="' + i + '">'
         + '<span class="sw" style="background:var(--' + (fn.s === "identical" ? "ok"
            : fn.s === "near" ? "near" : fn.s === "small" ? "small" : "todo") + ')"></span>'
         + '<span class="ad">' + fn.a.toString(16) + "</span>"
         + '<span class="nm">' + esc(fname(fn)) + "</span></div>";
  }
  idx.innerHTML = html || '<div class="none">nothing matches</div>';
}
function markIdx(i) {
  const prev = idx.querySelector(".row.on");
  if (prev) prev.classList.remove("on");
  const el = idx.querySelector('.row[data-i="' + i + '"]');
  if (!el) return;
  el.classList.add("on");
  const y = el.offsetTop - idx.clientHeight / 2;
  if (el.offsetTop < idx.scrollTop
      || el.offsetTop > idx.scrollTop + idx.clientHeight - 20) idx.scrollTop = y;
}
function jumpTo(i) { scroll.scrollTop = PY[i] + 1; render(); }
function gotoAddr(a) {
  let lo = 0, hi = FNS.length - 1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (FNS[m].a <= a) lo = m; else hi = m - 1; }
  jumpTo(lo);
}

idx.addEventListener("click", e => {
  const r = e.target.closest(".row"); if (r) jumpTo(+r.dataset.i);
});
slice.addEventListener("click", e => {
  const u = e.target.closest("u[data-a]");
  if (u) { const a = parseInt(u.dataset.a, 16);
           location.hash = "0x" + a.toString(16); gotoAddr(a); }
});
document.getElementById("q").addEventListener("input", e => buildIdx(e.target.value));
scroll.addEventListener("scroll", render, { passive: true });
addEventListener("resize", render);

// ---- legend and footnote -----------------------------------------------
const OFFN = FNS.filter(f => f.off).length;
{
  const c = {}; for (const f of FNS) c[f.s] = (c[f.s] || 0) + 1;
  const order = [["identical", "ok"], ["near", "near"], ["small", "small"], ["todo", "todo"]];
  document.getElementById("legend").innerHTML = order
    .filter(([k]) => c[k]).map(([k, v]) =>
      '<span class="lg"><span class="sw" style="background:var(--' + v + ')"></span>'
      + "<b>" + c[k] + "</b> " + k + "</span>").join("");
  document.getElementById("foot").innerHTML =
    "<b>identical</b> means exematch placed one of our compiled COMDATs at that exact "
    + "address &mdash; the same oracle the scoreboard counts, not a guess. "
    + "<b>near</b> means a function we wrote was <i>paired</i> to that address by length "
    + "and byte agreement; that is a heuristic, and most near-matches have no address at "
    + "all, so only the paired ones appear here. <b>small</b> is reconstructed but too "
    + "nearly all-relocation for the masked oracle to verify. <b>todo</b> has no source yet. "
    + "Signatures are demangled from the mangled COMDAT name and are omitted rather than "
    + "guessed where the demangler cannot parse one safely. Underlined operands are calls "
    + "or jumps landing on a known function &mdash; click to follow."
    + (OFFN ? " <b>" + OFFN + "</b> block" + (OFFN === 1 ? "" : "s")
        + " start at an address the disassembler decodes straight through: those"
        + " are spurious enumeration starts sitting inside the previous"
        + " function, not functions." : "");
}

buildIdx("");
if (location.hash && /^#0x[0-9a-f]+$/i.test(location.hash))
  gotoAddr(parseInt(location.hash.slice(1), 16));
else render();
</script>
"""

if __name__ == "__main__":
    main()
