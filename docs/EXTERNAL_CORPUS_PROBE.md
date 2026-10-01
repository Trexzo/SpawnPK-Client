# External readable-v308 corpus probe

This Source M1 diagnostic integrates a compiled external SpawnPK recovery
corpus as **research-only evidence**.

The first intended external corpus is:

- repository: `i-iz-adam/SpawnPk-Open-Inject`
- audited revision: `fff831c2d44c890833a868d9b02e4c5d99d58064`
- observed public source: build 308, 1,128 `rs/**` Java files

The external repository is useful because it independently recovered a large
readable SpawnPK client tree and documents several CFR/decompiler repair
families. It is **not** Source M1 authority.

## Trust boundary

The probe never:

- copies external source into the recovered tree;
- promotes an external class/member name;
- changes canonical class/member lineage;
- changes the exact-v308 authority SHA-256;
- changes Source M1 publication gates.

The exact v308 authority remains:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Every external readable name emitted by the probe is a research candidate only
and still requires the ordinary semantic review boundary before it can become
canonical.

## Inputs

The external side must be compiled bytecode, supplied as either:

- a class directory such as
  `SpawnPk-Open-Inject/build/classes/java/main`; or
- a JAR containing the compiled external classes.

The public external repository does not currently publish its vendored
dependency JARs, so a fresh clone may not be independently compilable without
the external author's local dependency artifact. The probe therefore does not
attempt to fetch or build the external repository itself.

The exact side is the exact v308 client JAR.

The caller must also supply the exact 40-hex Git revision of the external
corpus. Branch names such as `main` are rejected.

## Command

```powershell
spk-external-corpus-probe `
  C:\path\to\SpawnPk-Open-Inject\build\classes\java\main `
  C:\Users\Felix\.spawnpk-data\client.jar `
  --external-revision fff831c2d44c890833a868d9b02e4c5d99d58064 `
  --json-out C:\path\to\external-v308-probe.json
```

The known exact-v308 SHA-256 is pinned by default. A different exact pin can be
supplied explicitly for controlled research, but the supplied JAR must match
that pin exactly.

## Matching

The probe reuses the existing conservative class matcher.

It first deterministically indexes every compiled external class. Directory
authority is hashed over sorted relative class paths plus exact class bytes.
Class parse errors, empty `rs/` scope, case-fold collisions, and
path/internal-name mismatches fail closed.

The matcher then correlates external `rs/**` classes against exact v308
`rs/**` classes using the existing stages:

1. unique exact class SHA-256;
2. unique name-insensitive structural fingerprint;
3. strong package anchors;
4. mutual-best weighted evidence with score and margin gates.

The report separates:

- **structural** candidates: exact-SHA or unique structural matches;
- **inferred** candidates: package-anchor or weighted mutual-best matches;
- ambiguous and unmatched classes.

No match strategy is equivalent to semantic acceptance.

## Report

The deterministic report uses:

- kind: `external_class_corpus_probe`
- corpus ID prefix: `EXTCORPUS_`
- probe ID prefix: `EXTCORPUSPROBE_`

Each candidate records:

- external class path;
- external readable class name;
- exact-v308 class path;
- matcher strategy/confidence/score;
- full existing matcher evidence;
- whether the external name is descriptive;
- `candidate_only=true`;
- `promoted=false`.

The policy block must always report:

```json
{
  "research_only": true,
  "promotes_names": false,
  "copies_external_source": false,
  "changes_source_m1_authority": false,
  "requires_separate_semantic_review": true
}
```

## Chat ownership

Chat 1 may use the report to identify likely equivalents for unresolved
compiler/decompiler families and to test exact-bytecode-gated Source M1
normalizations.

Chat 2 remains the owner of semantic naming review and promotion.

Chat 3 remains the owner of historical/cross-version proof.

This probe is deliberately an evidence bridge between an external readable
corpus and exact v308, not a shortcut around any of those ownership or trust
boundaries.
