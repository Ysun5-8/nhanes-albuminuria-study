# Run the ML comparison with optional packages kept in a local folder.
param([switch]$Test, [switch]$Validation)
$ErrorActionPreference = 'Stop'
$mlRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$mlPython = Join-Path $mlRoot '.venv/Scripts/python.exe'
$mlLibrary = Join-Path $mlRoot '.ml-library'
$previousPythonPath = $env:PYTHONPATH
$previousThreads = $env:OMP_NUM_THREADS
Push-Location $mlRoot
try {
    if (Test-Path -LiteralPath $mlLibrary) {
        $env:PYTHONPATH = $mlLibrary
        if ($previousPythonPath) { $env:PYTHONPATH += [IO.Path]::PathSeparator + $previousPythonPath }
    }
    $env:OMP_NUM_THREADS = '2'
    if ($Test) {
        & $mlPython -B -m unittest discover -s tests -v
    } elseif ($Validation) {
        & $mlPython -B -m scripts.ml.validate_models
    } else {
        & $mlPython -B -m scripts.ml.run_models
    }
    if ($LASTEXITCODE) { throw 'ML command failed; see the output above.' }
} finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
    $env:OMP_NUM_THREADS = $previousThreads
}
