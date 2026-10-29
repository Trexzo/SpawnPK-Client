# R319 — visible inventory restored by fixing isolated-server tab setup

27 October 2026. Owner-private original-source recovered **v309** client acceptance milestone.

**Reproduced failure:** the local server sent incoming full-inventory update opcode **53** (widget **3214**, wire item ID **996**, quantity **7**) but did not assign an interface to the selected inventory tab. Read-only diagnostic proof: `selectedTab=3`, `tabInterfaceIds[3]=-1`, `WidgetComponent.widgetTable[3214].parentId=3213`, updated item values present, redraw flag true. The visible client previously displayed an empty inventory panel even though the widget was populated.

**Correct fixture:** source-verified opcode **71**, payload `0C 8D 83`, assigns parent interface **3213** to tab **3**; original client now renders its child container widget 3214. The isolated localhost server waits for a **real before screenshot** before transmitting the opcode53 item update.

**Actual original-cache graphical result:** both an opt-in diagnostic run and a separate **pure production-JAR-only** GUI replay passed. In the independent production-JAR run, original-cache world region **13386** and tab 3 rendered under isolated Linux/Xvfb 1400×900. The seven coins became visibly present after the item packet. The actual item-sprite ROI (x685–742, y389–439) changed **299 RGB pixels** after the packet; screenshots are different and SHA-pinned. Session **PASS, exit 0, 20.8 seconds**, client/server alive through the check, all fixture children cleaned. No game Java, binary, or cache changes. Client JAR remains SHA-256 `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`.

Real production-JAR screenshot SHA-256: before `44c65c750aaaf0b6cbddd3cb6bb3c79e00db33083d021541889a84ca308bdc9d`; after `cc5626c4c3a4a016b4404b279e193e7a6fbd0323ba0f3f7243b80599a5c34083`.

**Code committed to PRIVATE GitHub PR #4:** SHA-locked localhost server and unmodified-production-JAR visual runner patchers, opcode71/53 packet contract, original GUI receipt verifier, synthetic regression tests and cross-platform CI. The original owner game source and binaries remain **off this public repository**. The complete 1,277-source private GitHub import is still pending [issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3).

**Not certified:** actual authenticated live SpawnPK service, item drag-and-drop/actions, server inventory persistence across reconnects, native owner Windows graphics, broad gameplay parity or v311 original-bytecode equivalence. This is a **test-server fixture defect resolved**, not a production-client code patch. Both PRs remain draft and unmerged.
