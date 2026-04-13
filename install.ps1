# pkg-upgrade installer for Windows — https://github.com/liskeee/pkg-upgrade
# Usage:  iwr -useb https://raw.githubusercontent.com/liskeee/pkg-upgrade/main/install.ps1 | iex
# Env:
#   $env:PKG_UPGRADE_REF     = "main"                           # git ref for source installs
#   $env:PKG_UPGRADE_SOURCE  = "git+https://github.com/..."     # override pip spec entirely

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/liskeee/pkg-upgrade"
$Ref     = if ($env:PKG_UPGRADE_REF) { $env:PKG_UPGRADE_REF } else { "main" }
$Source  = if ($env:PKG_UPGRADE_SOURCE) { $env:PKG_UPGRADE_SOURCE } else { "git+$RepoUrl@$Ref" }

function Write-Log($msg)  { Write-Host "==> $msg" }
function Write-Warn($msg) { Write-Host "==> warning: $msg" -ForegroundColor Yellow }
function Die($msg)        { Write-Host "==> error: $msg" -ForegroundColor Red; exit 1 }

function Find-Python {
    foreach ($candidate in @("python3.13", "python3.12", "python3", "python", "py -3.13", "py -3.12", "py -3")) {
        $parts = $candidate -split " "
        $exe = $parts[0]
        $args = @()
        if ($parts.Count -gt 1) { $args = $parts[1..($parts.Count - 1)] }
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $check = & $exe @args -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"
            if ($LASTEXITCODE -eq 0) {
                return @{ Exe = $exe; Args = $args }
            }
        } catch { }
    }
    return $null
}

$py = Find-Python
if (-not $py) { Die "Python 3.12+ not found. Install from https://www.python.org/downloads/windows/ or 'winget install Python.Python.3.12'." }
Write-Log "Using Python: $(& $py.Exe @($py.Args + '--version'))"

function Try-Pipx {
    if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) { return $false }
    Write-Log "Installing via pipx..."
    & pipx install --force $Source
    return ($LASTEXITCODE -eq 0)
}

if (-not (Try-Pipx)) {
    Write-Log "pipx not found — bootstrapping with 'python -m pip install --user pipx'..."
    & $py.Exe @($py.Args + @("-m", "pip", "install", "--user", "pipx"))
    & $py.Exe @($py.Args + @("-m", "pipx", "ensurepath"))
    $env:PATH = "$env:PATH;$env:APPDATA\Python\Scripts;$env:USERPROFILE\.local\bin"
    if (-not (Try-Pipx)) {
        Write-Warn "pipx bootstrap failed; falling back to venv."
        $VenvDir = Join-Path $env:LOCALAPPDATA "pkg-upgrade"
        if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
        & $py.Exe @($py.Args + @("-m", "venv", $VenvDir))
        & "$VenvDir\Scripts\python.exe" -m pip install --upgrade pip
        & "$VenvDir\Scripts\python.exe" -m pip install $Source
        $ShimDir = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
        New-Item -ItemType Directory -Force -Path $ShimDir | Out-Null
        $Shim = Join-Path $ShimDir "pkg-upgrade.cmd"
        "@echo off`r`n`"$VenvDir\Scripts\pkg-upgrade.exe`" %*" | Set-Content -Encoding ASCII $Shim
        Write-Log "Installed to $VenvDir; shim at $Shim"
    }
}

# Install PowerShell completion — source it from $PROFILE idempotently.
# The packaged completion ships at pkg_upgrade/completions/pkg-upgrade.ps1
# inside the installed site-packages. We look it up via the package metadata
# so this works for both pipx and venv-fallback installs.
try {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "pkg-upgrade"
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    $completionSource = Join-Path $InstallRoot "pkg-upgrade.ps1"

    $locateScript = @'
import importlib.util, pathlib, sys
spec = importlib.util.find_spec("pkg_upgrade")
if not spec or not spec.submodule_search_locations:
    sys.exit(1)
for root in spec.submodule_search_locations:
    cand = pathlib.Path(root) / "completions" / "pkg-upgrade.ps1"
    if cand.exists():
        print(cand)
        sys.exit(0)
sys.exit(1)
'@

    $pyCompletion = $null
    $candidates = @()
    if (Get-Command pipx -ErrorAction SilentlyContinue) {
        $pipxPy = Join-Path $env:USERPROFILE ".local\pipx\venvs\pkg-upgrade\Scripts\python.exe"
        if (Test-Path $pipxPy) { $candidates += $pipxPy }
    }
    $VenvDir = Join-Path $env:LOCALAPPDATA "pkg-upgrade"
    $venvPy = Join-Path $VenvDir "Scripts\python.exe"
    if (Test-Path $venvPy) { $candidates += $venvPy }
    $candidates += (& $py.Exe @($py.Args + @("-c", "import sys; print(sys.executable)")))

    foreach ($pyExe in $candidates) {
        try {
            $found = & $pyExe -c $locateScript 2>$null
            if ($LASTEXITCODE -eq 0 -and $found -and (Test-Path $found)) {
                $pyCompletion = $found
                break
            }
        } catch { }
    }

    if ($pyCompletion -and (Test-Path $pyCompletion)) {
        Copy-Item -Force $pyCompletion $completionSource
        $sourceLine = ". `"$completionSource`""
        if (-not (Test-Path $PROFILE)) {
            New-Item -ItemType File -Force -Path $PROFILE | Out-Null
        }
        if (-not (Select-String -Path $PROFILE -SimpleMatch -Pattern 'pkg-upgrade.ps1' -Quiet)) {
            Add-Content -Path $PROFILE -Value $sourceLine
            Write-Log "Added pkg-upgrade completion to `$PROFILE. Restart PowerShell to activate."
        }
    } else {
        Write-Warn "Could not locate bundled PowerShell completion; skipping $PROFILE wiring."
    }
} catch {
    Write-Warn "Completion install failed: $_"
}

Write-Log "Done. Run: pkg-upgrade"
