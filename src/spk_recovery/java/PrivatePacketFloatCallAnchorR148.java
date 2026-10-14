import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.tools.*;
import javax.lang.model.type.TypeKind;
import com.sun.source.tree.*;
import com.sun.source.util.JavacTask;

/** R148: exact parse-only Float.intBitsToFloat(this.intReader()) call-shape.
 * Prints private class/method names only to the private orchestrator pipe.
 * The helper never evaluates Java expressions or runs source bytecode.
 */
public final class PrivatePacketFloatCallAnchorR148 {
    public static void main(String[] args) throws Exception {
        if (args.length != 2)
            throw new IllegalArgumentException("R148_JAVA_AND_EMPTY_CLASSPATH_REQUIRED");
        Path source = Paths.get(args[0]).toRealPath();
        Path empty = Paths.get(args[1]).toRealPath();
        if (!Files.isRegularFile(source) || Files.isSymbolicLink(source)
                || !Files.isDirectory(empty) || Files.isSymbolicLink(empty))
            throw new IllegalArgumentException("R148_UNSAFE_SOURCE_INPUT");
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        List<String> candidates = new ArrayList<>();
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, manager, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none",
                    "-classpath", empty.toString(), "-sourcepath", empty.toString()),
                null, manager.getJavaFileObjectsFromPaths(List.of(source)));
            int owners = 0;
            for (CompilationUnitTree unit : task.parse()) {
                for (Tree type : unit.getTypeDecls()) {
                    if (!(type instanceof ClassTree))
                        throw new IllegalStateException("R148_NONCLASS_TOP_LEVEL");
                    owners++;
                    ClassTree owner = (ClassTree) type;
                    List<MethodTree> methods = new ArrayList<>();
                    for (Tree member : owner.getMembers())
                        if (member instanceof MethodTree) methods.add((MethodTree) member);
                    for (MethodTree method : methods) {
                        if (!(method.getReturnType() instanceof PrimitiveTypeTree)
                                || ((PrimitiveTypeTree) method.getReturnType())
                                        .getPrimitiveTypeKind() != TypeKind.FLOAT
                                || !method.getParameters().isEmpty())
                            continue;
                        // More than one float() method is not automatically a
                        // trustworthy original↔source anchor.
                        if (method.getBody() == null
                                || method.getBody().getStatements().size() != 1)
                            continue;
                        StatementTree statement = method.getBody().getStatements().get(0);
                        if (!(statement instanceof ReturnTree)) continue;
                        ExpressionTree expression = ((ReturnTree) statement).getExpression();
                        if (!(expression instanceof MethodInvocationTree)) continue;
                        MethodInvocationTree outer = (MethodInvocationTree) expression;
                        if (outer.getTypeArguments().size() != 0
                                || outer.getArguments().size() != 1
                                || !(outer.getMethodSelect() instanceof MemberSelectTree))
                            continue;
                        MemberSelectTree select = (MemberSelectTree) outer.getMethodSelect();
                        if (!select.getIdentifier().contentEquals("intBitsToFloat")
                                || !select.getExpression().toString().equals("Float"))
                            continue;
                        ExpressionTree arg = outer.getArguments().get(0);
                        if (!(arg instanceof MethodInvocationTree)) continue;
                        MethodInvocationTree inner = (MethodInvocationTree) arg;
                        if (inner.getArguments().size() != 0
                                || inner.getTypeArguments().size() != 0
                                || !(inner.getMethodSelect() instanceof MemberSelectTree))
                            continue;
                        MemberSelectTree callee = (MemberSelectTree) inner.getMethodSelect();
                        if (!callee.getExpression().toString().equals("this")) continue;
                        String candidateCallee = callee.getIdentifier().toString();
                        int declarations = 0;
                        for (MethodTree other : methods) {
                            if (other.getName().contentEquals(candidateCallee)) {
                                declarations++;
                                if (!(other.getReturnType() instanceof PrimitiveTypeTree)
                                        || ((PrimitiveTypeTree) other.getReturnType())
                                               .getPrimitiveTypeKind() != TypeKind.INT
                                        || !other.getParameters().isEmpty())
                                    throw new IllegalStateException("R148_CALLEE_NOT_INT_ZERO_ARGS");
                            }
                        }
                        if (declarations != 1)
                            throw new IllegalStateException("R148_READER_NOT_UNIQUE");
                        candidates.add(method.getName().toString()
                            + "\t" + candidateCallee);
                    }
                }
            }
            if (owners != 1) throw new IllegalStateException("R148_NOT_SINGLE_TOP_LEVEL");
        }
        if (diagnostics.getDiagnostics().stream().anyMatch(
                x -> x.getKind() == Diagnostic.Kind.ERROR))
            throw new IllegalStateException("R148_SOURCE_SYNTAX_ERROR");
        if (candidates.size() != 1)
            throw new IllegalStateException("R148_FLOAT_CALL_PATTERN_NOT_UNIQUE");
        System.out.println(candidates.get(0));
    }
}
