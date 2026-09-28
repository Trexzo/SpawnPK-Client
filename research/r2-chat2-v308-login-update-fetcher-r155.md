# Chat 2 — exact-v308 login update fetcher R155

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R155 resolves the live forum-update worker owned by R11 `LoginScreen`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_5136D014B73E8CA7BE90`
- field/method proposals: **0**

## Stable ID

`rs/l/d/e` -> `CLIENT_CLASS_000396` -> `LoginUpdateFetcher`

## Exact lifecycle

`LoginScreen` checks whether its update text is still absent and whether the fetch has
already been started.

When needed it:

1. constructs `rs/l/d/e` with itself as the sole owner;
2. calls `Thread.start()`;
3. marks the fetch as started.

No other class constructs the worker.

## Exact network source

The thread opens:

`https://spawnpk.net/forums/index.php?/forum/10-updates/`

and reads the HTML response line by line.

## Exact parser behavior

The worker searches for forum headline markup:

`<span itemprop="name headline">`

and associated `href` content.

It then:

- extracts the update link;
- decodes HTML entities such as `&quot;`, `&amp;`, `&#039;`;
- formats bracket/date/title text with client color tags;
- truncates overlong headline text;
- accumulates up to six update rows;
- stops when the page reaches the Runex section;
- writes the resulting text/link/title fields and calculated display height back into
  `LoginScreen`.

On I/O failure it clears the update text rather than mutating another subsystem.

## Naming boundary

`LoginUpdateFetcher` is **0.999**.

Its owner, URL, Thread lifecycle, parser and sink are all exact and single-purpose. The name
is descriptive recovery rather than a claim of the original developer identifier.

## Acceptance boundary

Chat 2 does not promote R155. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5136D014B73E8CA7BE90`.
