# R130 — one private Java source class remapped safely by AST, then replayed through R129

The main recovery goal is a complete, standalone, deobfuscated **Java client source tree** at `recovered-source/v309/src/`. R127 and R128 yield original-v309 class-alignment **review candidates**, not automatically accepted class identities. R129 separately compiles restored private Java9 source and compares its classfile/method evidence against the SHA-pinned original. The practical missing link is transforming a reviewed Java source class from its readable name into the original JVM owner name **without corrupting constructors, type references, comments or constant literals**.

R130 implements a deliberately **narrow, fail-closed** version of this: only one Java class source file, only a **same-package top-level class** rename, no nested/local/anonymous classes, no unresolved compiler symbols and no project binary dependencies. It does not support whole-package moves, multiple source units, imports from other recovered classes, speculative class identity assignment or automatic derivation of mappings from heuristic R127/R128 matches. Those cases must remain unmodified until more extensive source-aware proof exists.

## Private workflow

```text
python -m spk_recovery.private_single_class_ast_rename_r130 \
  PRIVATE_STANDALONE_SOURCE_ROOT NEW_PRIVATE_REWRITTEN_SOURCE_DIR \
  --old-java-owner rs/Readable --new-original-owner rs/Obfuscated \
  --source-sha256 SHA256_OF_EXACT_ORIGINAL_Java_FILE
```

The input is a real private folder with exactly one Java source at `rs/Readable.java`. The destination must not exist. The tool records an exact SHA pin and stages a temporary copy. It compiles the trusted `ClientSingleClassRenameR130.java` parser, which runs JDK `JavacTask.parse()` **and** `JavacTask.analyze()` using an empty `-classpath` and `-sourcepath`. It refuses missing or multiple class declarations, unresolved symbols, changed source identities and any unsupported nested/local classes. The class name declaration, constructor names and every Java AST identifier/member-select bound to that exact top-level `TypeElement` are rewritten by source-span edits, in reverse offset order, on **only** the staged source copy.

The Java source file is moved to the new owner filename. A fresh independent `javac --release 9 -g:none -proc:none -classpath EMPTY -sourcepath EMPTY` must compile the renamed Java file into `rs/Obfuscated.class`; otherwise the private publication fails. The transient compiler classes are discarded, and only the rewritten private `.java` plus sanitized counts/hashes are promoted. Original client JAR and binary classes are **never** supplied to the AST analyzer or source compiler. No user source is committed to GitHub.

Next, feed `NEW_PRIVATE_REWRITTEN_SOURCE_DIR/src` into **R129**, along with the separately SHA-pinned original v309 client JAR and chosen original `.class` entry. R129 can now independently compare source-compiled headers, fields, methods, frames and operands. Both R130 and R129 remain bounded research gates; even if the full method matrix matches, neither asserts authorial source identity, whole-client rebuild, external dependencies or runtime equivalence.

## Tests and limitations

Synthetic Ubuntu/Windows tests genuinely compile a renamed Java source class with explicit constructor, factory method, typed parameter and return types. They verify symbol resolution changes exactly those identifiers, **does not replace the former class name appearing in a string literal or comment**, and subsequently chains the revised source through R129 to compare against an independently Java9-compiled reference JVM class. Additional tests reject wrong SHA, wrong source filename, multiple source files, cross-package moves, invalid source semantics and existing destination.

**No actual decompiled SpawnPK Java or original client JAR enters hosted CI.** The public GitHub branch contains only reusable tools, synthetic fixtures, and sanitized research documentation. The release remains blocked under [issue #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004) until the **entire** client source tree independently compiles and meets original identity, bytecode, runtime and release-rights gates.
