# Chat 2 — R347 duplicate definition-config audit

R347 retains **no semantic proposals**.

The attempted definition *Mapper* names duplicate exact class ownership already established
by R80 as definition config *Loader* classes:

- rs/t/a/a / CLIENT_CLASS_000983 -> SequenceDefinitionConfigLoader
- rs/t/a/b / CLIENT_CLASS_000984 -> NpcDefinitionConfigLoader
- rs/t/a/c / CLIENT_CLASS_000985 -> SpotAnimationDefinitionConfigLoader
- rs/t/a/d / CLIENT_CLASS_000986 -> ItemDefinitionConfigLoader
- rs/t/a/f / CLIENT_CLASS_000988 -> ObjectDefinitionConfigLoader

R80 review: SEMREVIEW_E585C37C70B2F894E280.

The later R347 evidence may corroborate the same config-to-definition mapping role, but it
does not establish a second semantic identity. The R347 candidate/review/test artifacts are
therefore removed to restore repository-wide class-owner uniqueness.

R347 is a correction/corroboration note only; no canonical acceptance or rewrite is performed.
