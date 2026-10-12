# R76 — final original-v309 36-op enum selection protected Java source form

R67–R75 inventoried 41 of the original 697-instruction settings method's 42 local `Exception`-protected regions with bounded JVM-backed Java source patterns. R76 reconstructs the last local 36-instruction region as **a private Java source block**. This completes the **local protected *shape* inventory only**, not a compiled equivalent original method.

## Real original v309 JVM source pattern

The final original 36-op region clears a static enum/reference field, then reads a `java.util.Properties` String key to test for non-null; when present it performs the **same property lookup again** and stores it in local3. It tests `String.contains` against the original delimiter; if true it invokes `String.split` with the original regex **twice** (not cached), taking element 0 into local4 and element 1 into local5. It compares the second fragment against the `.name()` of an original static enum reference using `String.equalsIgnoreCase`. Only on match does it invoke an original typed enum `valueOf(firstFragment)`, write its result into one original owner static enum field, then load that field and copy it to the initially-cleared owner field.

The two property lookups use the same original key; both String splits use the same original regex constant; all typed enum helper and field descriptors align in the original JVM. Three conditional branches exit the protected source region. The original `java.lang.Exception` catch is empty.

## Equivalent bounded private Java shape

```java
try {
    originalTargetEnum = null;
    if (originalLocalSlot1.getProperty("PRIVATE_KEY") != null) {
        String originalPropertyText = originalLocalSlot1.getProperty("PRIVATE_KEY");
        if (originalPropertyText.contains("PRIVATE_DELIMITER")) {
            String originalPrefix = originalPropertyText.split("PRIVATE_REGEX")[0];
            String originalSuffix = originalPropertyText.split("PRIVATE_REGEX")[1];
            if (originalSuffix.equalsIgnoreCase(OriginalMode.current.name())) {
                originalSourceEnum = OriginalEnum.valueOf(originalPrefix);
                originalTargetEnum = originalSourceEnum;
            }
        }
    }
} catch (java.lang.Exception ignored) {}
```

Names and quoted keys in this example are placeholders. The actual original literal delimiter, split regex, private class/member identities and source expression are emitted **only** to newly created private local files, never to GitHub or public aggregate evidence. The JVM's two split calls and subsequent two ordered static field assignments must not be optimized or reordered.

## GitHub implementation and verification

`spk_recovery.enum_selection_source` checks whole-original-JAR SHA before and after reading, a unique private original owner/method, exact 36 consecutive opcode positions, identical original target field for the initial null clear and final copy, exact intermediate source field declaration and copy, original String property-key equality, original typed `contains`, two identical `split` argument constants and methods, enum name/equalsIgnoreCase/typed valueOf identities, and the three actual conditional branch targets. It checks the empty original typed `Exception` handler and refuses any unrelated incoming branch/handler targets. The resulting original bytecode-backed Java source and full operand proof remain private.

Synthetic Java9 tests compile an original enum/Properties selector, extract private Java, recompile it into a separately named class and compare its branch topology, ordered exception handler table and three owner static writes using merged R66. They reject a changed second split regex, a different final enum field target, incorrect pinned complete-JAR SHA, and occupied output paths.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.enum_selection_source `
  'C:\private\original-v309.jar' 'example/PrivateOwner.class' `
  'privateOriginalMethod' '()V' 'C:\private\r76-new-output' `
  --original-sha256 '<whole original-v309 JAR SHA256>'
```

## Next substantive gate: actual whole method, not more local patterns

Following R76, the **42 local Exception-protected regions** have independently categorized JVM-backed candidate source shapes. This is *not* a statement that the original Java author code, all associated classes or the original 697-instruction method have been reconstructed. The exact original source enclosing sequence, external statics/enums and nested-class naming collision, values for static array/reference fields, and two outer IOException exception-table regions must now be assembled under original source and bytecode verification.

The new R76 generic CLI has not yet been privately replayed against the actual original v309 JAR, and the full original owner method has not been compiled and compared on R66 (697 instructions, all 44 typed exception entries, all 78 ordered static field writes and operand/side-effect parity). Thus no whole-method, source-level equivalence or client runtime parity is accepted. The public evidence file [R76 original facts](../research/v309-source-recovery/final-enum-selector-r76.json) marks those gates explicitly false.
