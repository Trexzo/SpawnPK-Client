# Chat 2 — exact-v308 client input event queue R282

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/m/a` -> `CLIENT_CLASS_000523` -> `ClientInputEventQueue`
- `rs/m/a$a` -> `CLIENT_CLASS_000522` -> `ClientInputEventRecord`
- review: `SEMREVIEW_9EAFFFB6D5E7B2A0C543`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 behavior

`ClientInputEventQueue` owns a fixed 256-entry ring of `ClientInputEventRecord` instances. Its append, reset and drain operations are synchronized. When the queue is full it increments an overflow counter, resets the buffered state and inserts the exact type-4 boundary record rather than silently overwriting an unread entry.

The base client input host `rs/C` feeds this queue from the active input path. Mouse motion contributes type 3 records carrying transformed x/y coordinates and `MouseEvent.getWhen()` timestamps. Press/release and related client-input paths use the other observed event types. Consecutive type-3 motion is coalesced into the latest record: current x/y/time are replaced while min/max x/y bounds are expanded to preserve the movement envelope.

`rs/Client.by()` is the exact consumer. It synchronizes on the queue, drains records into the client's preallocated record array and branches on types 1, 2, 3, 4 and 5. The consumer reads the record's event type, secondary button/code value, current coordinates, coordinate bounds and timestamp.

`ClientInputEventRecord` therefore describes the actual exact-v308 data contract without claiming a stripped original developer identifier.

## Deliberate exclusions

R282 does not rename the R281 holdouts (`rs/j` package markers, the no-op abstract input base, or the unused TOP/BOTTOM/BEFORE_LAST enum family), and it does not infer field or method names merely from adjacency.

## Acceptance boundary

R282 is non-canonical research only. These names describe exact-v308 responsibilities; Chat 2 performs no semantic acceptance or source rewrite.
