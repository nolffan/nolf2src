import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.SourceType;
import java.io.*;
import java.util.*;

/**
 * Batch-decompile a range of functions to one .c file.
 *
 * Args: <out.c> [lo hi [starts.txt]]
 *
 * starts.txt is one address per line (0x-prefixed), optionally followed by a
 * comma and a name. Ghidra's own analysis misses functions that are only
 * reached through a `push imm32` handed to the API — DLGPROCs, WNDPROCs — and
 * silently folds them into whatever function precedes them. Seeding the starts
 * from tools/enumfuncs.py fixes that, and the name column carries the
 * `Class::Method` literals enumfuncs recovers from the argument-check macro,
 * which is the only naming information a stripped engine binary still has.
 */
public class DumpDecomp extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String out = args.length > 0 ? args[0] : "/tmp/decomp.c";
        long lo = args.length > 2 ? Long.decode(args[1]) : 0;
        long hi = args.length > 2 ? Long.decode(args[2]) : Long.MAX_VALUE;

        int seeded = 0;
        if (args.length > 3) {
            BufferedReader r = new BufferedReader(new FileReader(args[3]));
            for (String line; (line = r.readLine()) != null; ) {
                line = line.trim();
                if (line.isEmpty()) continue;
                int comma = line.indexOf(',');
                String name = comma < 0 ? null : line.substring(comma + 1).trim();
                if (name != null && name.isEmpty()) name = null;
                if (name != null) name = name.replace("::", "__");
                Address a = toAddr(Long.decode(comma < 0 ? line : line.substring(0, comma)));
                Function f = getFunctionAt(a);
                if (f == null) {
                    // a start inside another function means that function was
                    // over-extended: split it rather than skip
                    Function o = getFunctionContaining(a);
                    if (o != null) removeFunction(o);
                    f = createFunction(a, name);
                    if (f != null) seeded++;
                } else if (name != null) {
                    f.setName(name, SourceType.USER_DEFINED);
                }
            }
            r.close();
            println("seeded " + seeded + " function starts");
        }

        DecompInterface d = new DecompInterface();
        d.toggleCCode(true);
        d.openProgram(currentProgram);
        PrintWriter w = new PrintWriter(new FileWriter(out));
        int n = 0;
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            long a = f.getEntryPoint().getOffset();
            if (a < lo || a > hi) continue;
            DecompileResults r = d.decompileFunction(f, 60, monitor);
            w.println("/* ===== " + f.getName() + " @ " + f.getEntryPoint() + " ===== */");
            if (r != null && r.decompileCompleted())
                w.println(r.getDecompiledFunction().getC());
            else
                w.println("/* decompile failed: " + (r == null ? "null" : r.getErrorMessage()) + " */");
            w.println();
            n++;
        }
        w.close();
        println("wrote " + n + " functions to " + out);
    }
}
