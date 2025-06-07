# Check if all document types are properly populated and being found
Write-Host "Checking document processing status..."

$baseDir = "d:\Github\VerseMind-RAG"
$dirs = @{
    "Source_Documents" = "storage\documents";
    "Loaded_Documents" = "backend\01-loaded_docs";
    "Chunked_Documents" = "backend\02-chunked-docs";
    "Parsed_Documents" = "backend\03-parsed-docs";
    "Embedded_Documents" = "backend\04-embedded-docs"
}

foreach ($key in $dirs.Keys) {
    $path = Join-Path $baseDir $dirs[$key]
    if (Test-Path $path) {
        $files = Get-ChildItem -Path $path -File
        Write-Host "$key`: $($files.Count) files in $path"
          # List the first few files for verification
        if ($files.Count -gt 0) {
            Write-Host "  First 3 files:"
            $files | Select-Object -First 3 | ForEach-Object {
                Write-Host "  - $($_.Name)"
            }
        } else {
            Write-Host "  No files found!"
        }
    } else {
        Write-Host "$key`: Directory doesn't exist: $path"
    }
}

# Check if any backend services are running
Write-Host "`nChecking if backend services are running..."
$backendProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "uvicorn" }
if ($backendProcess) {
    Write-Host "Backend server is running: $($backendProcess.Id)"
} else {
    Write-Host "Backend server does not appear to be running"
}
