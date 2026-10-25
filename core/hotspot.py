import os
import subprocess
import tempfile
import textwrap

from config import HOTSPOT_PASSWORD, HOTSPOT_SSID

_PS_SCRIPT = r"""
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

$asTaskAction = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
})[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

function AwaitAction($WinRtAction) {
    $netTask = $asTaskAction.Invoke($null, @($WinRtAction))
    $netTask.Wait(-1) | Out-Null
}

[Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType = WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking.NetworkOperators, ContentType = WindowsRuntime] | Out-Null

$profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
if ($null -eq $profile) {
    Write-Output "NO_INTERNET_PROFILE"
    exit 0
}

$manager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile)
$desiredSsid = "__SSID__"
$desiredPassword = "__PASSWORD__"

$config = $manager.GetCurrentAccessPointConfiguration()
$needsConfig = ($config.Ssid -ne $desiredSsid) -or ($config.Passphrase -ne $desiredPassword)

if ($needsConfig -and $manager.TetheringOperationalState -eq 'On') {
    $stopResult = Await ($manager.StopTetheringAsync()) ([Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult])
    Write-Output "STOP:$($stopResult.Status)"
}

if ($needsConfig) {
    $config = $manager.GetCurrentAccessPointConfiguration()
    $config.Ssid = $desiredSsid
    $config.Passphrase = $desiredPassword
    AwaitAction ($manager.ConfigureAccessPointAsync($config))
}

if ($manager.TetheringOperationalState -ne 'On') {
    $startResult = Await ($manager.StartTetheringAsync()) ([Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult])
    Write-Output "START:$($startResult.Status)"
} else {
    Write-Output "ALREADY_ON:$($config.Ssid)"
}
"""


def ensure_hotspot(timeout=25):
    script = textwrap.dedent(_PS_SCRIPT)
    script = script.replace("__SSID__", HOTSPOT_SSID)
    script = script.replace("__PASSWORD__", HOTSPOT_PASSWORD)
    script_path = os.path.join(tempfile.gettempdir(), "eca_print_hotspot.ps1")
    try:
        with open(script_path, "w", encoding="utf-8") as handle:
            handle.write(script)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=flags,
        )
        output = (result.stdout or "").strip()
        if output:
            print(f"[Hotspot] {output}")
        if result.returncode != 0:
            error = (result.stderr or "").strip()
            if error:
                print(f"[Hotspot] {error}")
            return False
        return True
    except Exception as exc:
        print(f"[Hotspot] Could not start: {exc}")
        return False
