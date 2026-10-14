# R154 — original v309 matrix string formatter Java source recovery

Client-only source restoration, stacked on R153 #1044, following R150 #1037–R152 #1039. Whole-client source milestone #1004 remains incomplete.

## Independently reconstructed original-v309 Java method

The original excluded, game-linked matrix class com/a/b/a/b.class contains public toString():String, a **105-byte Code body of 60 decoded JVM instructions**. It first invokes two internal matrix float-array decomposition helpers, discarding their results, and then formats the 4x4 float matrix with a StringBuilder. The outer and inner loops walk four rows and columns. It uses the **column+4*row** index; columns are separated by a TAB, rows end with newline, and absolute values whose sqrt(float-value-squared) is below an original **float** 1.0E-4F threshold print as 0.0F. Preserving the source float-to-double promotion retains the exact original double constant 9.999999747378752e-5.

On the **actual SHA-256-pinned original v309 class** (original owner class SHA 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030), independent private source reconstruction into the same JVM owner name, compiled with javac --release 9 -proc:none -implicit:none -g:none with **NO original game classpath**, yielded exactly **60/60 instruction and offset matches**, including resolved StringBuilder.append(String), append(float), Math.sqrt(double), literal tab/newline and the original double threshold. The strict original-vs-source verifier and StackMapTable metadata checks remain a separate replay gate; this match is independent original javap Code evidence rather than a claim of whole classfile identity.

**IMPORTANT temporary source scaffolding:** the selected original toString method invokes c():float[] and d():float[]. Their **compilation-only bodies** were stubbed in the isolated Java class, specifically to preserve the caller's original invocation instructions. These two helper bodies are not recovered, accepted, invoked at runtime or counted as original implementation. The original matrix toString source method is independently recovered; the full matrix Java owner is not yet completed.

The cumulative independent private source instruction frontier is now **14 distinct matrix method bodies and 410 matching original JVM instructions** (R150: 95 + R151: 181 + R152: 74 + R154: 60). This is not an exact official R150 CLI replay of all 14 private method bodies in a single full class, nor a complete client rebuild.

## GitHub tests and next original source work

R154 commits a synthetic original Java9 matrix that really depends on rs/Game (R136 original-linked exclusion), plus an independently built candidate Java owner with identical selected toString code but deliberately different helper bodies and without original rs/Game binary fallback. The R150 exact-source one-class verifier must accept **only** the selected toString Code method, count exactly 60 instructions and reject selecting the scaffold c() helper, changing the original float threshold, transposing the indexing expression or supplying an invalid source hash. CI runs on Ubuntu and Windows and rechecks R153's original coverage regression.

No user original JAR, actual v309 source, private original member method selection or compiled derivative is committed to public GitHub. Recovered source publication rights and independent dependency provenance remain separate acceptance requirements. The prior private whole 1,271-source original client Java javac diagnostic still has 516 errors: no additional reduction is claimed until source integration and real private whole-source javac replay.
