# Chat 2 — exact-v308 ScriptPacket direct handlers R118

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R118 is a separate non-canonical class-only review for four direct R115 ScriptPacket
handlers whose target state is independently exact.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_6F08C520C82D4C28AF06`
- field/method proposals: **0**

## Stable IDs / ScriptPacket IDs

- `rs/q/a/a/a/k` -> `CLIENT_CLASS_000756`
  -> `ObjectSpawnOverridePacketHandler` — ScriptPacket **2**
- `rs/q/a/a/a/l` -> `CLIENT_CLASS_000757`
  -> `MailCofferActionPromptPacketHandler` — ScriptPacket **3**
- `rs/q/a/a/a/b` -> `CLIENT_CLASS_000747`
  -> `DropdownPacketHandler` — ScriptPacket **40**
- `rs/q/a/a/a/i` -> `CLIENT_CLASS_000754`
  -> `NpcDefinitionOverridePacketHandler` — ScriptPacket **42**

## ObjectSpawnOverridePacketHandler

R77 already proves `rs/d/s` / `rs/d/s$a` as the object-spawn override manager and
record.

ScriptPacket 2 is the exact network-facing mutator for that subsystem.

Its operations:

- remove one coordinate-keyed override and clear the live scene object;
- construct/store/apply one six-int override;
- remove every override matching one requested object id.

The same six values are replayed through the exact
`Client.a(x,y,objectId,rotation,type,plane)` object-spawn API.

## MailCofferActionPromptPacketHandler

ScriptPacket 3 owns two exact action prompts:

- `<img=9> Claim`
  - `misc/treasure`
  - `misc/treasure 2`
  - `::claimcoffer`
- `<img=288> View`
  - `misc/mail 7`
  - `misc/mail 8`
  - `::mail`

The packet reads a selector:

- 1 -> coffer claim;
- 2 -> mail;

plus an enable/disable value and adds or removes the selected prompt from the live prompt
manager.

This is a separate implementation from the R113 overlay classes, but the same exact
mail/coffer domain and actions independently survive here.

## DropdownPacketHandler

ScriptPacket 40 targets the custom dropdown RSInterface subtype.

Packet mode 1:

- reads target interface id;
- reads option count;
- rebuilds the complete value/display option list;
- defaults display text to `Select` unless an alternate display String is supplied;
- installs the list;
- selects the first display value.

Mode 2 selects an existing option by index.

Mode 0 invokes the dropdown subsystem reset/clear path.

The handler noun is descriptive; confidence is **0.998**.

## NpcDefinitionOverridePacketHandler

ScriptPacket 42 mutates cached R28 `NpcDefinition` objects directly.

Its modes include:

- toggling NPC ids in one static override set;
- assigning the definition's `P` byte and resetting `Q/R` when disabled;
- forcing `P=-1` while assigning packet-provided `Q/R` integers.

R118 deliberately does not invent semantic names for the `P/Q/R` fields themselves.
The proven class role is therefore kept broad as
`NpcDefinitionOverridePacketHandler` with confidence **0.998**.

## Deliberate exclusions

R118 does not name the remaining direct handlers merely because their ScriptPacket IDs are
known. Several update generic Client/RSInterface/map state or static integer maps without
enough independently recovered field semantics for a precise class noun.

## Acceptance boundary

Chat 2 does not promote R118. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_6F08C520C82D4C28AF06`.
