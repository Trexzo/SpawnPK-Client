import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.lang.model.element.*;
import javax.lang.model.util.Elements;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/**
 * R131: JDK symbol-attributed Java source call edges, never lexical guessing.
 * User Java source is parsed/analyzed (annotation processing disabled) but
 * NEVER generated, loaded as JVM code, or executed.
 */
public final class ClientAttributedCallEdgesR131 {
    private static String enc(String value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(
            value.getBytes(StandardCharsets.UTF_8));
    }

    private static final class Collector extends TreePathScanner<Void, Void> {
        private final Trees trees;
        private final Elements elements;
        private final Deque<String> classOwners = new ArrayDeque<>();
        private final Map<String, Integer> edges = new TreeMap<>();
        private long analyzedInvocations = 0;
        private long unresolvedOrNonMethodCalls = 0;
        private long nonRsTargetCalls = 0;

        Collector(Trees trees, Elements elements) {
            this.trees = trees;
            this.elements = elements;
        }

        private String binaryName(TypeElement element) {
            return elements.getBinaryName(element).toString()
                .replace('.', '/');
        }

        private boolean localType() {
            TreePath previous = getCurrentPath().getParentPath();
            while (previous != null) {
                Tree leaf = previous.getLeaf();
                if (leaf instanceof MethodTree || leaf instanceof BlockTree
                    || leaf instanceof LambdaExpressionTree) return true;
                if (leaf instanceof ClassTree ||
                    leaf instanceof CompilationUnitTree) return false;
                previous = previous.getParentPath();
            }
            return false;
        }

        @Override public Void visitClass(ClassTree node, Void ignored) {
            if (node.getSimpleName().length() == 0 || localType()) {
                // Anonymous/local classes require independent compiler
                // binary-name ownership and are not promoted from AST.
                return null;
            }
            Element element = trees.getElement(getCurrentPath());
            if (!(element instanceof TypeElement)) {
                return null;
            }
            String name = binaryName((TypeElement) element);
            if (!name.startsWith("rs/")) {
                return null;
            }
            classOwners.addLast(name);
            super.visitClass(node, ignored);
            classOwners.removeLast();
            return null;
        }

        private void addResolved(Element method) {
            if (classOwners.isEmpty()) return;
            analyzedInvocations++;
            if (!(method instanceof ExecutableElement)) {
                unresolvedOrNonMethodCalls++;
                return;
            }
            Element declaredBy = method.getEnclosingElement();
            if (!(declaredBy instanceof TypeElement)) {
                unresolvedOrNonMethodCalls++;
                return;
            }
            String caller = classOwners.getLast();
            String target = binaryName((TypeElement) declaredBy);
            if (!target.startsWith("rs/")) {
                nonRsTargetCalls++;
                return;
            }
            String key = caller + "\t" + target;
            edges.merge(key, 1, Integer::sum);
        }

        @Override public Void visitMethodInvocation(
                MethodInvocationTree node, Void ignored) {
            addResolved(trees.getElement(getCurrentPath()));
            return super.visitMethodInvocation(node, ignored);
        }

        @Override public Void visitNewClass(
                NewClassTree node, Void ignored) {
            addResolved(trees.getElement(getCurrentPath()));
            return super.visitNewClass(node, ignored);
        }

        void report(long sourceFiles, long compilerErrors) {
            System.out.println("SUMMARY\t" + sourceFiles + "\t"
                + compilerErrors + "\t" + analyzedInvocations + "\t"
                + unresolvedOrNonMethodCalls + "\t"
                + nonRsTargetCalls);
            for (Map.Entry<String, Integer> item : edges.entrySet()) {
                String[] names = item.getKey().split("\t", -1);
                System.out.println("EDGE\t" + enc(names[0]) + "\t"
                    + enc(names[1]) + "\t" + item.getValue());
            }
        }
    }

    public static void main(String[] argv) throws Exception {
        if (argv.length != 2) {
            throw new IllegalArgumentException(
                "SOURCE_ROOT_AND_EMPTY_DEPENDENCY_DIRECTORY_REQUIRED");
        }
        Path root = Paths.get(argv[0]).toRealPath();
        Path empty = Paths.get(argv[1]).toRealPath();
        if (!Files.isDirectory(root) || !Files.isDirectory(empty)
            || Files.isSymbolicLink(root) || Files.isSymbolicLink(empty)) {
            throw new IllegalArgumentException("STAGED_SOURCE_ROOTS_INVALID");
        }
        try (Stream<Path> stream = Files.list(empty)) {
            if (stream.findAny().isPresent()) {
                throw new IllegalArgumentException(
                    "DEPENDENCY_CLASSPATH_MUST_BE_EMPTY");
            }
        }
        List<Path> sources;
        try (Stream<Path> stream = Files.walk(root)) {
            sources = stream.filter(Files::isRegularFile)
                .filter(x -> x.toString().endsWith(".java"))
                .sorted().collect(Collectors.toList());
        }
        if (sources.isEmpty() || sources.size() > 5000) {
            throw new IllegalArgumentException("JAVA_SOURCE_COUNT_OUT_OF_BOUNDS");
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();
        JavacTask task;
        Iterable<? extends CompilationUnitTree> units;
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            task = (JavacTask) compiler.getTask(
                null, manager, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none",
                              "-classpath", empty.toString(),
                              "-sourcepath", empty.toString(),
                              "-Xmaxerrs", "30"),
                null, manager.getJavaFileObjectsFromPaths(sources));
            units = task.parse();
            task.analyze();
            Trees trees = Trees.instance(task);
            Collector collector = new Collector(trees, task.getElements());
            for (CompilationUnitTree unit : units) collector.scan(unit, null);
            long errors = diagnostics.getDiagnostics().stream().filter(
                d -> d.getKind() == Diagnostic.Kind.ERROR).count();
            collector.report(sources.size(), errors);
        }
    }
}
