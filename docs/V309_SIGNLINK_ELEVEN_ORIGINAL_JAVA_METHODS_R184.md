# R184 — original v309 Signlink/bridge eleven Java method bodies

Client-only continuation of [R183 #1076](https://github.com/Trexzo/SpawnPK-Client/pull/1076), milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). This PR does not recover the entire original Signlink class.

## Private original-source evidence

Exact original full v309 JAR SHA256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.
Original rs/v/a.class SHA256: d0dc35deddc8016c3fdcaf2615810efa200c042120b83bed86cad5d04b1c0ddc.

One private original-named rs/v/a.java candidate now contains 11 selected independently recompiled original-method implementations, preserving the six from R183 and adding five new source-only Java9 implementations.

| Newly recovered method | Original decoded JVM instructions matched |
| --- | ---: |
| a(int):Socket | 18/18 |
| a(byte[],int):boolean | 26/26 |
| b(byte[],int):void | 23/23 |
| synchronized h():boolean | 13/13 |
| e(String):void | 5/5 |
| Total newly recovered | **85/85** |
| Prior R183 | 62/62 |
| Combined 11 methods | **147/147** |

The original version uses Java9 invokedynamic StringConcatFactory recipes for sound, jingle and error strings. A local javac --release 9 -g:none -proc:none -implicit:none build with empty original and external classpath reproduced the selected methods' instruction offsets, operations and resolved member references. Dynamic string concat recipes were checked in javap -verbose. The exact original exception handler ranges for a(int) also matched.

Important distinction: the recompiled a(int) Java declaration includes a Java-level throws IOException annotation to compile the original-ordered throw instructions, whereas the original method's optional Exceptions classfile attribute differs. R184 certifies selected JVM **Code**, access flags, and method identities, not *all* non-Code attributes. The partial source still has an intentionally unverified run() placeholder and incomplete original field declarations.

Private 11-method original-name source text SHA256: 00780b6e4968048efb065936d435d9a14707473a053e666851761c1a662aff95.
Private source ZIP SHA256: 3872fd5e21a3049ad5bdb6a0686937fedb35c869a79772fff89918918b968907.
Prior R183 partial source ZIP SHA256: 28ffe7d1b1e29f5d6e6466684423548d233ebdb7d498d7666aa6f6ea2c3371ad.

## GitHub source-verification gate

The new verifier requires exact SHA-pinned original class/JAR, previous 6-method source ZIP, and new 11-method source ZIP. It invokes the R183 original-six verifier first, recompiles the new source in a completely isolated Java9 build, checks class owner, superclass, access, release and interfaces, then uses R150 strict opcode, offsets, resolved member references, invokedynamic bootstrap recipes, stack limits and exception handlers across 11 selected original JVM methods.

It is partial-method acceptance only: original rs/v/a has 24 ordinary JVM methods in total. **13 original method bodies remain**, in addition to complete field/initializer/runtime attribute acceptance. Full class, network behavior, source-tree canonicalization, independent whole-v309 client build and derived-source publication rights are NOT claimed.

Synthetic Ubuntu/Windows tests use separately authored original-unrelated Java fixture classes, deliberately mutated selected methods, deliberately changed unselected placeholder method, wrong SHAs, counts and source names. No original derived Java or original binary enters hosted CI.

## Next

Recover the remaining 13 original rs/v/a methods and full field/initializer metadata with individually pinned Java source. Keep partial source OUT of recovered-source/v309/src until the entire class and dependencies have independently accepted. Then merge with original Packet and ISAAC source candidate and remeasure identical full-client javac inputs. R184 does not change previously reported full-source compiler errors.
