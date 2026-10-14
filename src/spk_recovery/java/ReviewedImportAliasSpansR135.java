import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/** Parse-only span scanner for one independently reviewed collision alias.
 * No application classpaths, javac attribution guesses, or source execution.
 */
public final class ReviewedImportAliasSpansR135 {
    private static long start(Trees trees, CompilationUnitTree unit, Tree t) {
        return trees.getSourcePositions().getStartPosition(unit, t);
    }
    private static long end(Trees trees, CompilationUnitTree unit, Tree t) {
        return trees.getSourcePositions().getEndPosition(unit, t);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("SOURCE_IMPORT_OWNER_METHOD");
        Path source = Paths.get(args[0]).toRealPath();
        if (!Files.isRegularFile(source) || Files.isSymbolicLink(source)) {
            throw new IllegalArgumentException("PRIVATE_JAVA_SOURCE_FILE_REQUIRED");
        }
        String expectedImport = args[1], ownerName = args[2];
        if (!expectedImport.endsWith("." + ownerName) ||
                !ownerName.matches("[A-Za-z_$][A-Za-z0-9_$]*")) {
            throw new IllegalArgumentException("REVIEWED_ALIAS_REQUIRED");
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        List<String> spans = new ArrayList<>();
        try (StandardJavaFileManager files = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, files, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none"),
                null, files.getJavaFileObjectsFromPaths(List.of(source)));
            Trees trees = Trees.instance(task);
            for (CompilationUnitTree unit : task.parse()) {
                for (ImportTree imp : unit.getImports()) {
                    if (!imp.isStatic() &&
                            imp.getQualifiedIdentifier().toString().equals(expectedImport)) {
                        Tree q = imp.getQualifiedIdentifier();
                        spans.add("IMPORT\t" + start(trees, unit, q) +
                                  "\t" + end(trees, unit, q));
                    }
                }
                new TreePathScanner<Void, Void>() {
                    @Override public Void visitMethodInvocation(
                            MethodInvocationTree node, Void unused) {
                        ExpressionTree method = node.getMethodSelect();
                        if (method instanceof MemberSelectTree) {
                            MemberSelectTree select = (MemberSelectTree) method;
                            ExpressionTree expression = select.getExpression();
                            if (expression instanceof IdentifierTree &&
                                    ((IdentifierTree) expression).getName()
                                        .contentEquals(ownerName)) {
                                if (!select.getIdentifier().contentEquals("a") ||
                                        node.getArguments().size() != 2 ||
                                        !(node.getArguments().get(0) instanceof TypeCastTree) ||
                                        !((TypeCastTree) node.getArguments().get(0))
                                            .getType().toString().equals("Object[]")) {
                                    throw new IllegalStateException(
                                        "UNREVIEWED_OWNER_METHOD_SHAPE");
                                }
                                spans.add("CALL\t" + start(trees, unit, expression) +
                                          "\t" + end(trees, unit, expression));
                            }
                        }
                        return super.visitMethodInvocation(node, unused);
                    }
                }.scan(unit, null);
            }
        }
        if (diagnostics.getDiagnostics().stream()
                .anyMatch(d -> d.getKind() == Diagnostic.Kind.ERROR)) {
            throw new IllegalStateException("PRIVATE_JAVA_SYNTAX_ERRORS");
        }
        Collections.sort(spans);
        if (spans.stream().filter(x -> x.startsWith("IMPORT\t")).count() != 1 ||
                spans.stream().filter(x -> x.startsWith("CALL\t")).count() != 1) {
            throw new IllegalStateException("EXPECTED_EXACTLY_ONE_IMPORT_AND_CALL");
        }
        for (String row : spans) System.out.println(row);
    }
}
