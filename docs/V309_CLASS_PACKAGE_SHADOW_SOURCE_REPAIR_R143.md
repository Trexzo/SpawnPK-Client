# R143 — source repair for JVM class/package shadows

R125 fixes two distinct **JVM-valid but Java-source-invalid** constructs: same-directory casefolded class names (suffix `__Case_`) and a class whose binary identity is also a package directory for another class (suffix `__Type_`). R141 handled only the former. R143 extends the same fail-closed JDK Javac AST source rewrite to the second verified class-leaf rename, provided the package stays unchanged and R125's exact original-to-remapped type identity proves the `java_class_package_shadow` reason.

The safety boundary is unchanged: exactly one eligible nonstatic imported class per source file, AST-proven import and type-identifier positions, rejection of expression/static receiver uses, source local type/parameter shadowing, multiple renamed imports or extra fully qualified source references. Any ambiguous source file stays byte-for-byte unchanged. No guessing member names or altering original `rs/` binaries.

## Real original-v309 offline evidence, October 14, 2026

An **independent private Python/JDK replay**, using separately hash-verified original source/JAR, reproduced R136's exact **10,502 original classes / 1,159 `rs/` / 9,343 other / eight game-linked non-`rs` / 9,335 provisional non-`rs`** partition. It independently implemented R125's deterministic namespace rules and produced 2,341 legal class remaps, then remapped those non-`rs` original classfiles with JDK's ASM `ClassRemapper` into one **private and uncertified** diagnostic classpath.

The same JDK 21 compiler, `--release 11 -proc:none -implicit:none -Xmaxerrs 3000`, unchanged provisional classpath digest `59faaf22c068e2d085d904747c96cb863e76ae4ee9c7e76914b4d5c0807e18de`, identical 1,271-source-file coverage, and clean sourcepath were used for all three diagnostic javac runs:

| Actual original-derived private source stage | javac errors | Cannot resolve symbol | Package missing | Other |
| --- | ---: | ---: | ---: | ---: |
| Unmodified 1,271 Java files | **625** | 518 | 60 | 47 |
| 27 JDK-AST class-casefold import/type repairs | **534** | 430 | 60 | 44 |
| Plus 4 JDK-AST class/package-shadow import/type repairs | **524** | 420 | 60 | 44 |

All counts are untruncated; **101 observed compiler errors fewer** without any original `rs/` classfile fallback. Between original and final stages **31 Java files, 31 explicit imports, 67 syntactically proven type identifier occurrences** changed; 1,240 Java files remained unchanged. The additional shadow source pass screened 9 imports across seven affected Java files: four files safely changed, one withheld for multiple remapped imports, two withheld for unsupported AST use. These were private source-preview edits only; no raw source, identifier maps, JARs, compiler paths, caches, account state or original assets enter GitHub.

**Strict caveat:** this was an *independent local reproduction*, not the exact repository R137/R138/R139/R140/R141/R142 CLI replay. Its JDK internal ASM emitted a private classpath that has not been proven **byte-identical** to R138's remapper. The historical 614-error result was from yet another **unnormalized** diagnostic classpath and is not comparable. R143's full real private CLI remains unverified until that exact replay. Both original client ZIP hashes were checked independently: original v309 JAR `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, source ZIP `2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536`.

The remaining 524 errors still include many unresolved source types and annotation-generated constructors (notably Lombok; also a Gson API source dependency). Some candidate loot-tracker Java may be postoriginal; do not add guessed stubs or arbitrarily adopt dependencies as original. Source-to-original class/member semantics, exact third-party provenance, full compilability, isolated runtime behavior, and source publication rights all remain outstanding.

## Synthetic CI

Cross-platform tests separately compile original Java9 classes `lib/node.class` and `lib/node/Child.class` in isolated folders, plus one original `rs/Game.class`. The R138 normalized provisional classpath and R143-edited source must pass real Java11 javac whereas the original unedited Java source fails. R142's three-stage source compiler also must show improvement from this **additional R143 shadow repair**. Negative cases prove ambiguous static receiver and extra qualified uses are withheld. R141 and R142 regression suites must remain passing on Ubuntu and Windows.

**Full milestone remains [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004): `recovered-source/v309/src/` as complete original-evidenced, independently compilable client Java; this repair is not that completion.**
