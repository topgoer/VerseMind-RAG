# Check if any files still exist in the backend/backend directory structure
Write-Host "Checking for files in backend/backend directory structure..."

$baseDir = "d:\Github\VerseMind-RAG"
$duplicateBase = Join-Path $baseDir "backend\backend"

$subdirs = @(
    "01-loaded_docs",
    "02-chunked-docs", 
    "03-parsed-docs",
    "04-embedded-docs"
)

$needsMigration = $false

foreach($dir in $subdirs) {
    $dupPath = Join-Path $duplicateBase $dir
    if (Test-Path $dupPath) {
        $files = Get-ChildItem -Path $dupPath -File
        if ($files.Count -gt 0) {
            Write-Host "Found $($files.Count) files in $dupPath"
            $needsMigration = $true
        } else {
            Write-Host "No files found in $dupPath"
        }
    } else {
        Write-Host "Directory doesn't exist: $dupPath"
    }
}

if ($needsMigration) {
    Write-Host "Some files still need migration from the backend/backend directory structure"
} else {
    Write-Host "No files found in backend/backend structure that need migration"
}

# Check for the backend/backend directory itself
if (Test-Path $duplicateBase) {
    Write-Host "The backend/backend directory still exists and should be removed after ensuring no important files remain"
} else {
    Write-Host "backend/backend directory doesn't exist"
}
