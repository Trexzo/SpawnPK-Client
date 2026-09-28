# Chat 2 — exact-v308 Runelite event API R169

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R169 records the exact readable class names that already survive in
`rs/runelite/events`.

## Deterministic review result

- candidate classes: **18**
- resolved proposals: **18**
- unresolved: **0**
- review ID: `SEMREVIEW_8BF377A25B58438FF825`
- stable-ID block: `CLIENT_CLASS_000835` through `CLIENT_CLASS_000852`
- confidence: **1.0** for every proposal
- field/method proposals: **0**

## Exact surviving API

| Stable ID | Exact v308 class |
| --- | --- |
| `CLIENT_CLASS_000835` | `ChatMessage` |
| `CLIENT_CLASS_000836` | `ClientShutdown` |
| `CLIENT_CLASS_000837` | `ClientStartUp` |
| `CLIENT_CLASS_000838` | `ConfigChanged` |
| `CLIENT_CLASS_000839` | `EntityInteraction` |
| `CLIENT_CLASS_000840` | `FocusChanged` |
| `CLIENT_CLASS_000841` | `GameStateChanged` |
| `CLIENT_CLASS_000842` | `MenuBuild` |
| `CLIENT_CLASS_000843` | `MenuHover` |
| `CLIENT_CLASS_000844` | `MenuOpened` |
| `CLIENT_CLASS_000845` | `NavigationButtonAdded` |
| `CLIENT_CLASS_000846` | `NavigationButtonRemoved` |
| `CLIENT_CLASS_000847` | `NotificationFired` |
| `CLIENT_CLASS_000848` | `NpcSpawned` |
| `CLIENT_CLASS_000849` | `ObjectInteraction` |
| `CLIENT_CLASS_000850` | `PluginChanged` |
| `CLIENT_CLASS_000851` | `PrivateChatMessage` |
| `CLIENT_CLASS_000852` | `SkillLevelChanged` |

These are not reconstructed English names. The readable class identifiers themselves remain
present in the exact v308 binary.

## Event payload evidence

The classes also preserve payload shapes matching their names:

- `ChatMessage`: message;
- `PrivateChatMessage`: sender + message;
- `ConfigChanged`: group/profile/key/old/new values;
- `FocusChanged`: focused boolean;
- `GameStateChanged`: recovered GameState value;
- `EntityInteraction`: entity + combat flag;
- `ObjectInteraction`: object id and x/y/z/hash coordinates;
- `NpcSpawned`: NPC;
- `SkillLevelChanged`: skill id, experience, current and maximum levels;
- `PluginChanged`: plugin + loaded state;
- `NavigationButtonAdded/Removed`: exact navigation-button payload;
- `NotificationFired`: message + `TrayIcon.MessageType`;
- `MenuBuild` and `MenuHover`: tooltip, menu row/id and command tuple;
- `MenuOpened` and `ClientStartUp`: zero-payload signals;
- `ClientShutdown`: shutdown-consumer Future queue and wait helpers.

## EventBus join

R168 recovers the exact `EventBus`, `DeferredEventBus`, `Subscribe` and subscriber
record.

R169 is the matching event-side API used by that infrastructure. Exact class-reference
scanning finds these event classes in live client/plugin/UI producers or consumers; the
names therefore belong to the runtime contract, not to a decompiler guess.

## Naming boundary

Every proposal is confidence **1.0** because its semantic name is the exact surviving binary
class name.

R169 does not infer method or field names beyond what already survives in bytecode.

## Acceptance boundary

R169 remains non-canonical. Main/Core may accept any proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_8BF377A25B58438FF825`.
