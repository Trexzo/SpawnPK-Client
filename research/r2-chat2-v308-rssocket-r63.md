# Chat 2 — exact-v308 RSSocket semantics R63

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R63 replaces a rejected duplicate rediscovery of the R24 on-demand hierarchy. The duplicate
guard correctly showed that `OnDemandData`, `OnDemandFetcher` and
`OnDemandFetcherParent` were already owned by R24, so they are not repeated here and do
not add to Chat 2's proposal count.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_E07DC3208D8F6F9D01B2`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/q/b` -> `CLIENT_CLASS_000763`

## `rs/q/b` -> `RSSocket`

The class is a final `Runnable` buffered socket wrapper. It owns:

- one `Socket`;
- one `InputStream`;
- one `OutputStream`;
- one circular `byte[]` write buffer;
- read/write queue cursors;
- close/writer/error lifecycle flags;
- an R48 `RSApplet` reference used to start the writer thread.

The constructor configures socket timeout, TCP no-delay and receive-buffer state before
capturing the streams.

Its exact I/O surface includes:

- read one byte;
- query available bytes;
- read an exact byte range and throw on EOF;
- enqueue bytes into the circular write buffer;
- start the writer thread through RSApplet when needed;
- drain queued bytes to the socket OutputStream in `run()`;
- flush when the queue becomes empty;
- close streams/socket and terminate the writer lifecycle.

Surviving strings include:

- `EOF`
- `Error closing stream`
- `Error in writer thread`
- `buffer overflow`
- `ioerror:`

That contract matches the classic client `RSSocket` abstraction exactly enough for a
high-confidence semantic proposal.

## Naming boundary

Exact v308 behavior is primary authority. `RSSocket` is a semantic/historical recovery
name and is not automatically promoted.

## Acceptance boundary

Chat 2 does not promote R63. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E07DC3208D8F6F9D01B2`.
