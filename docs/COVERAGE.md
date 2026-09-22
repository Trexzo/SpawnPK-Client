# R4D — semantic coverage dashboard

R4D reports how much of one exact authority build is actually readable today.

It keeps three states separate:

- `ACCEPTED` — authorized for readable namespace/remap use
- `CANDIDATE` — proposed but not accepted
- `UNKNOWN` — no semantic name

This prevents candidate volume from being mistaken for recovered/accepted coverage.

## Command

```powershell
spk-coverage `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  --build-id v308 `
  --out .\generated\v308-coverage.json
```

The report includes separate class, field and method counts/percentages, overall accepted/known coverage, and provenance-family counts for accepted names.

`known_percent` means `ACCEPTED + CANDIDATE`; it is not remap-ready coverage. `accepted_percent` is the remap-ready semantic coverage figure.
