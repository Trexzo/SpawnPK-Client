# Chat 2 — exact-v308 platform identity providers R174

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R174 is a separate non-canonical class-only review for the three obfuscated platform
identifier providers consumed by the already-reviewed R66 `Signlink`.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_58B30FAC567CE1A27397`
- field/method proposals: **0**

## Stable IDs

- `rs/secure/a` -> `CLIENT_CLASS_000977` -> `LinuxHardwareSerialProvider`
- `rs/secure/b` -> `CLIENT_CLASS_000978` -> `MacHardwareSerialProvider`
- `rs/secure/c` -> `CLIENT_CLASS_000979` -> `WindowsInstallDateProvider`

The nearby exact-named `rs/secure/HardwareValidator` is deliberately excluded from R174.
It only detects operating-system family and has no live project consumer outside its own
standalone diagnostic `main` method.

## LinuxHardwareSerialProvider

`rs/secure/a` exposes one cached String provider.

It first executes:

`dmidecode -t system`

and scans output for:

`Serial Number:`

If no serial has been recovered, it falls back to:

`lshal`

and scans for:

`system.hardware.serial =`

The matched value is stripped/trimmed, cached and returned on later calls.

R66 `Signlink.e()` invokes this provider only after the Windows and macOS sources fail,
making its Unix/Linux hardware-serial role exact.

## MacHardwareSerialProvider

`rs/secure/b` executes exactly:

`/usr/sbin/system_profiler SPHardwareDataType`

It scans the process output for:

`Serial Number`

splits on `:`, trims the value, caches it and returns the cached result on subsequent calls.

R66 `Signlink.e()` calls this source after Windows install-date lookup and before the
Linux/Unix serial source.

## WindowsInstallDateProvider

`rs/secure/c` provides one cached Windows installation timestamp.

The primary path runs:

`cmd /c systeminfo`

with a seven-second timeout and searches for:

`Original Install Date`

If that path does not produce a usable value, the class falls back to PowerShell:

`(Get-CimInstance Win32_OperatingSystem).InstallDate.ToString('yyyyMMddHHmmss.ffffff')`

with a ten-second timeout.

The class contains explicit normalization for multiple systeminfo date formats:

- `MM/dd/yyyy, hh:mm:ss a`;
- `dd/MM/yyyy, HH:mm:ss`;
- `yyyy-MM-dd, HH:mm:ss`.

The PowerShell path parses `yyyyMMddHHmmss.SSSSSS` in UTC.

The result is normalized into one timestamp String with timezone-offset information and is
cached together with a completed flag, so the external commands are not rerun after the
first provider call.

Exact live consumers include:

- Client startup/update work, which prewarms the provider;
- R66 `Signlink.e()`, where it is the first platform-identifier source.

## Signlink fallback chain

The exact R66 Signlink environment-identifier helper performs this order:

1. `WindowsInstallDateProvider`;
2. `MacHardwareSerialProvider`;
3. `LinuxHardwareSerialProvider`;
4. if the result is null/empty or matches known invalid sentinel text, fall back to
   Signlink's network-interface MAC-address helper.

This shared consumer proves that all three classes belong to platform identity retrieval,
while their exact external commands make each individual platform role independently clear.

## Naming boundary

All three proposed names are **0.999**.

They describe exact process commands, exact extracted fields and exact live consumers rather
than guessing from the `secure` package name.

The surviving `HardwareValidator` identifier is not repackaged into this batch because its
actual live authority is weaker than these three helpers.

R174 remains class-only.

## Acceptance boundary

Chat 2 does not promote R174. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_58B30FAC567CE1A27397`.
