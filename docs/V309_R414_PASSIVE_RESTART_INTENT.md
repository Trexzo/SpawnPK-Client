# R414 — passive restart-intent classification (strict quarantine, not recovery)

**Repository:** Trexzo/SpawnPK-Client  
**Stack:** R413 draft PR #1209  
**Status:** DRAFT / UNMERGED; owner-private installation and release gates CLOSED.

## Why this milestone is deliberately read-only

R409's independent portable filesystem prototype defined a version-1
delete-intent marker, an exact SHA-256 before/after image comparison
and startup states. R410–R413 then improved the isolated private
history writer's atomic replacement policy, staged-file force,
orphan-stage quarantine, confirmed panel preflight, and identity
restoration after **proven** failures before replacement.

The missing state remains a write that **may already have replaced**
the canonical history before the application received or recorded
an acknowledgment. A boolean failed write receipt cannot prove
which image is on disk.

R414 begins actual private-source integration by adding a
**passive classifier and all-entrypoint marker fence** to the
isolated history store. R414 does **not** implement a transaction
producer, automatic cleanup, journal replay, or an asynchronous
confirmed-delete protocol. It **does not fix the original frozen
client**.

## Exact owner-private change

Only \`rs/plugins/loottracker/LootHistoryStore.java\` changes
relative to R413. An additional nested enum class
\`LootHistoryStore$R414IntentState.class\` is compiled.

The classifier recognizes a specifically named local marker
\`loot-history.delete.intent\` in the same directory as
\`loot-history.json\`, and recognizes an interrupted prepared
marker \`loot-history.delete.intent.tmp\`. Its classification
states are:

| Result | Read-only evidence meaning | Action in R414 |
| --- | --- | --- |
| \`NONE\` | No marker or marker-temp observed at inspection time | Existing R411 history-stage check still applies |
| \`ABORTED_BEFORE_REPLACE\` | Canonical file SHA-256 exactly equals marker's before-image digest (or both record expected absence) | **Refuse** restore, save, Clear all, legacy cleanup and persistent confirmed edit |
| \`COMMITTED_BEFORE_ACK\` | Current canonical file SHA-256 equals marker's after-image digest | Same refusal and evidence preservation; **not** an acknowledged deletion |
| \`QUARANTINED\` | Unknown, malformed, oversized, truncated, unexpected path type, conflicting hash, unreadable or changing evidence | Same refusal; require a separate verified recovery decision |

The classifier follows R409's **synthetic** canonical version-1
sidecar grammar: \`v=1\`, positive bounded serial, lowercase
UUID nonce, \`before=ABSENT\` or 64 lowercase SHA-256 hex
characters, and \`after=\` 64 lowercase SHA-256 hex characters.
The marker is at most **512 bytes**, must be a regular file,
must match the canonical ASCII grammar and cannot describe
identical before and after digests.

A prepared marker-temp path of **any file type** immediately
causes \`QUARANTINED\`, before reading the final marker. This
handles an interrupted intent preparation without guessing
whether the writer is still running.

The bounded reader uses \`Files.newByteChannel(...,
LinkOption.NOFOLLOW_LINKS)\` and rejects a nonregular marker.
The canonical history file is hashed with SHA-256 via a
bounded streaming no-follow channel; the existing **64 MiB**
store limit applies. Both marker and history metadata are
rechecked around the reads. These checks can detect many
unexpected changes, but **cannot establish all-thread,
cross-process or hostile tampering safety**. The checksums
are **not an authentication mechanism**, and a matching
hash does not prove the JSON document itself can be safely
adopted into the panel.

The new \`r414IntentState()\` is called by the existing
\`r411StageState()\` **before** inspecting
\`loot-history.json.tmp\`. Any result other than \`NONE\`
is mapped to R411's \`UNSAFE\`, so its existing refusal
path automatically covers the startup history merge,
routine/final save, Clear all, legacy cleanup and
R412/R413 confirmed-delete pre-mutation admission.
Normal marker-free behavior and the price cache are
unchanged.

There is **no marker creation** in private R414.
No synthetic marker is introduced into real player
history directories. The classifier only activates if
a marker or its temporary precursor is observed.

## Verified owner Windows private build and tests

- Fresh isolated R413 → R414 owner TEMP source clone.
- JDK21 \`javac --release 11\` full compile **PASS**:
  **1,277 Java source files → 1,392 compiled class files**.
- Exhaustive source/class byte diff **PASS**: exactly
  **one** changed Java source (\`LootHistoryStore.java\`),
  **one** modified existing compiled class
  (\`LootHistoryStore.class\`) and **one** new nested enum
  class (\`LootHistoryStore$R414IntentState.class\`).
  All other private class/source bytes match R413;
  differences versus the independently SHA-pinned
  R381 class corpus remain confined to the established
  eight Loot Tracker classes plus the three new R411/R413
  enum/snapshot classes and this R414 enum.
- Public-only pinned static auditor
  \`tools/r414/audit_passive_restart_intent.py\`,
  run against actual owner-private source and compiled
  class trees, SHA-pinned R381 sources and JAR:
  **\`R414_PRIVATE_PASSIVE_RESTART_INTENT_GATE_PASS\`**,
  exit 0. Enforces no-follow bounded reads, canonical
  before/after grammar, all-write-path admission,
  unchanged strict writer and exact source/class scope.
- **37 Python** invented file/intent contract tests:
  **35 PASS / 2 SKIP** locally on owner Windows
  (optional symlink creation unsupported by host).
- Portable JDK21 standalone **25 mandatory Java**
  synthetic filesystem/restart cases PASS locally,
  repeated **5/5** consecutively. Two optional real
  symlink scenarios were unsupported locally. One
  case deliberately launches a **separate fabricated
  Java process** that commits a synthetic history
  replacement, exits before acknowledgment and is
  reopened by a fresh synthetic JVM; result:
  \`R414_CHILD_RECOVERY_COMMITTED_BEFORE_ACK\`.
  **No original client process was launched.**
- Private custody-only compiled archive:
  \`R414-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`,
  SHA-256
  \`c17d7b4f5762382adee39476c89a0aa7fa112d545f614c69418655f742ffda92\`.
  The JAR was built and packaged **but not executed,
  uploaded, distributed or installed**.

## Remaining release blockers

**No actual journal producer:** R414 cannot produce the
before/after marker during a real confirmed deletion. This
is an intentionally scoped preliminary integration.
The synthetic crash/restart test exercises its own invented
producer and inspector; it is **not** real private-client
start/stop acceptance.

**No safe cleanup/adoption:** Even when a marker matches
the main file, it remains in place and existing R411
admission refuses ordinary operations. This prevents an
unacknowledged UI state from silently overwriting history
but means that an unresolved marker can block routine
saves indefinitely. Do **not** delete the file solely
because it is old or a hash matches.

**No cross-process ownership:** A foreign writer can
change files before or after observation. Same-size,
same-mtime swaps and a null filesystem fileKey may
defeat portions of metadata consistency checks.
Neither ordinary SHA-256 nor the marker nonce is a
cryptographic MAC. There is no interprocess
lock or directory-metadata durability certification.

**No proven JSON schema adoption:** The marker hash may
match bytes that the actual \`LootHistoryStore\` reader
would reject. The correct authority must be established
by a future bounded JSON parse, version check, exact
rehash and UI-snapshot handoff before any marker cleanup.
Nothing in R414 authorizes automatically adopting
a document solely on digest equality.

**No EDT performance improvement:** Confirmed deletion
still performs a synchronous write under \`r401FileGate\`.
The original frozen-window root cause is unverified,
and no restricted guest game runtime or v312 acceptance
has been performed. Real production history untouched.

## R415 recommendation

Integrate a **strict, single-writer transaction producer**
for confirmed deletions, using exact old/new history
digests and a forced, atomically renamed intent before
replacing history. Design explicit acknowledgments and
restart adoption that preserve marker evidence until
the UI has safely adopted the verified resulting file;
then prove the protocol across process restart,
interprocess conflicts, interrupted marker preparation,
ambiguous commits and all existing history entrypoints.
Until then, do **not** enable async deletion or automatic
journal cleanup.

**Keep R414 draft/unmerged. Private execution,
production installation, release, merge and
distribution gates remain CLOSED.**
