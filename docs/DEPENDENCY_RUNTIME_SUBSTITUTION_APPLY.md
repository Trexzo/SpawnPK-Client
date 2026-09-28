# R8DEP38 runtime dependency substitution apply

R8DEP38 turns a **private, verified R8DEP37 substitution plan** into a
deterministic runtime postimage and independently verifies that postimage.

It does not merge third-party JARs into a new fat JAR. The output runtime is:

```text
postimage/
  residual-dependency-capsule.jar
  official/
    <exact official dependency jars>
  DEPENDENCY-RUNTIME-SUBSTITUTION.json
```

Keeping official artifacts separate matches normal JVM classpath semantics and
avoids treating ordinary duplicate resources such as `META-INF/MANIFEST.MF`
as class identity collisions.

## Apply prerequisites

The private R8DEP37 plan must:

- use schema version 2;
- include private identifiers;
- have a valid deterministic `DEPRUNTIMESUBPLAN_*` ID;
- bind the exact bundled/readable JAR SHA;
- bind the exact complete official-artifact SHA set;
- report `preimage_verified=true`;
- report `official_artifacts_verified=true`;
- report `collision_free=true`;
- contain no blocking class collisions.

R8DEP37 still keeps `apply_authorized=false`; R8DEP38 independently verifies
that boundary and then performs the explicit apply operation.

## Postimage guarantees

The residual capsule:

- contains every non-removed bundled file entry byte-for-byte;
- excludes every exact class/resource removal listed by R8DEP37;
- is written in sorted path order with fixed ZIP metadata and stored entries,
  making the residual JAR byte-deterministic across supported hosts.

The official runtime artifacts:

- are copied byte-for-byte from the exact supplied official JARs;
- are checked against the private plan's artifact names and SHA-256 values;
- remain separate JARs in the runtime classpath.

The postimage verifier re-opens the residual capsule and proves its complete
entry→payload map equals the exact expected retained preimage. It also re-hashes
and byte-compares every required official JAR.

The manifest is first written with `verified=false`. Only after the independent
postimage verification succeeds is it rewritten with `verified=true`, then
verified once more through the public verifier path.

## Resource overlap versus class collision

Separate classpath JARs commonly contain the same non-class resource path.
R8DEP38 therefore distinguishes:

- **class collisions** (`*.class`) — blocking;
- **resource overlaps** — recorded as informational unless a prior resource
  equivalence gate says the resource itself must be replaced.

This prevents harmless metadata overlaps from blocking an otherwise valid
runtime while retaining strict duplicate-class safety.

## Commands

Apply:

```powershell
spk-dependency-runtime-substitution-apply apply `
  .\private\runtime-substitution-plan.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out-dir .\generated\dependency-runtime-postimage
```

Verify an existing postimage:

```powershell
spk-dependency-runtime-substitution-apply verify `
  .\private\runtime-substitution-plan.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out-dir .\generated\dependency-runtime-postimage
```

This generic tooling still does **not** claim that exact v308 has passed the
private substitution gate. That claim requires running the private exact-v308
authority chain with the user's exact JAR/artifacts and preserving the resulting
postimage verification evidence.
