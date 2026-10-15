# R203 — original v309 spellbook filter enum source evidence

Client-only original JVM source recovery, stacked on R202 research branch. The original nested enum rs/n/c/ap$a.class (SHA256 `884186742e7d92489d6634e8cb6d0012ee5e8ba71bcc272c339bed4a8a9ee7df`) has the original enum labels COMBAT, TELEPORT and UTILITY in that order, 4 original fields, 5 JVM methods and 50 decoded instructions.

A private Java9 original-named source file recompiles with the correct enum labels and three explicit final aliases a/b/c. Source-only semantic JVM audit matches all 5 original methods and 50 original instructions after field-name normalization, permitting only 6 additional getstatic/putstatic alias initialization instructions. Generated `$VALUES` and `$values` identities are compiler generated and mapped to the original d array and a() helper.

**Not original binary identity:** source has three extra alias fields and six initializer operations, and original classfile attributes differ. It is a semantic Java source candidate, not proof of original runtime or authorization to redistribute original-derived source.

Original full v309 JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Private source ZIP SHA256: `2b362652ac6a89450c080ff3c771cfd1cc7443307603e90225a42d7a464d1558`.

A controlled, byte-preserving private experimental overlay adds only rs/n/c/ap$a.java to the R202 baseline: **1,294 -> 1,295 Java files**, unchanged previous 1,294 file bytes, no fake compiler helper source. Same JDK21 `--release 9`, empty original/external classpath, JDK-only full-source Javac diagnostics **2,366 -> 2,358 errors (−8)**. New private overlay SHA256: `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.

The full spellbook-filter parent rs/n/c/ap is **not recovered**, and whole-client compilation still fails. Private official source verifier and all hosted test gates are independent; synthetic CI never receives original game binaries or source.