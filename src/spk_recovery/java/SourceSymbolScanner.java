import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

public final class SourceSymbolScanner {
    private static final Base64.Encoder B64 = Base64.getUrlEncoder().withoutPadding();

    private static String enc(String value) {
        return B64.encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private static final class Scanner extends TreePathScanner<Void, Void> {
        private final CompilationUnitTree unit;
        private final Trees trees;
        private final Path root;
        private final Path sourcePath;
        private final Deque<String> classes = new ArrayDeque<>();
        private final Set<VariableTree> parameters =
            Collections.newSetFromMap(new IdentityHashMap<>());
        private String currentMethod = null;
        private int currentArity = -1;
        private long currentMethodStart = -1L;

        Scanner(
            CompilationUnitTree unit,
            Trees trees,
            Path root,
            Path sourcePath
        ) {
            this.unit = unit;
            this.trees = trees;
            this.root = root;
            this.sourcePath = sourcePath;
        }

        private String ownerInternal() {
            String pkg = unit.getPackageName() == null
                ? ""
                : unit.getPackageName().toString().replace('.', '/');
            List<String> names = new ArrayList<>(classes);
            Collections.reverse(names);
            String cls = String.join("$", names);
            return pkg.isEmpty() ? cls : pkg + "/" + cls;
        }

        private String rel() {
            return root.relativize(sourcePath).toString().replace('\\', '/');
        }

        private long start(Tree tree) {
            return trees.getSourcePositions().getStartPosition(unit, tree);
        }

        private long end(Tree tree) {
            return trees.getSourcePositions().getEndPosition(unit, tree);
        }

        private void methodRow(MethodTree node) {
            String name = node.getReturnType() == null
                ? "<init>"
                : node.getName().toString();
            System.out.println(
                "M\t" + enc(rel())
                + "\t" + enc(ownerInternal())
                + "\t" + enc(name)
                + "\t" + node.getParameters().size()
                + "\t" + start(node)
                + "\t" + end(node)
            );
        }

        private void variableRow(
            VariableTree node,
            String kind,
            int parameterIndex
        ) {
            String type = node.getType() == null
                ? ""
                : node.getType().toString();
            System.out.println(
                "V\t" + enc(rel())
                + "\t" + enc(ownerInternal())
                + "\t" + enc(currentMethod == null ? "" : currentMethod)
                + "\t" + currentArity
                + "\t" + currentMethodStart
                + "\t" + enc(kind)
                + "\t" + enc(node.getName().toString())
                + "\t" + enc(type)
                + "\t" + parameterIndex
                + "\t" + start(node)
                + "\t" + end(node)
            );
        }

        @Override
        public Void visitClass(ClassTree node, Void unused) {
            String name = node.getSimpleName().toString();
            if (name.isEmpty()) {
                return super.visitClass(node, unused);
            }
            classes.push(name);
            try {
                return super.visitClass(node, unused);
            } finally {
                classes.pop();
            }
        }

        @Override
        public Void visitMethod(MethodTree node, Void unused) {
            String priorMethod = currentMethod;
            int priorArity = currentArity;
            long priorStart = currentMethodStart;

            currentMethod = node.getReturnType() == null
                ? "<init>"
                : node.getName().toString();
            currentArity = node.getParameters().size();
            currentMethodStart = start(node);
            methodRow(node);

            int index = 0;
            for (VariableTree parameter : node.getParameters()) {
                parameters.add(parameter);
                variableRow(parameter, "parameter", index++);
            }

            try {
                return super.visitMethod(node, unused);
            } finally {
                for (VariableTree parameter : node.getParameters()) {
                    parameters.remove(parameter);
                }
                currentMethod = priorMethod;
                currentArity = priorArity;
                currentMethodStart = priorStart;
            }
        }

        @Override
        public Void visitVariable(VariableTree node, Void unused) {
            if (parameters.contains(node)) {
                return super.visitVariable(node, unused);
            }
            if (currentMethod == null) {
                return super.visitVariable(node, unused);
            }

            TreePath parentPath = getCurrentPath().getParentPath();
            Tree.Kind parent = parentPath == null
                ? Tree.Kind.OTHER
                : parentPath.getLeaf().getKind();

            String kind;
            if (parent == Tree.Kind.CATCH) {
                kind = "catch";
            } else if (parent == Tree.Kind.ENHANCED_FOR_LOOP) {
                kind = "enhanced_for";
            } else if (parent == Tree.Kind.TRY) {
                kind = "resource";
            } else if (parent == Tree.Kind.LAMBDA_EXPRESSION) {
                kind = "lambda_parameter";
            } else {
                kind = "local";
            }
            variableRow(node, kind, -1);
            return super.visitVariable(node, unused);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("usage: <source-root>");
        }
        Path root = Paths.get(args[0]).toAbsolutePath().normalize();
        List<Path> sources;
        try (Stream<Path> stream = Files.walk(root)) {
            sources = stream
                .filter(path -> Files.isRegularFile(path))
                .filter(path -> path.toString().endsWith(".java"))
                .sorted()
                .collect(Collectors.toList());
        }
        if (sources.isEmpty()) {
            throw new IllegalArgumentException("source root has no Java files");
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("system Java compiler unavailable");
        }

        try (StandardJavaFileManager manager =
                 compiler.getStandardFileManager(null, Locale.ROOT, StandardCharsets.UTF_8)) {
            Iterable<? extends JavaFileObject> units =
                manager.getJavaFileObjectsFromPaths(sources);
            JavacTask task = (JavacTask) compiler.getTask(
                null,
                manager,
                null,
                List.of("-proc:none"),
                null,
                units
            );
            Iterable<? extends CompilationUnitTree> parsed = task.parse();
            Trees trees = Trees.instance(task);
            for (CompilationUnitTree unit : parsed) {
                Path sourcePath = Paths.get(unit.getSourceFile().toUri())
                    .toAbsolutePath().normalize();
                new Scanner(unit, trees, root, sourcePath).scan(unit, null);
            }
        }
    }
}
