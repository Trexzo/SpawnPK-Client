# Chat 2 — exact-v308 legacy runtime helpers R49

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R49 is a separate non-canonical class-only semantic review batch covering two remaining
high-confidence legacy runtime helpers.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_CEA31CD5E3BE66DE0413`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/L` -> `CLIENT_CLASS_000039`
- `rs/N` -> `CLIENT_CLASS_000041`

## `rs/L` -> `AudioClipPlayer`

The class is a dedicated threaded Java Sound playback helper.

It:

- accepts an InputStream plus volume and delay;
- starts its own Runnable thread;
- decodes audio with `AudioSystem.getAudioInputStream`;
- converts the stream to signed 16-bit PCM;
- opens a `javax.sound.sampled.Clip`;
- applies volume through `MASTER_GAIN`;
- optionally delays playback;
- starts the clip and refreshes gain while active;
- waits for completion and flushes/closes the audio resources.

Client's queued sound-effect loop constructs this exact class after resolving the requested
sound bytes and passes the queued volume/delay values. `AudioClipPlayer` therefore states
the exact implementation role without assuming a broader sound-engine responsibility.

## `rs/N` -> `SpawnObjectNode`

This class extends R25 `Node` and contains twelve integer fields, one initialized to -1.

Client uses it as a delayed world-object transition record. The record stores tile/scene
coordinates and object-category state. Client queries R40 `Scene` at those coordinates,
extracts the current object id plus orientation/config bits and writes that snapshot into
the record.

The update loop keeps the records in a NodeList, decrements two independent countdowns,
installs either the queued replacement object or restores/applies the captured prior
object state, then unlinks the record when the transition is complete.

Historical clients expose the same twelve-int Node-derived structure as
`SpawnObjectNode`, including the -1 sentinel and plane/type/x/y/id/face plus delayed
replacement state. Exact v308 behavior independently establishes the role; the historical
source only corroborates the recovered name.

## Acceptance boundary

Chat 2 does not promote R49. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_CEA31CD5E3BE66DE0413`.
