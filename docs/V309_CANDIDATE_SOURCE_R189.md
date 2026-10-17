# R189 — private R9 candidate repairs in the full 1,274-source client tree

**Three additional edited Java sources** from the user-supplied third-party decompilation:

| Source owner | Before SHA-256 | R9 SHA-256 |
|---|---|---|
| `rs/util/QuantityFormatter.java` | `645b6cad7fc5ac85a3304a084232bb379d9aaf5e9fe336f9419374bfd5f10b2e` | `551b7c1e6099ddce1e08f40d6ae145cb53efe5de7c049b2939ac3a4096b097b7` |
| `rs/ui/components/colorpicker/ColorPickerHexFilter.java` | `8b6249f2c517700ff266f70d602f63dc4ec545b786ec33695351ac975ac9dec7` | `b0857fe6940c0fc8f695f427fe19618111c5e829b1d48e37e8567911676cbe07` |
| `rs/ui/components/colorpicker/ColorValuePanelIntFilter.java` | `b1ac6b4929606c8662e23947c979da27c401a676f1e17957a47e7b834671969c` | `feedee99033ecc2c0e95f27da22e49b354f01a15e4f2feae40ad408da89ca62a` |

The quantity parser now explicitly handles `ParseException` while retaining its non-throws public method descriptor and propagating the checked exception at runtime through a generic unchecked throw helper, matching the observed intent of Lombok's `@SneakyThrows`. Both Swing `DocumentFilter.replace` implementations now declare `BadLocationException`, which is allowed by the actual parent API; Lombok annotation imports removed.

### Verifications actually executed

- Isolated JDK 21 `javac --release 9 -proc:none` compilation of `QuantityFormatter` and its Java behavioral test: **PASS**.
- Executed three decimal/suffix parsing cases and the invalid-input `ParseException` propagation test: **PASS**.
- Full **same-profile** JDK 21 source compilation of all **1,274** Java files (no external dependency archives): **R8 2,099 errors / 9 warnings** → **R9 2,092 errors / 9 warnings**. The seven-diagnostic reduction is attributable to source/annotation changes and possible cascades; it is not seven original-method recoveries.
- SHA-pin manifest lists exactly three changed Java files; 1,271 other Java source files are carried over from R8 unchanged.

### Private deliverable

`SpawnPK_v309_FULL_SOURCE_R9_PRIVATE.zip`: private full source snapshot, SHA-256 manifest and `QuantityFormatterTest` source, delivered in conversation. Do not commit the private original-derived Java into the public repo without redistribution authorization.

**Acceptance limits:** no original exact-v309 client `.class` parity; no original full private 1,279-source candidate compilation; two Swing document filters are not independently integration-tested with their full UI dependencies. This remains a candidate-source repair lane, not a releaseable deobfuscated original-v309 client.
