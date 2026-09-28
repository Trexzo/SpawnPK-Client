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

public final class DependencySourceOverlay {
    private static final Base64.Decoder B64 = Base64.getUrlDecoder();

    private static String dec(String value) {
        int rem = value.length() % 4;
        if (rem != 0) {
            value += "=".repeat(4 - rem);
        }
        return new String(B64.decode(value), StandardCharsets.UTF_8);
    }

    private static final class Target {
        final String bindingId;
        final String sourceFile;
        final long start;
        final long end;
        final String action;
        final String elementKind;
        final String oldOwner;
        final String oldName;
        final String oldDescriptor;
        final String newText;
        boolean found = false;

        Target(
            String bindingId,
            String sourceFile,
            long start,
            long end,
            String action,
            String elementKind,
            String oldOwner,
            String oldName,
            String oldDescriptor,
            String newText
        ) {
            this.bindingId = bindingId;
            this.sourceFile = sourceFile;
            this.start = start;
            this.end = end;
            this.action = action;
            this.elementKind = elementKind;
            this.oldOwner = oldOwner;
            this.oldName = oldName;
            this.oldDescriptor = oldDescriptor;
            this.newText = newText;
        }

        String key() {
            return sourceFile + "\u0000"
                + start + "\u0000"
                + end + "\u0000"
                + elementKind;
        }
    }

    private static final class Replacement {
        final int start;
        final int end;
        final String oldText;
        final String newText;
        final String bindingId;

        Replacement(
            int start,
            int end,
            String oldText,
            String newText,
            String bindingId
        ) {
            this.start = start;
            this.end = end;
            this.oldText = oldText;
            this.newText = newText;
            this.bindingId = bindingId;
        }
    }

    private static final class Analysis {
        final int errorCount;
        final boolean analysisException;

        Analysis(
            int errorCount,
            boolean analysisException
        ) {
            this.errorCount = errorCount;
            this.analysisException = analysisException;
        }
    }

