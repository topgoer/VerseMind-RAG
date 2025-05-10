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

def main():
    """Clean up temporary test files in storage/documents directory"""
    logging.basicConfig(level=logging.INFO,
                      format='[%(asctime)s] %(levelname)s - %(message)s')
    
    logger = logging.getLogger(__name__)
    logger.info("Starting direct storage/documents test file cleanup...")
    
    # Define the storage documents directory
    project_root = Path(__file__).parent.parent.parent
    storage_docs_dir = os.path.join(project_root, 'storage', 'documents')
    
    if not os.path.exists(storage_docs_dir):
        logger.error(f"Directory not found: {storage_docs_dir}")
        return
    
    # Patterns for test files
    test_patterns = [
        r'tmp[0-9a-zA-Z]+\.',                # Temporary file naming pattern
        r'[0-9a-f]{8}\.pdf',                 # Short hex ID followed by .pdf
        r'test',                             # Contains "test"
        r'\d{8}_\d{6}',                      # Contains a timestamp like 20250412_123456
    ]
    
    # Current time for age comparison
    current_time = datetime.datetime.now().timestamp()
    
    # Print stats about files before cleanup
    count_before = len([f for f in os.listdir(storage_docs_dir) if os.path.isfile(os.path.join(storage_docs_dir, f))])
    logger.info(f"Found {count_before} files in storage/documents directory before cleanup")
    
    # Find and clean temp files
    cleaned_files = []
    for filename in os.listdir(storage_docs_dir):
        filepath = os.path.join(storage_docs_dir, filename)
        
        # Skip directories
        if os.path.isdir(filepath):
            continue
            
        # Check if it's a test file
        is_test_file = False
        for pattern in test_patterns:
            if re.search(pattern, filename):
                is_test_file = True
                break
                
        # Check the file age (clean files older than a day)
        if is_test_file:
            try:
                file_mtime = os.path.getmtime(filepath)
                file_age_hours = (current_time - file_mtime) / 3600
                
                # Print file info
                logger.info(f"Found test file: {filename} (Age: {file_age_hours:.1f} hours)")
                
                # Remove files that are at least 1 hour old
                if file_age_hours >= 1:
                    try:
                        os.remove(filepath)
                        cleaned_files.append(filepath)
                        logger.info(f"Cleaned test file: {filepath}")
                    except Exception as e:
                        logger.error(f"Error cleaning file {filepath}: {e}")
            except Exception as e:
                logger.warning(f"Error processing file {filepath}: {e}")
    
    # Print final stats
    count_after = len([f for f in os.listdir(storage_docs_dir) if os.path.isfile(os.path.join(storage_docs_dir, f))])
    logger.info(f"Cleaned {len(cleaned_files)} test files from storage/documents")
    logger.info(f"Files in storage/documents: {count_before} before, {count_after} after cleanup")

if __name__ == "__main__":
    main()
