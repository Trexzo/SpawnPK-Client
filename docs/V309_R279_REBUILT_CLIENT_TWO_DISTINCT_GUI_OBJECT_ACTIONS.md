# SpawnPK v309 R279 — patched R278 rebuilt binary, genuine GUI selection of two different world objects

**2026-10-18. Sole active client-owner integration PR #1142, DRAFT.** This batch changes **no production game Java**. It runs the actual fully-source-built R278 Java11-target client (1,277 source files → 1,386 compiled classes), with the R274/R278 object-authority guards already present, under an isolated Linux/Xvfb dummy-login localhost session. The user/private client source, class JAR, original client binaries and assets are not published to GitHub.

## Actual GUI and independently received socket evidence

An isolated SHA256-pinned owner asset home staged **10,772 original cache files** plus the actual original client’s **non-class** UI resources. Actual rebuilt **R278 class-only JAR SHA256 \`dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd\`** started the real rs.gui.Launcher. Its 504x335 3D viewport passed a **>99.7% nonblack rendered-scene gate**.

After real client outbound ISAAC map-ready **opcode 121**, the test-only listener at **127.0.0.1:43594** sent one genuine 22-byte opcode60 update containing four original object151 spawns:

- **Open chest ID104**, model1226, local (50,49)
- **Cooking range ID114**, model5274, local (51,49)
- **Compost heap ID152**, model1428, local (49,50)
- **Cave Entrance ID2**, model731, local (52,52)

Real mouse right-click screenshots show visible contextual menus for **Open chest** (Search/Shut/Examine), **Compost heap** (Search/Examine), and **Cooking range** (Examine). A genuinely native \`java.awt.Robot\` sequence then selected **Search Compost heap** and **Search Open chest** in the **same GUI session**. The local listener independently ISAAC-decoded **two** six-byte client-originated **opcode 132** object actions and separately replied with **opcode 253** *synthetic test chat* for each:

| Real GUI click | Object ID | Actual world target | Outbound opcode | Wire offset from initial successful replay |
| --- | ---: | --- | ---: | ---: |
| Search Compost heap | 152 | (3201,3202) | 132 (six bytes) | 47 |
| Search Open chest | 104 | (3202,3201) | 132 (six bytes) | 56 |

That initial run’s 63 received postlogin ciphertext bytes have SHA256 **\`da742e3c76fcfd4db0bf494f697b9ac35ccab87ea74ff18b2c51f4ddf3712119\`** and **no parser error**. An independent second GUI replay after improving graphics automation again passed both actions, mapping ID152→ID104 at wire offsets **46/56**, received ciphertext SHA256 **\`e840d0386ef59e9d18ba9ae710244368d2daf823e75beed56f94d89046fe81f0\`**, 63 bytes, no parser error. Several *further* clean staged GUI runs also received both actual packets; headless Xvfb/Robot cleanup was intermittently slow, so those wrapper-timeout runs are not misclassified as clean process-exit acceptance. A separate safe-cleanup replay completed with exit 0 and independently decoded both actions. **Receipt correctness, not graphics-driver teardown, defines the wire acceptance.**

Original client \`PacketCapture\` independently logged one inbound **60/22**, outgoing **121**, outbound **132/6 twice**, and incoming **253 twice** in the first replay. There was an additional outbound **98** approach packet before the compost action. Both GUI actions produced distinct on-screen context-menu screenshots and a populated 3D viewport after interaction.

## Testing and source-free handoff

One deterministically built public-safe ZIP: \`SpawnPK_v309_R279_REBUILT_GUI_TWO_OBJECT_ACTIONS_EVIDENCE.zip\` — **SHA256 \`edb1009e8101823eef25aa8b8326b5d1a31623d6114441fb602a72329e60bd97\`**, **2,119,889 bytes**, **35 entries**. Two independent ZIP builds were byte-identical; all archive CRCs, file sizes and per-entry SHA256 hashes verified. Standard-library + Pillow evidence validator **161/161 checks PASS**, including each replay’s wire bytes, two specific decoded IDs/opcodes/coords, two corresponding synthetic responses, map-ready proof, client outbound capture and authentic 1400x900 screenshots with >95% viewport population.

Source-free package contains independently authored synthetic localhost server, safe SHA-256 original-asset staging, Linux graphical replay wrapper, AWT Robot source, framing helpers, a reproducibility/integrity verifier, two actual GUI replay logs/screenshot sets, and object-menu reference images. It does NOT redistribute recovered SpawnPK game source, private compiled classes, original client JAR or original cache data. Exact pinned private inputs documented in package README.

## Strict boundaries

- **Verified:** real R278 patched source-built binary graphical launch; genuine original cached compost/chest model picking; **two distinct mouse-initiated object action opcode132 receipts and independent synthetic opcode253 responses in one localhost session**; real cooking-range Examine menu shown.
- **Not verified:** actual original compost/chest gameplay effects, cave entrance object menu selection, any Cooking-range action beyond Examine, continuous navigation around objects in this specific GUI replay, native Windows GUI acceptance, original server authentication, live gameplay, indefinite stability, exact original executable parity, or crash/power-loss durability.
- No fresh full source rebuild in this specific R279 turn; it intentionally tests the already full-source-built **R278** JAR. Production code unchanged.
- **Maintain PR #1142 DRAFT, no main merge**, and preserve all owner-private provenance boundaries.

Next R280: isolated mouse selection of Cave Entrance and a source-safe clickable action if the original object definition supports one, rotated object collision under real GUI approach pathfinding, and finally owner native Windows GUI launch at a meaningful integrated milestone.