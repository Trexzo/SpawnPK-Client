# R79 — original v309 complete 48-op prefix source form

Read-only direct inspection of SHA-256 pinned original v309 shows the 697-instruction settings method begins with **48 instructions** before the first local Exception-protected source region. R69 already reconstructs the first 24: static preflight, File.exists early return, Properties and FileInputStream creation, load and close. R79 recovers the remaining four strict six-instruction property/static-write chains.

1. An original two-argument Properties.getProperty(String,String) with typed Boolean.parseBoolean(String) to a Boolean static field.
2. A direct original single-key getProperty, Boolean.valueOf(String), Boolean.booleanValue() static assignment.
3. A direct original single-key getProperty, Integer.valueOf(String), Integer.intValue() static assignment.
4. A second direct single-key Boolean conversion and static assignment.

The verifier checks original field declarations, exact JVM type descriptors and overloads, real String constant-pool tags, complete 48 opcode positions, direct original assignment ordering and no unexpected incoming branch into the four assignments. It **preserves** the previously verified R69 Java prefix. Output is a private Java fragment using original keys/members, with aggregate SHA/count metadata only. Java 9 synthetic source→recovered source→recompiled candidate tests and adversarial mutations are included.

On private local original-JAR storage, invoke:

    python -m spk_recovery.properties_48_prefix_source ORIGINAL_JAR PRIVATE_OWNER.class METHOD "()V" NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA256

An independent original JAR read-only JVM inspection supports the 48-op and four-write facts; **the generic R79 CLI has not yet been replayed against that original JAR**, and no complete 697-instruction Java source or original 44-handler/operand/runtime equivalence has been certified. Never publish original class identifiers, literal property keys, Java source or JAR.
## Independent original-binary Java 9 compilation witness

After locating the exact SHA-pinned original JAR in the user's private Library, a separate private Java source candidate was assembled using the original 48 JVM instruction operands, including original String keys and static-field targets. `javac --release 9` compiled the candidate. Read-only `javap -c -p` comparison of **all first 48 JVM instruction offsets, opcodes and checked String/member/field/type operands** found **zero mismatches**. This validates the bounded prefix candidate source form, not the actual generic R79 Python CLI replay, helper-body equivalence or complete method. The first method preflight helper in that temporary candidate was a stub. The original private Java source and JAR have not been uploaded.

Public-safe aggregate proof: `research/v309-source-recovery/original-48-prefix-compiled-witness-r79.json`. The synthetic R79 regression tests and future real generic-CLI private replay remain separate acceptance gates.
