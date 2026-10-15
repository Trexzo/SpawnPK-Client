# R193 — private Java source R13: configuration file loader cluster

Latest private full candidate: `SpawnPK_v309_FULL_SOURCE_R13_PRIVATE.zip` (delivered in chat, not committed to public GitHub). It carries **all 1,274 Java files**, the three source replacements, complete SHA-256 per-file manifest and actual stderr from the complete-source compilation.

## Three Java source changes

| Java class | Private preimage SHA-256 | Private postimage SHA-256 |
|---|---|---|
| `rs/definitions/BloodCounts.java` | `5602d622a475035afa1e6a18ff525dd9ec2f65356ca08c05bc7b529a87247336` | `672df64e8ce2a1d9eb780b20e6a3f698815bfa0912ee6c5e34ffe9675e1469df` |
| `rs/definitions/ItemHovers.java` | `fb9e6b33ff60f59b2821f93e5d78d18583384dd539728188003013608444c9d7` | `85478eb2071d6360f5d30a2a54d9eb5b81123bda0864dcf2bbac2ac416a94815` |
| `rs/definitions/ItemRarities.java` | `3bc9919c51fc42975cc00df7e0e54395887eda9cc3ffa90fe36cc00a4484f19d` | `c2892d58c933bdbb8d3bfa89cd863177b632903a7b732cd35e8c8bfb06448608` |

These methods previously relied on Lombok `@SneakyThrows` around `new FileInputStream(file)`. The private candidate removes Lombok imports/annotations and introduces per-owner private file-open helpers that forward the original `FileNotFoundException` instance through a generic unchecked propagation method. Public `load():void` declared signatures and the original YAML parsing/config lookup code remain unchanged. A generic exception helper avoids broadening checked exceptions at callers.

## Full-tree replay

Exactly the same no-external-JAR JDK 21.0.12.1 profile and same number of source files as R12:

- R12: **2,071** raw compiler errors, **9** warnings.
- R13: **2,065** raw compiler errors, **9** warnings.
- Difference: **-6** diagnostic occurrences; likely cascades from the removed Lombok annotation usage.
- Original uploaded baseline: 2,391 compiler errors. Reduction from this diagnostic profile: 326.

The three owners still report missing external Trove/SnakeYAML dependencies. This class group has not passed full isolated behavioral tests and is **not accepted as original v309 bytecode parity**. The result is a third-party-derived private candidate source fix, not a completed reconstructed client. The separately recovered original-v309 1,279-source tree is still unverified under this overlay.

**Critical next dependency frontier:** approved external library classpath, source-owner cross-reference graph and original exact-v309 method verification. No invented library stubs or original-client-JAR fallback are acceptable for source-only build acceptance.
