# Complete cleanup of redundant backend/backend directory
Write-Host "Starting complete cleanup of redundant backend/backend directory..."

$baseDir = "d:\Github\VerseMind-RAG"
$duplicateBase = Join-Path $baseDir "backend\backend"

# First check if there are any files
$hasFiles = $false
if (Test-Path $duplicateBase) {
    $allFiles = Get-ChildItem -Path $duplicateBase -Recurse -File
    if ($allFiles.Count -gt 0) {
        Write-Host "WARNING: Found $($allFiles.Count) files in the duplicate directory structure!"
        Write-Host "Please manually check these files first:"
        foreach($file in $allFiles) {
            Write-Host "  - $($file.FullName)"
        }
        $hasFiles = $true
    }
}

# Only proceed if no files or force flag is set
if ($hasFiles) {
    Write-Host "Aborting cleanup because files were found. Please check them first."
    exit 1
}

# Proceed with deletion
Write-Host "No files found in redundant structure. Proceeding with removal..."

# Remove recursive directories
$subdirs = @(
    "01-loaded_docs",
    "02-chunked-docs", 
    "03-parsed-docs",
    "04-embedded-docs",
    "storage"
)

foreach($dir in $subdirs) {
    $dupPath = Join-Path $duplicateBase $dir
    if (Test-Path $dupPath) {
        Write-Host "Removing directory: $dupPath"
        Remove-Item -Path $dupPath -Recurse -Force
    }
}

# Finally remove the parent directory
if (Test-Path $duplicateBase) {
    Write-Host "Removing parent directory: $duplicateBase"
    Remove-Item -Path $duplicateBase -Recurse -Force
}

if (Test-Path $duplicateBase) {
    Write-Host "ERROR: Could not completely remove $duplicateBase"
} else {
    Write-Host "Successfully removed redundant backend/backend directory!"
}

# Report on the existing correct structure
Write-Host "`nVerifying correct document structure:"
$correctStructure = @(
    "backend\01-loaded_docs",
    "backend\02-chunked-docs",
    "backend\03-parsed-docs",
    "backend\04-embedded-docs"
)

foreach($dir in $correctStructure) {
    $path = Join-Path $baseDir $dir
    if (Test-Path $path) {
        $fileCount = (Get-ChildItem -Path $path -File).Count
        Write-Host "Correct directory $path exists with $fileCount files"
    } else {
        Write-Host "WARNING: Expected directory $path does not exist!"
    }
}
