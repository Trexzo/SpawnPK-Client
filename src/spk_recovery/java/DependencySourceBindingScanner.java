import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.lang.model.element.*;
import javax.lang.model.type.*;
import javax.lang.model.util.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

public final class DependencySourceBindingScanner {
    private static final Base64.Decoder B64 = Base64.getUrlDecoder();
    private static final Base64.Encoder ENC =
        Base64.getUrlEncoder().withoutPadding();

    private static String dec(String value) {
        int rem = value.length() % 4;
        if (rem != 0) {
            value += "=".repeat(4 - rem);
        }
        return new String(
            B64.decode(value),
            StandardCharsets.UTF_8
        );
    }

    private static String enc(String value) {
        return ENC.encodeToString(
            value.getBytes(StandardCharsets.UTF_8)
        );
    }

    private static final class OwnerTarget {
        final String ownerId;
        final String classification;
        final String oldOwner;
        final String newOwner;

        OwnerTarget(
            String ownerId,
            String classification,
            String oldOwner,
            String newOwner
        ) {
            this.ownerId = ownerId;
            this.classification = classification;
            this.oldOwner = oldOwner;
            this.newOwner = newOwner;
        }
    }

    private static final class MemberTarget {
        final String memberId;
        final String oldOwner;
        final String oldName;
        final String oldDescriptor;
        final String newOwner;
        final String newName;
        final String newDescriptor;

        MemberTarget(
            String memberId,
            String oldOwner,
            String oldName,
            String oldDescriptor,
            String newOwner,
            String newName,
            String newDescriptor
        ) {
            this.memberId = memberId;
            this.oldOwner = oldOwner;
            this.oldName = oldName;
            this.oldDescriptor = oldDescriptor;
            this.newOwner = newOwner;
            this.newName = newName;
            this.newDescriptor = newDescriptor;
        }

        String key() {
            return oldOwner + "\u0000"
                + oldName + "\u0000"
                + oldDescriptor;
        }
    }

    private static final class Mapping {
        final Map<String, OwnerTarget> owners =
            new LinkedHashMap<>();
        final Map<String, MemberTarget> members =
            new LinkedHashMap<>();
    }

    private static Mapping loadMapping(Path path)
        throws IOException {
        Mapping mapping = new Mapping();
        for (String line : Files.readAllLines(
            path,
            StandardCharsets.UTF_8
        )) {
            if (line.isBlank() || line.startsWith("#")) {
                continue;
            }
            String[] p = line.split("\\t", -1);
            if (p[0].equals("O") && p.length == 5) {
                OwnerTarget row = new OwnerTarget(
                    dec(p[1]),
                    dec(p[2]),
                    dec(p[3]),
                    dec(p[4])
                );
                if (mapping.owners.put(
                    row.oldOwner,
                    row
                ) != null) {
                    throw new IllegalArgumentException(
                        "duplicate owner mapping"
                    );
                }
            } else if (p[0].equals("M") && p.length == 8) {
                MemberTarget row = new MemberTarget(
                    dec(p[1]),
                    dec(p[2]),
                    dec(p[3]),
                    dec(p[4]),
                    dec(p[5]),
                    dec(p[6]),
                    dec(p[7])
                );
                if (mapping.members.put(
                    row.key(),
                    row
                ) != null) {
                    throw new IllegalArgumentException(
                        "duplicate member mapping"
                    );
                }
            } else {
                throw new IllegalArgumentException(
                    "bad dependency source binding mapping row"
                );
            }
        }
        if (mapping.owners.isEmpty()) {
            throw new IllegalArgumentException(
                "dependency owner mapping is empty"
            );
        }
        return mapping;
    }

    private static List<Path> sources(Path root)
        throws IOException {
        try (Stream<Path> stream = Files.walk(root)) {
            return stream
                .filter(Files::isRegularFile)
                .filter(
                    path -> path.toString().endsWith(".java")
                )
                .sorted()
                .collect(Collectors.toList());
        }
    }

    private static String binaryName(
        TypeElement element,
        Elements elements
    ) {
        return elements.getBinaryName(element)
            .toString()
            .replace('.', '/');
    }

    private static TypeElement enclosingType(Element element) {
        Element current = element.getEnclosingElement();
        while (current != null) {
            if (current instanceof TypeElement) {
                return (TypeElement) current;
            }
            current = current.getEnclosingElement();
        }
        return null;
    }

