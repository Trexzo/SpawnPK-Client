# R6D rewritten-source rebuild acceptance

R6C proves that an explicitly accepted inferred parameter/local name can be applied using
javac semantic element resolution.

R6D proves whether that rewritten source still survives the project's binary regression
gates.

## Authority model

Source-name changes do **not** create a new binary authority.

R6D keeps:

- the exact original client JAR + exact index as bytecode/toolchain authority;
- the verified readable client JAR as the clean-rebuild and round-trip authority;
- the R6C output tree as a derived recovered-source workspace.

A deterministic `SRCWSR_*` workspace ID is created for the rewritten source tree.

## One-command acceptance chain

`spk-source-rewrite-accept` runs:

1. rewritten source-tree SHA verification;
2. derived recovered-source manifest generation;
3. R5A source-readiness audit;
4. R5B toolchain/dependency authority generation;
5. R5D clean project rebuild;
6. explicit check that project binary fallback is zero;
7. R5E round-trip structural verification;
8. one `SRCACCEPT_*` report.

`accepted=true` requires:

- clean rebuild status `complete`;
- `clean_project_build=true`;
- `project_binary_fallback_count=0`;
- R5E `rebuild_authority_candidate.ready=true`;
- zero R5E semantic-surface blockers.

Compilation success by itself is not enough.

## Command

```powershell
spk-source-rewrite-accept `
  .\source-v308\recovered-source-manifest.json `
  .\source-v308-renamed\source-rewrite-manifest.json `
  .\source-v308-renamed\src `
  .\client-v308.jar `
  .\authority\v308-index.json `
  .\readable-v308\readable-client-manifest.json `
  .\readable-v308\readable-client.jar `
  --out-dir .\generated\source-v308-renamed-acceptance
```

The command returns exit code 0 only for an accepted source state, 3 for a completed but
rejected gate, and 2 for malformed/stale authority input.

## Output

The workspace contains:

```text
rewritten-source-manifest.json
source-readiness.json
build-authority.json
clean-rebuild/
  clean-rebuild.json
  dependency-capsule.jar
  rebuilt-client.jar       (only when clean build succeeds)
roundtrip-verification.json (only when clean build succeeds)
source-rewrite-acceptance.json
```

Generated JARs and recovered source remain outside the public Git repository.

An accepted source rename is still an **inferred readable replacement**, never a claim
that the lost original local/parameter identifier was recovered.
