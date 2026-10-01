# Chat 2 — exact-v308 queued input buffer R387

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/m/a` -> `CLIENT_CLASS_000522` -> `QueuedInputBuffer`
- `rs/m/a$a` -> `CLIENT_CLASS_000523` -> `QueuedInputEvent`
- review: `SEMREVIEW_DEE419516E7AE0D4B49D`

## Exact buffer contract

The client shell `rs/C` constructs one synchronized `rs/m/a` instance.

The buffer owns:

- exactly 256 reusable event records;
- ring head and count;
- an overflow counter;
- synchronized enqueue, reset and drain operations.

When full it increments the overflow counter, clears the ring and inserts a type-4 reset
record.

Consecutive movement records (type 3) are coalesced. Instead of emitting every mouse-move
sample separately, the buffer preserves the latest coordinates/timestamp while widening the
record's min/max x/y excursion bounds.

## Exact event record

`rs/m/a$a` stores:

- event type;
- secondary code/button;
- x / y;
- minX / maxX;
- minY / maxY;
- timestamp.

The drain operation copies those fields into caller-provided records in FIFO order.

## Bundled regression corroboration

Exact v308 ships regression/investigation classes named:

- `tools.QueuedInputRegression`
- `tools.QueuedClicksInvestigation`
- `tools.QueuedSwitchingRegression`

Those tools reflect the client-shell field as `mouseInputQueue` and the consumer as
`processQueuedMouseInput`.

The switching regression additionally proves that F-key/tab switching enters the same
ordering domain: a switch must wait for earlier queued mouse events, and a switch inserted
between press/release must remain ordered between them.

Therefore the semantic names are intentionally broader than MouseEventQueue:

- `QueuedInputBuffer`
- `QueuedInputEvent`

## Boundary

This batch recovers the client-side input-ordering data structure only. It does not claim
server input authority or original stripped source identifiers.

R387 is non-canonical semantic research only.
