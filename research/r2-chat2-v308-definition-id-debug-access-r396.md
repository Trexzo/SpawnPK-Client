# Chat 2 — definition ID debug access R396

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/d/v` -> `CLIENT_CLASS_000137` -> `DefinitionIdDebugAccess`
- proposal: `SEMPROP_A60C16070088805024F6`
- review: `SEMREVIEW_3F108BF84AB8720175A2`

## Exact predicates

The class contains only two integer predicates:

- predicate A: true only for value **2**
- predicate B: true for **2, 26, 204, 205**

The input is `Client.cT`, which exact-v308 assigns directly from the successful login
response stream.

## Exact presentation role

The predicates are consumed on definition/debug presentation paths.

The broader predicate controls an exact Examine-string suffix whose surviving concat recipe is:

`@gre@(@cya@ID: @whi@<id>@gre@)`

The narrower predicate is also consumed by ItemDefinition/client menu construction where
definition IDs are exposed under additional developer/debug settings.

## Boundary

The class does **not** define authentication, mutate privileges or prove names for privilege
values 2/26/204/205.

Accordingly the semantic name is limited to `DefinitionIdDebugAccess`; no staff/admin/
owner/developer rank title is asserted.

R396 remains non-canonical semantic research only.
