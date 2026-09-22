# R5B — dependency and Java toolchain authority

R5B separates evidence that is easy to accidentally conflate during source recovery.

## Command

```powershell
spk-build-authority `
  .\client-v308.jar `
  .\authority\v308-index.json `
  --source-readiness .\generated\source-v308\source-readiness.json `
  --class-prefix rs/ `
  --out .\generated\source-v308\build-authority.json
```

## Evidence classes

### Original bytecode level

Classfile major versions come directly from the exact indexed authority JAR.

For example, class major 53 means Java 9 bytecode.

This proves the bytecode release level of those classfiles. It does not prove which JDK vendor or exact compiler build the original developer used.

### Embedded Maven metadata

The tool extracts `META-INF/maven/**/pom.properties` and matching embedded `pom.xml` entries when present and records exact hashes.

This proves those metadata strings/files are embedded in the authority archive.

It does **not** automatically prove:
- the original top-level dependency graph;
- whether an artifact was a direct or transitive dependency;
- whether the archive was shaded/assembled from that exact POM.

### Root build metadata

Root-level `pom.xml`, Ant/Gradle files and IntelliJ `.iml` files are separately inventoried and hash-pinned if the archive contains them.

### Rebuild compiler runtime

The resolved `java` and `javac` executables are probed and their version output/path/binary SHA are recorded when available.

This is the toolchain used by **our rebuild**, not a claim about the original SpawnPK developer environment.

### Recovered-source dependency surface

R5A external import roots can be carried into the manifest as discovery evidence. Import roots are not automatically mapped to Maven coordinates.

## Why this boundary matters

R5C can use this manifest to construct a reproducible compile harness while still labeling exact archive evidence separately from inferred dependency resolution.
