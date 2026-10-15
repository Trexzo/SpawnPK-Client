# R185 — original v309 Signlink Java selected-source recovery (16/24 methods)

Client-only continuation of [R184 #1077](https://github.com/Trexzo/SpawnPK-Client/pull/1077), milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). This work intentionally does not claim original full-class recovery.

## Private original bytecode/source evidence

- SHA-pinned original full v309 JAR: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
- Original rs/v/a.class SHA256: d0dc35deddc8016c3fdcaf2615810efa200c042120b83bed86cad5d04b1c0ddc
- Original Java version 9 (major 53); Java rebuilt with JDK21 --release 9 -g:none -proc:none -implicit:none, empty original/external compiler classpath.
- The 11 previously selected method bodies from R184 still match **147/147** original JVM instructions.
- Five newly reconstructed original-Java method bodies:

| New original method | Matching original JVM instructions |
| --- | ---: |
| c(String):DataInputStream, stream request | 19/19 |
| a():void, cache-file initialization | 29/29 |
| a(InetAddress):void, worker initialization | 45/45 |
| f(String):int, persisted identifier read | 54/54 |
| c():String, network-interface hardware identifier | 62/62 |
| Newly matched | **209/209** |
| Combined 16 selected original methods | **356/356** |

Local selected-method comparison checked the original and rebuilt Java9 instruction offsets, opcodes, operands and symbolic owner/member references using javap; original invokedynamic string recipes and exception handler boundaries were examined. The network-interface implementation initially produced ldc_w instead of original ldc due to constant pool ordering. Moving the method earlier in the private Java declaration order restored original bytecode offsets and instruction sizes.

## Private source identity

- Previous pinned 6-method partial Java ZIP SHA: 28ffe7d1b1e29f5d6e6466684423548d233ebdb7d498d7666aa6f6ea2c3371ad
- Previous pinned 11-method partial Java ZIP SHA: 3872fd5e21a3049ad5bdb6a0686937fedb35c869a79772fff89918918b968907
- New private 16-method original-named Java source text SHA256: dbdf9d383bb4bb9ae169aa883f8e7f98dabacbbad8e0826c21286544c2320dd4
- Private 16-method Java source ZIP SHA256: 69c989c677d3032b3d79c5a15f56cb486dd13d9b4863b0dba6d9a0960bbafd68

The new public GitHub R185 verifier SHA-pins the original JAR and all three private Java ZIPs, REQUIRES R183→R184 prior acceptance, compiles the new exact owner with only JDK Java9 source and checks all 16 selected original JVM Code streams via strict original/source bytecode comparison (CP-normalized symbolic references, indy constants, stack limits and handlers).

## Critical boundaries

The original class has **24 JVM methods**. Eight are still unverified, including complex run(), complete static initializer, platform helpers and cache/network methods. The expanded partial private class retains a compiler-only unverified no-argument f() and run() implementation. Some newly verified selected methods call an unverified method, so full method call-closure and runtime behavior are NOT accepted. Its field declarations, full method-level exception/annotation attributes, original nested types and runtime I/O safety are NOT certified.

**Do not publish or add this partial original-class Java file to canonical recovered-source/v309/src.** The recovery is method-level only. No original game code is run in tests. Source redistribution rights, original full runtime and whole-client compilation remain unverified. The last reported complete-client JDK-only javac frontier is unchanged; the private source-tree candidate is not modified by R185.

Synthetic Ubuntu/Windows CI uses separately invented Java9 classfiles for staged 6→11→16 verification, intentional old/new method mutations, wrong SHA/count failures and unverified run placeholder acceptance checks. Public CI never receives original client JAR or Java source.

Next priority: reconstruct the final 8 JVM methods and complete class dependency/field/initialization metadata before original-source-tree integration. Maintain isolation from production game networking during future runtime tests.
