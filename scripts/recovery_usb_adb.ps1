param(
    [string]$Adb = ".\adb.exe",
    [string]$Target = "",
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

function Get-AdbDevices {
    param([string]$AdbPath)
    $lines = & $AdbPath devices 2>$null
    $devices = @()
    foreach ($line in $lines) {
        if ($line -match '^([^\s]+)\s+device$') {
            $devices += $Matches[1]
        }
    }
    return $devices
}

function Is-NetworkSerial {
    param([string]$Serial)
    return ($Serial -match '^[0-9a-fA-F:.]+:\d+$' -or $Serial -match '^\d{1,3}(\.\d{1,3}){3}:\d+$')
}

$before = Get-AdbDevices $Adb
if (-not $Target) {
    if ($before.Count -ne 1) {
        throw "Specify -Target when more than one (or no) normal-Android ADB device is connected. Current devices: $($before -join ', ')"
    }
    $Target = $before[0]
}

Write-Host "Requesting recovery from normal Android target: $Target"
& $Adb -s $Target reboot recovery

Write-Host "Network ADB is expected to disappear now."
Write-Host "Recovery requires the PHYSICAL USB data wiring soldered to the board's USB-A connector."
Write-Host "Waiting for one non-network ADB serial..."

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$usb = @()
do {
    Start-Sleep -Milliseconds 500
    $all = Get-AdbDevices $Adb
    $usb = @($all | Where-Object { -not (Is-NetworkSerial $_) })
    if ($usb.Count -eq 1) { break }
} while ((Get-Date) -lt $deadline)

if ($usb.Count -ne 1) {
    throw "Did not find exactly one physical-USB recovery ADB device within $TimeoutSeconds seconds. Found: $($usb -join ', ')"
}

$RecoverySerial = $usb[0]
Write-Host "Recovery USB ADB serial: $RecoverySerial"
& $Adb -s $RecoverySerial shell id
& $Adb -s $RecoverySerial shell "ls -l /dev/block/mmcblk0 2>/dev/null || true"
Write-Host "Recovery USB ADB is ready. Keep UART connected in parallel."
