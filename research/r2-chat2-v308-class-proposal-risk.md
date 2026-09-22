# R2 Chat 2 — v308 semantic class risk preflight

The nine current Chat 2 class semantic candidates were checked against the same exact-build
risk categories introduced by R2A.

Exact v308 authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Per-candidate result

| Source | Semantic candidate | Exact class-name literal hits | Non-class resources under source package |
| --- | --- | ---: | ---: |
| `rs/i/b` | `AdventureOrbRenderer` | 0 | 0 |
| `rs/n/c/c` | `AdventureBookInterface` | 0 | 0 |
| `rs/n/c/aL` | `RaidPartySetupInterface` | 0 | 0 |
| `rs/n/c/av` | `DailyMoneyMakingInterface` | 0 | 0 |
| `rs/n/c/b` | `DailyChallengesInterface` | 0 | 0 |
| `rs/n/c/G` | `ItemEnchantmentInterface` | 0 | 0 |
| `rs/n/c/z` | `ConstructionRoomSelectionInterface` | 0 | 0 |
| `rs/n/c/v` | `CollectionLogInterface` | 0 | 0 |
| `rs/n/c/am` | `WelcomeBackInterface` | 0 | 0 |

Combined R2A-style summary for these nine candidate source classes:

```text
mapped_classes                  9
literal_class_name_hit_count    0
package_resource_hit_count      0
service_descriptor_count        2
manifest_requires_review        true
```

The two service descriptors are global JAR entries:

- `META-INF/services/com.fasterxml.jackson.core.JsonFactory`
- `META-INF/services/com.fasterxml.jackson.core.ObjectCodec`

None of the nine proposed class names appears as an exact surviving class-name string
literal, and none sits in a source package that currently contains a non-class resource.

## Consequence

R2C2 may resolve and explicitly accept these semantic names without mutating bytecode.
If a later class-remap specification uses the accepted class names, the current R2B
fail-closed checks would not require:

- `rewrite_class_name_strings`
- `allow_package_resource_risk`

for these nine mappings based on the present exact-v308 risk categories.

This is a preflight finding only. Chat 2 does not authorize semantic acceptance or execute
a remap.
