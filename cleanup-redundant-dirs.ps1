# Script to check for and clean up redundant backend/backend directory
Write-Host "Checking for redundant backend/backend directory..."

$mainBackendPath = "d:\Github\VerseMind-RAG\backend"
$redundantPath = "d:\Github\VerseMind-RAG\backend\backend"

if (Test-Path $redundantPath) {
    # First ensure all files from redundant directories are copied to main directories
    $docsDir = Join-Path -Path $redundantPath -ChildPath "01-loaded_docs"
    $mainDocsDir = Join-Path -Path $mainBackendPath -ChildPath "01-loaded_docs"
    
    if (Test-Path $docsDir) {
        if (-not (Test-Path $mainDocsDir)) {
            New-Item -Path $mainDocsDir -ItemType Directory -Force
        }
        
        # Copy all JSON files
        Get-ChildItem -Path $docsDir -Filter "*.json" | ForEach-Object {
            $destPath = Join-Path -Path $mainDocsDir -ChildPath $_.Name
            if (-not (Test-Path $destPath)) {
                Copy-Item -Path $_.FullName -Destination $mainDocsDir -Force
                Write-Host "Copied $($_.Name) to $mainDocsDir"
            }
        }
    }
    
    # Check if there are any unique files or directories that need to be preserved
    $shouldRemove = $true
    $uniqueItems = @()
    
    Get-ChildItem -Path $redundantPath -Recurse | ForEach-Object {
        $relativePath = $_.FullName.Replace("$redundantPath\", "")
        $correspondingPath = Join-Path -Path $mainBackendPath -ChildPath $relativePath
        
        if (-not (Test-Path $correspondingPath) -and -not $_.PSIsContainer) {
            $uniqueItems += $_.FullName
            $shouldRemove = $false
        }
    }
    
    if ($uniqueItems.Count -gt 0) {
        Write-Host "Found $($uniqueItems.Count) unique files in the redundant directory:"
        $uniqueItems | ForEach-Object { Write-Host "  - $_" }
        Write-Host "Skipping removal to avoid data loss. Please migrate these files manually."
    } else {
        Write-Host "All files from redundant directory have been migrated or already exist in main directory."
        Write-Host "Would remove redundant backend/backend directory if this wasn't a dry run."
        # Uncomment this line to actually perform removal
        # Remove-Item -Path $redundantPath -Recurse -Force
    }
} else {
    Write-Host "No redundant backend/backend directory found. Your configuration is clean."
}

Write-Host "Done!"
