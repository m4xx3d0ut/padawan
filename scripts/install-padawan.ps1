$ErrorActionPreference = "Stop"

$DefaultBaseUrl = "https://github.com/m4xx3d0ut/padawan/releases/latest/download"
$BaseUrl = if ($env:PADAWAN_INSTALL_BASE_URL) { $env:PADAWAN_INSTALL_BASE_URL } else { $DefaultBaseUrl }
$ArchiveName = if ($env:PADAWAN_WHEELHOUSE_ARCHIVE) { $env:PADAWAN_WHEELHOUSE_ARCHIVE } else { "padawan-wheelhouse.zip" }
$ForceStandalone = if ($env:PADAWAN_FORCE_STANDALONE) { $env:PADAWAN_FORCE_STANDALONE } else { "0" }
$LocalAppData = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $HOME "AppData\Local" }
$InstallDir = if ($env:PADAWAN_INSTALL_DIR) { $env:PADAWAN_INSTALL_DIR } else { Join-Path $LocalAppData "Padawan" }
$BinDir = if ($env:PADAWAN_BIN_DIR) { $env:PADAWAN_BIN_DIR } else { Join-Path $InstallDir "bin" }

function Fail($Message) {
  Write-Error "padawan install: $Message"
  exit 1
}

function Find-Python {
  if ($env:PYTHON) {
    return @{ Exe = $env:PYTHON; Args = @() }
  }
  $Candidates = @(
    @{ Exe = "py"; Args = @("-3.11") },
    @{ Exe = "py"; Args = @("-3") },
    @{ Exe = "python"; Args = @() }
  )
  foreach ($Candidate in $Candidates) {
    try {
      & $Candidate.Exe @($Candidate.Args) --version *> $null
      if ($LASTEXITCODE -eq 0) {
        return $Candidate
      }
    } catch {
      continue
    }
  }
  Fail "missing Python 3.11 or newer"
}

$Python = Find-Python
& $Python.Exe @($Python.Args) -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
  Fail "Python 3.11 or newer is required"
}

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("padawan-install-" + [System.Guid]::NewGuid())
New-Item -ItemType Directory -Path $TempDir | Out-Null
try {
  $Archive = Join-Path $TempDir $ArchiveName
  $Wheelhouse = Join-Path $TempDir "wheelhouse"
  $Url = "$BaseUrl/$ArchiveName"
  Write-Host "Downloading Padawan wheelhouse from $Url"
  if ($BaseUrl -like "file://*") {
    $LocalBase = ([System.Uri]$BaseUrl).LocalPath
    Copy-Item -Path (Join-Path $LocalBase $ArchiveName) -Destination $Archive
  } else {
    Invoke-WebRequest -Uri $Url -OutFile $Archive
  }
  New-Item -ItemType Directory -Path $Wheelhouse | Out-Null
  Expand-Archive -Path $Archive -DestinationPath $Wheelhouse -Force
  $NestedWheelhouse = Join-Path $Wheelhouse "padawan-wheelhouse"
  if (Test-Path $NestedWheelhouse) {
    $Wheelhouse = $NestedWheelhouse
  }

  if ($env:VIRTUAL_ENV -and $ForceStandalone -ne "1") {
    $TargetPython = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
    $InstallMode = "active-venv"
  } else {
    $TargetPython = Join-Path $InstallDir "venv\Scripts\python.exe"
    $InstallMode = "standalone"
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    & $Python.Exe @($Python.Args) -m venv (Join-Path $InstallDir "venv")
    if ($LASTEXITCODE -ne 0) {
      Fail "failed to create venv; install Python venv support or activate an existing venv"
    }
  }

  $PackageSpec = "padawan"
  $PackageWheel = Get-ChildItem -Path $Wheelhouse -Filter "padawan-*.whl" | Select-Object -First 1
  if ($PackageWheel -and $PackageWheel.Name -match "^padawan-(.+?)-") {
    $PackageSpec = "padawan==$($Matches[1])"
  }

  & $TargetPython -m pip install --upgrade pip *> $null
  & $TargetPython -m pip install --no-compile --no-index --find-links $Wheelhouse $PackageSpec
  if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Bundled wheelhouse install failed; retrying with package index access for platform-specific wheels."
    & $TargetPython -m pip install --no-compile --find-links $Wheelhouse $PackageSpec
    if ($LASTEXITCODE -ne 0) {
      Fail "pip install failed"
    }
  }

  if ($InstallMode -eq "standalone") {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
    $CmdWrapper = Join-Path $BinDir "padawan.cmd"
    $PsWrapper = Join-Path $BinDir "padawan.ps1"
    Set-Content -Path $CmdWrapper -Encoding ASCII -Value @"
@echo off
"$TargetPython" -m padawan.cli %*
"@
    Set-Content -Path $PsWrapper -Encoding UTF8 -Value @"
& "$TargetPython" -m padawan.cli @args
exit `$LASTEXITCODE
"@
    $PathEntries = ($env:PATH -split ";")
    if ($PathEntries -notcontains $BinDir) {
      Write-Host ""
      Write-Host "Add Padawan to your PATH:"
      Write-Host "  `$env:PATH = `"$BinDir;`$env:PATH`""
    }
  }

  $PadawanCmd = "$TargetPython -m padawan.cli"
  if (Get-Command padawan -ErrorAction SilentlyContinue) {
    $PadawanCmd = "padawan"
  }

  Write-Host ""
  Write-Host "Padawan installed ($InstallMode)."
  Write-Host "Verify with: $PadawanCmd doctor"
  Write-Host "Run with:    $PadawanCmd serve"
} finally {
  Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
