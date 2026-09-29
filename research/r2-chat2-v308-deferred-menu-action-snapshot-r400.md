# Chat 2 — deferred menu action snapshot R400

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/Client$a` -> `CLIENT_CLASS_000030` -> `DeferredMenuActionSnapshot`
- proposal: `SEMPROP_5EB9D7CACA2E66842B6D`
- review: `SEMREVIEW_970395AED54C89F28C74`

## Exact capture path

The Client owns one persistent instance of this nested class.

When a menu action enters the deferred-input path, Client captures the currently selected
menu row (`eV - 1`) into the snapshot.

The object copies:

- five parallel menu-action integer values;
- the exact current action text from `Client.fx[index]`;
- the resolved `RSInterface` object for the captured widget/action;
- relevant active interface/widget ids only when those ids occur in the captured widget's
  parent chain;
- the active child/slot state needed to prove the target did not mutate.

## Exact validation path

Before later queued input is accepted, Client calls the snapshot's boolean validation
method.

Validation fails if any captured live UI dependency changed, including:

- active interface ids;
- the exact RSInterface instance installed for the target id;
- the captured child/slot state.

If validation fails, Client aborts/resets the deferred action path.

## Exact replay path

When the action must be replayed, Client does not re-read the current menu arrays.

Instead it feeds the snapshot's five stored integer values plus its stored action String
back into the normal six-argument menu-action executor.

That establishes this class as a deferred menu-action state snapshot and stale-UI guard,
not a generic menu entry DTO.

## Lineage

- `rs/Client` = 000029 (R170)
- `rs/Client$a` = 000030
- `rs/D` = 000031 (R332)

R400 remains non-canonical semantic research only.
