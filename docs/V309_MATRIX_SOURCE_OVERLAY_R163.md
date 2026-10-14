# R163 — private v309 source tree with recovered original matrix Java

Client-only; stacked on R162 #1053, milestone #1004.

The SHA-pinned preliminary client archive has **1,271 Java sources**, all with unique casefold paths. It did NOT contain the original com/a/b/a/b.java source. The independent R162 reconstruction has now compiled all **24 of 24** original matrix methods with **3,780/3,780** matching decoded JVM instructions, without an original game binary on the compiler classpath.

R163 creates a PRIVATE recovered-source/v309/src/ candidate by preserving all 1,271 preliminary Java files **byte-for-byte** and adding exactly one verified original matrix Java owner. The result has **1,272 Java files** and contains NONE of the five provisional source-only Packet/maths helper implementations. These helper bodies are not accepted original source.

Exact private source SHA-256 records:
- Preliminary original client source ZIP: 2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536
- Full original v309 JAR: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
- Full recovered matrix Java ZIP: fd2c330c8cdadb5c5f5c8640e624b566395eca589386a272933cc04da93a56
- Matrix Java file bytes: 5216a40c8e996fb9b6975d568a39ef800c6dcc48409a39506aa6087fdf21fda5
- New PRIVATE 1,272-source candidate ZIP: e4832383e0484af0b5e73f403f4740d8ad5fc8aeee4ad574a97b0c6cb589d66a
- Original 1,271-file content-tree SHA: adbfe3c75c11c95070df9615b592a852e964867e4479988f6244fef1253f6229

GitHub R163's private overlay tool first requires an exact R162 original-JAR-versus-Java compiler proof, including full original matrix field/method ABI, 24 methods, 3,780 instructions, original call closure and SHA checks. Only then does it create the fresh private source-tree ZIP. It fails on overwrite, conflicting class/path/casefold names, altered inputs, source/helper collision or missing R162 proof. Cross-platform CI uses only independent synthetic classfiles and Java source examples.

**Not complete:** This 1,272-file tree is not yet a successfully compiled v309 client. Its other class mappings and external dependencies remain unresolved; previously observed 516 javac errors have NOT been rerun after this change. Source distribution and runtime equivalence also remain pending.