    private static String typeDescriptor(
        TypeMirror raw,
        Types types,
        Elements elements
    ) {
        TypeMirror type;
        try {
            type = types.erasure(raw);
        } catch (IllegalArgumentException exc) {
            type = raw;
        }

        switch (type.getKind()) {
            case BOOLEAN: return "Z";
            case BYTE: return "B";
            case SHORT: return "S";
            case INT: return "I";
            case LONG: return "J";
            case CHAR: return "C";
            case FLOAT: return "F";
            case DOUBLE: return "D";
            case VOID: return "V";
            case ARRAY:
                return "["
                    + typeDescriptor(
                        ((ArrayType) type).getComponentType(),
                        types,
                        elements
                    );
            case DECLARED:
            case ERROR: {
                Element element =
                    ((DeclaredType) type).asElement();
                if (!(element instanceof TypeElement)) {
                    throw new IllegalArgumentException(
                        "declared type has no TypeElement"
                    );
                }
                return "L"
                    + binaryName(
                        (TypeElement) element,
                        elements
                    )
                    + ";";
            }
            default:
                throw new IllegalArgumentException(
                    "unsupported source binding type kind: "
                    + type.getKind()
                );
        }
    }

    private static String executableDescriptor(
        ExecutableElement element,
        Types types,
        Elements elements
    ) {
        StringBuilder out = new StringBuilder("(");
        for (VariableElement parameter
            : element.getParameters()) {
            out.append(
                typeDescriptor(
                    parameter.asType(),
                    types,
                    elements
                )
            );
        }
        out.append(")");
        if (
            element.getKind()
            == ElementKind.CONSTRUCTOR
        ) {
            out.append("V");
        } else {
            out.append(
                typeDescriptor(
                    element.getReturnType(),
                    types,
                    elements
                )
            );
        }
        return out.toString();
    }

    private static String rel(
        Path root,
        CompilationUnitTree unit
    ) {
        Path source = Paths.get(
            unit.getSourceFile().toUri()
        ).toAbsolutePath().normalize();
        return root.relativize(source)
            .toString()
            .replace('\\', '/');
    }

