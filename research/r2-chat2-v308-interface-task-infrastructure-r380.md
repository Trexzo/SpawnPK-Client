# Chat 2 successor — interface task infrastructure R380

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/b/a` -> `CLIENT_CLASS_000538` -> `InterfaceTask`
- `rs/n/b/a/a` -> `CLIENT_CLASS_000539` -> `TimedInterfaceTask`
- `rs/n/b/b` -> `CLIENT_CLASS_000543` -> `InterfaceTaskRegistry`
- review: `SEMREVIEW_8C3274103B6012B73C76`

R288 already accepted:

- `rs/n/b/a/b` -> InterfaceDrawCallback
- `rs/n/b/a/c` -> DeferredHoverTask
- `rs/n/b/a/d` -> InterfaceRenderTask

R380 closes the previously unnamed base infrastructure beneath those accepted roles.

## InterfaceTask

The abstract base owns:

- interval milliseconds;
- last-run timestamp;
- abstract work hook `c()`.

Its gate runs `c()` whenever interval is zero or elapsed time reaches the configured
interval, then records the current timestamp.

It also owns the three typed interface-task registries and the shared registry list.

## TimedInterfaceTask

This abstract subtype contains no second behavior. Its constructor accepts the interval and
stores it into the inherited gate. It occupies its own dedicated registry category beside
DeferredHoverTask and InterfaceRenderTask.

Accepted R288 evidence had already referred to this exact behavior as the
`TimedInterfaceTask interval gate`; R380 makes that semantic identity explicit.

## InterfaceTaskRegistry

The generic type is:

`InterfaceTaskRegistry<T extends InterfaceTask>`

It owns an integer-keyed Trove map of `List<T>`.

Registration lazily creates the list for a key and appends the task. Dispatch by integer key
iterates the corresponding list and invokes the shared InterfaceTask gate on each task.

The three exact registries are typed for:

- DeferredHoverTask;
- TimedInterfaceTask;
- InterfaceRenderTask.

The integer keys are consumed as RSInterface/widget ids by the accepted R288 render/hover
paths.

## Boundary

R380 is non-canonical semantic research only.
