# Chat 2 — R8/R6 exact-v308 source-pipeline empirical findings

Date: 2026-09-22

This note records a local/private exact-v308 validation performed against the current Chat 2
head on top of Main/Core R8C. No client JAR, readable JAR, recovered source, decompiler JAR,
or local safety acceptance is committed.

## Exact authorities

Exact client:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Pinned Procyon 0.6.0:

`821da96012fc69244fa1ea298c90455ee4e021434bc796d3b9546ab24601b779`

The Procyon binary was fetched through a temporary GitHub Actions artifact, verified by SHA
and exact size (2,004,704 bytes), then used only in the local validation workspace. The
temporary helper branch was reset afterwards.

## Canonical authority regeneration

The private exact client re-indexed as:

- entries: **10,970**
- classes: **10,472**
- canonical `rs/**` classes: **1,129**
- parse errors: **0**
- fields: **7,247**
- non-constructor methods: **6,564**
- canonical members: **13,811**

The original R2 Chat 2 semantic candidates re-resolved to:

- review: `SEMREVIEW_DD69CD752A6E46181BAC`
- proposals: **39**
- unresolved: **0**
- committed review object equality: **true**

Applying Main's committed acceptance spec locally produced exactly:

- accepted classes: **32**
- accepted fields: **3**
- accepted methods: **4**

No additional semantic proposal was accepted by Chat 2.

## R8C readable-client reproduction

With source-safe fallback enabled, the namespace contains:

- accepted semantic class remaps: **32**
- source-safety fallback class remaps: **85**
- total class remaps: **117**
- accepted member remaps: **7**

The class-risk scanner reports:

- exact class-name literal hits: **0**
- package-resource overlap records: **49**

The package-resource findings are dominated by fallback classes whose source package is the
broad `rs/` root while bundled resources also live below `rs/`. The gate was acknowledged
locally only to reproduce Main's validated source-safe rewrite boundary.

The exact member safety report is:

`MEMRISKREVIEW_20D4CB4F1CFE1BC379CB`

Risk levels:

- high: **5**
- medium: **1**
- low: **1**
- critical: **0**

The high findings are conservative public-API and one-character source-name/reflection
signals. The reflected one-character literals occur in unrelated third-party owners rather
than owner-bound `rs/Client` reflection evidence. A report-ID-bound local acceptance was used
for this validation only and was not committed.

The resulting readable build completed and independently verified:

- manifest: `READABLE_DB58B71C56F29C9AD8A7`
- namespace: `SEMNS_8B2250664AAD43CBA191`
- readable SHA-256:
  `927245c86d9d734a632d34ef3c02a0345781380ae70b3bd2b15b8f04361ac68f`
- verification pass: **true**
- archive entries: **10,970**
- classes: **10,472**
- semantic readable classes: **32**
- fallback classes: **85**

This hash is for the local reproduction that applies both class/fallback and the seven
accepted member remaps.

## Procyon whole-archive observations

Main R8B already proved the pathological `rs/d/a` class succeeds with default Procyon.

A research-only eager-method-loading run (`-eml`) produced thousands of Java files before
manual termination, showing substantially better archive progress in this environment.
However the partial third-party source already contained genuine Procyon inline failure
markers in bundled dependencies such as `com/google/**` and `com/jacob/**`.

This exposes an R5A scope issue:

> current source readiness treats decompiler failure markers in bundled dependency source as
> project-source readiness failures.

R8C already distinguishes project-owned source prefixes during clean rebuild, but R5A does
not currently apply that ownership boundary when scanning decompiler failures.

The known pathological `rs/d/a` class was also isolated from the verified readable JAR and
tested both ways:

- default Procyon: success, no stderr, one Java file, about 124 KB
- `-eml`: success, no stderr, same Java size

So `-eml` does not itself regress the known pathological class.

## Project-only source-quality probe

A research-only JAR containing exactly the **1,129 project-owned classes** was decompiled with
the full verified readable JAR on Procyon's classpath for dependency resolution.

Before the local tool execution ceiling interrupted the pass:

- emitted project Java files: **201**
- emitted source bytes: **2,151,131**
- stderr bytes: **0**
- Procyon failure-marker hits in emitted project source: **0**

R5A static-readiness logic reported only two high findings:

1. `rs/A/q.java` — `multiple_public_top_level_types`
2. `rs/a/a/a.java` — `multiple_public_top_level_types`

Both are false positives. The files contain one public top-level class plus public **nested**
interfaces/enums. R5A's regex is line-based and does not track brace depth, so an indented
`public interface` or `public enum` inside the outer class is misclassified as a second
top-level public type.

That gives two concrete Core follow-ups:

1. scope decompiler-failure readiness to project-owned source (or separate dependency
   decompiler quality from project readiness);
2. make public-top-level type detection brace/AST aware rather than regex-only.

## R8 fallback -> R6A identity loss

The same 201-file real source probe was passed through R6A source-symbol inventory.

Result:

- source methods: **1,803**
- source symbols: **9,308**
- canonical method matches: **846**
- ambiguous canonical method matches: **329**
- methods with no canonical owner: **512**
- methods with no canonical method ID: **957**

Of the **512** methods with no canonical owner, **461** are in
`recovered/spawnpk/fallback/CLIENT_CLASS_*`.

Cause:

R6A maps ACCEPTED classes to the readable semantic namespace, but maps every non-accepted
class back to its original `rs/**` owner. R8A/R8C have moved 85 non-accepted classes into the
fallback namespace, so R6A currently cannot map those recovered owners back to their stable
`CLIENT_CLASS_*` identity.

This is a cross-stage compatibility gap between R8A/R8C and R6A. A future Core fix should
consume the readable namespace/fallback mapping (or equivalent exact authority) rather than
reconstructing readable owners from semantic status alone.

## Real R6 source-name intelligence probe

On the same partial real source inventory, Chat 2's source-name producer emitted **440**
non-canonical candidates:

- parameters: **4**
- ordinary locals: **178**
- catch variables: **241**
- resource variables: **4**
- enhanced-for variables: **13**

All four accepted friend/ignore methods resolve correctly and produce the expected
`nameKey` parameter candidates at confidence **0.97**.

R6G/R6H exact AST flow found:

- direct `this.field = symbol` relations: **384**
- direct `local = this.field` relations: **340**
- total observed direct relations: **724**
- accepted-field bindings: **0**
- flow ambiguities: **0**

The zero matched bindings are not a scanner failure: **622** observations target fields that
are not currently ACCEPTED semantic fields, and **102** observations belong to source methods
that do not match the partial inventory context. The current accepted field set simply does
not yet intersect these direct-flow patterns.

## Boundary

These are research findings only.

Chat 2 does not:

- weaken R5A/R5D gates;
- accept the local member-safety decision canonically;
- promote any R3-R12 semantic proposal;
- mutate Core namespace/source-readiness behavior;
- claim the partial recovered source is a canonical R5 workspace.

The findings are intended as exact evidence for the next Main/Core source-recovery hardening
step while Chat 2 continues semantic/source-name intelligence.
