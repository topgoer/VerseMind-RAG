# Complete migration script for VerseMind-RAG document directories
Write-Host "Starting comprehensive document migration..." -ForegroundColor Green

# Define paths
$projectRoot = "d:\Github\VerseMind-RAG"
$mainBackendPath = Join-Path $projectRoot "backend"
$redundantPath = Join-Path $mainBackendPath "backend"

# Define directories to check and migrate
$dirPairs = @(
    @{ source = "$redundantPath\01-loaded_docs"; dest = "$mainBackendPath\01-loaded_docs" },
    @{ source = "$redundantPath\02-chunked-docs"; dest = "$mainBackendPath\02-chunked-docs" },
    @{ source = "$redundantPath\03-parsed-docs"; dest = "$mainBackendPath\03-parsed-docs" },
    @{ source = "$redundantPath\04-embedded-docs"; dest = "$mainBackendPath\04-embedded-docs" }
)

# Counter for statistics
$totalFiles = 0
$migratedFiles = 0

# Process each directory pair
foreach ($dirPair in $dirPairs) {
    $sourcePath = $dirPair.source
    $destPath = $dirPair.dest
    
    # Check if source directory exists
    if (Test-Path $sourcePath) {
        Write-Host "Processing directory: $sourcePath" -ForegroundColor Cyan
        
        # Create destination directory if it doesn't exist
        if (-not (Test-Path $destPath)) {
            New-Item -Path $destPath -ItemType Directory -Force | Out-Null
            Write-Host "  Created destination directory: $destPath"
        }
        
        # Copy all JSON files that don't already exist in the destination
        $jsonFiles = Get-ChildItem -Path $sourcePath -Filter "*.json"
        $totalFiles += $jsonFiles.Count
        
        foreach ($file in $jsonFiles) {
            $destFilePath = Join-Path -Path $destPath -ChildPath $file.Name
            if (-not (Test-Path $destFilePath)) {
                Copy-Item -Path $file.FullName -Destination $destPath -Force
                $migratedFiles++
                Write-Host "  Migrated: $($file.Name)" -ForegroundColor Yellow
            } else {
                Write-Host "  Already exists: $($file.Name)" -ForegroundColor Gray
            }
        }
    }
}

# Summary
Write-Host "`nMigration Summary:" -ForegroundColor Green
Write-Host "Total files scanned: $totalFiles" -ForegroundColor Cyan
Write-Host "Files migrated to main directories: $migratedFiles" -ForegroundColor Cyan

# Create a report file
$date = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $projectRoot "migration_report_$date.txt"

@"
VERSEMIND-RAG DOCUMENT MIGRATION REPORT
======================================
Date: $(Get-Date)

Main backend path: $mainBackendPath
Redundant path: $redundantPath

Total files scanned: $totalFiles
Files migrated: $migratedFiles

NOTE: After verifying that all files have been properly migrated,
you can safely remove the redundant backend/backend directory.
"@ | Out-File -FilePath $reportPath -Encoding utf8

Write-Host "`nMigration report saved to: $reportPath" -ForegroundColor Green
Write-Host "`nIMPORTANT: After verifying that all files were properly migrated," -ForegroundColor Yellow
Write-Host "you can safely remove the redundant directory: $redundantPath" -ForegroundColor Yellow
Write-Host "This script only copied files and did not delete anything." -ForegroundColor Yellow

Write-Host "`nDone!" -ForegroundColor Green
