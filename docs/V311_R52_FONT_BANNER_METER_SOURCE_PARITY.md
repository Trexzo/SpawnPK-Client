# Original v311: 52 distinct Java source recoveries; connected font, banner and progress-meter slice

**Date:** 2026-10-22. **Original user-provided v311 JAR SHA256:** `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.

This report describes a private owner-authorized original-v311 source-reconstruction milestone. The original game JAR, classfiles, restored Java and raster/probe implementation are **not** committed here. Public CI tests only unrelated synthetic Java9 code.

## Three additional original connected Swing classes

| Original class | Original class SHA-256 | Independently rebuilt class SHA-256 | Ordered JVM instructions |
|---|---|---|---:|
| `rs/gui/w.class` | `4c47a4dd176bf2cfef035067050e3a499a55f14f454ae921da2f68bebb6796ab` | `feb6c068cd4115266551582371adeacefaf5da368995ed12b2b826c394019260` | **117 / 117** |
| `rs/ui/components/u.class` | `60afdaee6961fd0ff1a6c1c756bf2ee5cb934632944ccaf7105f02c85a7812bb` | `6762ccaceb53b790aef85184a25d6102d251cbdc8739a8f81e1e7a54168efd4f` | **76 / 76** |
| `rs/ui/components/v.class` | `4763e115f0378c4313fb15d1569ebf9bd1950618379437dc65828231c2b87cd4` | `f38847ee9195c5a7c583964a1beea1503c13808606d205f547a872d14aa478cc` | **290 / 290** |
| **New combined** | | | **483 / 483** |

The font class `rs/gui/w` loads three RuneScape TrueType fonts via `Class.getResourceAsStream`, derives registered 16pt fonts, and exposes five font accessors. Both runtime font identities and both exception-handler paths' bytecode were checked. The banner `rs/ui/components/u` instantiates recovered shadow-label instances, uses the original font registry, and updates an HTML caption. Its Java9 invokedynamic `StringConcatFactory` bootstrap recipe exactly agrees with the original. The progress meter `rs/ui/components/v` extends the already recovered `rs/ui/components/f` colored panel, references the font registry and shadow-label UI, draws percentage/marker lines and toggles its three labels.

**All twelve available private recovered Java sources compiled together** in a single `javac --release 9 -proc:none -g:none` invocation with **no original game binaries on the compilation classpath or sourcepath**. All **896 / 896** original ordered JVM instructions, offsets, resolved symbolic field/method references, branches and class declarations agree (numeric constant-pool indexes normalized). Generated complete classfile SHA hashes deliberately differ from the original; full binary/attribute/StackMap identity is **not** asserted. All nine R49 reconstructed classes preserved their expected prior source-rebuild fingerprints.

## Original-versus-private-source bounded behavior evidence

Isolated original-JAR versus privately compiled-source Java processes, with the official TTF resources supplied **only at runtime**, agreed:

- **6/6** banner label/five-font identity and 280 × 130 full ARGB image cases including empty text, HTML caption and offset font cases;
- **8/8** progress meter state/marker/percentage and 210 × 32 full ARGB image cases with disabled, enabled, empty, overfilled and nonzero progress states;
- prior **4/4** color-panel state checks;
- original and rebuilt UI text `invokedynamic` bootstrap recipes, including original HTML prefix/suffix.

A newly packaged **private 12-source archive** includes a deterministic verifier that checks all twelve original class hashes, compiled class hashes, Java9 major 53, complete symbolic instructions, panel behavior, raster equality and bootstrap recipes. The archive intentionally excludes the original JAR, original font assets and game classfiles; it is not published in this repository.

## Cumulative and limits

Prior certified R49: **49 distinct classes / 2,307 matching instructions** across **separate source compilation records**. Adding this new connected three-class batch (**3 / 483**) gives **52 distinct original source-built classes / 2,790 matching original JVM instructions** across those records. It does **not** mean 52 classes compiled together; the largest **available combined private source build** is twelve classes and 896 original JVM instructions.

This is source and bounded headless Java2D behavior parity. It does not prove that the full original 1,184-class client can be source-built, that custom game resources and runtime initialization work, that all JAR classfile attributes match, or that live gameplay is accepted. No owner game launch is required for this milestone. Private R52 archive SHA-256: `20c56231d7670ef40b3ccacca1fbfedc7d4d766a13ca8ffdd87631763c0e953d`.

The independent [synthetic Java9 font/banner/meter regression](../tests/test_v311_three_component_ui_source_parity.py) uses intentionally unrelated JDK-only classes, verifies the three-class compiler dependency chain and six raster cases, and refuses altered font-size/paint-height source. No game class, font, code or binary is hosted.

**Next engineering focus:** further UI dependency closure and eventual integration into larger client/scene source groups, while preserving exact original-v311 authority and keeping all unreconstructed class roles provisional.
