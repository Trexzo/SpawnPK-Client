# R200 — GroundMarkersPlugin generic decompilation repair

The private R15 candidate contains 1,274 Java sources. The `GroundMarkersPlugin.method2634(int)` return expression from decompilation combined a generic `Collections.emptyList()` with an obfuscated generic JSON-deserializer call, which under Java 11 inferred `List<Object>` and emitted an incompatible-types error against `Collection<GroundMarkerPoint>`.

The private R200 candidate changes only the return expression so the empty branch retains the typed `Collections.emptyList()` result and the deserialization branch explicitly passes through `Collection<?>` to `Collection<GroundMarkerPoint>`. This is an unchecked cast and requires an original-JAR behavioral/type witness before being considered authoritative recovery. It does not change the public method descriptor or JSON input path.

**Actual full-tree result:** `javac --release 11 -proc:none -g:none -encoding UTF-8 -Xmaxerrs 3000` across all 1,274 private Java source files, no third-party JARs: **R15/R199 2,002 errors → R200 2,001 errors**. Remaining external-library errors prevent a build; the compiler still emits unresolved symbols on the same source line from the unprovided JSON library. This eliminates the specific `List<Object> cannot be converted to Collection<GroundMarkerPoint>` error, not verified original-bytecode parity.

Private ZIP (not committed): `SpawnPK_v309_FULL_SOURCE_R200_PRIVATE.zip`, SHA256 `12ad696df20ebb328db35148c3a1eacdb6c974047ab2ff75ba65c38ae38f51ed`. Contains 1,274 complete `.java` files, pre/post SHA-256 witness, full compiler stderr. Do not assert a runnable client or original exact v309 reconstruction.
