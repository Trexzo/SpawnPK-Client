# v311 R75 private source-verification evidence

Three new original classes are independently reconstructed from owner-private Java9 bytecode: `rs/runelite/events/ChatMessage` (81 original instruction matches), `PrivateChatMessage` (124), and `SkillLevelChanged` (148). Their declarations, instruction offsets and symbolic operands match. The invokedynamic string-concatenation recipes also match.

A 46-class Java9 original-name source build matches 4,595/4,595 original JVM instructions with 43 previously rebuilt fingerprints unchanged, no unverified dependency stubs and no original game binary on the compiler classpath. Bounded original-versus-rebuilt behavior matches in 756/756 cases. The private clean-extracted verifier passed, including all five deliberate refusal cases across two bounded runs.

Accepted cumulative evidence: **75 distinct classes and 5,803 original JVM instruction matches across separate source-build records**. Only **46 classes / 4,595 instructions** have been compiled together in this particular source island.

The owner-private archive `SpawnPK-v311-R75-Chat-Skill-46-Class-Private-Sources.zip` has SHA-256 `5b2af2d1c2c7452bb925c641562b11de3de365423accb476a838b295c6b372a9`. It excludes the original client binary and compiled game classfiles; reconstructed owner-private Java is not in this repository. Hosted [synthetic-only regression tests](../tests/test_v311_synthetic_chat_skill_event_parity.py) are separate from authentic private source proof.

The seven `rs/I` and tile candidates remain provisional because `rs/k/e` and `rs/a/a` source dependencies are unrecovered. Full client, runtime, asset, graphics and gameplay acceptance are not claimed. PR #1142 remains draft/unmerged.