    private static final class Scanner
        extends TreePathScanner<Void, Void> {
        private final Path root;
        private final CompilationUnitTree unit;
        private final Trees trees;
        private final Types types;
        private final Elements elements;
        private final Mapping mapping;
        private final Set<String> emitted;

        Scanner(
            Path root,
            CompilationUnitTree unit,
            Trees trees,
            Types types,
            Elements elements,
            Mapping mapping,
            Set<String> emitted
        ) {
            this.root = root;
            this.unit = unit;
            this.trees = trees;
            this.types = types;
            this.elements = elements;
            this.mapping = mapping;
            this.emitted = emitted;
        }

        private void emit(
            Tree node,
            Element element,
            String syntaxKind
        ) {
            if (element == null) {
                return;
            }

            String owner;
            String name;
            String descriptor;
            String elementKind;

            if (element instanceof TypeElement) {
                TypeElement type = (TypeElement) element;
                owner = binaryName(type, elements);
                name = "";
                descriptor = "";
                elementKind = "class";
            } else if (
                element instanceof VariableElement
                && element.getKind() == ElementKind.FIELD
            ) {
                TypeElement type = enclosingType(element);
                if (type == null) {
                    return;
                }
                owner = binaryName(type, elements);
                name = element.getSimpleName().toString();
                try {
                    descriptor = typeDescriptor(
                        element.asType(),
                        types,
                        elements
                    );
                } catch (IllegalArgumentException exc) {
                    return;
                }
                elementKind = "field";
            } else if (element instanceof ExecutableElement) {
                ExecutableElement executable =
                    (ExecutableElement) element;
                TypeElement type = enclosingType(element);
                if (type == null) {
                    return;
                }
                owner = binaryName(type, elements);
                name = (
                    executable.getKind()
                    == ElementKind.CONSTRUCTOR
                )
                    ? "<init>"
                    : executable.getSimpleName().toString();
                try {
                    descriptor = executableDescriptor(
                        executable,
                        types,
                        elements
                    );
                } catch (IllegalArgumentException exc) {
                    return;
                }
                elementKind = (
                    executable.getKind()
                    == ElementKind.CONSTRUCTOR
                )
                    ? "constructor"
                    : "method";
            } else {
                return;
            }

            OwnerTarget ownerTarget =
                mapping.owners.get(owner);
            if (ownerTarget == null) {
                return;
            }

            String matchStatus;
            String mappingId = ownerTarget.ownerId;
            if (elementKind.equals("class")) {
                matchStatus = ownerTarget.classification.equals(
                    "official_replaceable"
                )
                    ? "exact_approved_class"
                    : "non_replaceable_owner";
            } else {
                MemberTarget member = mapping.members.get(
                    owner + "\u0000"
                    + name + "\u0000"
                    + descriptor
                );
                if (
                    member != null
                    && ownerTarget.classification.equals(
                        "official_replaceable"
                    )
                ) {
                    matchStatus = "exact_approved_member";
                    mappingId = member.memberId;
                } else if (
                    ownerTarget.classification.equals(
                        "official_replaceable"
                    )
                ) {
                    matchStatus =
                        "approved_owner_unmatched_member";
                } else {
                    matchStatus = "non_replaceable_owner";
                }
            }

            long start = trees.getSourcePositions()
                .getStartPosition(unit, node);
            long end = trees.getSourcePositions()
                .getEndPosition(unit, node);
            if (start < 0 || end < start) {
                return;
            }

            String key = rel(root, unit)
                + "\u0000" + start
                + "\u0000" + end
                + "\u0000" + elementKind
                + "\u0000" + owner
                + "\u0000" + name
                + "\u0000" + descriptor;
            if (!emitted.add(key)) {
                return;
            }

            System.out.println(
                "R\t" + enc(rel(root, unit))
                + "\t" + start
                + "\t" + end
                + "\t" + enc(syntaxKind)
                + "\t" + enc(elementKind)
                + "\t" + enc(owner)
                + "\t" + enc(name)
                + "\t" + enc(descriptor)
                + "\t" + enc(matchStatus)
                + "\t" + enc(mappingId)
                + "\t" + enc(ownerTarget.classification)
            );
        }

        @Override
        public Void visitIdentifier(
            IdentifierTree node,
            Void unused
        ) {
            emit(
                node,
                trees.getElement(getCurrentPath()),
                "identifier"
            );
            return super.visitIdentifier(node, unused);
        }

        @Override
        public Void visitMemberSelect(
            MemberSelectTree node,
            Void unused
        ) {
            emit(
                node,
                trees.getElement(getCurrentPath()),
                "member_select"
            );
            return super.visitMemberSelect(node, unused);
        }

        @Override
        public Void visitMemberReference(
            MemberReferenceTree node,
            Void unused
        ) {
            emit(
                node,
                trees.getElement(getCurrentPath()),
                "member_reference"
            );
            return super.visitMemberReference(node, unused);
        }

        @Override
        public Void visitNewClass(
            NewClassTree node,
            Void unused
        ) {
            emit(
                node,
                trees.getElement(getCurrentPath()),
                "new_class"
            );
            return super.visitNewClass(node, unused);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            throw new IllegalArgumentException(
                "usage: <source-root> <mapping.tsv> <classpath>"
            );
        }
        Path root = Paths.get(args[0])
            .toAbsolutePath().normalize();
        Path mappingPath = Paths.get(args[1])
            .toAbsolutePath().normalize();
        String classpath = args[2];

        Mapping mapping = loadMapping(mappingPath);
        List<Path> files = sources(root);
        if (files.isEmpty()) {
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

        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();

        try (StandardJavaFileManager manager =
            compiler.getStandardFileManager(
                diagnostics,
                Locale.ROOT,
                StandardCharsets.UTF_8
            )) {
            Iterable<? extends JavaFileObject> units =
                manager.getJavaFileObjectsFromPaths(files);
            List<String> options = Arrays.asList(
                "-proc:none",
                "-Xlint:none",
                "-classpath",
                classpath
            );
            JavacTask task = (JavacTask) compiler.getTask(
                null,
                manager,
                diagnostics,
                options,
                null,
                units
            );
            Iterable<? extends CompilationUnitTree> parsed =
                task.parse();
            try {
                task.analyze();
            } catch (RuntimeException ignored) {
                // Partial attribution is still usable. Positive bindings
                // require concrete Elements and exact JVM descriptors.
            }

            Trees trees = Trees.instance(task);
            Types types = task.getTypes();
            Elements elements = task.getElements();
            Set<String> emitted = new HashSet<>();
            for (CompilationUnitTree unit : parsed) {
                new Scanner(
                    root,
                    unit,
                    trees,
                    types,
                    elements,
                    mapping,
                    emitted
                ).scan(unit, null);
            }
        }

        long errorCount = diagnostics.getDiagnostics()
            .stream()
            .filter(
                diagnostic ->
                    diagnostic.getKind()
                    == Diagnostic.Kind.ERROR
            )
            .count();

        System.err.println(
            "SPK_BINDING_DIAGNOSTIC_ERRORS="
            + errorCount
        );
    }
}
