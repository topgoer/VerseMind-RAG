# Script to consolidate document JSON files
Write-Host "Consolidating document JSONs from duplicate directories..."

# Define paths
$mainPath = "d:\Github\VerseMind-RAG\backend\01-loaded_docs"
$dupPath = "d:\Github\VerseMind-RAG\backend\backend\01-loaded_docs"

# Create directory if it doesn't exist
if (-not (Test-Path $mainPath)) {
    New-Item -Path $mainPath -ItemType Directory -Force
    Write-Host "Created main directory: $mainPath"
}

# Check if duplicate directory exists
if (Test-Path $dupPath) {
    # Copy JSON files from duplicate directory to main directory
    $jsonFiles = Get-ChildItem -Path $dupPath -Filter "*.json"
    foreach ($file in $jsonFiles) {
        $destPath = Join-Path -Path $mainPath -ChildPath $file.Name
        if (-not (Test-Path $destPath)) {
            Copy-Item -Path $file.FullName -Destination $mainPath -Force
            Write-Host "Copied $($file.Name) to main directory"
        } else {
            Write-Host "File already exists in main directory: $($file.Name)"
        }
    }
    
    $jsonCount = (Get-ChildItem -Path $mainPath -Filter "*.json").Count
    Write-Host "Consolidated. Main directory now has $jsonCount JSON files."
} else {
    Write-Host "Duplicate directory not found: $dupPath"
}

Write-Host "Done!"
