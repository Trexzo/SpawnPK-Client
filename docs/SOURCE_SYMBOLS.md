# R6A source symbol inventory

R6A inventories source-level parameters and local declarations from one verified recovered
source workspace.

The exact v308 client does not contain original local-variable or parameter names. These
records therefore represent **source-level identities for inferred replacement names**,
not recovered original identifiers.

## Parser

The scanner uses the JDK compiler AST APIs (`com.sun.source.*`) instead of source-text
regular expressions.

It distinguishes:

- method parameters
- ordinary local variables
- catch variables
- try-with-resources variables
- enhanced-for variables
- lambda parameters

Fields are excluded because fields already have canonical `CLIENT_FIELD_*` identities.

## Stable source IDs

Methods receive:

`SRC_METHOD_<20 hex>`

Source symbols receive kind-specific IDs such as:

```text
SRC_PARAM_<20 hex>
SRC_LOCAL_<20 hex>
SRC_CATCH_<20 hex>
SRC_RESOURCE_<20 hex>
SRC_ENHFOR_<20 hex>
SRC_LAMBDA_PARAM_<20 hex>
```

For an unchanged source workspace the inventory is deterministic.

When a readable source method maps uniquely to a canonical `CLIENT_METHOD_*`, that stable
member ID is attached. Overload ambiguity remains unresolved rather than guessed.

## Authority gate

Before scanning, R6A recomputes the Java source-tree SHA-256 and file count and requires
both to match the R4C recovered-source manifest.

## CLI

```powershell
spk-source-symbols `
  .\recovered-source-manifest.json `
  .\src `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  --build-id v308 `
  --out .\source-symbols.json
```

If the readable semantic namespace used a custom class target package, pass the same
package using `--target-package`.

R6B may attach non-canonical naming candidates to these IDs. R6C owns explicit acceptance
and deterministic source rewriting.
