import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/** Source-only, parse-only exact AST spans for one collision-aliased imported type.
 *  Unsupported expression uses remain unmodified and prevent the whole edit.
 */
public final class PrivateImportedTypeAliasSpansR141 {
    private static boolean typeContext(Tree child, Tree parent) {
        if (parent instanceof VariableTree)
            return ((VariableTree) parent).getType() == child;
        if (parent instanceof MethodTree)
            return ((MethodTree) parent).getReturnType() == child;
        if (parent instanceof ParameterizedTypeTree) {
            ParameterizedTypeTree p = (ParameterizedTypeTree) parent;
            return p.getType() == child || p.getTypeArguments().contains(child);
        }
        if (parent instanceof ArrayTypeTree)
            return ((ArrayTypeTree) parent).getType() == child;
        if (parent instanceof NewClassTree)
            return ((NewClassTree) parent).getIdentifier() == child;
        if (parent instanceof NewArrayTree)
            return ((NewArrayTree) parent).getType() == child;
        if (parent instanceof TypeCastTree)
            return ((TypeCastTree) parent).getType() == child;
        if (parent instanceof InstanceOfTree)
            return ((InstanceOfTree) parent).getType() == child;
        if (parent instanceof AnnotationTree)
            return ((AnnotationTree) parent).getAnnotationType() == child;
        if (parent instanceof ClassTree) {
            ClassTree p = (ClassTree) parent;
            return p.getExtendsClause() == child || p.getImplementsClause().contains(child);
        }
        if (parent instanceof WildcardTree)
            return ((WildcardTree) parent).getBound() == child;
        if (parent instanceof AnnotatedTypeTree)
            return ((AnnotatedTypeTree) parent).getUnderlyingType() == child;
        if (parent instanceof UnionTypeTree)
            return ((UnionTypeTree) parent).getTypeAlternatives().contains(child);
        if (parent instanceof IntersectionTypeTree)
            return ((IntersectionTypeTree) parent).getBounds().contains(child);
        if (parent instanceof TypeParameterTree)
            return ((TypeParameterTree) parent).getBounds().contains(child);
        return false;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("JAVA_EMPTY_OLD_IMPORT_REQUIRED");
        Path source = Paths.get(args[0]).toRealPath();
        Path empty = Paths.get(args[1]).toRealPath();
        String oldImport = args[2];
        if (!Files.isRegularFile(source) || Files.isSymbolicLink(source)
                || !Files.isDirectory(empty)
                || !oldImport.matches("[A-Za-z_$][A-Za-z0-9_$]*(\\.[A-Za-z_$][A-Za-z0-9_$]*)+")) {
            throw new IllegalArgumentException("INVALID_REVIEWED_IMPORT_INPUTS");
        }
        String simple = oldImport.substring(oldImport.lastIndexOf('.') + 1);
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        List<String> spans = new ArrayList<>();
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                    null, manager, diagnostics,
                    Arrays.asList("--release", "11", "-proc:none", "-implicit:none",
                            "-classpath", empty.toString(),
                            "-sourcepath", empty.toString()),
                    null, manager.getJavaFileObjectsFromPaths(List.of(source)));
            Trees trees = Trees.instance(task);
            for (CompilationUnitTree unit : task.parse()) {
                int matches = 0;
                for (ImportTree imp : unit.getImports()) {
                    if (imp.isStatic()) continue;
                    String q = imp.getQualifiedIdentifier().toString();
                    if (q.equals(oldImport)) {
                        matches++;
                        Tree node = imp.getQualifiedIdentifier();
                        long a = trees.getSourcePositions().getStartPosition(unit, node);
                        long b = trees.getSourcePositions().getEndPosition(unit, node);
                        spans.add("IMPORT\t" + a + "\t" + b + "\t" + q);
                    } else if (q.endsWith("." + simple)) {
                        spans.add("UNSUPPORTED\t0\t0\tDUPLICATE_SIMPLE_IMPORT");
                    }
                }
                if (matches != 1) throw new IllegalStateException("SINGLE_EXACT_IMPORT_REQUIRED");
                new TreePathScanner<Void, Void>() {
                    @Override public Void visitClass(ClassTree node, Void unused) {
                        if (node.getSimpleName().contentEquals(simple))
                            spans.add("UNSUPPORTED\t0\t0\tLOCAL_CLASS_SHADOW");
                        return super.visitClass(node, unused);
                    }
                    @Override public Void visitTypeParameter(TypeParameterTree node, Void unused) {
                        if (node.getName().contentEquals(simple))
                            spans.add("UNSUPPORTED\t0\t0\tTYPE_PARAMETER_SHADOW");
                        return super.visitTypeParameter(node, unused);
                    }
                    @Override public Void visitIdentifier(IdentifierTree node, Void unused) {
                        if (node.getName().contentEquals(simple)) {
                            TreePath parentPath = getCurrentPath().getParentPath();
                            Tree parent = parentPath == null ? null : parentPath.getLeaf();
                            long a = trees.getSourcePositions().getStartPosition(unit, node);
                            long b = trees.getSourcePositions().getEndPosition(unit, node);
                            boolean safe = parent != null && typeContext(node, parent);
                            spans.add((safe ? "TYPE" : "UNSUPPORTED") + "\t" +
                                    a + "\t" + b + "\t" + simple);
                        }
                        return super.visitIdentifier(node, unused);
                    }
                }.scan(unit, null);
            }
        }
        for (Diagnostic<? extends JavaFileObject> d : diagnostics.getDiagnostics()) {
            if (d.getKind() == Diagnostic.Kind.ERROR)
                throw new IllegalStateException("PRIVATE_SOURCE_SYNTAX_ERRORS");
        }
        for (String item : spans) System.out.println(item);
    }
}
