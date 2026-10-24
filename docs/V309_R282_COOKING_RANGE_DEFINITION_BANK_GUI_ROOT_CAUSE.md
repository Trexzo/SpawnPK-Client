# SpawnPK v309 R282 — Cooking range GUI ID proven; definition-bank mismatch, not a client defect

**Sole active client development chat, 2026-10-18.** Continues draft PR #1142 from R281. **NO production Java change**; exact current private R278 full source-built Java11-target class-only JAR SHA256 \`dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd\` was reused. Original game Java/JAR/cache resources remain private.

## Real GUI identity witness

The original GUI was rebuilt into a disposable Linux/Xvfb home from SHA-pinned owner inputs. The actual compiled Client had a **diagnostic-only private source overlay**, printing real menu-builder values from \`Client.z()\` when the genuine scene picker retrieved its \`Model.field229\` and \`Scene.getHashAtTile\` result. The diagnostic class was not added to production or published.

A right-click at screen **(570,323)** on the rendered Cooking range yielded the real context menu **Walk here / Examine Cooking range / Cancel**, with a rendered 504×335 viewport. The actual source-side diagnostic showed:

\`\`\`
R282_SCENE_PICK id=114 packed=1075615923 xy=51,49 sceneHash=10 pickedName=Cooking range pickedActions=null transform=false mode=field1133 override=false cached=false pickedModel=[5274] rawActions=null
\`\`\`

Therefore, the scene picker really chose **ID114**, not same-named ID4172/22154. \`ObjectDefinition.get(114)\` AND direct \`ObjectDefinition.method2342(114)\` agreed that the standard-region definition's actions are **null**. No YAML/binary override, cached definition overlay or object transform was involved. The actual region-loader log selected **region 12593, bank \`field1133\`**. The GUI behavior is consistent with its own active definition bank.

## Cause of R281's apparently contradictory offline result

In R281 the previous 28-assertion standalone test called \`ObjectDefinition.load(new Archive(config,...))\` and then checked ID114 **without asserting the active bank**. On the pinned current owner assets, that initialization ends with the **OSRS-config definition bank \`field1136\` active**, so ID114 rightly has first option **Cook**. The GUI subsequently changes banks based on the *region*, to \`field1133\` (standard). Thus R281 had demonstrated the OSRS config ID114 **only**, and its results must not be generalized to a standard-region gameplay menu.

New independently authored, actual R278-compiled \`ObjectDefinition\` source-backed test \`R282DefinitionBankIsolationRegression.java\` explicitly cycles and checks all modes and resets:

| Test state | Definition bank | ID114 model | First action | Another ID16641 |
| --- | --- | --- | --- | --- |
| Initial standalone config load | \`field1136\` | 5274 | **Cook** | OSRS model5274 / Cook |
| Actual GUI standard region | \`field1133\` | 5274 | **None** | Different standard model10464 / Climb-down |
| Legacy OSRS bank | \`field1134\` | 5274 | **Cook** | OSRS model5274 / Cook |
| OSRS config bank | \`field1136\` | 5274 | **Cook** | OSRS model5274 / Cook |
| Return to standard bank | \`field1133\` | 5274 | **None** | Standard model10464 / Climb-down |

Each state asserts both normal lookup **and raw decode**, object identity, model ID, footprint, actions, and absence of a file/cached override. **78/78 assertions PASS** in the direct run, plus an independently rerun **SHA-pinned clean extraction 78/78 PASS**. The prior original-source R278 compatibility runner, including the real client 10-suite Java and strict object packet-framing tests, was also independently REEXECUTED: **797/797 checks PASS**. Thus **875 passing offline assertions across two separate suites**, not a new full 1,277-source compile or a new production build.

## Why no production patch

Enabling Cook by force in the standard bank would cross-contaminate legitimate standard-region and OSRS object definitions. For example, object16641 is a different **Climb-down** object in the standard bank yet **Cooking range / Cook** in OSRS. Patching \`ObjectDefinition.get(114)\` or adding a GUI-specific action would invent behavior not warranted by the current scene and could break region-specific interactions. R282 intentionally applies **no production edit**.

## Source-free owner evidence package

\`SpawnPK_v309_R282_COOKING_RANGE_DEFINITION_BANK_EVIDENCE.zip\`, SHA256 **\`5bb9f8ecd9bf4d2b9ebaab47de296c30dc5a98d7c40dd1b9882c01b9f92dc9f6\`**, 435,935 bytes, 16 entries. Exact deterministic rebuild twice **byte-identical**; CRC and per-file SHA256 manifest PASS; independent Pillow/stdlib validator **72/72 checks PASS**. Contains source-independent Java bank regression, guarded Linux/PowerShell offline runner and pinned asset-staging helper, actual owner scene-pick log, 1400×900 GUI screenshot, 78/797-check logs and corrected explanation. No original/recovered client Java/class JAR, dependency game JAR, cache files, account secrets, or private diagnostic overlay included. The PowerShell runner is provided for owner convenience but **has not been executed on Windows**.

The public files in this draft PR are independently authored source/verification material only. Keep #1142 DRAFT and preserve previous source provenance, do not merge \`main\` on this bank-diagnostic outcome.

**Next milestone R283:** specifically test a genuinely OSRS-bank region GUI pick and Cook request (without forcing actions onto legacy objects), then proceed toward owner-native Windows GUI acceptance and longer mixed-activity local gameplay.
