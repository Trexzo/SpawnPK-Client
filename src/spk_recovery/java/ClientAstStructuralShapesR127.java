import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.lang.model.element.Modifier;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/** R127: source-only structural signatures; never class identity acceptance. */
public final class ClientAstStructuralShapesR127 {
    private static String enc(String value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(
            value.getBytes(StandardCharsets.UTF_8));
    }

    private static String typeShape(Tree type) {
        if (type == null) return "L;";
        if (type instanceof ArrayTypeTree) {
            return "[" + typeShape(((ArrayTypeTree) type).getType());
        }
        if (type instanceof AnnotatedTypeTree) {
            return typeShape(((AnnotatedTypeTree) type).getUnderlyingType());
        }
        if (type instanceof PrimitiveTypeTree) {
            switch (((PrimitiveTypeTree) type).getPrimitiveTypeKind()) {
                case BOOLEAN: return "Z";
                case BYTE: return "B";
                case SHORT: return "S";
                case INT: return "I";
                case LONG: return "J";
                case CHAR: return "C";
                case FLOAT: return "F";
                case DOUBLE: return "D";
                case VOID: return "V";
                default: throw new IllegalArgumentException("UNKNOWN_PRIMITIVE");
            }
        }
        return "L;";
    }

    private static class Collector extends TreePathScanner<Void, Void> {
        private final String pkg;
        private final Deque<String> types = new ArrayDeque<>();
        private final List<String> output;

        Collector(String pkg, List<String> output) {
            this.pkg = pkg;
            this.output = output;
        }

        @Override public Void visitClass(ClassTree node, Void ignored) {
            String name = node.getSimpleName().toString();
            if (name.isEmpty()) return null;
            types.addLast(name);
            String internal = (pkg.isEmpty() ? "" : pkg + "/")
                + String.join("$", types);
            String kind = node.getKind().name();
            List<String> fields = new ArrayList<>();
            List<String> methods = new ArrayList<>();
            int constructors = 0;
            for (Tree member : node.getMembers()) {
                if (member instanceof VariableTree) {
                    VariableTree field = (VariableTree) member;
                    if (field.getType() != null) {
                        boolean stat = field.getModifiers()
                            .getFlags().contains(Modifier.STATIC);
                        fields.add((stat ? "S:" : "I:")
                                   + typeShape(field.getType()));
                    }
                } else if (member instanceof MethodTree) {
                    MethodTree method = (MethodTree) member;
                    StringBuilder descriptor = new StringBuilder("(");
                    for (VariableTree parameter : method.getParameters()) {
                        descriptor.append(typeShape(parameter.getType()));
                    }
                    descriptor.append(")");
                    boolean constructor = method.getReturnType() == null;
                    if (constructor) constructors++;
                    descriptor.append(constructor ? "V"
                        : typeShape(method.getReturnType()));
                    boolean stat = method.getModifiers()
                        .getFlags().contains(Modifier.STATIC);
                    methods.add((stat ? "S:" : "I:") + descriptor);
                }
            }
            if (kind.equals("CLASS") && constructors == 0) {
                methods.add("I:()V"); // source implicit default constructor
            }
            Collections.sort(fields);
            Collections.sort(methods);
            output.add(enc(internal) + "\t" + kind + "\t"
                       + enc(String.join("|", fields)) + "\t"
                       + enc(String.join("|", methods)));
            super.visitClass(node, ignored);
            types.removeLast();
            return null;
        }

        // Local/anonymous JVM names are compiler-numbered; do not infer them.
        @Override public Void visitMethod(MethodTree node, Void ignored) {
            return null;
        }
        @Override public Void visitBlock(BlockTree node, Void ignored) {
            return null;
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("ONE_ROOT");
        Path root = Paths.get(args[0]).toRealPath();
        List<Path> sources;
        try (Stream<Path> stream = Files.walk(root)) {
            sources = stream.filter(Files::isRegularFile)
                .filter(x -> x.toString().endsWith(".java"))
                .sorted().collect(Collectors.toList());
        }
        if (sources.isEmpty() || sources.size() > 5000) {
            throw new IllegalArgumentException("SOURCE_COUNT_BOUND");
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();
        List<String> rows = new ArrayList<>();
        try (StandardJavaFileManager files = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, files, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none"),
                null, files.getJavaFileObjectsFromPaths(sources));
            for (CompilationUnitTree unit : task.parse()) {
                String pkg = unit.getPackageName() == null ? ""
                    : unit.getPackageName().toString().replace('.', '/');
                new Collector(pkg, rows).scan(unit, null);
            }
        }
        long failures = diagnostics.getDiagnostics().stream()
            .filter(d -> d.getKind() == Diagnostic.Kind.ERROR).count();
        if (failures != 0) throw new IllegalStateException(
            "AST_PARSE_ERRORS_" + failures);
        Collections.sort(rows);
        for (String row : rows) System.out.println(row);
    }
}
