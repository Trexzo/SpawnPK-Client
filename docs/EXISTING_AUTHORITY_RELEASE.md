# R7B one-command existing-authority release

R7B composes the already-tested R4/R5 stages for one exact build whose class/member
authority and semantic acceptance already exist.

```text
exact client + canonical lineage
  -> readable verified JAR
  -> hash-pinned recovered source
  -> source readiness + build authority
  -> clean project rebuild
  -> round-trip verification
  -> R7A recovery release manifest
```

The command does not accept semantic candidates or weaken any safety gate.

## Command

```powershell
spk-release-build `
  .\client-v308.jar `
  .\authority\v308-index.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\tools\cfr.jar `
  --decompiler-sha256 <PINNED_SHA256> `
  --engine cfr `
  --build-id v308 `
  --out-dir .\generated\release-v308
```

Optional class/member safety acknowledgements remain explicit.

## Official-first dependency compile

After R8DEP18, the same release command can explicitly select the
official-API compile / bundled-runtime restoration path. The inputs remain
external authority artifacts; private replacement/reverse plans are passed by
path and are never copied into the public release report.

```powershell
spk-release-build `
  .\client-v308.jar `
  .\authority\v308-index.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\tools\cfr.jar `
  --decompiler-sha256 <PINNED_SHA256> `
  --engine cfr `
  --build-id v308 `
  --project-source-only `
  --official-first-restored `
  --official-overlay-manifest .\private\overlay-manifest.json `
  --official-overlay-source-root .\private\overlay-src `
  --private-dependency-replacement-plan .\private\replacement.json `
  --private-dependency-reverse-plan .\private\reverse.json `
  --official-artifact .\deps\official-a.jar `
  --official-artifact .\deps\official-b.jar `
  --out-dir .\generated\release-v308
```

The opt-in requires `--project-source-only` because the derived official
overlay compiler accepts only project Java sources. It then forwards into the
fail-closed clean-rebuild authority gate. Official artifacts are compile-only, generated project bytecode is restored to bundled
dependency identities, and runtime dependency bytes remain the original
verified readable-client bytes. The release run records only safe transport
authority IDs, not private plan contents or paths.

A safety or compilation blocker is a normal result:
`release-run.json` is written with `ready_for_release=false` and exit code 3.

Hash mismatch, malformed authority, stale decompiler pin, or inconsistent canonical state
refuses the run with exit code 2.
