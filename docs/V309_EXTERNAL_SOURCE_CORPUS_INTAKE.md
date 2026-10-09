# External v309 source corpus intake and Source M1 status

The independently supplied decompiled SpawnPK source ZIP is useful as an **unverified v309 candidate**, not a substitute for the JAR-bound recovery pipeline or a certified source release. This intake is deliberately separate from the existing `recovered-source/<build>/` publication gate.

## Input and measured local evidence (2026-10-09)

- External source ZIP SHA256: `3a3b84a03f9cc6588a714b03f8b36ae3a7008ce4976de2609841fdf9db9e80ad`.
- Independent original client v309 SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Auxiliary deob pipeline ZIP SHA256: `a4a5db25ee916885462a8b5efc946b9541154d2f0106df0b33b8ff58e27d17c7`.
- Corpus declares Java build number 309. It includes 1,270 Java files (1,265 under `rs/`) and 427 resources, compared with 10,502 original client .class entries.
- Exactly 28 source Java paths have unchanged path-equivalent original class entries. Paths alone **do not** prove class identities.
- Cross-checked all **1,092** accepted v309 class-entry SHAs against the original JAR: **26** of those 28 direct-path original classes have preaccepted binary logical IDs. The two still-unaccepted direct-path originals are `rs/Client.class` and `rs/gui/Launcher.class`; all **15** documented Loot Tracker original classes remain outside the accepted v309 class-ID set. Even accepted *binary* class identity does **not** prove that the separately modified candidate Java source reconstructs its bytecode.
- Its edited Loot Tracker documentation cites 15 original raw class names present in the exact v309 JAR, but document-proposed renames, one-to-many merges, and absent counterparts are **not** accepted mappings.
- A local clean-source `javac --release 11 -proc:none` attempt **failed** on missing third-party code/packages; original client class bytecode was not used as a fallback. The candidate build references an absent `libs/vendored-unidentified.jar`.

No original JAR, decompiled corpus, generated Java files, raw Code bytes, decoded CP values, or proprietary source are added to Git by this change. Only public-safe aggregate and a gated reusable intake tool are committed.

## Reproducible local inventory

Using a clean Python 3.11+ checkout with both **local private** input files:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.v309_external_source_corpus_intake `
  --source-zip 'C:\path\to\SpawnPk-Decompiled-main.zip' `
  --original-jar 'C:\path\to\exact-v309-client.jar' `
  --source-sha256 '3a3b84a03f9cc6588a714b03f8b36ae3a7008ce4976de2609841fdf9db9e80ad' `
  --original-sha256 'ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38' `
  --out 'C:\private\new-v309-source-intake.json'
```

The output path must not already exist. The result is **research-only** and contains only class/file counts, source and JAR hash pins, a content-derived report ID, and zero mapping acceptances. An unchanged name or an edited markdown mapping never auto-accepts a semantic identity.

## Next gates — two independent source tracks

**1. v308 canonical Source Milestone 1:** `recovered-source/v308/src/` is currently **not published**. Run the existing exact v308 Source M1 gate at an exact recovery-tooling commit, resolve the measured clean-source Java compiler frontier with no project binary fallback, independently verify source-to-class set, and publish to `recovered-source/v308/` only when `publishable=true`. Historical last measured source compiler frontier had 98 errors; that is **not** a fresh rerun or a release pass.

**2. v309 independently supplied Java source candidate:** preserve the ZIP outside Git; build an exact-original-class → renamed candidate source crosswalk with explicit evidence and no unsafe one-to-many promotion. Independently classify bundled manual plugins vs decompiled binary-backed classes. Reconstruct an evidence-backed dependency capsule and achieve a zero-original-project-binary-fallback Java 11 compile before class-set and method/bytecode equivalence review. Only after v309 canonical class/member authority is explicitly accepted and Source Milestone publication gates pass can a `recovered-source/v309/` directory be published.

The separate `spawnpk-deob-master` Maven/ASM/Vineflower/CFR pipeline offers possible compiler repair strategies, not accepted original client semantic mappings. Its class-name, lambda, bridge, and compiler-fixer transformations need isolated reproducible tests before integration with the trusted Source M1 recovery toolchain.

**Current protected frontier:** v309 `ACCEPTED_INCOMPLETE` with 143 unresolved field relationships including 26 descriptor blockers; 0 new class, member, or field acceptances.
