# Chat 2 — RuneLite task scheduler R350

Exact authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Recovered with exact-v308 behavior plus historical RuneLite source identity:

- `rs/y/a` -> `CLIENT_CLASS_001122` -> `Schedule`
- `rs/y/b` -> `CLIENT_CLASS_001123` -> `ScheduledMethod`
- `rs/y/c` -> `CLIENT_CLASS_001124` -> `Scheduler`

Review: `SEMREVIEW_0C940EC4C68D5DDC6CF0`

Exact v308 preserves the Scheduler trace literal `Scheduled task triggered: {}`, runtime
method-annotation scanning in PluginManager, the ScheduledMethod(schedule, method, plugin,
runnable) shape, period/unit timing and async execution via ScheduledExecutorService.

These names are historical-source proven, not merely descriptive. R350 remains non-canonical.
