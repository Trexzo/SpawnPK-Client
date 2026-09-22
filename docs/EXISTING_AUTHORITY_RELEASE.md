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

A safety or compilation blocker is a normal result:
`release-run.json` is written with `ready_for_release=false` and exit code 3.

Hash mismatch, malformed authority, stale decompiler pin, or inconsistent canonical state
refuses the run with exit code 2.
