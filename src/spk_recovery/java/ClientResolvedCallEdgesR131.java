import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.lang.model.element.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/**
 * R131: independently resolve Java source calls using javac's symbol table.
 * Never generates or executes candidate application classes.
 * A complete source-symbol resolution is required; zero fallback to game JARs.
 */
public final class ClientResolvedCallEdgesR131 {
    private static String enc(String value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(
            value.getBytes(StandardCharsets.UTF_8));
    }

    private static String internal(Elements elements, TypeElement type) {
        return elements.getBinaryName(type).toString().replace('.', '/');
    }

    private static final class EdgeScanner extends TreePathScanner<Void, Void> {
        private final Trees trees;
        private final Elements elements;
        private final Map<String, Integer> edges;
        private String topLevelOwner = null;
        int unresolved = 0;
        int sourceMethodReferencesExcluded = 0;

        EdgeScanner(Trees trees, Elements elements,
                    Map<String, Integer> edges) {
            this.trees = trees;
            this.elements = elements;
            this.edges = edges;
        }

        private void recordOwner(Element element) {
            if (topLevelOwner == null) return;
            if (!(element instanceof ExecutableElement)) {
                unresolved++;
                return;
            }
            Element owner = element.getEnclosingElement();
            if (!(owner instanceof TypeElement)) {
                unresolved++;
                return;
            }
            String callee = internal(elements, (TypeElement) owner);
            if (!topLevelOwner.startsWith("rs/") || !callee.startsWith("rs/"))
                return;
            String key = topLevelOwner + "\t" + callee;
            edges.put(key, edges.getOrDefault(key, 0) + 1);
        }

        @Override public Void visitClass(ClassTree tree, Void ignored) {
            if (topLevelOwner != null) {
                // Nested/local source classes have separate JVM binary owners.
                // Do not incorrectly assign their calls to the outer class.
                return null;
            }
            Element element = trees.getElement(getCurrentPath());
            if (!(element instanceof TypeElement)) {
                unresolved++;
                return null;
            }
            TypeElement owner = (TypeElement) element;
            if (owner.getNestingKind() != NestingKind.TOP_LEVEL) {
                return null;
            }
            topLevelOwner = internal(elements, owner);
            super.visitClass(tree, ignored);
            topLevelOwner = null;
            return null;
        }

        @Override public Void visitMethodInvocation(
                MethodInvocationTree tree, Void ignored) {
            recordOwner(trees.getElement(getCurrentPath()));
            return super.visitMethodInvocation(tree, ignored);
        }

        @Override public Void visitNewClass(
                NewClassTree tree, Void ignored) {
            recordOwner(trees.getElement(getCurrentPath()));
            return super.visitNewClass(tree, ignored);
        }

        @Override public Void visitMemberReference(
                MemberReferenceTree tree, Void ignored) {
            // Method-reference implementation goes via invokedynamic. The
            // original R130 deliberately does NOT guess its target owner.
            sourceMethodReferencesExcluded++;
            return super.visitMemberReference(tree, ignored);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("SOURCE_AND_EMPTY_CLASSPATH_REQUIRED");
        }
        Path root = Paths.get(args[0]).toRealPath();
        Path empty = Paths.get(args[1]).toRealPath();
        if (!Files.isDirectory(root) || !Files.isDirectory(empty)
                || Files.isSymbolicLink(root) || Files.isSymbolicLink(empty)) {
            throw new IllegalArgumentException("ISOLATED_SOURCE_PATHS_REQUIRED");
        }
        List<Path> sources;
        try (Stream<Path> walk = Files.walk(root)) {
            sources = walk.filter(Files::isRegularFile)
                .filter(p -> p.toString().endsWith(".java"))
                .sorted().collect(Collectors.toList());
        }
        if (sources.isEmpty() || sources.size() > 5000) {
            throw new IllegalArgumentException("JAVA_SOURCE_COUNT_OUTSIDE_BOUND");
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();
        Map<String, Integer> edges = new TreeMap<>();
        int unresolved = 0;
        int sourceMethodReferencesExcluded = 0;
        try (StandardJavaFileManager files = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, files, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none",
                    "-classpath", empty.toString(),
                    "-sourcepath", empty.toString()),
                null, files.getJavaFileObjectsFromPaths(sources));
            List<CompilationUnitTree> units = new ArrayList<>();
            for (CompilationUnitTree unit : task.parse()) units.add(unit);
            task.analyze();  // NO task.generate(), no code execution.
            long errors = diagnostics.getDiagnostics().stream()
                .filter(d -> d.getKind() == Diagnostic.Kind.ERROR).count();
            if (errors > 0) {
                // Do not leak user's private source names or diagnostic text.
                throw new IllegalStateException("SOURCE_SYMBOL_RESOLUTION_FAILED");
            }
            Trees trees = Trees.instance(task);
            Elements elements = task.getElements();
            for (CompilationUnitTree unit : units) {
                EdgeScanner scan = new EdgeScanner(trees, elements, edges);
                scan.scan(unit, null);
                unresolved += scan.unresolved;
                sourceMethodReferencesExcluded +=
                    scan.sourceMethodReferencesExcluded;
            }
        }
        if (unresolved != 0) {
            throw new IllegalStateException("UNRESOLVED_METHOD_CALL_OWNER");
        }
        for (Map.Entry<String, Integer> edge : edges.entrySet()) {
            String[] names = edge.getKey().split("\t", -1);
            if (names.length != 2) throw new IllegalStateException("EDGE_SCHEMA");
            System.out.println(enc(names[0]) + "\t" +
                enc(names[1]) + "\t" + edge.getValue());
        }
        System.err.println("R131_EXCLUDED_SOURCE_METHOD_REFERENCES=" +
            sourceMethodReferencesExcluded);
    }
}
