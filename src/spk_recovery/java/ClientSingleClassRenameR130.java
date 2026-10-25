import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import javax.lang.model.element.Element;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/**
 * R130: one Java source-only top-level class rename using javac semantic
 * symbols; no global string replacement, no project binary dependencies.
 * Input is already staged privately. Never consumes original client bytecode.
 */
public final class ClientSingleClassRenameR130 {
    private static final class Edit {
        final int start;
        final int end;
        final String before;
        final String after;
        Edit(int start, int end, String before, String after) {
            this.start = start;
            this.end = end;
            this.before = before;
            this.after = after;
        }
    }

    private static void require(boolean value, String why) {
        if (!value) throw new IllegalStateException(why);
    }

    private static void mark(
            List<Edit> edits, String content, long start, long end,
            String oldName, String newName) {
        require(start >= 0 && end == start + oldName.length()
                && end <= content.length(), "R130_INVALID_SOURCE_SPAN");
        require(content.substring((int) start, (int) end).equals(oldName),
                "R130_SOURCE_TOKEN_DOES_NOT_MATCH_DECLARED_IDENTITY");
        edits.add(new Edit((int) start, (int) end, oldName, newName));
    }

    private static long uniqueToken(
            String text, int start, int end, Pattern pattern, String why) {
        require(start >= 0 && end > start && end <= text.length(),
                "R130_INVALID_DECLARATION_HEADER_SPAN");
        Matcher matcher = pattern.matcher(text);
        matcher.region(start, end);
        long found = -1;
        while (matcher.find()) {
            require(found < 0, why);
            found = matcher.start(1);
        }
        require(found >= 0, why);
        return found;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException(
            "R130_EXPECTED_SOURCE_ROOT_OLD_NAME_NEW_NAME_EMPTY_CLASSPATH");
        Path root = Paths.get(args[0]).toRealPath();
        String oldInternal = args[1];
        String newInternal = args[2];
        Path emptyClasspath = Paths.get(args[3]).toRealPath();
        require(Files.isDirectory(root) && Files.isDirectory(emptyClasspath),
                "R130_ISOLATED_SOURCE_AND_EMPTY_CLASSPATH_REQUIRED");
        require(!Files.isSymbolicLink(root)
                && !Files.isSymbolicLink(emptyClasspath),
                "R130_SYMLINK_SOURCE_OR_CLASSPATH_REJECTED");
        int oldSlash = oldInternal.lastIndexOf('/');
        int newSlash = newInternal.lastIndexOf('/');
        require(oldSlash > 0 && newSlash == oldSlash
                && oldInternal.substring(0, oldSlash)
                    .equals(newInternal.substring(0, newSlash)),
                "R130_ONLY_SAME_PACKAGE_CLASS_RENAME_SUPPORTED");
        String oldName = oldInternal.substring(oldSlash + 1);
        String newName = newInternal.substring(newSlash + 1);
        Path input = root.resolve(oldInternal + ".java").normalize();
        Path output = root.resolve(newInternal + ".java").normalize();
        require(input.startsWith(root) && output.startsWith(root)
                && Files.isRegularFile(input) && !Files.isSymbolicLink(input)
                && !Files.exists(output),
                "R130_EXPECTED_SINGLE_SOURCE_FILE_OR_DESTINATION_OCCUPIED");
        String text = Files.readString(input, StandardCharsets.UTF_8);
        final String oldText = text;
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        require(compiler != null, "R130_JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();
        List<Edit> edits = new ArrayList<>();

        try (StandardJavaFileManager manager =
                compiler.getStandardFileManager(
                    diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, manager, diagnostics,
                Arrays.asList("--release", "9", "-proc:none",
                              "-implicit:none", "-classpath",
                              emptyClasspath.toString(), "-sourcepath",
                              emptyClasspath.toString()),
                null, manager.getJavaFileObjects(input.toFile()));
            Iterator<? extends CompilationUnitTree> it = task.parse().iterator();
            require(it.hasNext(), "R130_SOURCE_PARSE_EMPTY");
            CompilationUnitTree unit = it.next();
            require(!it.hasNext(), "R130_MULTIPLE_UNITS_UNSUPPORTED");
            List<ClassTree> top = new ArrayList<>();
            for (Tree declaration : unit.getTypeDecls()) {
                if (declaration instanceof ClassTree) {
                    top.add((ClassTree) declaration);
                }
            }
            require(top.size() == 1 &&
                    top.get(0).getSimpleName().toString().equals(oldName) &&
                    top.get(0).getKind() == Tree.Kind.CLASS,
                    "R130_ONLY_EXACT_ONE_TOP_LEVEL_CLASS_SUPPORTED");
            String pkg = unit.getPackageName() == null ? ""
                : unit.getPackageName().toString().replace('.', '/');
            require(pkg.equals(oldInternal.substring(0, oldSlash)),
                    "R130_SOURCE_PACKAGE_DOES_NOT_MATCH_ORIGINAL_NAME");

            task.analyze();
            require(diagnostics.getDiagnostics().stream().noneMatch(
                d -> d.getKind() == Diagnostic.Kind.ERROR),
                "R130_SOURCE_SEMANTIC_ANALYSIS_FAILED");
            Trees trees = Trees.instance(task);
            SourcePositions positions = trees.getSourcePositions();
            ClassTree declaration = top.get(0);
            Element target = trees.getElement(
                TreePath.getPath(unit, declaration));
            require(target != null, "R130_TARGET_CLASS_SYMBOL_NOT_RESOLVED");

            int begin = (int) positions.getStartPosition(unit, declaration);
            int brace = text.indexOf('{', begin);
            require(brace > begin, "R130_CLASS_HEADER_NOT_FOUND");
            Pattern classToken = Pattern.compile(
                "\\bclass\\s+(" + Pattern.quote(oldName) + ")(?![\\w$])");
            long declarationToken = uniqueToken(
                text, begin, brace, classToken,
                "R130_AMBIGUOUS_OR_MISSING_CLASS_DECLARATION_TOKEN");
            mark(edits, text, declarationToken,
                 declarationToken + oldName.length(), oldName, newName);

            new TreePathScanner<Void, Void>() {
                @Override public Void visitClass(ClassTree node, Void unused) {
                    require(node == declaration,
                            "R130_NESTED_LOCAL_OR_ANONYMOUS_TYPE_UNSUPPORTED");
                    return super.visitClass(node, unused);
                }

                @Override public Void visitMethod(MethodTree node, Void unused) {
                    Element symbol = trees.getElement(getCurrentPath());
                    if (node.getReturnType() == null && symbol != null &&
                            target.equals(symbol.getEnclosingElement())) {
                        long first = positions.getStartPosition(unit, node);
                        long last = node.getBody() == null
                            ? positions.getEndPosition(unit, node)
                            : positions.getStartPosition(unit, node.getBody());
                        Pattern constructor = Pattern.compile(
                            "\\b(" + Pattern.quote(oldName)
                            + ")\\s*\\(");
                        long at = uniqueToken(
                            oldText, (int) first, (int) last, constructor,
                            "R130_AMBIGUOUS_OR_MISSING_CONSTRUCTOR_TOKEN");
                        mark(edits, oldText, at, at + oldName.length(),
                             oldName, newName);
                    }
                    return super.visitMethod(node, unused);
                }

                @Override public Void visitIdentifier(
                        IdentifierTree node, Void unused) {
                    Element symbol = trees.getElement(getCurrentPath());
                    if (target.equals(symbol)) {
                        long begin = positions.getStartPosition(unit, node);
                        long end = positions.getEndPosition(unit, node);
                        mark(edits, oldText, begin, end, oldName, newName);
                    }
                    return super.visitIdentifier(node, unused);
                }

                @Override public Void visitMemberSelect(
                        MemberSelectTree node, Void unused) {
                    Element symbol = trees.getElement(getCurrentPath());
                    if (target.equals(symbol)) {
                        long end = positions.getEndPosition(unit, node);
                        mark(edits, oldText, end - oldName.length(), end,
                             oldName, newName);
                    }
                    return super.visitMemberSelect(node, unused);
                }
            }.scan(unit, null);
        }

        edits.sort((a, b) -> Integer.compare(b.start, a.start));
        int boundary = text.length();
        for (Edit edit : edits) {
            require(edit.end <= boundary,
                    "R130_OVERLAPPING_SOURCE_SYMBOL_EDITS");
            boundary = edit.start;
            text = text.substring(0, edit.start) + edit.after
                 + text.substring(edit.end);
        }
        // Only the staged, temporary private copy is ever modified.
        Files.writeString(input, text, StandardCharsets.UTF_8);
        Files.move(input, output, StandardCopyOption.ATOMIC_MOVE);
        System.out.println("R130_AST_SOURCE_CLASS_REWRITE_PASS");
        System.out.println("source_symbol_replacements=" + edits.size());
    }
}
