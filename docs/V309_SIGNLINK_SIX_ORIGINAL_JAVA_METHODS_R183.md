# R183 — original v309 Signlink/bridge six Java methods

Client-only partial original-source recovery, stacked on R182 #1075 and tracked under source milestone #1004. This is the original JVM owner rs/v/a, a larger runtime/network coordination class; **only six selected source method bodies are evidenced and the other original methods remain unverified**.

## Privately verified original evidence

- Original v309 JAR SHA-256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
- Original rs/v/a.class SHA-256: d0dc35deddc8016c3fdcaf2615810efa200c042120b83bed86cad5d04b1c0ddc
- Original owner has **24 total JVM methods**, including its initializer and networking/runtime methods. No full original method-set recovery is claimed.
- One privately reconstructed original-named rs/v/a.java compiles with Java9 source-only (JDK21, --release 9 -g:none -proc:none -implicit:none), empty external/original binary classpath and an explicitly unverified run() placeholder.
- Exact selected original JVM method instruction-offset/opcode/operand/reference comparison:

| Selected original method | Exact JVM instructions |
| --- | ---: |
| private constructor <init>()V | 6/6 |
| a(String):boolean | 17/17 |
| b(String):boolean | 7/7 |
| synchronized d(String):void | 5/5 |
| synchronized a(Runnable,int):void | 5/5 |
| i():boolean (architecture property check) | 22/22 |
| **TOTAL selected** | **62/62** |

Other 18 original methods and the full original 40+-field ABI, static initializer, nested classes, complete I/O, thread/network behavior and runtime interoperability are NOT recovered by this work. The source-only placeholder method and incomplete fields are not original-evidenced. This private partial Java file **must remain outside** recovered-source/v309/src until full class restoration.

- Private original-name Java source text SHA-256: 7153c816d8f0c89dca1ebfeef092dec878855181f0de43d96620f7a991fcbc79
- Private partial source-only ZIP SHA-256: 28ffe7d1b1e29f5d6e6466684423548d233ebdb7d498d7666aa6f6ea2c3371ad

## New GitHub verifier

The private R183 verifier pins the original JAR and class SHA256 as well as the partial private source ZIP. It compiles the original-name Java using an empty source and binary classpath, verifies original class owner/super/JDK release/access/interfaces, requires exact six method identities, and uses the same strict R150 resolved-JVM-instruction comparator. It publishes only selected method count and bytecode evidence. The result expressly marks full class, runtime, networking, canonical overlay, whole-client compile and redistribution as NOT accepted.

Hosted tests use **invented** synthetic Java9 sources with distinct owner/behavior and no original SpawnPK code or binaries. They check selected positive parity, changed selected operations fail closed, unselected placeholders are NOT accepted, wrong SHA/method count/source owner failure, and R182 regression.

## Next

Continue original JVM evidence-guided recovery of the remaining rs/v/a methods and nested/support types. Work in parallel with rs/h queue reconstruction on existing R180 branch and rs/f/a global configuration class. Re-run a normalized full-source build only after full class source is recovered; do **not** count partial Signlink source as a new canonical Java file or claim an improvement over the last measured JDK-only 2,339/2,343 compiler errors (different snapshots).
