# R5D — clean SpawnPK project rebuild

R5D removes the R5C **project binary fallback**.

The goal is not to rebuild every shaded third-party library from decompiled source.
The goal is to prove that SpawnPK project classes themselves compile from recovered source
without any SpawnPK classfile being supplied on the compiler classpath.

## Dependency capsule

The verified readable client JAR is split into:

- project classes: every prefix published by R4B `project_source_prefixes` — normally original `rs/**`, the accepted semantic target package, and any enabled source-safety fallback package;
- non-project classes: bundled dependency bytecode.

R5D writes a deterministic `dependency-capsule.jar` containing only non-project classfiles.

No project class is allowed into the capsule.

R5D consumes the manifest-owned prefix set by default. If an older readable manifest says
source-safety fallbacks exist but does not publish `project_source_prefixes`, R5D fails
closed rather than silently treating fallback-remapped SpawnPK classes as dependencies.
Explicit `--source-prefix` overrides remain available for reviewed/manual workflows.

## Compile

All recovered project Java files are compiled together with:

- exact R5B `javac` toolchain;
- R5B bytecode release target when present;
- dependency capsule as the only binary classpath;
- empty sourcepath;
- deterministic `javac @argfile` so Windows command-line length is not a limiter.

## Class-set gate

Compilation success is not enough.

The generated project class entry set must exactly equal the project class set in the
verified readable authority:

- no missing project classes;
- no unexpected project classes.

Only then is `rebuilt-client.jar` produced.

The rebuilt JAR combines:

- newly compiled SpawnPK project classes;
- exact retained non-project dependency classes;
- exact retained resources/manifest from the readable authority.

## Command

```powershell
spk-clean-rebuild `
  .\generated\source-v308\recovered-source-manifest.json `
  .\generated\source-v308\source-readiness.json `
  .\generated\readable-v308\readable-client-manifest.json `
  .\generated\readable-v308\readable-client.jar `
  .\generated\source-v308\build-authority.json `
  .\generated\source-v308\src `
  --out-dir .\generated\source-v308\clean-rebuild
```

A successful report states:

```text
clean_project_build=true
project_binary_fallback_count=0
all_dependencies_rebuilt_from_source=false
```

The last line is intentional: external/bundled dependency binaries remain dependencies.
R5E compares the newly compiled project bytecode against the readable authority and detects
semantic/structural drift.
