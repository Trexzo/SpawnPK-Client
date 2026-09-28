# Chat 2 — R352 duplicate wandering-merchant audit

R352 retains **no semantic proposal**.

Direct exact-v308 inspection rediscovered `rs/t/a/g`, but the repository-wide uniqueness
gate proved this class is already owned by **R81**.

The new evidence strengthens that older ownership:

- loads `configs/wandering_merchant.yaml` / `configs/w.bin`;
- walks nested merchant `items` entries and records item IDs;
- normalizes noted/certificate-style IDs with exact exclusions 995, 20693 and 20842;
- Client startup loads the registry;
- item-name rendering checks the registry and appends exact marker `<img=370>` when the
  related client presentation flag is enabled.

The attempted R352 candidate/review/test artifacts are removed. This batch is
corroboration-only and performs no canonical acceptance or rewrite.
