# Chat 2 — exact-v308 mouse input event buffer R353

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/m/a` -> `CLIENT_CLASS_000522` -> `MouseInputEventBuffer`
- `rs/m/a$a` -> `CLIENT_CLASS_000523` -> `MouseInputEvent`
- review: `SEMREVIEW_C1E15D3D1A5912020DF9`

## Producer

`rs/C` is the AWT applet/input base and implements MouseListener, MouseMotionListener,
MouseWheelListener and KeyListener.

It constructs exactly one `rs/m/a`.

Mouse input is enqueued while buffering is active:

- mouse press -> type 1;
- mouse release -> type 2;
- mouse motion -> type 3;
- buffer fence/reset -> type 4;
- mouse wheel -> type 5.

Keyboard input follows separate key-state paths and is not inserted into this ring.

## Buffer behavior

The buffer preallocates **256** records.

It owns synchronized:

- enqueue;
- drain/copy;
- clear/reset;
- overflow counting.

Repeated type-3 motion records are coalesced into the newest pending motion record. The
record updates current x/y/time while preserving min/max x/y bounds across the coalesced
motion span.

## Client consumer

Client drains the records into its own preallocated array each cycle and interprets:

- type 1 as mouse-button press state;
- type 2 as release;
- type 3 as movement/drag coordinates;
- type 4 as a reset/fence marker;
- type 5 as wheel input.

The event timestamp is also consumed by the normal input-processing path.

## Naming boundary

The queue is mouse-specific. Keyboard handling in `rs/C` bypasses it entirely.

R353 remains non-canonical semantic research only.
