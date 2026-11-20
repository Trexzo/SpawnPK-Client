# R435 — exact R422 JVM ownership-response protocol

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R434 draft PR #1230  
**State:** DRAFT / UNMERGED. Public acceptance tooling, no release.

## Concrete problem

R422's real owner-private cross-JVM harness parsed some successful ownership and release responses with substring checks, for example `"RELEASED" in released_stdout`. This also accepts `NOT_RELEASED`, `UNRELEASED` and similarly `NOT_ACQUIRED` for acquisition checks if a failed JVM or future harness prints a misleading status token. Because R432 treats all 17 R422 named checks as necessary acceptance evidence, ambiguous protocol matching could yield a false pass. The current Java harness normally prints exact values, so this is a latent acceptance weakness, not proof of an actual failure.

## R435 behavior

The public `tools/r422/run_private_store_acceptance.py` adds `exact_stdout_protocol(output, *expected)`. It requires **complete, exact, ordered stdout lines with a trailing newline**, permitting only the platform's LF or CRLF sequence. It refuses missing, truncated, extra, misordered, negated, prefixed, suffixed, whitespace-padded and duplicate records. No stderr fragment can authorize a successful ownership check.

Applied to seven real R422 acceptance checks: contested-owner refusal (`REFUSED_OWNER`); holder shutdown (`RELEASED`); reacquire after shutdown (`ACQUIRED`, `RELEASED`); crash (`ACQUIRED` with exit code 77); reacquire after crash; fresh leaf acquisition; and outstanding-marker evidence preservation. The initial live holder handshake remains R434's exact `ACQUIRED` equality under a ten-second startup deadline.

R422's 17 named check labels, 73-assertion minimum, actual class SHA pin, OS-lock tests, R415/R417 persisted intent / write-block policy and R432 release gates are unchanged. This PR does not install the speculative R429 ledger.

## Evidence / CI

- Eleven focused tests exercise normal LF/CRLF output, deceptive negative substrings, duplicate/reordered/extra/missing records, invalid inputs, actual R422 call-site wiring, exact 17 required receipt names, and real Python subprocesses on the host OS.
- A new Windows/Ubuntu × Python 3.11/3.13 matrix also rechecks inherited R434 startup timeout, R433 producer contracts and R432 public gates.
- The existing R422 synthetic workflow is triggered by changes to its runner. No owner-private recovered Java class, game runtime or actual loot history is available in hosted CI.

**Until GitHub confirms the exact final R435 HEAD, do not claim a fully passing build.** Public mock and process tests are not proof of live client acceptance.

## Remaining owner-only gates

Private R424/425 full-source overlay compilation with pinned source and JAR hashes; R432 actual private 39+ / 73+ Store assertions and 17 cross-JVM checks; R427–R431 real LootHistoryStore/LootTrackerPlugin asynchronous deletion integration; real Swing lifecycle and v312 restart testing. Existing intent markers must not be removed, and writes must stay fenced until a separately proven restart adoption/ack mechanism exists. No merge, deployment, deletion, or history cleanup authorized.
