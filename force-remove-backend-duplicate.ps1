# Force remove the backend/backend directory
Write-Host "Forcefully removing the redundant backend/backend directory..."

$duplicateDir = "D:\Github\VerseMind-RAG\backend\backend"

if (Test-Path -Path $duplicateDir -PathType Container) {
    # First check if there are any actual files (not directories)
    $files = Get-ChildItem -Path $duplicateDir -File -Recurse
    if ($files.Count -gt 0) {
        Write-Host "WARNING: Found $($files.Count) files in the directory:"
        $files | ForEach-Object {
            Write-Host "  - $($_.FullName)"
        }
        $confirm = Read-Host "Are you sure you want to delete these files? (y/n)"
        if ($confirm.ToLower() -ne "y") {
            Write-Host "Aborted. No files were deleted."
            exit
        }
    }
    
    # Try to force remove the directory
    try {
        Write-Host "Removing directory: $duplicateDir"
        Remove-Item -Path $duplicateDir -Recurse -Force -ErrorAction Stop
        if (Test-Path -Path $duplicateDir) {
            throw "Directory still exists after removal attempt"
        }
        Write-Host "Successfully removed the backend/backend directory!"
    }
    catch {
        Write-Host "ERROR: Could not remove the directory: $_"
        
        # If the standard removal fails, try an alternative approach
        Write-Host "Trying alternative removal method..."
        try {
            # Use cmd.exe to run rmdir command with /s /q flags
            cmd /c "rmdir /s /q $duplicateDir"
            
            if (Test-Path -Path $duplicateDir) {
                Write-Host "ERROR: Directory still exists after alternative removal attempt"
            } else {
                Write-Host "Successfully removed the directory using alternative method!"
            }
        }
        catch {
            Write-Host "ERROR: Alternative removal failed: $_"
        }
    }
} else {
    Write-Host "Directory does not exist: $duplicateDir"
}

# Verify removal
if (Test-Path -Path $duplicateDir) {
    Write-Host "VERIFICATION FAILED: Directory still exists at: $duplicateDir"
} else {
    Write-Host "VERIFICATION PASSED: Directory has been successfully removed!"
}
