# R152 — original matrix static pool source reconstruction (client-only)

Stacked on R151 #1038 → R150 #1037 and milestone #1004.

## Actual private original v309 Java method reconstruction

The matrix partial Java source now has **13 original methods / 350 matching JVM instructions** as independently verified against the original 8,172-byte v309 linked matrix class. All rebuilt source was compiled using Java9 in an isolated private workspace with **no original client JAR or original classfile on the javac classpath**.

| Verified scope | Matching original instructions |
| --- | ---: |
| R150: six matrix calculation/copy/equality methods | 95 / 95 |
| R151: two non-Packet constructors, identity and zero reset | 181 / 181 |
| R152: synchronized factory / pool acquire | 31 / 31 |
| R152: synchronized instance pool release | 28 / 28 |
| R152: original static class initializer / pool capacity | 15 / 15 |
| **Recovered selected bodies** | **350 / 350** |

The private matrix pool reconstructed the original static object array, capacity 100, current pool count, synchronously guarded borrow/return and singleton instance initialization. Original JVM Code shows its release path updates the counter using pre-increment and minus one, not a naive postincrement source expression; the second form compiles to different JVM Code. The private reconstructed implementation was corrected and **both methods and static initialization** independently reproduce original instruction offsets, operation sequence, resolved member operands and constants.

Original matrix class SHA256: 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030. Full original v309 SHA256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.

## New GitHub source validation change

R152 extends the R150/R151 verifier with a **separate, explicit** class initializer opt-in flag: `--allow-class-initializer`. Only a privately SHA-pinned method selection explicitly containing `<clinit>:()V` can evaluate that initializer. Without this flag, it is rejected. Constructor selection continues to require its **separate** `--allow-constructor-methods` flag, and unselected original class members or scaffolding are never accepted.

The verifier compiles one original owner path Java source from a private ZIP using Java9, empty classpath and sourcepath, annotation processing disabled, and requires original R136 rs-game-linked binary exclusion. Each chosen source method, including an explicitly approved class initializer, is compared using fully decoded JVM Code and CP-resolved instruction operands, raw constants, stack/locals, access and exception handlers; StackMap evidence is compared separately, not silently upgraded to full Code-attribute parity. A sanitized report records selected constructor count, selected class-initializer count and only aggregate evidence.

Synthetic Ubuntu/Windows tests independently construct original Java9 linked rs.Game and ext.Matrix classes, and compile a matching stand-alone matrix pool class with **different unselected reset/constructor behavior**. They prove selected borrow/return/static init operations, reject altered pool capacity, incorrect postincrement source code, initializer selection without opt-in and constructor selection without its own opt-in. R150/R151 regression suites run in the same CI.

The recovered private source stays outside the public GitHub repo pending redistribution authorization. The 13 selected method bodies are an actual partial original Java tree, but **the whole matrix class remains unfinished**. Its Packet-dependent constructor, matrix rotations/composition and other routines are not accepted; original member names and mappings remain private. The full v309 Java source compilation still has the previously independently observed **516 errors**. We cannot claim that 350 matching instructions imply the whole original owner is compilable or source-equivalent.
