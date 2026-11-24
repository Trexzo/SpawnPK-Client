# R466 — selective hierarchy caching from exact reference overlap

Parent: R465 draft PR #1266, exact head d0de6affa3552144d21d2714f900f386b0e7e177.
Status: DRAFT / UNMERGED / SYNTHETIC CI ONLY.

## Why

R465 showed reduced R454 ancestry and member lookup work when the R455
constant-pool references and R456 decoded opcode targets overlap.
Its no-overlap control showed that forced R464 cache creation adds overhead
when there are no reusable results.

R466 changes ONLY whether optional transient R464 hierarchy memoization
is enabled in the consolidated static analysis. The original independent
R455/R456 semantic checks and refusals remain untouched.

## Gate

The selector examines decoded R456 Site.target entries and R453
ClassMembers.references in rebuilt classes. An eligible target must match
the exact Member owner/name/descriptor/kind, with an owner in the combined
selected/rebuilt graph and outside platform roots.

At least 16 distinct exact matching targets are required by default.
No modeled opcode sites skip immediately, without inspecting references.
Fewer than 16 eligible distinct targets skip without reference scans.
A positive probe stops once 16 distinct matches are found. Invalid hints
and a bounded-scan budget disable optimization, not analyzer validation.

The optional R459 hierarchy_selector callback must return a literal bool
and requires an accompanying hierarchy_factory. No selector means the
legacy R459/R463 path remains unchanged. R464 class-record identity and
ancestry-chain admission still run when the cache is selected. The R454
rebuilt-only graph remains independently checked.

## Tests

Synthetic cases cover the exact 16 threshold, 8 low-overlap targets,
24/96/192 overlapping owners, 96-owner no-opcode negative control,
forged mismatched Member hints, unsupported inputs and probe budgets,
R459 full-public/private audit parity, and selector configuration refusal.

The R466 in-memory benchmark compares three modes on identical fabricated
class graphs: independent, always-cached, and adaptive selection. Adaptive
timing includes the selection probe. All complete public and private
synthetic outputs must be identical, and both unchanged and negative-control
paths are measured. Two counterbalanced trials per case by default on
Windows/Ubuntu × Python 3.11/3.13. Inherited R465-R442 safety suites run
as separate steps.

Run locally with no owner inputs:

    python -B tools/r466/benchmark_adaptive_hierarchy.py --pairs 2

The synthetic benchmark opens no game JAR or real reconstructed source;
it does not run SHA scans itself, read game history, or execute Java.
The inherited R464/R459 audit tests still cover source/class/dependency
SHA admission, pinned v309 JAR and final consistency checks. Real owner-PC
performance, complete historical R421 source provenance, full source/assets,
client compilation, runtime compatibility, FPS and network latency remain
unverified. No production write-fence change, merge, release or promotion.
