# R2D transformed verification + decompiler handoff

R2D turns the transformed client into a reproducible validation/decompilation workflow.

## Independent transformed-JAR verification

`verify-remap` does not trust the remapper's own success result. It re-indexes the
produced JAR and independently checks it against the original exact-build index plus the
class/member plans.

Checks include:

- exact source-plan SHA agreement
- entry-count preservation
- zero class parse errors
- renamed source class paths absent
- target class paths/internal names present
- renamed field/method declarations present
- stale source member signatures absent
- descriptor types adjusted for simultaneous class renames
- manifest `Main-Class` resolves to a class in the output JAR
- bundled `rs/**` / `recovered/**` service providers still resolve

Example:

```powershell
spk-recovery verify-remap `
  .\evidence\indexes\v308.json `
  .\generated\client-v308-readable.jar `
  --class-plan .\generated\v308.class-remap-plan.json `
  --member-plan .\generated\v308.member-remap-plan.json `
  --out .\generated\v308.verify.json
```

A failing report exits non-zero.

## Decompiler handoff

The project intentionally does not vendor CFR, Vineflower, or another third-party
decompiler JAR.

Instead, `decompile` requires an exact SHA-256 for the locally supplied decompiler:

```powershell
Get-FileHash -Algorithm SHA256 .\tools\vineflower.jar

spk-recovery decompile `
  .\generated\client-v308-readable.jar `
  .\tools\vineflower.jar `
  --decompiler-sha256 <EXACT_SHA256> `
  --engine vineflower `
  --out-dir .\generated\decompiled-v308 `
  --result-out .\generated\decompiled-v308.result.json
```

CFR is also supported:

```powershell
spk-recovery decompile `
  .\generated\client-v308-readable.jar `
  .\tools\cfr.jar `
  --decompiler-sha256 <EXACT_SHA256> `
  --engine cfr `
  --out-dir .\generated\decompiled-v308
```

The output directory must be empty unless `--clean-out` is explicitly supplied. The
adapter refuses a decompiler hash mismatch and refuses success if no `.java` files were
created.

Decompiler output remains generated evidence, not canonical recovered source. Promotion
into `recovered-src/` should happen only after naming/provenance review and build parity
work.
