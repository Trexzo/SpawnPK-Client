# Original v311 R72 — 43-source renderer/UI event and regex source recovery

**Private evidence date:** 2026-10-23. Exact owner-supplied original v311 JAR SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original game JAR, canonical private reconstructed Java, game binary classfiles and actual original-vs-rebuilt behavior probe have **not been committed to GitHub**.

## Three genuinely new independently source-rebuilt original classes

| Original class | Original JVM classfile SHA-256 | Independently compiled Java9 class SHA-256 | Exact original symbolic JVM instructions |
| --- | --- | --- | ---: |
| `rs/z/t.class` — regex/wildcard matcher | `a11a743a17f7cc2ae686ec3b93a1356ef7542c849f61d05ad281e6e1ba6b0275` | `21516769b334e8c5d5a466e312017dbd069fa55c2e75a9ef0de03425795e08cc` | **53/53** |
| `rs/runelite/events/FocusChanged.class` — focus event | `e4c8ad25dfd349c39c3b101c437f3fcc9ddbda2b41dc338d754048694a3d9221` | `86b8816802878a7252de51505ba3787c0a1f47fbc8c8246761f76a76ef81665f` | **62/62** |
| `rs/runelite/events/NotificationFired.class` — notification value event | `35b862ef90be36dd500bebccbd3639ea15015f44f2e4faa608ab171176837472` | `5f16ff94782d74237f5c98c3f31cec44f1c1c55c46b1825b4899a4e3380ecfc4` | **105/105** |
| **New, distinct classes** | | | **3 / 220** |

The three original-named Java files were independently reconstructed and built with `javac --release 9 -proc:none -g:none`. Complete original-versus-rebuilt class declarations and descriptors, ordered JVM byte offsets/opcodes, resolved symbolic operands and control flow agree after normalizing only numeric constant-pool indexes. Their project-class references are self-only. For both new Java9 event classes, the actual **`StringConcatFactory` invokedynamic bootstrap recipes** match, including their original `toString()` text structure. The two full original/rebuilt binary classfile SHA values differ, and complete classfile attribute, StackMapTable or original authored source-text identity is **not** claimed.

## Complete independent 43-source original build

The **40 previously verified original-v311 Java source files** from R69 and all three new sources compile together in one Java9-target invocation, with an explicitly empty original client/game binary compiler classpath and sourcepath. The existing narrowly reviewed **compile-only `rs/k/c` class/package alias** is applied only in a disposable source copy, then reversed on copied emitted JVM constant-pool class metadata. No original game binary or canonical private Java source is modified.

The strict owner-private source validator verifies:

- **43 genuine reconstructed original Java sources, 43 original-name restored Java9 class outputs**.
- **4,242 / 4,242 exact original symbolic JVM instruction matches** and complete selected class declarations.
- **40 / 40 previous independently rebuilt class SHA-256 fingerprints unchanged**.
- **Zero temporary declaration-only source stubs**.
- **Zero missing explicit original project-class dependencies** (static constant-pool and descriptors, not dynamic/reflection/native/assets).
- Original whole-JAR SHA and all 43 original, canonical-source and rebuilt-class SHA pins, no incidental compiler classpath fallback.

## Bounded original-vs-rebuilt behavior and failures

An independent private JDK-only behavior suite agreed across **347 new regex/focus/notification cases** and all **278 prior renderer, scene, geometry and display cases**: **625 / 625 matched**. New patterns include wildcard combinations, case-insensitive literals, regex metacharacters, international text, null/empty messages, boolean focus toggles, equality, hash consistency and `TrayIcon.MessageType` values. Because object identity hashes vary between separately launched JVMs, the probe compares equal notification-object hashes within each JVM for nonnull message-type enum objects instead of equating unrelated numeric identity hashes.

**Five deliberate fail-closed trials passed in the original private working tree**: modified source SHA, missing class, wrong JAR SHA, unreviewed alias identity, and changed method instructions even after repinning **both** reconstructed source and independently compiled class SHA values. The ZIP was independently extracted and the full 43-class source/behavior validator passed. Four of the five refusal trials passed during a separate clean-extraction run; its final repinned-bytecode run exceeded the tool execution limit, and the clean-extracted five-trial rerun is **not** claimed complete.

Owner-private archive: `SpawnPK-v311-R72-Event-Regex-43-Class-Private-Sources.zip` **SHA-256 `6c26e2494e39e61cfba40bc82cb7b6e1188aeb73d41282214b4348e103e41a2f`**. The archive contains 43 owner-private reconstructed Java sources, exact class hashes/manifest, verification scripts and bounded original-vs-rebuilt behavior probes, **no original game binary/JAR, compiled original game classfiles, game assets, credentials, font binaries or token material**. This archive is **not hosted on public GitHub**.

## Correct progress accounting and limits

Previously R69: **69 distinct independently recovered original-v311 source classes / 5,230 matching original JVM instructions**, accumulated across separate accepted compilations. R72 adds **3 classes / 220 new instructions**, for a cumulative accepted tally of **72 distinct classes / 5,450 matching original JVM instructions across separate source-build records**. **Only 43 classes / 4,242 original instructions compile together in this one closed source island**; do not call it a 72-class combined build.

The original `rs/I` and six tile classes remain provisional and are **not accepted** because original `rs/k/e` renderer and `rs/a/a` model source dependencies remain unreconstructed. Full 1,184-class source build, all original classfile bytes/attributes, native/OpenGL graphics, gameplay and online authenticated behavior have not been established.

Public [synthetic-only Java9 event/regex parity tests](../tests/test_v311_synthetic_regex_events_source_parity.py) use independently authored toy JDK classes and test strict dependency closure, behavior equality and refusal cases, never the original proprietary game Java. Public CI must be checked separately. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. No manual game launch is appropriate for this source-only milestone.
