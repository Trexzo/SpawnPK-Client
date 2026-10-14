import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/**
 * R139 parse-only import spans; never attributes symbols or executes client code.
 * Emits tab-separated Java character offsets for explicit non-static imports.
 */
public final class PrivateSingleImportSpansR139 {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("JAVA_AND_EMPTY_PATH");
        Path source = Paths.get(args[0]).toRealPath();
        Path empty = Paths.get(args[1]).toRealPath();
        if (!Files.isRegularFile(source) || Files.isSymbolicLink(source)
                || !Files.isDirectory(empty)) {
            throw new IllegalArgumentException("TRUSTED_LOCAL_SOURCE_REQUIRED");
        }
        JavaCompiler javac = ToolProvider.getSystemJavaCompiler();
        if (javac == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        ArrayList<String> output = new ArrayList<>();
        try (StandardJavaFileManager files = javac.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) javac.getTask(null, files, diagnostics,
                    Arrays.asList("--release", "11", "-proc:none", "-implicit:none",
                            "-classpath", empty.toString(),
                            "-sourcepath", empty.toString()),
                    null, files.getJavaFileObjectsFromPaths(List.of(source)));
            Trees trees = Trees.instance(task);
            for (CompilationUnitTree unit : task.parse()) {
                for (ImportTree entry : unit.getImports()) {
                    if (entry.isStatic()) continue;
                    Tree target = entry.getQualifiedIdentifier();
                    String dotted = target.toString();
                    if (dotted.endsWith(".*")) continue;
                    long start = trees.getSourcePositions().getStartPosition(unit, target);
                    long end = trees.getSourcePositions().getEndPosition(unit, target);
                    if (start < 0 || end <= start) {
                        throw new IllegalStateException("INVALID_IMPORT_SPAN");
                    }
                    output.add(start + "\t" + end + "\t" + dotted);
                }
            }
        }
        for (Diagnostic<? extends JavaFileObject> diagnostic : diagnostics.getDiagnostics()) {
            if (diagnostic.getKind() == Diagnostic.Kind.ERROR) {
                throw new IllegalStateException("SOURCE_SYNTAX_ERROR");
            }
        }
        Collections.sort(output);
        for (String line : output) System.out.println(line);
    }
}
