# Chat 2 — exact-v308 client input event queue R374

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/m/a` -> `CLIENT_CLASS_000522` -> `InputEventQueue`
- `rs/m/a$a` -> `CLIENT_CLASS_000523` -> `InputEventRecord`
- review: `SEMREVIEW_899AAB0E950B32652D17`

## AWT producer side

The applet/input base `rs/C` constructs one queue and feeds it from live AWT input callbacks.

Observed enqueue paths include mouse press/release, mouse movement/dragging and key events. Records carry event type, button/key code, x/y coordinates and the event timestamp.

## Queue behavior

The queue owns a fixed 256-record ring and exposes synchronized enqueue/reset/drain operations.

Consecutive type-3 movement records are coalesced: the latest x/y/timestamp is retained while min/max x/y bounds are widened across the coalesced motion.

Overflow resets the queue through its existing sentinel/reset path rather than silently extending storage.

## Client consumer side

`Client.by()` drains queued records before the normal input/game-tick logic.

It dispatches record types 1..5 into live input state, including mouse-button press/release, pointer coordinates/movement bounds and key state. The consumer reads the same timestamp and bounds stored by InputEventRecord.

This proves the subsystem is the synchronized AWT-to-Client input handoff, not network telemetry.

R374 is non-canonical semantic research only.
