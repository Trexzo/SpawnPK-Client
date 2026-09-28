# Chat 2 — exact-v308 Censor semantics R57

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R57 is a separate non-canonical single-class semantic review for the classic chat
word-filter subsystem.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_49EB6237A9C765E8B723`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/c` -> `CLIENT_CLASS_000112`

## `rs/d/c` -> `Censor`

The startup loader receives the chat-system StreamLoader and reads four surviving
word-filter resources:

- `badenc.txt`
- `domainenc.txt`
- `fragmentsenc.txt`
- `tldlist.txt`

Those payloads populate the bad-word pattern tables, domain/TLD structures and fragment
lookup data consumed by the text filter.

The public filtering path normalizes chat text, detects obfuscated substitutions and
word/domain/TLD/numeric patterns, censors matching spans and then restores permitted
capitalization/whitelisted terms.

Client invokes this exact class when processing player-entered and received chat text
before the resulting strings are stored or displayed.

That exact resource set and behavior is the classic client `Censor` subsystem.

## Naming boundary

`Censor` is a semantic/historical recovery name grounded in exact v308 resources and
call sites. It remains non-canonical until explicit Main/Core acceptance.

## Acceptance boundary

Chat 2 does not promote R57. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_49EB6237A9C765E8B723`.
