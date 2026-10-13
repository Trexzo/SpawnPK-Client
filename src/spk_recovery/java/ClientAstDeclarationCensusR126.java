import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;
import com.sun.source.util.JavacTask;

/**
 * R126: parse (never execute/compile) Java source for top-level/member
 * declarations. Output is private and contains names. Never use CI output
 * from real user source; hosted fixtures are strictly synthetic.
 */
public final class ClientAstDeclarationCensusR126 {
    private static String enc(String s) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(
            s.getBytes(StandardCharsets.UTF_8));
    }

    private static class Collector extends TreePathScanner<Void, Void> {
        private final String sourcePath;
        private final String packagePath;
        private final Deque<String> types = new ArrayDeque<>();
        private final List<String> declarations;

        Collector(String sourcePath, String packagePath,
                  List<String> declarations) {
            this.sourcePath = sourcePath;
            this.packagePath = packagePath;
            this.declarations = declarations;
        }

        @Override public Void visitClass(ClassTree node, Void ignored) {
            String name = node.getSimpleName().toString();
            if (name.isEmpty()) {
                // Anonymous classes have no source-declarable binary name.
                return null;
            }
            types.addLast(name);
            String internal = (packagePath.isEmpty() ? "" : packagePath + "/")
                + String.join("$", types);
            declarations.add(enc(sourcePath) + "\t" + enc(internal));
            super.visitClass(node, ignored);
            types.removeLast();
            return null;
        }

        // Local and anonymous classes depend on javac binary-name numbering.
        // They are NOT accepted by this source-structure census.
        @Override public Void visitMethod(MethodTree node, Void ignored) {
            return null;
        }

        @Override public Void visitBlock(BlockTree node, Void ignored) {
            return null;
        }
    }

    public static void main(String[] argv) throws Exception {
        if (argv.length != 1) {
            throw new IllegalArgumentException("EXPECTED_EXACT_PRIVATE_SOURCE_ROOT");
        }
        Path root = Paths.get(argv[0]).toRealPath();
        if (!Files.isDirectory(root) || Files.isSymbolicLink(root)) {
            throw new IllegalArgumentException("PRIVATE_SOURCE_ROOT_REQUIRED");
        }
        List<Path> paths;
        try (Stream<Path> stream = Files.walk(root)) {
            paths = stream.filter(Files::isRegularFile)
                .filter(x -> x.toString().endsWith(".java"))
                .sorted().collect(Collectors.toList());
        }
        if (paths.isEmpty() || paths.size() > 5000) {
            throw new IllegalArgumentException("SOURCE_COUNT_OUTSIDE_BOUND");
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("JDK_JAVA_COMPILER_REQUIRED");
        }
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();
        List<String> declarations = new ArrayList<>();
        try (StandardJavaFileManager files = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, files, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none"),
                null, files.getJavaFileObjectsFromPaths(paths));
            for (CompilationUnitTree unit : task.parse()) {
                if (unit.getSourceFile() == null) {
                    throw new IllegalStateException("SOURCE_UNIT_MISSING_PATH");
                }
                Path file = Paths.get(unit.getSourceFile().toUri()).toRealPath();
                if (!file.startsWith(root)) {
                    throw new IllegalStateException("SOURCE_ESCAPED_SCAN_ROOT");
                }
                String relative = root.relativize(file).toString()
                    .replace('\\', '/');
                String pkg = unit.getPackageName() == null
                    ? "" : unit.getPackageName().toString().replace('.', '/');
                new Collector(relative, pkg, declarations)
                    .scan(unit, null);
            }
        }
        long errors = diagnostics.getDiagnostics().stream().filter(
            d -> d.getKind() == Diagnostic.Kind.ERROR).count();
        if (errors != 0) {
            // Deliberately suppress paths and source snippets, which can be
            // private. The calling script receives a closed-gate status.
            throw new IllegalStateException("JAVA_AST_PARSE_ERRORS_" + errors);
        }
        Collections.sort(declarations);
        for (String row : declarations) {
            System.out.println(row);
        }
    }
}
