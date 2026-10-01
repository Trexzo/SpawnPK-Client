# Chat 2 — R464 duplicate QuantityFormatter audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R464 retains **no semantic proposal**.

The attempted R464 proposal exactly duplicated R20:

- owner: `rs/A/p`
- stable ID: `CLIENT_CLASS_000019`
- semantic name: `QuantityFormatter`
- proposal ID: `SEMPROP_7BB3024033EBBDFCF3B4`

R20 already owns that exact class/name/ID tuple in
`SEMREVIEW_E6BE3592C064143A3007`.

The repository-wide uniqueness guard correctly rejected the duplicate and caused later
R465-R469 overlap tests to fail transitively while R464 remained present.

## Additional corroboration retained from the attempted batch

The later R464 investigation did add stronger provenance for the existing R20 identity:

- exact validation regex `^-?[0-9,.]+([a-zA-Z]?)$`;
- exact parse diagnostics including
  `does not resemble a properly formatted stack.` and `Invalid Suffix:`;
- exact K/M/B/T suffix behavior;
- English-locale number/decimal formatting;
- direct live consumers in the trading/price presentation family;
- historical RuneLite `net.runelite.client.util.QuantityFormatter` identity with the same
  API/algorithm, modulo SpawnPK's T suffix extension.

That evidence corroborates R20. It does not create a second semantic owner.

## Boundary

R464 is a correction/corroboration note only.

No R464 candidate JSON, semantic-review JSON, deterministic review test, acceptance spec,
or source rewrite is retained.
