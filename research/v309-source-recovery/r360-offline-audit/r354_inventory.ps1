# R354: inventory only. No Windows feature changes, firewall changes, network traffic,
# game launch, process termination, elevation or OS-isolation claims.
$ErrorActionPreference = 'Stop'
$names = @(
  'Containers-DisposableClientVM',
  'Microsoft-Hyper-V-All',
  'VirtualMachinePlatform',
  'HypervisorPlatform',
  'Microsoft-Windows-Subsystem-Linux'
)
$featureStates = [ordered]@{}
foreach ($name in $names) {
  try {
    $result = @(Get-CimInstance -ClassName Win32_OptionalFeature -Filter "Name='$name'" -ErrorAction Stop)
    if ($result.Count -eq 1 -and $null -ne $result[0].InstallState) {
      $featureStates[$name] = [int]$result[0].InstallState
    } else {
      $featureStates[$name] = $null
    }
  } catch {
    $featureStates[$name] = $null
  }
}
$os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
$computer = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop
$data = [ordered]@{
  schema = 'R354_READ_ONLY_WINDOWS_FEATURE_INVENTORY_V1'
  source = 'Win32_OptionalFeature+Win32_OperatingSystem+Win32_ComputerSystem'
  operating_system = [string]$os.Caption
  os_version = [string]$os.Version
  hypervisor_present = [bool]$computer.HypervisorPresent
  sandbox_executable_present = [bool](Test-Path -LiteralPath "$env:WINDIR\System32\WindowsSandbox.exe")
  features = $featureStates
  runtime_admitted = $false
  os_egress_attested = $false
  original_client_started = $false
}
$data | ConvertTo-Json -Depth 6 -Compress
