# R190 — recover v309 Signlink nested direction enum and compile with real outer Java

Original-client source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). Stacked on R189 PR #1082. This recovers another **real Java source owner** used by the original v309 client, replacing one of seven R188/R189 declaration-only compiler helpers with a working Java enum.

## Exact original binary source evidence

- Original v309 client JAR SHA-256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.
- Original rs/v/a$a.class SHA-256: b93d684eef2b78751121637f1a3175ea7d5dc6d26cf7aea933b9ac9b1a773e3c (795 bytes, Java major 53).
- Original nested class: final three-value enum rs/v/a$a extends java/lang/Enum, 4 fields, 5 methods, original constant labels **LEFT**, **RIGHT**, **NORMAL**, in that ordinal order.
- Obfuscated enum **field identifiers** in original class: a, b, c, with private synthetic enum array d and private helper method a(). The original outer rs/v/a.run() checks the obfuscated a and b references when setting left/right pan.
- Exact previous private R188 full original-named outer Java source ZIP: a7172b3aae3a794bbd5a59f6de085a7ee7b68749a117671d5cf6b47a0fcd5288.
- Exact new private R190 original-named enum Java source ZIP SHA-256: **367c02a4e7fcc9ba9d7eb5bb99504751c6c17cd7d3eaf5717c7f2b32942dc766** (source text SHA-256 4127bad45575bb6e061eb0f811231cf3d41681444ba4851c7937159f56a99f63).

## Why Java requires explicit aliases

Java does NOT permit specifying an enum constant's Java field name `a` while independently giving `Enum.name()` the original literal LEFT. Therefore the semantically recovered source declares genuine enum constants `LEFT`, `RIGHT`, `NORMAL` and publishes **a=LEFT, b=RIGHT, c=NORMAL** as final aliases. That preserves both the original enum name/ordinal semantics and the obfuscated field references used by the outer class.

A normal JDK21 compiler with `--release 9` emits synthetic `$VALUES` and `$values()`, not the original binary's obfuscated `d` and `a()`. The new R190 audit maps only these compiler-generated identities and requires exactly three expected alias field initializers; all five original enum JVM method bodies must match the mapped original bytecode except those six extra alias getstatic/putstatic instructions.

**Not byte-identical:** The rebuilt enum class has 7 fields, not the original 4; lacks the original InnerClasses attribute since the reconstructed class is a top-level `a$a` Java source file; and its static initializer includes three alias writes. No exact enum ABI/classfile identity is claimed. This is a **source-compilable semantic reconstruction**, not a proprietary original source dump.

## Real local integrated compilation evidence

I compiled the SHA-pinned private R188 original-named rs/v/a.java together with the new real rs/v/a$a.java enum, plus precisely six clearly NONORIGINAL declaration-only helpers for rs/f/a, rs/k/j, rs/secure/a, rs/secure/b, rs/secure/c, rs/w/c. Command uses `javac --release 9 -g:none -proc:none -implicit:none`, empty original/external binary classpath, and emits all 8 expected sources. No original binary is loaded for compilation or execution.

A local independent `javap -p -c -v` comparison found that the **24 outer rs/v/a JVM methods still match semantically**, 870 decoded original instructions including 35 unchanged-value ldc-to-ldc_w width encodings. Original field declarations, method ABI, branch/exception handler destinations and resolved constant values match. This is the same bounded R189 semantic identity, now with the original enum's correct runtime type and labels instead of a dummy helper.

The new public R190 verifier SHA-pins original v309 JAR and both original classfile hashes, original-named outer-source ZIP, original-named new enum-source ZIP and the six remaining helper declarations. It recompiles the eight owners source-only, verifies the enum's original mapped five-method Code and three aliases, then reuses the R189 24-method whole-owner semantic audit. Hosted CI uses only invented unrelated Java9 fixture enums and negative mutations, not original game Java or binaries.

## Important exclusions

- All original rs/v/a member Code semantics are accepted only modulo the 35 explicitly documented width differences; no exact classfile byte parity or StackMap verification asserted.
- The enum's public field aliases, extra writes and missing InnerClasses attribute are explicit deviations from original binary structure.
- The other six supporting Java classes are still **fake compiler-only declarations**, not recovered original code.
- The complete v309 client is NOT compiled; compiler-error reduction is NOT measured by this branch.
- Original production client, network/audio runtime, source redistribution rights, cross-version v308/v309 parity and official GitHub private-input runner replay remain unverified.
- **Keep draft** until private source proof is replayed on pinned inputs, CI passes and dependency source closure is measured.

Next restore another six dependency owners with original JVM Code, validate actual static enum alias interoperability in a non-networked isolated local test, and integrate the real recovered source into the next private canonical v309 tree candidate. Do NOT insert the old declaration-only helpers as original recovered code.
