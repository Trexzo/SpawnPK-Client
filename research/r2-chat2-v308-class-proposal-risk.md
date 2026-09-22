# R2 Chat 2 — v308 semantic class risk preflight

All **73 current Chat 2 class semantic candidates** were checked against the exact-build
risk categories introduced by R2A.

Exact v308 authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

Across all 73 source classes:

- exact class-name literal hits elsewhere in the JAR: **0**
- non-class resources under the source class package: **0**
- global service descriptors: **2**
- manifest review: **required** by the generic R2A rule for any non-empty class remap

Combined R2A-style summary:

```text
mapped_classes                  73
literal_class_name_hit_count     0
package_resource_hit_count       0
service_descriptor_count         2
manifest_requires_review         true
```

The two service descriptors are:

- `META-INF/services/com.fasterxml.jackson.core.JsonFactory`
- `META-INF/services/com.fasterxml.jackson.core.ObjectCodec`

The scan uses the same R2A evidence categories: exact string literals matching the source
internal/dotted class name and non-class entries beneath the source package.

## Preflighted class candidate set

```text
rs/i/b
rs/n/c/G
rs/n/c/O
rs/n/c/T
rs/n/c/U
rs/n/c/V
rs/n/c/Y
rs/n/c/a
rs/n/c/aC
rs/n/c/aD
rs/n/c/aG
rs/n/c/aH
rs/n/c/aI
rs/n/c/aL
rs/n/c/aQ
rs/n/c/aS
rs/n/c/aU
rs/n/c/aX
rs/n/c/aY
rs/n/c/ab
rs/n/c/ad
rs/n/c/af
rs/n/c/ag
rs/n/c/ai
rs/n/c/al
rs/n/c/am
rs/n/c/ap
rs/n/c/as
rs/n/c/at
rs/n/c/au
rs/n/c/av
rs/n/c/aw
rs/n/c/b
rs/n/c/ba
rs/n/c/c
rs/n/c/c/a
rs/n/c/d/b
rs/n/c/h
rs/n/c/i
rs/n/c/k
rs/n/c/l
rs/n/c/m
rs/n/c/n
rs/n/c/o
rs/n/c/p
rs/n/c/q
rs/n/c/s
rs/n/c/u
rs/n/c/v
rs/n/c/z
rs/n/c/E
rs/n/c/F
rs/n/c/H
rs/n/c/I
rs/n/c/J
rs/n/c/Z
rs/n/c/aE
rs/n/c/aF
rs/n/c/aJ
rs/n/c/aW
rs/n/c/aZ
rs/n/c/an
rs/n/c/ar
rs/n/c/az
rs/n/c/d/e
rs/n/c/j
```

## Consequence

The semantic review layer may continue to review these names without mutating bytecode.
If selected names are later explicitly accepted and used by an R4 semantic namespace
plan, none of these 73 class coordinates currently requires R2B's:

- `rewrite_class_name_strings`
- `allow_package_resource_risk`

based on the exact-v308 R2A categories.

The ordinary manifest/service review boundary still applies.

This is a preflight finding only. Chat 2 does not authorize semantic acceptance or execute
a remap.
