#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Direct cleanup script for the storage/documents directory.
This script scans the directory directly for test files and removes them.
"""

import os
import re
import datetime
import logging
from pathlib import Path


def get_test_file_patterns():
    """Return the list of regex patterns for identifying test files."""
    return [
        r"tmp[0-9a-zA-Z]+\.",  # Temporary file naming pattern
        r"[0-9a-f]{8}\.pdf",  # Short hex ID followed by .pdf
        r"test",  # Contains "test"
        r"\d{8}_\d{6}",  # Contains a timestamp like 20250412_123456
    ]


def is_test_file(filename, test_patterns):
    """Check if a file matches any of the test file patterns."""
    for pattern in test_patterns:
        if re.search(pattern, filename):
            return True
    return False


def clean_test_file(filepath, current_time, logger):
    """Clean a test file if it is older than 1 hour."""
    try:
        file_mtime = os.path.getmtime(filepath)
        file_age_hours = (current_time - file_mtime) / 3600

        logger.info(
            f"Found test file: {os.path.basename(filepath)} (Age: {file_age_hours:.1f} hours)"
        )

        if file_age_hours >= 1:
            os.remove(filepath)
            logger.info(f"Cleaned test file: {filepath}")
            return filepath
    except Exception as e:
        logger.warning(f"Error processing file {filepath}: {e}")
    return None


def main():
    """Clean up temporary test files in storage/documents directory"""
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting direct storage/documents test file cleanup...")

    # Define the storage documents directory
    project_root = Path(__file__).parent.parent.parent
    storage_docs_dir = os.path.join(project_root, "storage", "documents")

    if not os.path.exists(storage_docs_dir):
        logger.error(f"Directory not found: {storage_docs_dir}")
        return

    test_patterns = get_test_file_patterns()
    current_time = datetime.datetime.now().timestamp()

    # Print stats about files before cleanup
    count_before = len(
        [
            f
            for f in os.listdir(storage_docs_dir)
            if os.path.isfile(os.path.join(storage_docs_dir, f))
        ]
    )
    logger.info(
        f"Found {count_before} files in storage/documents directory before cleanup"
    )

    # Find and clean temp files
    cleaned_files = []
    for filename in os.listdir(storage_docs_dir):
        filepath = os.path.join(storage_docs_dir, filename)

        # Skip directories
        if os.path.isdir(filepath):
            continue

        # Check if it's a test file
        if is_test_file(filename, test_patterns):
            cleaned_file = clean_test_file(filepath, current_time, logger)
            if cleaned_file:
                cleaned_files.append(cleaned_file)

    # Print final stats
    count_after = len(
        [
            f
            for f in os.listdir(storage_docs_dir)
            if os.path.isfile(os.path.join(storage_docs_dir, f))
        ]
    )
    logger.info(f"Cleaned {len(cleaned_files)} test files from storage/documents")
    logger.info(
        f"Files in storage/documents: {count_before} before, {count_after} after cleanup"
    )


if __name__ == "__main__":
    main()
