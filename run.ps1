<#
.SYNOPSIS
    Build and run the OpenRouter prices Docker container, then copy output files.
.DESCRIPTION
    Builds the Docker image, runs it to scrape rankings and generate reports,
    and copies prices.md and prices.html to the current directory.
.EXAMPLE
    .\run.ps1
#>

$ErrorActionPreference = "Stop"

$ImageName = "openrouter-prices"
$OutputDir = Join-Path (Get-Location) "output"

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Write-Host "Building Docker image '$ImageName'..." -ForegroundColor Cyan
docker build -t $ImageName (Split-Path $MyInvocation.MyCommand.Path -Parent)

Write-Host "Running container (scraping rankings and generating reports)..." -ForegroundColor Cyan
try {
    docker run --rm -v "${OutputDir}:/app/output" $ImageName
} catch {
    Write-Host "Container exited with errors. No output files generated." -ForegroundColor Red
    Remove-Item -Path $OutputDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# Only copy output files if they exist and are non-empty
$updated = $false
if (Test-Path (Join-Path $OutputDir "prices.html")) {
    $size = (Get-Item (Join-Path $OutputDir "prices.html")).Length
    if ($size -gt 0) {
        Copy-Item -Path (Join-Path $OutputDir "prices.html") -Destination ./prices.html -Force
        $updated = $true
    }
}

if (Test-Path (Join-Path $OutputDir "prices.md")) {
    $size = (Get-Item (Join-Path $OutputDir "prices.md")).Length
    if ($size -gt 0) {
        Copy-Item -Path (Join-Path $OutputDir "prices.md") -Destination ./prices.md -Force
        $updated = $true
    }
}

# Cleanup output dir
Remove-Item -Path $OutputDir -Recurse -Force -ErrorAction SilentlyContinue

if ($updated) {
    Write-Host "Done. Files written:" -ForegroundColor Green
    Write-Host "  ./prices.html" -ForegroundColor Yellow
    Write-Host "  ./prices.md" -ForegroundColor Yellow
} else {
    Write-Host "No output files generated. Check logs above for errors." -ForegroundColor Red
    exit 1
}