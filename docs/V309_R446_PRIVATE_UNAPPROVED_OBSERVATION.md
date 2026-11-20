# R446 — Owner-private CURRENT observation, not historical approval

**Parent:** R445 draft PR #1241. **Status:** DRAFT / UNMERGED / NOT DEPLOYED.

## Why this is a substantive recovery path

R441–R445 have a meaningful integrity safeguard: a real owner-private R421 source/class gate must match independently approved earlier reference SHA values. The blocker is that no separately approved complete **1,277-source/1,394-class R421 manifest** was located in the current Library or checked connected private-repository trees. The authorized owner desktop `DESKTOP-LTXXO4K` remains **offline**. Creating a new passing SHA from current files and claiming it was historically approved would be incorrect.

R446 enables a distinct and useful operation: **observe** the exact isolated R421 source and class bytes *as they exist now*, with clear **UNAPPROVED** labeling. This produces evidence for subsequent manual comparison and source reconstruction without pretending it establishes old custody or authorizes private javac, migration, deletion or deployment.

## Implementation

`tools/r446/observe_owner_private_inventory.py` has no arbitrary source-root argument. It reads only the exact R421 private acceptance directories under the owner's OS TEMP:
- `SpawnPK-R386-Isolated-Acceptance/R421-Private-NoFollow-Cache-Directory-Preflight/Source-Candidate-R421/source`
- The same parent `R421-Compiled-Classes`
- The same source candidate's `dependencies/R239_filtered.jar` and `dependencies/R218.jar`

It reuses R440 exact-root and ancestor no-link admission plus R445 bounded nofollow reads. It walks at most 9,500 members / 2,200 directories / depth 40 and reads a maximum 32 MiB per source/class member, 48 MiB per dependency and 700 MiB total per source/class tree. It requires exactly 1,277 Java sources, 1,394 class files, original hard-pinned R421 Store.java and Store.class SHA identities, and distinct dependency JAR bytes. **It never prints private filenames, per-file SHA values, source content, actual local paths or the live client.**

Default mode is entirely read-only; the only output is aggregate JSON:

```powershell
python -B tools\r446\observe_owner_private_inventory.py --observe-isolated-r421
```

The optional, **explicit** `--emit-owner-private-unapproved-candidate` makes a new private quarantine directory *under OS TEMP*, never under the installed client or inside GitHub, and writes a complete `R446-UNAPPROVED-CURRENT-SOURCE-CLASS-INVENTORY.json` source/class/dependency SHA map **without source or class bytecode**. The observed inputs are rehashed in full before output, and a mismatch blocks writing. New directory names are unpredictable, file creation is exclusive/no-overwrite, and no pre-existing inventory, client, history, journal or stored data is modified. Do not upload the quarantine file to public GitHub or share its full contents without appropriate permissions.

```powershell
python -B tools\r446\observe_owner_private_inventory.py --observe-isolated-r421 --emit-owner-private-unapproved-candidate
```

The JSON intentionally uses schema `SpawnPK-R446-current-observation-UNAPPROVED-v1` and immutable `independent_prior_manifest_custody_approved:false`, `compilation_authorized:false`, `release_authorized:false`. It **cannot** pass R442's schema check even if someone copies its freshly calculated raw SHA256 into the R442 expected-hash field. A current observed snapshot is not an independent older reference.

### Optional R315 comparison

R446 also accepts `--historical-r315-manifest` paired with `--approved-historical-r315-manifest-sha256`. The earlier owner-private R315 import file must already have an independent trusted whole-file SHA. Its original per-source hashes are compared against currently observed R421 *in memory*. Output contains **only aggregate changed, unchanged, added and removed Java source path counts** and whether dependency SHA values agree. R315 has no full compiled-class SHA map, so class lineage and older R421 custody remain **unproven**, even if the source paths happen to agree.

This is an owner-only reference diagnostic. Do not treat a newly computed hash of a current R315 copy as independent approval.

## Honest evidence and remaining gates

Hosted Windows/Ubuntu × Python 3.11/3.13 CI tests **invented** 2-file isolated client trees and dummy dependency files. It verifies observed source/class hash maps, no-write default, opt-in private TEMP creation and no overwrite, wrong original Store pins, missing files, unsafe links, same-count but changed file bytes, bounded traversal and data reads, retest-before-emission, invalid R315 reference SHA, and deliberate R442 refusal of the unapproved manifest. R445–R440 and R426 public synthetic suites run alongside them.

There is **no** real R421 owner-private execution or SHA observation in hosted CI. No recovered source assets, real JAR, player loot history, deletion intent/ack marker or production client was modified. The actual original R421 archive's age/custody is still unknown. R442 historical approval, R440 real admission, R425 1,278-source/1,399-class compiler acceptance, R432 73+ true assertions/17 real cross-process checks, real R427–R431 asynchronous Store/Plugin integration and Swing/v312 lifecycle testing remain separately gated.

**No release, merge, live JAR replacement, history deletion, persistent journal cleanup or write unlock is authorized.**
