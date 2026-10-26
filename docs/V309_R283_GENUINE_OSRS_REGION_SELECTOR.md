# R283 — Genuine OSRS region selection

**Verified:** the actual R278 compiled v309 client and owner cache passed **35/35** source-backed checks, independently repeated via a disposable SHA-pinned owner-input runner.

The real compiled `Client.field407` legacy-OSRS region list **includes 13129** and excludes standard test region **12593**. Its `field408` OSRS-config region list is empty. In the real `ObjectDefinition`, standard bank `field1133` has ID114 Cooking range/model5274 with no Cook, while legacy-OSRS `field1134` has ID114 with **Cook**. Restoring standard removes Cook again. ID16641 also changes model/name semantics across these banks. Raw decode agrees with cached lookups.

This validates a **candidate real OSRS region** for a future GUI Cook test, not GUI loading of that region, actual mouse selection, a transmitted Cook packet, or original cooking gameplay. No production edits, no full client rebuild, no Windows execution or merge. Keep integration PR #1142 **DRAFT**.

Next: create a real localhost region13129 GUI world load using authentic map resources, confirm loader chose bank field1134, then perform AWT Cook action.