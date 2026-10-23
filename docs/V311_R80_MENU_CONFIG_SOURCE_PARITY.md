# Original v311 R80 — 51-class menu and configuration event source island

**Owner-private original authority:** `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original JAR, reconstructed original game Java, actual original-client classfiles and owner-private probes remain **OFF public GitHub**.

## Five newly source-reconstructed original classes

| Original class | Original class SHA-256 | Source-rebuilt Java9 class SHA-256 | Exact original JVM instructions |
|---|---|---|---:|
| `rs/runelite/events/MenuOpened.class` | `013c20205d35dafa1619f9bc14c3140e02bc3b4dfadbd38f58dcff0e875f50a6` | `2afcab5887f549ce55a136d0879c60281d0bd423422ad23770aa2ff5f30b9b67` | **33/33** |
| `rs/runelite/events/ClientStartUp.class` | `a0cb56ad70c2b2cb2ab5996014f99e1e333e1d0896ac30d3cff446ea8a2edfea` | `432dad605fcde23906266830e1418e3301561675526c425f146fa7dbe093cf3d` | **33/33** |
| `rs/runelite/events/ConfigChanged.class` | `7715688a61c0d197c48753c2f24686f4709ea2ba97756e90e6c5087e0450d529` | `9651ea8ad5d76ac363a4a397aae87e74f6c51cca1f96eb2bb04f419c4532a29b` | **235/235** |
| `rs/runelite/events/MenuBuild.class` | `6e3a4d1009662a7f39d591296e09f6bb745548453520770ca3ab33e2fb0b3788` | `991a4a56c0ffffa1c90196208ae7e10b62e52d2508de85f8b070c4f5e0e9442a` | **236/236** |
| `rs/runelite/events/MenuHover.class` | `87e262314b85da17668cce7163533148766b9db5971dc152103fbed68c597ce5` | `62c84c9b50591e417f3f67bf197329b5df874246bde2247afeccc6abb7502f8c` | **236/236** |
| **New, nonduplicated source classes** | | | **5 / 773** |

All original JVM class declarations, fields, method descriptors, opcode sequence, exact instruction offsets/branch targets and resolved symbolic operands match Java9 source rebuilt with only numeric constant-pool indices normalized. The original `StringConcatFactory` bootstrap records also match for `ConfigChanged`, `MenuBuild` and `MenuHover`. This is **not** a byte-for-byte original classfile attribute/StackMapTable reproduction claim.

## Closed source build and behavioral replay

The five new candidates and previously certified 46 R75 source files compile in **one Java9 `javac --release 9 -proc:none -g:none` build** with **no original game binary on the compiler classpath or external sourcepath**. There are exactly **51 genuine original Java source classes / 5,368/5,368 matching original JVM instructions**, **46/46 unchanged previously accepted built class SHA-256 fingerprints**, **zero declaration-only source stubs**, and **zero missing explicit project-class dependencies**. The existing reviewed disposable compile-only alias for `rs/k/c` is inverse-restored in copied classfile metadata; canonical Java files and original binary remain unmodified.

Isolated original-vs-rebuilt offline JVM probes matched **186/186 new menu/startup/config behavior transcript lines**, checking startup equality/identity, multi-field configuration values including null and Unicode, command indices beyond and inside switch ranges, singleton state, equality, hash and formatting. All **756/756 prior renderer, scene, geometry, coordinate and event comparisons** passed again: **942/942 total**.

An owner-private ZIP was clean-extracted and successfully replayed through the full 51-class original-parity and behavior verifier. **All five deliberately incorrect cases** also failed closed **from the clean extraction**, in two bounded runs: tampered source SHA, missing original-name source, wrong original JAR SHA, unauthorized compile alias, and changed JVM instructions even after repinning both source and newly compiled class SHA-256 fingerprints.

The owner-private self-contained ZIP `SpawnPK-v311-R80-Menu-Config-51-Class-Private-Sources.zip` has SHA-256 **`5ae51945a1353c6e265f6948f850fe80786cc62f13cc7a5e251a8b2eb70e0d5a`**. It contains exactly 51 reconstructed original-source Java files, hash manifests, verifier and probes; **no original game JAR, compiled game classfiles, credentials, fonts or gameplay assets**. It must **never** be committed to public GitHub.

## Count ledger and limitations

Prior accepted R75 source-recovery inventory: **75 distinct original classes / 5,803 original JVM instruction matches across separate accepted source builds**. R80 adds **five genuinely new classes / 773 original instructions**, resulting in **80 distinct accepted classes / 6,576 exact original JVM instruction matches cumulatively across separate source-build records**. The **largest source-closed combined compilation is 51 original Java classes / 5,368 instructions**, not all 80 in one compilation.

The independent [synthetic Java9 menu/config regression](../tests/test_v311_synthetic_menu_config_source_parity.py) uses unrelated toy Java classes to verify exact source parity, switch tables and refusal gates. Hosted public GitHub CI cannot verify the private original game JAR or reconstructed owner-only sources, and its result must be checked separately.

The earlier `rs/I` and six tile classes remain provisional and excluded because original `rs/k/e` renderer and `rs/a/a` model-source dependency chains are still unrecovered. Full 1,184-class client source closure, original complete binary identity, native/OpenGL rendering or gameplay are **not** claimed. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**.
