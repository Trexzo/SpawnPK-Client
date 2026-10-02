# Chat 2 — plugin scheduled-task subsystem R329

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/y/a` -> `CLIENT_CLASS_001122` -> `ScheduledTask`
- `rs/y/b` -> `CLIENT_CLASS_001123` -> `ScheduledTaskDescriptor`
- `rs/y/c` -> `CLIENT_CLASS_001124` -> `ScheduledTaskManager`
- review: `SEMREVIEW_53C95552A49FEFB7F48B`

## Exact lifecycle

The live plugin manager `rs/s/g` scans plugin methods for `rs/y/a`, converts each annotated method to a Runnable when possible, wraps it in `rs/y/b`, logs `Scheduled task {}`, and adds it to `rs/y/c`.

On plugin stop it copies the scheduler list, finds descriptors whose target object is that plugin, logs `Removing scheduled task {}`, and removes them.

`rs/y/c` keeps descriptors in a CopyOnWriteArrayList. Its trigger loop uses `Instant.now()`, `Duration.between`, the annotation amount and ChronoUnit, and the annotation async flag. Due tasks run through the injected ScheduledExecutorService when async, otherwise through the descriptor Runnable/reflective Method path.

The class IDs are proven by exact 1-based lexicographic JAR lineage ordering and the existing `rs/z/a = CLIENT_CLASS_001126` anchor.

R329 is non-canonical semantic research only.
