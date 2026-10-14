import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.tools.*;
import javax.lang.model.element.Modifier;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/** R146: parse-only Java member and BigInteger literal census, no attribution. */
public final class PrivatePacketNamedSourceR147 {
    private static int access(Set<Modifier> flags) {
        int value = 0;
        if (flags.contains(Modifier.PUBLIC)) value |= 1;
        if (flags.contains(Modifier.PRIVATE)) value |= 2;
        if (flags.contains(Modifier.PROTECTED)) value |= 4;
        if (flags.contains(Modifier.STATIC)) value |= 8;
        if (flags.contains(Modifier.FINAL)) value |= 16;
        if (flags.contains(Modifier.SYNCHRONIZED)) value |= 32;
        if (flags.contains(Modifier.NATIVE)) value |= 256;
        if (flags.contains(Modifier.ABSTRACT)) value |= 1024;
        return value;
    }
    private static String type(Tree input) {
        if (input == null) return "V";
        if (input instanceof PrimitiveTypeTree) {
            switch (((PrimitiveTypeTree) input).getPrimitiveTypeKind()) {
                case BOOLEAN: return "Z";
                case BYTE: return "B";
                case CHAR: return "C";
                case DOUBLE: return "D";
                case FLOAT: return "F";
                case INT: return "I";
                case LONG: return "J";
                case SHORT: return "S";
                case VOID: return "V";
                default: throw new IllegalArgumentException("UNSUPPORTED_PRIMITIVE");
            }
        }
        if (input instanceof ArrayTypeTree)
            return "[" + type(((ArrayTypeTree) input).getType());
        if (input instanceof AnnotatedTypeTree)
            return type(((AnnotatedTypeTree) input).getUnderlyingType());
        return "L;";
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("R146_SOURCE_AND_EMPTY_DIR_REQUIRED");
        Path source = Paths.get(args[0]).toRealPath();
        Path empty = Paths.get(args[1]).toRealPath();
        if (!Files.isRegularFile(source) || Files.isSymbolicLink(source)
                || !Files.isDirectory(empty) || Files.isSymbolicLink(empty))
            throw new IllegalArgumentException("R146_UNSAFE_SOURCE_OR_CLASSPATH");
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        List<String> output = new ArrayList<>();
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, manager, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none",
                              "-classpath", empty.toString(),
                              "-sourcepath", empty.toString()),
                null, manager.getJavaFileObjectsFromPaths(List.of(source)));
            int topLevels = 0;
            for (CompilationUnitTree unit : task.parse()) {
                String pkg = unit.getPackageName() == null
                    ? "" : unit.getPackageName().toString().replace('.', '/');
                for (Tree declaration : unit.getTypeDecls()) {
                    if (!(declaration instanceof ClassTree))
                        throw new IllegalStateException("R146_NONCLASS_TOP_LEVEL");
                    topLevels++;
                    ClassTree owner = (ClassTree) declaration;
                    String name = owner.getSimpleName().toString();
                    if (name.isEmpty()) throw new IllegalStateException("R146_ANONYMOUS_TOP_LEVEL");
                    output.add("OWNER\t" + (pkg.isEmpty() ? "" : pkg + "/") + name);
                    for (Tree member : owner.getMembers()) {
                        if (member instanceof VariableTree) {
                            VariableTree field = (VariableTree) member;
                            output.add("F\t" + access(field.getModifiers().getFlags())
                                + "\t" + type(field.getType()) + "\t" + field.getName());
                        } else if (member instanceof MethodTree) {
                            MethodTree method = (MethodTree) member;
                            StringBuilder descriptor = new StringBuilder("(");
                            for (VariableTree parameter : method.getParameters())
                                descriptor.append(type(parameter.getType()));
                            descriptor.append(')').append(type(method.getReturnType()));
                            output.add("M\t" + access(method.getModifiers().getFlags())
                                + "\t" + descriptor + "\t" + method.getName());
                        }
                    }
                    new TreeScanner<Void, Void>() {
                        @Override public Void visitNewClass(NewClassTree node, Void value) {
                            String identifier = node.getIdentifier().toString();
                            if (identifier.equals("BigInteger")
                                    || identifier.equals("java.math.BigInteger")) {
                                if (node.getArguments().size() != 1
                                        || !(node.getArguments().get(0) instanceof LiteralTree))
                                    throw new IllegalStateException("R146_NONLITERAL_BIG_INTEGER");
                                Object literal = ((LiteralTree) node.getArguments().get(0)).getValue();
                                if (!(literal instanceof String)
                                        || !((String) literal).matches("[0-9]{1,512}"))
                                    throw new IllegalStateException("R146_NONDECIMAL_BIG_INTEGER");
                                output.add("RSA\t" + literal);
                            }
                            return super.visitNewClass(node, value);
                        }
                    }.scan(owner, null);
                }
            }
            if (topLevels != 1) throw new IllegalStateException("R146_EXACT_ONE_SOURCE_OWNER_REQUIRED");
        }
        if (diagnostics.getDiagnostics().stream().anyMatch(
                x -> x.getKind() == Diagnostic.Kind.ERROR))
            throw new IllegalStateException("R146_SOURCE_PARSE_DIAGNOSTICS");
        for (String row : output) System.out.println(row);
    }
}
