import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.lang.model.element.Modifier;
import javax.lang.model.type.TypeKind;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/** R149. Parse-only JDK source spans for exactly two identical signed-short
 * reader bodies. Never execute private source; all names/spans are private.
 */
public final class PrivateSignedShortSourceSpansR149 {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("EXACT_SOURCE_AND_EMPTY_DIR_REQUIRED");
        Path source = Paths.get(args[0]).toRealPath();
        Path empty = Paths.get(args[1]).toRealPath();
        if (!Files.isRegularFile(source) || Files.isSymbolicLink(source)
                || !Files.isDirectory(empty) || Files.isSymbolicLink(empty))
            throw new IllegalArgumentException("R149_UNSAFE_SOURCE_INPUT");
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        List<String> result = new ArrayList<>();
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, manager, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none",
                        "-classpath", empty.toString(), "-sourcepath", empty.toString()),
                null, manager.getJavaFileObjectsFromPaths(List.of(source)));
            Trees trees = Trees.instance(task);
            int owners = 0;
            String canonical = null;
            int candidates = 0;
            for (CompilationUnitTree unit : task.parse()) {
                for (Tree type : unit.getTypeDecls()) {
                    if (!(type instanceof ClassTree)) throw new IllegalStateException("R149_UNEXPECTED_TOP_LEVEL");
                    owners++;
                    ClassTree owner = (ClassTree) type;
                    for (Tree member : owner.getMembers()) {
                        if (!(member instanceof MethodTree)) continue;
                        MethodTree method = (MethodTree) member;
                        if (!(method.getReturnType() instanceof PrimitiveTypeTree)
                                || ((PrimitiveTypeTree) method.getReturnType()).getPrimitiveTypeKind() != TypeKind.INT
                                || !method.getParameters().isEmpty()
                                || !method.getModifiers().getFlags().contains(Modifier.PUBLIC)
                                || method.getBody() == null) continue;
                        BlockTree body = method.getBody();
                        String bodyShape = body.toString();
                        if (!(bodyShape.contains("32767") && bodyShape.contains("65536")
                                && bodyShape.contains("this.caret") && bodyShape.contains("this.payload"))) continue;
                        if (body.getStatements().size() != 4)
                            throw new IllegalStateException("R149_SIGNED_SHORT_WRONG_STATEMENT_COUNT");
                        if (canonical != null && !canonical.equals(bodyShape))
                            throw new IllegalStateException("R149_CANDIDATE_BODIES_DIFFER");
                        canonical = bodyShape;
                        candidates++;
                        long begin = trees.getSourcePositions().getStartPosition(unit, method);
                        long end = trees.getSourcePositions().getEndPosition(unit, method);
                        if (begin < 0 || end <= begin)
                            throw new IllegalStateException("R149_METHOD_SPAN_UNKNOWN");
                        List<String> fields = new ArrayList<>();
                        new TreeScanner<Void, Void>() {
                            @Override public Void visitMemberSelect(MemberSelectTree node, Void ignored) {
                                String qualified = node.toString();
                                if (!(qualified.equals("this.caret") || qualified.equals("this.payload")))
                                    throw new IllegalStateException("R149_UNEXPECTED_SOURCE_FIELD_OR_METHOD_SELECT");
                                long start = trees.getSourcePositions().getStartPosition(unit, node);
                                long finish = trees.getSourcePositions().getEndPosition(unit, node);
                                if (start < begin || finish > end || finish <= start)
                                    throw new IllegalStateException("R149_FIELD_SPAN_OUTSIDE_METHOD");
                                fields.add("FIELD\t" + qualified + "\t" + start + "\t" + finish);
                                return super.visitMemberSelect(node, ignored);
                            }
                        }.scan(body, null);
                        if (fields.stream().filter(x -> x.startsWith("FIELD\tthis.caret\t")).count() != 3
                                || fields.stream().filter(x -> x.startsWith("FIELD\tthis.payload\t")).count() != 2)
                            throw new IllegalStateException("R149_FIELD_USE_COUNT_MISMATCH");
                        result.add("METHOD\t" + method.getName() + "\t" + begin + "\t" + end);
                        result.addAll(fields);
                        result.add("END");
                    }
                }
            }
            if (owners != 1 || candidates != 2)
                throw new IllegalStateException("R149_EXPECTED_EXACTLY_TWO_IDENTICAL_READERS");
        }
        if (diagnostics.getDiagnostics().stream().anyMatch(
                d -> d.getKind() == Diagnostic.Kind.ERROR))
            throw new IllegalStateException("R149_SOURCE_PARSE_ERRORS");
        result.forEach(System.out::println);
    }
}
