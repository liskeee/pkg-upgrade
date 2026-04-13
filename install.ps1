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

Write-Log "Done. Run: pkg-upgrade"
