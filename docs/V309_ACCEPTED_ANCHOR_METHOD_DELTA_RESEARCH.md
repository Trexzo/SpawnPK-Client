# v309 000029 accepted-anchor method drift (research only)

This CLI isolates the **single removed static call** from proposed class
\`CLIENT_CLASS_000029\` to the already accepted class \`CLIENT_CLASS_000081\`
between exact original v308/v309. It finds the v308 Code-bearing member that
contained the invocation and checks whether the proposed new class has a
**unique exactly same-named, same JVM descriptor and same-access** member.

The diagnostic compares complete **opcode-only** 5-gram distributions against
all ordinary methods of the proposed new class and reports a non-autojunk
sequence alignment, changed-region counts, Code byte lengths, and exception
handler counts. Opcode similarity **does not prove CP referent equality,
full bytecode semantics, or member continuity**. In particular, branch
destinations, invokedynamic arguments and exception handler structure may
differ. It never accepts or promotes a canonical class/member/field identity.

Run locally with Python 3.11+ and the current GitHub repository source:

\`\`\`powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.v309_accepted_anchor_method_delta_research \`
    --v308-jar 'C:\path\to\original-v308.jar' \`
    --v309-jar 'C:\path\to\original-v309.jar' \`
    --frontier 'research\v309-field-recovery\frontier.json' \`
    --class-lineage 'research\v309-field-recovery\class-lineage.json' \`
    --global-report 'research\v309-field-recovery\global-field-usage.json' \`
    --out 'C:\outside-checkout\v309-000029-method-delta.json'
\`\`\`

The published GitHub copies of the two protected research JSON inputs may have
LF rather than the frontier's originally pinned CRLF file bytes. Those exact
SHA checks are **intentional**; do not relax them or repin accepted authority.
Use SHA-exact original copies for the local research run.

Both original private JAR SHA-256 pins, frontier, lineage build, accepted
target v308/v309 classfile SHA-256, old proposed classfile SHA, exact
one-call preimage and no-clobber output are checked before success. It writes
one bounded aggregate-only result. Private original JARs, bytecode, literal
constants, obfuscated members, descriptors and fingerprints must stay local.

Independent original-JAR preflight prior to this PR observed matching exact
name/descriptor/access for one ~3,300-instruction old/new method,
99.25% opcode alignment ratio, and the removed accepted target invocation in
one changed region. This observation **does not certify this new module**:
require exact-head hosted Ubuntu/Windows Recovery CI and an independent run of
the new module on the original private files.

The protected v309 authority stays **ACCEPTED_INCOMPLETE**, 143 unresolved
fields, 26 descriptor-blocked, zero class/member/field acceptances. Source M1
last measured 98 javac errors; this method drift diagnostic does not alter it.
