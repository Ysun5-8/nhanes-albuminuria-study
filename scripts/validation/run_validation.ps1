# Run validation from any working folder; project paths come from this script.
# Both modes replace named aggregate outputs and reports. See docs/reproduction.md.
param(
    # Relative overrides are resolved from the repository, not the caller's folder.
    [string]$RscriptPath = '',
    [string]$LibraryPath = '',
    [switch]$ReviewRobustness
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

function Resolve-ProjectPath([string]$Path) {
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return Join-Path $projectRoot $Path
}

# Prefer an optional repository-local R installation, then the user's PATH.
# On Windows, the R installer can also register its location without adding PATH.
if (-not $RscriptPath) {
    $localRscript = Join-Path $projectRoot '.tools\R\bin\Rscript.exe'
    if (Test-Path -LiteralPath $localRscript -PathType Leaf) {
        $RscriptPath = $localRscript
    } else {
        $command = Get-Command -Name Rscript.exe,Rscript -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) { $RscriptPath = $command.Source }
    }
    if (-not $RscriptPath) {
        foreach ($key in @('HKCU:\Software\R-core\R', 'HKLM:\Software\R-core\R')) {
            $installation = Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
            if ($installation -and $installation.InstallPath) {
                $candidate = Join-Path $installation.InstallPath 'bin\Rscript.exe'
                if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                    $RscriptPath = $candidate
                    break
                }
            }
        }
    }
} else {
    $RscriptPath = Resolve-ProjectPath $RscriptPath
}
if (-not $RscriptPath -or -not (Test-Path -LiteralPath $RscriptPath -PathType Leaf)) {
    throw 'Rscript was not found. Install R or supply -RscriptPath with an absolute or repository-relative executable path.'
}

# Use a project library only when it exists. Otherwise retain R's normal library
# discovery, including an existing R_LIBS_USER value. Never install packages here.
if ($LibraryPath) {
    $LibraryPath = Resolve-ProjectPath $LibraryPath
    if (-not (Test-Path -LiteralPath $LibraryPath -PathType Container)) {
        throw 'The requested R library folder does not exist. Install the documented packages before validation.'
    }
} else {
    $localLibrary = Join-Path $projectRoot '.r-library'
    if (Test-Path -LiteralPath $localLibrary -PathType Container) {
        $LibraryPath = $localLibrary
    }
}

# Restore the caller's setting on success or failure; no permanent environment edit.
$previousLibrary = $env:R_LIBS_USER
try {
    if ($LibraryPath) { $env:R_LIBS_USER = $LibraryPath }
    $analysisScript = 'validate_with_r.R'
    if ($ReviewRobustness) {
        & $RscriptPath --vanilla (Join-Path $projectRoot 'tests\test_reliability_helpers.R') $projectRoot
        if ($LASTEXITCODE -ne 0) { throw 'Reliability helper tests failed.' }
        $analysisScript = 'review_robustness.R'
    }
    & $RscriptPath --vanilla (Join-Path $PSScriptRoot $analysisScript) $projectRoot
    if ($LASTEXITCODE -ne 0) { throw "R validation failed (exit $LASTEXITCODE). Read its output and comparison report." }
} finally {
    $env:R_LIBS_USER = $previousLibrary
}
