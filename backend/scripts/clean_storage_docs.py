#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to clean up temporary test files in the storage/documents directory.
This can be run directly to remove all temporary PDF files created during tests.
"""

import os
import sys
import logging
from pathlib import Path
from app.utils.test_cleanup import TestFileCleanup

# Add the parent directory to sys.path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

def main():
    """Clean up temporary test files in storage/documents directory"""
    logging.basicConfig(level=logging.INFO,
                      format='[%(asctime)s] %(levelname)s - %(message)s')

    logger = logging.getLogger(__name__)
    logger.info("Starting storage/documents test file cleanup...")

    # Define the storage documents directory
    project_root = Path(__file__).parent.parent.parent
    storage_docs_dir = os.path.join(project_root, 'storage', 'documents')

    if not os.path.exists(storage_docs_dir):
        logger.error(f"Directory not found: {storage_docs_dir}")
        return

    # Print stats about files before cleanup
    count_before = len([f for f in os.listdir(storage_docs_dir) if os.path.isfile(os.path.join(storage_docs_dir, f))])
    logger.info(f"Found {count_before} files in storage/documents directory before cleanup")

    # Create a TestFileCleanup instance
    cleaner = TestFileCleanup()

    # Only clean the storage documents directory specifically
    logger.info("Cleaning storage/documents directory...")
    count, files = cleaner._clean_storage_documents_directory()

    if count > 0:
        logger.info(f"Cleaned {count} files from storage/documents directory:")
        for file in files:
            logger.info(f"  - {os.path.basename(file)}")
    else:
        logger.info("No files needed cleaning in storage/documents directory")

    # Store total count (we're only cleaning storage/documents directory)
    total_count = count

    # Print final stats
    count_after = len([f for f in os.listdir(storage_docs_dir) if os.path.isfile(os.path.join(storage_docs_dir, f))])
    logger.info(f"Total files cleaned: {total_count}")
    logger.info(f"Files in storage/documents: {count_before} before, {count_after} after cleanup")

if __name__ == "__main__":
    main()
