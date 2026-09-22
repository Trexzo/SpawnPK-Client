# R2 Chat 2 — v308 semantic class risk preflight

All **32 current Chat 2 class semantic candidates** were checked against the exact-build
risk categories introduced by R2A.

Exact v308 authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

For every current semantic class coordinate:

- exact class-name literal hits elsewhere in the JAR: **0**
- non-class resources under the source class package: **0**

This includes the original nine candidates plus the 23 dossier-driven additions.

Combined R2A-style summary:

```text
mapped_classes                  32
literal_class_name_hit_count     0
package_resource_hit_count       0
service_descriptor_count         2
manifest_requires_review         true
```

The two service descriptors are global JAR entries:

- `META-INF/services/com.fasterxml.jackson.core.JsonFactory`
- `META-INF/services/com.fasterxml.jackson.core.ObjectCodec`

The manifest-review flag is the generic R2A rule for any non-empty class remap. No current
candidate source class appears as an exact surviving class-name string literal, and none
sits in a source package containing a non-class resource.

## Current class candidate set

The 32 source classes are:

```text
rs/i/b
rs/n/c/G
rs/n/c/O
rs/n/c/U
rs/n/c/V
rs/n/c/a
rs/n/c/aC
rs/n/c/aD
rs/n/c/aG
rs/n/c/aH
rs/n/c/aI
rs/n/c/aL
rs/n/c/aX
rs/n/c/aY
rs/n/c/ab
rs/n/c/ad
rs/n/c/am
rs/n/c/ap
rs/n/c/av
rs/n/c/aw
rs/n/c/b
rs/n/c/c
rs/n/c/c/a
rs/n/c/h
rs/n/c/i
rs/n/c/l
rs/n/c/m
rs/n/c/o
rs/n/c/p
rs/n/c/s
rs/n/c/v
rs/n/c/z
```

## Consequence

R2C2 may resolve and explicitly accept these semantic names without mutating bytecode.
If a later class-remap specification uses accepted class names, the current R2B
fail-closed checks would not require:

- `rewrite_class_name_strings`
- `allow_package_resource_risk`

for these 32 class mappings based on the present exact-v308 risk categories.

This is a preflight finding only. Chat 2 does not authorize semantic acceptance or execute
a remap.
