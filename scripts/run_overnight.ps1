param(
    [int]$Epochs = 3,
    [int]$BatchSize = 1,
    [int]$GradAccum = 1,
    [double]$LearningRate = 0.0002,
    [string]$TrainData = "data/training",
    [string]$EvalData = "data/evaluation",
    [string]$AdapterDir = "models/srs-task-adapter",
    [string]$SampleFile = "samples/sample_srs_erp.md",
    [string]$SampleOutput = "output/overnight_tasks.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string[]]$Command
    )

    Write-Host ""
    Write-Host ("=" * 72)
    Write-Host $Name
    Write-Host ("=" * 72)
    Write-Host ($Command -join " ")

    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$TrainDataPath = (Resolve-Path $TrainData).Path
$EvalDataPath = (Resolve-Path $EvalData).Path
$SampleFilePath = (Resolve-Path $SampleFile).Path
$AdapterPath = Join-Path $ProjectRoot $AdapterDir
$SampleOutputPath = Join-Path $ProjectRoot $SampleOutput

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logsDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
$transcriptPath = Join-Path $logsDir "overnight_run_$timestamp.log"

Start-Transcript -Path $transcriptPath | Out-Null

try {
    Write-Host "Project root: $ProjectRoot"
    Write-Host "Train data:   $TrainDataPath"
    Write-Host "Eval data:    $EvalDataPath"
    Write-Host "Adapter dir:  $AdapterPath"
    Write-Host "Sample file:  $SampleFilePath"
    Write-Host "Log file:     $transcriptPath"

    Invoke-Step -Name "1. Training" -Command @(
        "python",
        "src/train.py",
        "--data", $TrainDataPath,
        "--eval-data", $EvalDataPath,
        "--output", $AdapterPath,
        "--batch-size", "$BatchSize",
        "--grad-accum", "$GradAccum",
        "--epochs", "$Epochs",
        "--lr", "$LearningRate"
    )

    Invoke-Step -Name "2. Holdout Evaluation" -Command @(
        "python",
        "src/evaluate.py",
        "--eval-data", $EvalDataPath,
        "--adapter", $AdapterPath
    )

    Invoke-Step -Name "3. Sample Generation Smoke Test" -Command @(
        "python",
        "src/generate.py",
        "--file", $SampleFilePath,
        "--adapter", $AdapterPath,
        "--output", $SampleOutputPath
    )

    Write-Host ""
    Write-Host ("=" * 72)
    Write-Host "Overnight run completed successfully."
    Write-Host "Sample output: $SampleOutputPath"
    Write-Host "Evaluation reports: $(Join-Path $ProjectRoot 'evaluation_results')"
    Write-Host "Log file: $transcriptPath"
    Write-Host ("=" * 72)
}
finally {
    Stop-Transcript | Out-Null
}
