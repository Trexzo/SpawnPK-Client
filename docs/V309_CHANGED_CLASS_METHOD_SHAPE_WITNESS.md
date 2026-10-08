# v309 changed-class method-shape research — no automatic identity acceptance

The v309 accepted frontier is **143 unresolved field relationships**. Existing
same-entry-SHA and same-structural-SHA class witnesses do not cover all eight
descriptor-blocked class hypotheses because the candidate class bytes and
structural digests changed. A separate globally unique String-literal research
lane covers some candidates, but other classes have zero stable literal anchors.

This new **independent research lane** compares exact class method/field
structure from the *full* v308/v309 private JAR class indexes without
decompiling, executing, or publishing the client.

## Exact research criteria

1. Verify the pinned tracked frontier, SHA-256 of the accepted class lineage
   and field report, both exact JARs, and full parse-error-free **10,472**
   old / **10,502** new class indexes.
2. Rebuild the eight unaccepted descriptor-blocked class groups directly
   from the accepted global 143-field report; verify the exact old class
   entry and structural fingerprints against v308 canonical lineage.
3. Require the proposed new class to be unowned, and both raw and structural
   class SHA fingerprints to differ.
4. Require **exact equality** of the multiset of field-access flags and
   JVM-erased field descriptor shapes, with at least two fields.
5. Exclude constructors, class initializers, and native/abstract members from
   method evidence. Match a multiset of method-access flags, JVM-erased
   descriptors, and **exact Code attribute lengths**. Require three
   common code-bearing method shapes and a multiset Jaccard overlap of
   **at least 0.75**.
6. Search every class in each whole archive that has the same field-shape
   multiset. The proposed pair must be the **only qualifying pairing in
   both directions**. Any competing old/new class causes refusal, not a
   confidence-score promotion.
7. Output only class IDs already in the GitHub research queue, compact
   aggregate counts, scores, and rejections. Do not emit bytecode, method
   descriptors, class indexes, private JARs, or canonical identity updates.

For the three private exploratory pairs with zero surviving globally unique
literals, a separate bounded method-structure scan observed the following
noncanonical research overlap (not an official replay result):

| Old logical class | Common/union code-bearing shapes | Jaccard |
| --- | ---: | ---: |
| `CLIENT_CLASS_000486` | 27 / 28 | 0.9643 |
| `CLIENT_CLASS_000943` | 3 / 4 | 0.7500 |
| `CLIENT_CLASS_000965` | 20 / 22 | 0.9091 |

The proposed new class in each case was the only match under this probe's
filter in either direction. The official command and its hosted tests must
still be verified; this table does **not** establish canonical identities.

## Private run

Run from an exact repo checkout with the user's SHA-pinned private JARs:

```powershell
python -m spk_recovery.v309_changed_class_method_shape_witness `
  --v308-jar "C:\private\exact-v308-client.jar" `
  --v309-jar "C:\private\exact-v309-client.jar" `
  --out "$env:TEMP\v309-method-shape-new.json"
```

Paths are examples, not claims about the local machine. The output path must
be new and must not collide with an input.

**Proof boundary:** method descriptors, field shapes and Code lengths may
coincide even for unrelated classes. Whole-archive mutual uniqueness is
research evidence, not a bytecode-equivalent or semantic identity proof.
Independent canonical method/caller-context review and explicit class/member
acceptance are still required. This tool never removes any of the 143
unresolved relationships or changes historical exact-v308 authority.
