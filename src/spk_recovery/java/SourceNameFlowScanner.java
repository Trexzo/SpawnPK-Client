import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

public final class SourceNameFlowScanner {
    private static final Base64.Encoder B64 =
        Base64.getUrlEncoder().withoutPadding();

    private static String enc(String value) {
        return B64.encodeToString(
            value.getBytes(StandardCharsets.UTF_8)
        );
    }

    private static final class Scanner
            extends TreePathScanner<Void, Void> {
        private final CompilationUnitTree unit;
        private final Trees trees;
        private final Path root;
        private final Path sourcePath;
        private final Deque<String> classes = new ArrayDeque<>();
        private String currentMethod = null;
        private int currentArity = -1;
        private long currentMethodStart = -1L;
        private int currentMethodClassDepth = -1;
        private int anonymousClassDepth = 0;

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
                : unit.getPackageName()
                    .toString()
                    .replace('.', '/');
            List<String> names = new ArrayList<>(classes);
            Collections.reverse(names);
            String cls = String.join("$", names);
            return pkg.isEmpty() ? cls : pkg + "/" + cls;
        }

        private String rel() {
            return root.relativize(sourcePath)
                .toString()
                .replace('\\', '/');
        }

        private long start(Tree tree) {
            return trees.getSourcePositions()
                .getStartPosition(unit, tree);
        }

        @Override
        public Void visitClass(ClassTree node, Void unused) {
            String name = node.getSimpleName().toString();
            if (name.isEmpty()) {
                anonymousClassDepth++;
                try {
                    return super.visitClass(node, unused);
                } finally {
                    anonymousClassDepth--;
                }
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
            int priorClassDepth = currentMethodClassDepth;

            currentMethod = node.getReturnType() == null
                ? "<init>"
                : node.getName().toString();
            currentArity = node.getParameters().size();
            currentMethodStart = start(node);
            currentMethodClassDepth = classes.size();
            try {
                return super.visitMethod(node, unused);
            } finally {
                currentMethod = priorMethod;
                currentArity = priorArity;
                currentMethodStart = priorStart;
                currentMethodClassDepth = priorClassDepth;
            }
        }

        @Override
        public Void visitVariable(
            VariableTree node,
            Void unused
        ) {
            if (currentMethod != null
                    && anonymousClassDepth == 0
                    && currentMethodClassDepth == classes.size()
                    && node.getInitializer() != null
                    && node.getInitializer().getKind()
                        == Tree.Kind.MEMBER_SELECT) {
                MemberSelectTree source =
                    (MemberSelectTree) node.getInitializer();
                ExpressionTree receiver = source.getExpression();
                if (receiver.getKind() == Tree.Kind.IDENTIFIER) {
                    IdentifierTree id = (IdentifierTree) receiver;
                    if (id.getName().contentEquals("this")) {
                        System.out.println(
                            "I\t" + enc(rel())
                            + "\t" + enc(ownerInternal())
                            + "\t" + enc(currentMethod)
                            + "\t" + currentArity
                            + "\t" + currentMethodStart
                            + "\t" + enc(
                                source.getIdentifier().toString()
                            )
                            + "\t" + enc(
                                node.getName().toString()
                            )
                            + "\t" + start(node)
                        );
                    }
                }
            }
            return super.visitVariable(node, unused);
        }

        @Override
        public Void visitAssignment(
            AssignmentTree node,
            Void unused
        ) {
            if (currentMethod != null
                    && anonymousClassDepth == 0
                    && currentMethodClassDepth == classes.size()
                    && node.getVariable().getKind()
                        == Tree.Kind.MEMBER_SELECT
                    && node.getExpression().getKind()
                        == Tree.Kind.IDENTIFIER) {
                MemberSelectTree target =
                    (MemberSelectTree) node.getVariable();
                ExpressionTree receiver = target.getExpression();
                if (receiver.getKind() == Tree.Kind.IDENTIFIER) {
                    IdentifierTree id = (IdentifierTree) receiver;
                    if (id.getName().contentEquals("this")) {
                        IdentifierTree rhs =
                            (IdentifierTree) node.getExpression();
                        System.out.println(
                            "A\t" + enc(rel())
                            + "\t" + enc(ownerInternal())
                            + "\t" + enc(currentMethod)
                            + "\t" + currentArity
                            + "\t" + currentMethodStart
                            + "\t" + enc(
                                target.getIdentifier().toString()
                            )
                            + "\t" + enc(
                                rhs.getName().toString()
                            )
                            + "\t" + start(node)
                        );
                    }
                }
            }
            return super.visitAssignment(node, unused);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException(
                "usage: <source-root>"
            );
        }
        Path root = Paths.get(args[0])
            .toAbsolutePath()
            .normalize();
        List<Path> sources;
        try (Stream<Path> stream = Files.walk(root)) {
            sources = stream
                .filter(Files::isRegularFile)
                .filter(
                    path -> path.toString().endsWith(".java")
                )
                .sorted()
                .collect(Collectors.toList());
        }
        if (sources.isEmpty()) {
            throw new IllegalArgumentException(
                "source root has no Java files"
            );
        }

        JavaCompiler compiler =
            ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException(
                "system Java compiler unavailable"
            );
        }

        try (StandardJavaFileManager manager =
                 compiler.getStandardFileManager(
                     null,
                     Locale.ROOT,
                     StandardCharsets.UTF_8
                 )) {
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
            Iterable<? extends CompilationUnitTree> parsed =
                task.parse();
            Trees trees = Trees.instance(task);
            for (CompilationUnitTree unit : parsed) {
                Path sourcePath =
                    Paths.get(unit.getSourceFile().toUri())
                        .toAbsolutePath()
                        .normalize();
                new Scanner(
                    unit,
                    trees,
                    root,
                    sourcePath
                ).scan(unit, null);
            }
        }
    }
}
