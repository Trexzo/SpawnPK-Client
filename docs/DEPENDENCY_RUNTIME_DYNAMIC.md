# R8DEP27 dynamic runtime loading inventory

R8DEP27 inventories exact bytecode callsites that can expand runtime behavior
beyond the static dependency closure.

It consumes an R8DEP26 runtime-resource authority plus the exact bundled/readable
JAR and verifies that both are bound to the same JAR bytes.

The current inventory recognizes calls to:

- `Class.forName`;
- `ClassLoader.loadClass`;
- `MethodHandles.Lookup.findClass`;
- `ServiceLoader.load`;
- `System.load` and `System.loadLibrary`;
- `Class.getResource` / `getResourceAsStream`;
- `ClassLoader.getResource`, `getResources`, and `getResourceAsStream`.

Private reports include exact caller class, caller method/descriptor, bytecode
offset, invocation kind, and invoked owner/name/descriptor. Public reports use
stable callsite IDs and category/classification only.

## Target-proof boundary

R8DEP27 does **not** infer targets from nearby string constants.

Even code such as:

```java
Class.forName("example.Target");
```

is reported as unresolved until a dedicated bytecode stack/data-flow proof
establishes that the literal is the actual invocation argument. Same-method or
same-class string proximity is not authority.

Native-load calls are separately classified as `native_load_dynamic`.

The report always keeps:

- external/native reflection absence unproven;
- unresolved dynamic targets explicit;
- `runtime_capsule_mutation_ready=false`.

## Command

```powershell
spk-dependency-runtime-dynamic `
  .\generated\dependency-runtime-resource.json `
  .\generated\readable-client.jar `
  --out .\generated\dependency-runtime-dynamic.json
```

Use `--include-identifiers` only for private exact callsite inspection.
