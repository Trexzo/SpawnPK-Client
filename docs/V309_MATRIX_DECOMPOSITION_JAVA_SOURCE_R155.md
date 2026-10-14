# R155 — recover original v309 matrix decomposition methods and close toString dependencies

Original-v309 client only; stacked on R154 #1045, R153 #1044, R150–R152. Complete canonical recovered-source/v309/src remains unbuilt.

## New real private source implementation and JVM evidence

The exact original SHA-256-pinned matrix class (com/a/b/a/b.class, SHA-256 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030) has **24 declared JVM methods including its static class initializer**. The earlier R150–R152 private reconstruction investigated 13. R154 rebuilt toString() with 60 original instructions, but that method invoked two internal float[] decomposition methods that had originally been left as nonaccepting compilation-only stubs.

R155 independently recovered **both actual source implementations** from original v309 JVM Code evidence and recompiled them together with the reconstructed toString source into an isolated class with the same exact original JVM owner. Running Java9 javac with **no original client JAR or game classfiles on the classpath** produced exact private original-vs-recompiled instruction/offset, branch destination, CP-resolved Math function, constant and field-access matches:

| Newly recovered method source | Matching original JVM instructions |
| --- | ---: |
| Matrix rotation/Euler float-array decomposition, internal c():float[] | **108/108** |
| Alternate decomposition, public d():float[] | **113/113** |
| Previous R154 4x4 string formatter toString():String, now with *real* c/d implementations | **60/60** |
| **Verified invocation-closed group** | **281/281** |

The first helper computes signed angular decomposition with a threshold at plus/minus 0.999D and Math.asin, Math.cos and Math.atan2. The second computes a related decomposition with an original Math.abs(cos(angle)) > 0.005D branch and a sign-handling fallback. The Java source preserves exact original float/double casts and array indexing, which were independently compared with real v309 JVM Code; no guessed mathematics or imported game binaries were used.

**Important:** the three methods form a closure of *selected self-calls* from toString to c and d. It is not a complete class-level runtime/dependency or initializer closure, and full original StackMapTable attributes or byte-for-byte classfile equality have not been verified. They must not be promoted to whole original-equivalent class acceptance.

Across R150–R152 plus R154–R155, the independently observed original source implementation frontier now contains **16 selected method bodies and 631 matching original JVM instructions** (prior 13 / 350, plus c/d/toString 3 / 281). On the original 24-member JVM class, **eight methods remain unselected**, including the original Packet-dependent constructor and decoder/loader; the other six include longer matrix math, conversion and transformation operations. No complete public source tree is yet published.

## New GitHub acceptance improvement

The previously selected-only R150 verifier could successfully verify toString while its c/d callee bodies remained stubs. R155 adds an explicit **--require-selected-self-call-closure** opt-in, which analyzes *both* the original and rebuilt JVM profiles. For each selected method it enumerates all method invokes targeting its **same JVM owner**, and refuses the whole private replay unless every such invoked method (exact JVM name + descriptor, including any constructors) is also in the SHA-pinned selected method list. It also proves the total number of selected original and rebuilt self-call edges agrees, on top of the existing fully decoded Code parity. Thus toString cannot be counted inside this closure unless **both** c() and d() are separately selected and successfully recompiled to original instructions.

This does NOT certify external library calls, unselected constructors/static initializers, field layout, annotation metadata, indirect dispatch or full JVM bytecode equivalence. It remains optional to preserve earlier explicitly partial R150–R152 verification; the output records whether closure was required and how many self-call edges were checked. Original game-linked binaries never enter the diagnostic compile classpath.

## Synthetic tests and exact private replay

Cross-platform synthetic CI compiles a genuinely original-game-linked matrix owner against synthetic rs.Game; it checks an independently built Java matrix source with three matching method bodies and two internal invokes; then verifies exactly three selected methods and two closed self-call edges. It proves that selecting only toString or omitting one invoked decomposition helper is refused under strict closure, even where the caller's instructions match. A mutated helper body and original hash drift fail. R154 and R150 regressions run on Ubuntu and Windows. Only synthetic sources enter hosted GitHub Actions; no actual SpawnPK source/JAR or private original names/maps are posted.

Private complete three-member method selection is:

    [{"name":"c","descriptor":"()[F"},
     {"name":"d","descriptor":"()[F"},
     {"name":"toString","descriptor":"()Ljava/lang/String;"}]

Use the existing R150 CLI with a privately staged one-original-owner Java ZIP and this private method selection JSON, adding --require-selected-self-call-closure and exact source/selection SHA-256 pins. No compilation-only placeholder or original binary may satisfy the three-method proof.

The independently reproduced whole 1,271-Java v309 javac diagnostic remains at **516 errors**. R155's 631-instruction partial class recovery is not yet integrated into that whole-client compilation, and no new error-count reduction can be claimed. The next bounded target is additional non-Packet matrix math methods; the original signed short Packet constructor/loader still needs independently mapped original member callsites and source identity.
