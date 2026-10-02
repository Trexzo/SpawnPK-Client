# Chat 2 — source-proven interface task roots R410

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/b/a` / 000538 -> `ScheduledTask`
- `rs/n/b/b` / 000543 -> `TaskGroup`
- `rs/n/b/a/a` / 000539 -> `TimedTask`
- review: `SEMREVIEW_E713246E9F7300D509F0`

The recovered source map supplies the exact source identities.

Exact-v308 bytecode independently proves the structure:

- ScheduledTask owns interval/last-run timestamps and invokes its abstract hook only when due;
- it creates/registers the three global task groups used by hover/timed/render task families;
- TaskGroup is an int-keyed map of task lists and dispatches each registered task through
  ScheduledTask's interval gate;
- TimedTask is the direct abstract ScheduledTask subtype whose constructor sets the interval.

R288 already owns the child classes `rs/n/b/a/b`, `c`, and `d` under descriptive names.
The source map provides stronger source names for those children, but R410 deliberately does
not mutate R288 review/proposal IDs.

R410 remains non-canonical semantic research only.
