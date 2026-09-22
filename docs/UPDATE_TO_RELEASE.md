# R7C future update to release

R7C connects the R3 update migration pipeline to the R7 release pipeline.

```text
previous exact authority + new client.jar
  -> R3 migration / focused review queue
  -> authority-candidate gate
  -> immutable new authority snapshot
  -> accepted class/member semantic carry-forward
  -> R7B readable/recovered-source release
```

The workflow only crosses each boundary when the previous stage proves it is safe.

## Command

```powershell
spk-update-release `
  .\authority\v308-index.json `
  .\authority\v308.snapshot.json `
  .\client-v309.jar `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\tools\cfr.jar `
  --decompiler-sha256 <PINNED_SHA256> `
  --engine cfr `
  --old-build-id v308 `
  --new-build-id v309 `
  --new-build-number 309 `
  --member-candidates .\research\v308-to-v309.members.json `
  --old-jar .\client-v308.jar `
  --out-dir .\generated\update-v309
```

If migration is unresolved, the command stops at `terminal_stage=migration` and preserves
the focused R3 review workspace. If accepted class/member semantic identity cannot be
carried, it stops at `semantic_carryforward`. Otherwise it runs the R7B release path.

R6 parameter/local inferred-name carry-forward is intentionally a post-source extension:
it requires the new recovered-source symbol inventory and never blocks promotion of the
underlying exact binary/class/member authority.
