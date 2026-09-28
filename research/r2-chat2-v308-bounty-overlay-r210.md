# Chat 2 — R210 bounty overlay duplicate-owner correction

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Correction

R210 does **not** retain a semantic review.

The attempted R210 proposal targeted:

- `rs/l/f/a/c/c`
- `CLIENT_CLASS_000452`
- proposed name `BountyOverlay`

The exact-v308 evidence was strong, including the surviving self-label
`BountyOverlay`, bounty-hunter assets, commands and presentation state.

However, the owner was already reviewed in R3:

- `rs/l/f/a/c/c`
- `CLIENT_CLASS_000452`
- prior proposal `BountyHunterOverlay`
- R3 review `SEMREVIEW_1948F58DF9A849992F1A`

The R210 no-overlap test correctly failed because Chat 2 must not create a second
independent semantic proposal for the same stable class owner.

## Retained evidence value

The R210 audit still contributes useful corroboration:

- exact constructor self-label: `BountyOverlay`;
- exact `popups/bh ...` asset family;
- exact bounty commands including `::bhtask`, `::bhtaskinfo`, `::bhtaskskip` and `::skipbh`;
- exact labels including `Target:`, `Kills:`, `Time Left:` and `Risk:`.

This strengthens the already-existing R3 identity but does not create a new proposal.

If Main/Core later decides that the exact self-label warrants changing
`BountyHunterOverlay` to `BountyOverlay`, that must be handled as an explicit correction
of the existing R3 proposal/provenance, not as a duplicate R210 semantic owner.

## Retained R210 status

- retained semantic candidate file: **none**
- retained semantic review file: **none**
- retained semantic test: **none**
- retained review ID: **none**
- new proposal count: **0**
- unresolved: **0**

The research note is retained so the exact evidence and reason for withholding are not
lost.

## Acceptance boundary

R210 performs no semantic acceptance and creates no acceptance spec.
