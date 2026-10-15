# R191 — original v309 platform enum Java, integrated with the recovered Signlink owner

Stacked on [R190 #1083](https://github.com/Trexzo/SpawnPK-Client/pull/1083), milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). CLIENT original-source restoration only; no server emulator.

## What was actually reconstructed

The original rs/k/j.class is a Java 9 enum (SHA256 **820acef9584e669760389461af78b899530a32ef1dfcd5b4c22a72b3309d995e**, 1,267 bytes). It has original JVM fields a/b/c/d (four enum values), e (detected OS), f (compiler-generated values array), and six methods. The original enum **labels** are, in order, **Windows, MacOS, Linux, Other**.

The new private original-named rs/k/j.java is real Java source with four genuine enum constants bearing those original names, four explicit obfuscated field aliases, private final detected-OS field, and original OS detection:

- Read System.getProperty("os.name","generic").toLowerCase().
- mac OR darwin -> MacOS; win -> Windows; nux -> Linux; otherwise Other.
- Preserve public static j a() returning the selected platform enum.

The original JVM method and field names were obfuscated, so a plain Java enum declaration cannot preserve both original enum string labels and the a/b/c/d enum declaration field identifiers. The aliases preserve the original outer class's field references and the readable constants preserve Enum.name()/ordinal semantics. The compiled Java class has **four extra alias fields** and eight additional getstatic/putstatic initializer operations; they are **explicitly modeled deviations**, not falsely called byte identity.

Original JVM compiler-synthetic values array f and helper b() are emitted by modern javac as $VALUES and $values(). The R191 verifier normalizes only those explicit identities plus the known original obfuscated enum field references. It checks all six original enum method bodies, the original branch/switch and exception-handler instruction targets as instruction indices (removing only the eight documented alias operations), and exact OS property and substring literal operands. StackMap representation is reported independently, not assumed identical.

## Private source evidence

- Exact original full v309 client JAR SHA256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.
- Original rs/k/j.class SHA256: 820acef9584e669760389461af78b899530a32ef1dfcd5b4c22a72b3309d995e.
- Real private platform enum Java source text SHA256: **4246c2c97e66c9b63cd2ef8af25b048f763c02c4594d18cfffc4deb086b8d43d**.
- Private original-named source ZIP SHA256: **07d1e38deebe95ede0297d08ca2922bea33c4518af22af6ffe1d1ed1ba9ecfa2**.
- Previous R190 original direction-enum source ZIP SHA256: 367c02a4e7fcc9ba9d7eb5bb99504751c6c17cd7d3eaf5717c7f2b32942dc766.
- Previous R188 original Signlink outer Java source ZIP SHA256: a7172b3aae3a794bbd5a59f6de085a7ee7b68749a117671d5cf6b47a0fcd5288.
- Five NONORIGINAL remaining declaration-only Java helper sources ZIP SHA256: **34622f7c892e77b16e555e4ec8c38ad449195c5a3994ce3c3e27c55cf6f462d1**.

## Actual integrated source-only compilation

A local JDK21 javac --release 9 -g:none -proc:none -implicit:none compilation of **three real original-semantic Java source owners** in the same isolated build completed:

1. rs/v/a.java — original Signlink outer class (all 24 original methods).
2. rs/v/a$a.java — real direction enum LEFT/RIGHT/NORMAL from R190.
3. rs/k/j.java — real platform enum Windows/MacOS/Linux/Other from R191.

Exactly five remaining external original-dependent declarations were provided as separately labeled NONORIGINAL compiler-only helpers: rs/f/a, rs/w/c and rs/secure/{a,b,c}. **No original JAR/classfile was on the compilation classpath.** The original binary was inspected only as read-only independent JVM evidence.

A fresh local `javap -p -c -v` comparison confirms all **24/24 outer JVM methods still match resolved original Code semantics**: 870 original decoded instructions, exactly 35 ldc-to-ldc_w constant-pool index width changes with referenced constants and method/field operations unchanged, and corresponding branch/exception handler destinations. This is **not** a measured whole-client build improvement.

## GitHub R191 verifier and CI

The new Python verifier SHA-pins the original JAR and all three original-class hashes, source ZIPs and five compiler-helper declarations, requires original-named source-only compilation of exactly eight Java owners, reuses R189 24-method outer Code and R190 real direction enum audits, then proves six-method OS enum semantic equality with only four explicitly mapped aliases. Synthetic unrelated Java9 tests on Ubuntu and Windows fail closed on mutated OS strings, branch rules, enum order, aliases and digests.

## What remains unverified

- The enum is **not byte-identical** to original: extra alias declarations, renamed synthetic values helper, original class metadata/StackMap encoding differences.
- Five other helper owners are still compiler-only declarations; their original member behavior and runtime remain unrecovered.
- Official private original-input R191 replay is pending, as are JVM verifier runtime tests, field annotations/optional attributes, entire original v309 client Javac closure, all game resources/network dependencies, and redistribution authorization.
- Do not commit original-derived Java or original client binary to public GitHub, mislabel helper scaffolds as original recovered classes, merge the draft as production-ready, or claim full client compilation.
