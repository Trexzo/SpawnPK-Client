# R190 — R10 private client-source repair continuation

Private full candidate: `SpawnPK_v309_FULL_SOURCE_R10_PRIVATE.zip` (not committed to GitHub). This archive contains 1,274 Java source files with five additional candidate edits relative to R8: `rs/util/QuantityFormatter.java`, `rs/ui/components/colorpicker/ColorPickerHexFilter.java`, `ColorValuePanelIntFilter.java`, `rs/util/Class78.java`, `rs/eventbus/Class87.java`.

The three R9 repairs remove Lombok annotation dependencies by preserving QuantityFormatter's public no-checked-exception signature while propagating Java `ParseException`, and by using the actual Swing `DocumentFilter.replace` checked exception declaration. The two R10 repairs remove Lombok `@SneakyThrows` from `ScheduledExecutorService` wrapper methods and a reflection-based event callback; the former declare exactly the checked exceptions permitted by the Java API, and the latter forwards `IllegalAccessException` and `InvocationTargetException` without wrapping them into different exception classes.

## Measured build frontier

All results use the same complete 1,274-file third-party decompiled source set, JDK 21.0.12.1, and a no-third-party-dependencies `javac -proc:none -g:none -encoding UTF-8 -Xmaxerrs 3000` compilation. Neither original client JAR nor external JARs are added:

| Candidate | Full-tree javac errors | Warnings |
|---|---:|---:|
| Original uploaded baseline | 2,391 | 9 |
| R8 (nine edits) | 2,099 | 9 |
| R9 (twelve cumulative edits) | 2,092 | 9 |
| R10 (fourteen cumulative edits) | **2,084** | **9** |

R10 reduces raw errors by 15 compared with R8 and 307 relative to baseline; those are diagnostic occurrences, not independently corrected original methods.

## Executable verification

- `QuantityFormatterTest`: `javac --release 9 -proc:none` and executable tests for decimal suffixes and invalid-input `ParseException`: PASS.
- `EventInvocationTest`: `javac --release 9 -proc:none` and executable tests for reflective receiver dispatch, lambda callbacks and original `InvocationTargetException` propagation: PASS.
- `Class78` and the two Swing filters participate in the complete-source diagnostic replay but were **not independently executed with original full client dependencies**.
- Exact per-Java-file before/after SHA-256 values are in the R10 private manifest and R189 GitHub evidence file. The private full source is not published in GitHub.

This remains **repair of third-party candidate Java**, not exact original v309 bytecode source recovery. It has not been applied to the separately recovered 1,279-file private original-v309 snapshot; strict original JVM Code parity, real dependency closure and full-client compilation remain unverified.