    private static Map<String, Target> loadTargets(Path path)
        throws IOException {
        Map<String, Target> out = new LinkedHashMap<>();
        for (String line : Files.readAllLines(
            path,
            StandardCharsets.UTF_8
        )) {
            if (line.isBlank() || line.startsWith("#")) {
                continue;
            }
            String[] p = line.split("\\t", -1);
            if (p.length != 11 || !p[0].equals("E")) {
                throw new IllegalArgumentException(
                    "bad dependency source overlay target row"
                );
            }
            Target target = new Target(
                dec(p[1]),
                dec(p[2]),
                Long.parseLong(p[3]),
                Long.parseLong(p[4]),
                dec(p[5]),
                dec(p[6]),
                dec(p[7]),
                dec(p[8]),
                dec(p[9]),
                dec(p[10])
            );
            if (
                !target.action.equals(
                    "class_type_rename_required"
                )
                && !target.action.equals(
                    "member_name_rename_required"
                )
            ) {
                throw new IllegalArgumentException(
                    "unsupported direct edit action"
                );
            }
            if (out.put(target.key(), target) != null) {
                throw new IllegalArgumentException(
                    "duplicate dependency source edit target"
                );
            }
        }
        return out;
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

    private static String relative(
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

    private static String binaryName(
        TypeElement element,
        Elements elements
    ) {
        return elements.getBinaryName(element)
            .toString()
            .replace('.', '/');
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
                    "unsupported overlay type kind: "
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
        if (element.getKind() == ElementKind.CONSTRUCTOR) {
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

    private static String[] identity(
        Element element,
        Types types,
        Elements elements
    ) {
        if (element instanceof TypeElement) {
            return new String[] {
                "class",
                binaryName(
                    (TypeElement) element,
                    elements
                ),
                "",
                "",
            };
        }
        if (
            element instanceof VariableElement
            && element.getKind() == ElementKind.FIELD
        ) {
            TypeElement owner = enclosingType(element);
            if (owner == null) {
                return null;
            }
            try {
                return new String[] {
                    "field",
                    binaryName(owner, elements),
                    element.getSimpleName().toString(),
                    typeDescriptor(
                        element.asType(),
                        types,
                        elements
                    ),
                };
            } catch (IllegalArgumentException exc) {
                return null;
            }
        }
        if (element instanceof ExecutableElement) {
            ExecutableElement executable =
                (ExecutableElement) element;
            TypeElement owner = enclosingType(element);
            if (owner == null) {
                return null;
            }
            try {
                return new String[] {
                    executable.getKind()
                        == ElementKind.CONSTRUCTOR
                        ? "constructor"
                        : "method",
                    binaryName(owner, elements),
                    executable.getKind()
                        == ElementKind.CONSTRUCTOR
                        ? "<init>"
                        : executable.getSimpleName().toString(),
                    executableDescriptor(
                        executable,
                        types,
                        elements
                    ),
                };
            } catch (IllegalArgumentException exc) {
                return null;
            }
        }
        return null;
    }

    private static int terminalNameStart(
        String source,
        int start,
        int end,
        String name
    ) {
        int cursor = Math.min(end, source.length());
        while (cursor >= start + name.length()) {
            int hit = source.lastIndexOf(name, cursor - 1);
            if (hit < start) {
                break;
            }
            int after = hit + name.length();
            boolean leftOk = hit == 0
                || !Character.isJavaIdentifierPart(
                    source.charAt(hit - 1)
                );
            boolean rightOk = after >= source.length()
                || !Character.isJavaIdentifierPart(
                    source.charAt(after)
                );
            if (leftOk && rightOk && after <= end) {
                return hit;
            }
            cursor = hit;
        }
        return -1;
    }

    private static Analysis analyzeAndCollect(
        Path root,
        String classpath,
        Map<String, Target> targets,
        Map<String, List<Replacement>> replacements,
        boolean collect
    ) throws Exception {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException(
                "system Java compiler unavailable"
            );
        }
        List<Path> files = sources(root);
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();
        boolean analysisException = false;

        try (StandardJavaFileManager manager =
            compiler.getStandardFileManager(
                diagnostics,
                Locale.ROOT,
                StandardCharsets.UTF_8
            )) {
            Iterable<? extends JavaFileObject> units =
                manager.getJavaFileObjectsFromPaths(files);
            JavacTask task = (JavacTask) compiler.getTask(
                null,
                manager,
                diagnostics,
                Arrays.asList(
                    "-proc:none",
                    "-Xlint:none",
                    "-classpath",
                    classpath
                ),
                null,
                units
            );
            Iterable<? extends CompilationUnitTree> parsed =
                task.parse();
            try {
                task.analyze();
            } catch (RuntimeException exc) {
                analysisException = true;
            }

            if (collect) {
                Trees trees = Trees.instance(task);
                Types types = task.getTypes();
                Elements elements = task.getElements();

                for (CompilationUnitTree unit : parsed) {
                    String rel = relative(root, unit);
                    Path file = root.resolve(rel);
                    String source = Files.readString(
                        file,
                        StandardCharsets.UTF_8
                    );

                    new TreePathScanner<Void, Void>() {
                        private void inspect(Tree node) {
                            long start = trees.getSourcePositions()
                                .getStartPosition(unit, node);
                            long end = trees.getSourcePositions()
                                .getEndPosition(unit, node);
                            if (start < 0 || end < start) {
                                return;
                            }

                            Element element = trees.getElement(
                                getCurrentPath()
                            );
                            if (element == null) {
                                return;
                            }
                            String[] identity = identity(
                                element,
                                types,
                                elements
                            );
                            if (identity == null) {
                                return;
                            }

                            String key = rel
                                + "\u0000" + start
                                + "\u0000" + end
                                + "\u0000" + identity[0];
                            Target target = targets.get(key);
                            if (target == null) {
                                return;
                            }
                            if (target.found) {
                                throw new IllegalStateException(
                                    target.bindingId
                                    + ": edit target resolved more than once"
                                );
                            }
                            if (
                                !identity[1].equals(target.oldOwner)
                                || !identity[2].equals(target.oldName)
                                || !identity[3].equals(
                                    target.oldDescriptor
                                )
                            ) {
                                throw new IllegalStateException(
                                    target.bindingId
                                    + ": semantic source identity drift"
                                );
                            }

                            int editStart;
                            int editEnd;
                            if (
                                target.action.equals(
                                    "class_type_rename_required"
                                )
                            ) {
                                if (!identity[0].equals("class")) {
                                    throw new IllegalStateException(
                                        target.bindingId
                                        + ": class edit is not a TypeElement"
                                    );
                                }
                                editStart = (int) start;
                                editEnd = (int) end;
                            } else {
                                if (
                                    !identity[0].equals("field")
                                    && !identity[0].equals("method")
                                ) {
                                    throw new IllegalStateException(
                                        target.bindingId
                                        + ": member edit is not field/method"
                                    );
                                }
                                editStart = terminalNameStart(
                                    source,
                                    (int) start,
                                    (int) end,
                                    target.oldName
                                );
                                if (editStart < 0) {
                                    throw new IllegalStateException(
                                        target.bindingId
                                        + ": terminal member token not found"
                                    );
                                }
                                editEnd = (
                                    editStart
                                    + target.oldName.length()
                                );
                            }

                            String oldText = source.substring(
                                editStart,
                                editEnd
                            );
                            replacements.computeIfAbsent(
                                rel,
                                ignored -> new ArrayList<>()
                            ).add(
                                new Replacement(
                                    editStart,
                                    editEnd,
                                    oldText,
                                    target.newText,
                                    target.bindingId
                                )
                            );
                            target.found = true;
                        }

                        @Override
                        public Void visitIdentifier(
                            IdentifierTree node,
                            Void unused
                        ) {
                            inspect(node);
                            return super.visitIdentifier(
                                node,
                                unused
                            );
                        }

                        @Override
                        public Void visitMemberSelect(
                            MemberSelectTree node,
                            Void unused
                        ) {
                            inspect(node);
                            return super.visitMemberSelect(
                                node,
                                unused
                            );
                        }

                        @Override
                        public Void visitMemberReference(
                            MemberReferenceTree node,
                            Void unused
                        ) {
                            inspect(node);
                            return super.visitMemberReference(
                                node,
                                unused
                            );
                        }
                    }.scan(unit, null);
                }
            }
        }

        int errorCount = (int) diagnostics.getDiagnostics()
            .stream()
            .filter(
                diagnostic ->
                    diagnostic.getKind()
                    == Diagnostic.Kind.ERROR
            )
            .count();

        return new Analysis(
            errorCount,
            analysisException
        );
    }

    private static int apply(
        Path root,
        Map<String, List<Replacement>> replacements
    ) throws IOException {
        int count = 0;
        for (
            Map.Entry<String, List<Replacement>> row
            : replacements.entrySet()
        ) {
            Path file = root.resolve(row.getKey());
            String source = Files.readString(
                file,
                StandardCharsets.UTF_8
            );
            List<Replacement> edits = row.getValue();
            edits.sort(
                Comparator.comparingInt(
                    (Replacement item) -> item.start
                ).thenComparingInt(item -> item.end)
            );

            int previousEnd = -1;
            for (Replacement edit : edits) {
                if (edit.start < previousEnd) {
                    throw new IllegalStateException(
                        "overlapping dependency source edits in "
                        + row.getKey()
                    );
                }
                previousEnd = edit.end;
            }

            StringBuilder out = new StringBuilder(source);
            ListIterator<Replacement> iterator =
                edits.listIterator(edits.size());
            while (iterator.hasPrevious()) {
                Replacement edit = iterator.previous();
                String current = out.substring(
                    edit.start,
                    edit.end
                );
                if (!current.equals(edit.oldText)) {
                    throw new IllegalStateException(
                        edit.bindingId
                        + ": stale source edit span"
                    );
                }
                out.replace(
                    edit.start,
                    edit.end,
                    edit.newText
                );
                count++;
            }
            Files.writeString(
                file,
                out.toString(),
                StandardCharsets.UTF_8
            );
        }
        return count;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            throw new IllegalArgumentException(
                "usage: <source-root> <targets.tsv> "
                + "<pre-classpath> <post-classpath>"
            );
        }
        Path root = Paths.get(args[0])
            .toAbsolutePath().normalize();
        Map<String, Target> targets = loadTargets(
            Paths.get(args[1]).toAbsolutePath().normalize()
        );

        Map<String, List<Replacement>> replacements =
            new LinkedHashMap<>();
        Analysis before = analyzeAndCollect(
            root,
            args[2],
            targets,
            replacements,
            true
        );

        for (Target target : targets.values()) {
            if (!target.found) {
                throw new IllegalStateException(
                    target.bindingId
                    + ": planned dependency edit target was not resolved"
                );
            }
        }

        int editCount = apply(root, replacements);
        if (editCount != targets.size()) {
            throw new IllegalStateException(
                "applied edit count does not match planned target count"
            );
        }

        Analysis after = analyzeAndCollect(
            root,
            args[3],
            Collections.emptyMap(),
            new LinkedHashMap<>(),
            false
        );
        if (after.analysisException) {
            throw new IllegalStateException(
                "post-overlay javac analysis raised an exception"
            );
        }
        if (
            before.errorCount == 0
            && after.errorCount != 0
        ) {
            throw new IllegalStateException(
                "compile-clean input gained javac errors after overlay"
            );
        }

        System.out.println(
            "SPK_DEPENDENCY_SOURCE_OVERLAY_PASS"
        );
        System.out.println(
            "planned_edits=" + targets.size()
        );
        System.out.println(
            "applied_edits=" + editCount
        );
        System.out.println(
            "files_changed=" + replacements.size()
        );
        System.out.println(
            "pre_diagnostic_errors=" + before.errorCount
        );
        System.out.println(
            "post_diagnostic_errors=" + after.errorCount
        );
    }
}
