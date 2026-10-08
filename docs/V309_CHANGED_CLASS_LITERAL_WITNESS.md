# v309 changed-class globally unique literal witness (research-only)

The accepted v309 field frontier remains **143 unresolved**. The existing
descriptor-class SHA / structural-SHA replay cannot identify all eight
descriptor-blocking proposed class pairs when the classes genuinely change.

This independent research lane tests whether each proposed new class retains
**globally unique JVM String constants** from the accepted old class:

1. First verify tracked GitHub `frontier.json`, class lineage and global
   report SHA-256, and the two pinned exact private JAR hashes.
2. Index the *entire* v308 and v309 client archives in memory, requiring zero
   class parse errors and exactly 10,472 / 10,502 class entries respectively.
3. Recompute all **eight** unproven class dependencies directly from the
   accepted global 143-field report (26 descriptor-veto relationships).
4. Count String literals once per class across each whole archive. Consider
   only constants at least six characters long and not whitespace-only.
5. Accept a **research candidate** only when at least three literals occur in
   exactly one class on each side, all point to the expected proposed new
   descriptor class, no other new class receives even one surviving globally
   unique old-class witness, and class entry/structural hashes actually differ.
6. Persist only the deterministic aggregate report: no literals, no client
   bytes, no complete indexes or canonical identity changes. A newly created
   output path is required; existing files are not overwritten.

Run from a checkout with the actual pinned private JARs:

```powershell
python -m spk_recovery.v309_changed_class_literal_witness `
  --v308-jar "C:\private\exact-v308-client.jar" `
  --v309-jar "C:\private\exact-v309-client.jar" `
  --out "$env:TEMP\v309-literal-research-new.json"
```

Those are illustrative paths, **not known paths**. Do not put the exact JARs,
raw indexes, or raw string constants on GitHub. Treat the generated report
as private evidence.

This is strictly an **independent class research clue**, not proof of class
identity. Multiple constants can be emitted by one source/initializer and
thus correlate. Even many globally unique literals may be moved together by
transformations. Candidates must go through the ordinary independent exact
bytecode, canonical class-lineage review, dependent field replay and explicit
acceptance gates. No automatic member mapping or reduction of 143 unresolved
fields is permitted.

The three pairs with no surviving constants may require separate exact
caller, declaration and method-context evidence. This module does not
replace the two-lane #868 dual-bundle command and does not alter its three
file contract or offline verifier.
