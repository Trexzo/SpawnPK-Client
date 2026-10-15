# R204 — original v309 spell definitions and spellbook modes

Client-only, original JVM-evidenced Java9 source reconstruction, stacked on [R203](https://github.com/Trexzo/SpawnPK-Client/tree/research/r203-v309-original-spellbook-filter-enum), source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Actual private original binary and independent source proof

Original v309 client JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Two NEW original Java owner source candidates:

| Original JVM owner | SHA256 original .class | Complete original methods and decoded instructions | Privately held one-source ZIP SHA256 |
| --- | --- | --- | --- |
| `rs/n/c/ap$b` | `d93b66584019f930d6d14cecd69f9611c579300df1031835211cf879cf25fc74` | **6/6; 586/586** | `4326e992898ddbf2f5a14523b11d4e03dc67a32dd4931b47636a59d7141d45f1` |
| `rs/n/c/ap$c` | `a4b10c2b2a46602227f2de4c73d1bffde8029a1c354496fa80650c3c0a770c08` | **5/5; 50/50** | `989f83eecd2c817554ff5140be0f6017a918d627d64693030795e338a12046db` |
| **Combined** | | **11 methods; 636 instructions** | |

The original spell definition `ap$b` contains **41 original Java enum name labels**, widget IDs, level requirements, and category references. Original source-named Java entries have real labels AIR_STRIKE, CONFUSE, WATER_STRIKE, etc., through BOUNTY_TELEPORT. `a(int)` performs the original widget-ID lookup and preserves its JVM loop, branch and null-return semantics. The original `ap$c` has three spellbook modes **MODERN, LUNAR, ANCIENTS**. The third source owner `ap$a` (COMBAT, TELEPORT, UTILITY) was recovered and pinned separately in R203.

All three **real Java enum source files** compile in one `javac --release 9 -g:none -proc:none -implicit:none` build with EMPTY original/external binary classpath and sourcepath. No compiler-only stub or original JAR class was supplied to `javac`. Java code was never loaded or executed.

The original classes declare 41 and 3 obfuscated enum constant fields, respectively. Java language cannot simultaneously preserve those obfuscated declaration names *and* the original `Enum.name()` strings, so the source declares genuine named constants and exposes the necessary original member IDs as **44 extra aliases**. The compiler inserts **82 + 6 = 88 extra initializer instructions** in the two rebuilt classfiles. The verifier requires those **exact** alias assignments and explicitly excludes them from original method Code parity. It checks every original selected instruction opcode, symbolic operand, branch offset, stack/local limit, access flag, exception handler, and generated enum values helper method name mapping. Only the original static initializer RETURN offset moves because of the 88 added alias writes. **These are semantically reconstructed, not byte-identical original classfiles**; binary field inventory and Java metadata differ.

The decompiled v309 private Java tree contains **`rs/interfaces/widgets/Class177.java` and `Class178.java`**, which correspond to the original spell-definition and spellbook-mode enum behavior. The decompiled `Class176.java` corresponds to the R203 original category enum. This correspondence is supported by full enumeration values, IDs and method behavior; it does **not** alone establish byte-identical class mapping, source-safe rename or permission to publish the original-derived Java. The original parent `rs/n/c/ap.java` is not yet reconstructed.

## Actual controlled whole-tree source compiler result

The R203 private **1,295-source** original-name candidate ZIP:
`cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.

The private R204 experimental **1,297-source** overlay ZIP:
`5c971fcb3c2e29bd3623ba728f6e967f41a11eafad6adb2d91b91fa56a60fe5b`.

All **1,295 prior Java file bytes are unchanged**. Only the two original-named enum Java candidates were added. No fake helper declarations or original client compiled classes were inserted.

Same JDK21.0.12.1, `javac -J-Xmx4g --release 9 -g:none -proc:none -implicit:none -Xmaxerrs 10000 -classpath EMPTY -sourcepath EMPTY`:

| Pinned tree | Java files | Actual Javac errors | Result |
| --- | ---: | ---: | --- |
| R203 prior | 1,295 | **2,358** | failed |
| R204 new enums | 1,297 | **2,358** | failed |
| Delta | +2 | **0** | still fails |

Original R203 compiler stderr SHA256: `86af8444a7a32f4e5c4e6ae3a066d77cf53a6f9c02ee30d64bc97243e8035ddc`; R204 stderr SHA256: `e52a0d38e3ea55e557928c56a7e7c658e70d714bfab04d29c113534cea97d271`.

The two new source owners do not remove other unresolved client compiler errors while their large parent remains missing, and no compiler improvement is claimed.

## Public GitHub verifier, independent negatives, remaining work

The public verifier SHA-pins the original full client JAR and both original classfiles plus three source ZIPs; builds only these three enum sources with Java9; requires exactly three emitted classfiles; and reuses strict original semantic JVM Code with explicit alias normalization. Public Ubuntu/Windows CI uses an unrelated invented 41-value enum and three-mode enum, with changed original widget ID, lookup condition, alias values, alias omission and original class SHA negative tests. No original binary or derived Java is uploaded to hosted CI.

Privately I also independently ran a JDK9 `javap -p -v` replay against original pinned classes and both reconstructed source files. **11/11 methods, 636/636 original instructions and all original instruction byte offsets (except each static initializer RETURN moved by the extra alias writes) matched.** Seven separate mutation tests on the real private candidates rejected altered original numeric IDs, level requirements, category references, lookup control flow, alias targets and enum ordering.

**Next:** reconstruct `rs/n/c/ap` original parent incrementally, validate superclass `rs/n/c` and widget `rs/n/e` source dependencies, and compare owner-level method/field ABI. The full v309 original client still has 2,358 JDK-only errors and has not been independently source-compiled, runtime-tested or licensed for redistribution. Keep R204 draft and original-derived source private.
