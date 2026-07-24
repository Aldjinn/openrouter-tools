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
docker run --rm -v "${OutputDir}:/app/output" $ImageName

Write-Host "Copying output files to current directory..." -ForegroundColor Cyan
Copy-Item -Path (Join-Path $OutputDir "prices.html") -Destination ./prices.html -Force
Copy-Item -Path (Join-Path $OutputDir "prices.md") -Destination ./prices.md -Force

# Cleanup output dir
Remove-Item -Path $OutputDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Done. Files written:" -ForegroundColor Green
Write-Host "  ./prices.html" -ForegroundColor Yellow
Write-Host "  ./prices.md" -ForegroundColor Yellow