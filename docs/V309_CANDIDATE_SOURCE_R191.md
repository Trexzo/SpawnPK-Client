# R191 — private R11 source repairs (four production Java classes)

Private artifact: `SpawnPK_v309_FULL_SOURCE_R11_PRIVATE.zip`. Contains **all 1,274 Java sources**, four R10→R11 replacements, per-file SHA-256 witness and two executable test harnesses. The source ZIP is not published to GitHub while original-derived code redistribution permission is unresolved.

| Repaired source | Change |
|---|---|
| `rs/tools/PlainLogHandler.java` | Remove Lombok `@SneakyThrows`; propagate the actual `BadLocationException` instance with unchanged public no-throws interface |
| `rs/tools/LoginLogHandler.java` | Same exception handling for Swing document insertion |
| `rs/FileUtils.java` | Remove Lombok and preserve the original `IOException` object on stream read/flush |
| `rs/plugins/PluginClassLoader.java` | Replace Lombok with the inherited `loadClass(String) throws ClassNotFoundException` declaration |

## Verified
- `javac --release 9 -proc:none` compiled `LogHandler`, both log handlers, and `LogHandlersTest`; `-Djava.awt.headless=true` test passed.
- `javac --release 9 -proc:none` compiled `FileUtils` and `SourceUtilityTest`; byte-array and original-IOException-propagation tests passed.
- `PluginClassLoader.java` independently compiled with Java9 settings.
- Full **1,274 Java** JDK21 dependency-free javac replay using the same profile as R10: **2,084 → 2,076 errors**, **9 warnings** unchanged. **8 fewer raw diagnostics** from four candidate repairs. This is not eight verified original methods.

This is repair of a third-party decompiled *candidate*, not exact original-v309 bytecode source recovery, and it does not modify the separately recovered 1,279-source original-v309 private snapshot. Full client build, original bytecode parity, dependency closure, and redistribution rights remain unverified.
