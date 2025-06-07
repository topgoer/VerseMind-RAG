#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility module for cleaning up temporary files created during tests.
This module identifies and removes temporary files in:
1. System temp directory (particularly PDF files with document IDs)
2. Project test directories (01-loaded_docs, 02-chunked-docs, 03-parsed-docs, 04-embedded-docs)
"""

import os
import tempfile
import logging
import shutil
import glob
from typing import List, Optional, Set, Tuple
import datetime
import re

logger = logging.getLogger(__name__)

class TestFileCleanup:
    """
    Class for cleaning up temporary files created during tests.
    Can be used in test fixtures, test teardown, or as a standalone cleanup utility.
    """

    def __init__(self, 
                 storage_dir=None,
                 documents_dir="01-loaded_docs", 
                 chunks_dir="02-chunked-docs", 
                 parsed_dir="03-parsed-docs",
                 embeddings_dir="04-embedded-docs"):
        """
        Initialize the cleanup utility with paths to relevant directories.

        Args:
            storage_dir: The root storage directory. If None, will be calculated from the current file.
            documents_dir: The directory name for loaded documents
            chunks_dir: The directory name for chunked documents
            parsed_dir: The directory name for parsed documents
            embeddings_dir: The directory name for embedded documents
        """
        # Calculate storage_dir if not provided
        if storage_dir is None:
            self.storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        else:
            self.storage_dir = storage_dir

        # Define directory paths
        self.documents_dir = os.path.join(self.storage_dir, 'backend', documents_dir)

        # Also add direct storage directory paths for files outside the backend directory
        self.storage_documents_dir = os.path.join(self.storage_dir, 'storage', 'documents')
        self.chunks_dir = os.path.join(self.storage_dir, 'backend', chunks_dir)
        self.parsed_dir = os.path.join(self.storage_dir, 'backend', parsed_dir)
        self.embeddings_dir = os.path.join(self.storage_dir, 'backend', embeddings_dir)

        # System temp directory
        self.temp_dir = tempfile.gettempdir()
        logger.debug("TestFileCleanup initialized with directories:")
        logger.debug(f"  Storage: {self.storage_dir}")
        logger.debug(f"  Documents: {self.documents_dir}")
        logger.debug(f"  Chunks: {self.chunks_dir}")
        logger.debug(f"  Parsed: {self.parsed_dir}")
        logger.debug(f"  Embeddings: {self.embeddings_dir}")
        logger.debug(f"  Storage Documents: {self.storage_documents_dir}")
        logger.debug(f"  Temp: {self.temp_dir}")

    def _is_test_file(self, filepath: str) -> bool:
        """
        Determine if a file is likely a test file.
        This checks for patterns like UUIDs, timestamps, or test markers.

        Args:
            filepath: Path to the file to check

        Returns:
            bool: True if the file is likely a test file
        """
        filename = os.path.basename(filepath)

        # Patterns that suggest a test file
        test_patterns = [
            r'test',                             # Contains "test"
            r'[0-9a-f]{8}[-_]',                  # Contains a UUID-like pattern
            r'\d{8}_\d{6}',                      # Contains a timestamp like 20250412_123456
            r'tmp[0-9a-zA-Z]+\.',                # Temporary file naming pattern
            r'[0-9a-f]{4,8}\.pdf',               # Short hex ID followed by .pdf
        ]

        # Check the creation time - if it's recent (e.g., past hour), it's more likely a test file
        try:
            file_mtime = os.path.getmtime(filepath)
            file_age_hours = (datetime.datetime.now().timestamp() - file_mtime) / 3600
            # If file is less than 1 hour old and in a test context, it's likely a test file
            if file_age_hours < 1 and os.environ.get('TEST_ENV') == 'true':
                return True
        except Exception:
            pass  # Ignore errors in getting file time

        # Check for patterns in filename
        for pattern in test_patterns:
            if re.search(pattern, filename):
                return True

        return False

    def _get_files_to_clean(self, directory: str, age_hours: float = 24.0) -> List[str]:
        """
        Get a list of files that should be cleaned up in the given directory.

        Args:
            directory: The directory to scan for files to clean
            age_hours: Only clean up files older than this many hours (default 24.0)

        Returns:
            List of file paths that should be cleaned up
        """
        files_to_clean = []

        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            return files_to_clean

        # Current time for age comparison
        current_time = datetime.datetime.now().timestamp()

        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)

            # Skip directories
            if os.path.isdir(filepath):
                continue

            # Check if it's a test file
            if self._is_test_file(filepath):
                # Check file age
                try:
                    file_mtime = os.path.getmtime(filepath)
                    file_age_hours = (current_time - file_mtime) / 3600

                    if file_age_hours >= age_hours:
                        files_to_clean.append(filepath)
                except Exception as e:
                    logger.warning(f"Error getting file time for {filepath}: {e}")

        return files_to_clean

    def _clean_temp_directory(self, doc_ids: Optional[List[str]] = None) -> Tuple[int, List[str]]:
        """
        Clean up files in the system temp directory that match document IDs or test patterns.

        Args:
            doc_ids: Optional list of document IDs to specifically clean up

        Returns:
            Tuple of (count of files cleaned, list of files cleaned)
        """
        cleaned_files = []

        # Check temp directory for PDF files with document IDs
        if os.path.exists(self.temp_dir):
            for filename in os.listdir(self.temp_dir):
                filepath = os.path.join(self.temp_dir, filename)

                # Skip directories
                if os.path.isdir(filepath):
                    continue

                # If doc_ids provided, only match files containing one of those IDs
                if doc_ids:
                    if not any(doc_id in filename for doc_id in doc_ids):
                        continue

                # For safety, only clean PDF files in temp directory
                if filename.endswith('.pdf') and self._is_test_file(filepath):
                    try:
                        os.unlink(filepath)
                        cleaned_files.append(filepath)
                        logger.info(f"Cleaned temp file: {filepath}")
                    except Exception as e:
                        logger.warning(f"Failed to clean temp file {filepath}: {e}")

        return len(cleaned_files), cleaned_files

    def _clean_document_directory(self) -> Tuple[int, List[str]]:
        """
        Clean up test files in the documents directory.

        Returns:
            Tuple of (count of files cleaned, list of files cleaned)
        """
        files_to_clean = self._get_files_to_clean(self.documents_dir)
        cleaned_files = []

        for filepath in files_to_clean:
            try:
                os.remove(filepath)
                cleaned_files.append(filepath)
                logger.info(f"Cleaned document file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to clean document file {filepath}: {e}")

        return len(cleaned_files), cleaned_files

    def _clean_chunks_directory(self) -> Tuple[int, List[str]]:
        """
        Clean up test files in the chunks directory.

        Returns:
            Tuple of (count of files cleaned, list of files cleaned)
        """
        files_to_clean = self._get_files_to_clean(self.chunks_dir)
        cleaned_files = []

        for filepath in files_to_clean:
            try:
                os.remove(filepath)
                cleaned_files.append(filepath)
                logger.info(f"Cleaned chunk file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to clean chunk file {filepath}: {e}")

        return len(cleaned_files), cleaned_files

    def _clean_parsed_directory(self) -> Tuple[int, List[str]]:
        """
        Clean up test files in the parsed directory.

        Returns:
            Tuple of (count of files cleaned, list of files cleaned)
        """
        files_to_clean = self._get_files_to_clean(self.parsed_dir)
        cleaned_files = []

        for filepath in files_to_clean:
            try:
                os.remove(filepath)
                cleaned_files.append(filepath)
                logger.info(f"Cleaned parsed file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to clean parsed file {filepath}: {e}")

        return len(cleaned_files), cleaned_files

    def _clean_embeddings_directory(self) -> Tuple[int, List[str]]:
        """
        Clean up test files in the embeddings directory.

        Returns:
            Tuple of (count of files cleaned, list of files cleaned)
        """
        files_to_clean = self._get_files_to_clean(self.embeddings_dir)
        cleaned_files = []

        for filepath in files_to_clean:
            try:
                os.remove(filepath)
                cleaned_files.append(filepath)
                logger.info(f"Cleaned embedding file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to clean embedding file {filepath}: {e}")

        return len(cleaned_files), cleaned_files

    def _clean_storage_documents_directory(self) -> Tuple[int, List[str]]:
        """
        Clean up test files in the storage/documents directory.

        Returns:
            Tuple of (count of files cleaned, list of files cleaned)
        """
        files_to_clean = self._get_files_to_clean(self.storage_documents_dir)
        cleaned_files = []

        for filepath in files_to_clean:
            try:
                os.remove(filepath)
                cleaned_files.append(filepath)
                logger.info(f"Cleaned storage document file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to clean storage document file {filepath}: {e}")

        return len(cleaned_files), cleaned_files

    def clean_document_files(self, document_id: str) -> Tuple[int, List[str]]:
        """
        Clean up all files related to a specific document ID.

        Args:
            document_id: The document ID to clean up files for

        Returns:
            Tuple of (count of files cleaned, list of files cleaned)
        """
        total_cleaned = 0
        all_cleaned_files = []

        # Clean temp directory for this document ID
        count, files = self._clean_temp_directory([document_id])
        total_cleaned += count
        all_cleaned_files.extend(files)

        # Check each directory for files with this document ID
        for directory in [self.documents_dir, self.chunks_dir, self.parsed_dir, self.embeddings_dir, self.storage_documents_dir]:
            if not os.path.exists(directory):
                continue

            for filename in os.listdir(directory):
                if document_id in filename:
                    filepath = os.path.join(directory, filename)
                    try:
                        os.remove(filepath)
                        all_cleaned_files.append(filepath)
                        total_cleaned += 1
                        logger.info(f"Cleaned file for document {document_id}: {filepath}")
                    except Exception as e:
                        logger.warning(f"Failed to clean file {filepath}: {e}")

        return total_cleaned, all_cleaned_files

    def clean_all_test_files(self) -> Tuple[int, List[str]]:
        """
        Clean up all test files across all directories.

        Returns:
            Tuple of (count of files cleaned, list of files cleaned)
        """
        total_cleaned = 0
        all_cleaned_files = []

        # Clean temp directory
        count, files = self._clean_temp_directory()
        total_cleaned += count
        all_cleaned_files.extend(files)

        # Clean each directory
        for clean_func in [
            self._clean_document_directory,
            self._clean_chunks_directory,
            self._clean_parsed_directory,
            self._clean_embeddings_directory,
            self._clean_storage_documents_directory
        ]:
            count, files = clean_func()
            total_cleaned += count
            all_cleaned_files.extend(files)

        return total_cleaned, all_cleaned_files

    def get_document_ids_from_files(self) -> Set[str]:
        """
        Extract document IDs from filenames across all directories.
        This can be useful to find document IDs for cleaning.

        Returns:
            Set of document IDs found
        """
        document_ids = set()
        id_pattern = r'([0-9a-f]{8})[-_]'  # Pattern to match document IDs

        # Check all directories for files containing document IDs
        for directory in [self.documents_dir, self.chunks_dir, self.parsed_dir, self.embeddings_dir]:
            if not os.path.exists(directory):
                continue

            for filename in os.listdir(directory):
                match = re.search(id_pattern, filename)
                if match:
                    document_ids.add(match.group(1))

        return document_ids


# Function for easy use in tests
def cleanup_test_files(document_id: Optional[str] = None):
    """
    Clean up test files, either for a specific document ID or all test files.
    This is a convenience function for use in test fixtures.

    Args:
        document_id: Optional document ID to clean up. If None, cleans all test files.

    Returns:
        Tuple of (count of files cleaned, list of files cleaned)
    """
    cleaner = TestFileCleanup()

    if document_id:
        return cleaner.clean_document_files(document_id)
    else:
        return cleaner.clean_all_test_files()


if __name__ == "__main__":
    # When run directly, clean all test files
    logging.basicConfig(level=logging.INFO,
                       format='[%(asctime)s] %(levelname)s - %(message)s')

    cleaner = TestFileCleanup()
    count, files = cleaner.clean_all_test_files()

    print(f"Cleaned {count} test files:")
    for file in files:
        print(f"  - {file}")

    if count == 0:
        print("No test files found to clean.")
d)
    """
    cleaner = TestFileCleanup()
    
    if document_id:
        return cleaner.clean_document_files(document_id)
    else:
        return cleaner.clean_all_test_files()


if __name__ == "__main__":
    # When run directly, clean all test files
    logging.basicConfig(level=logging.INFO,
                       format='[%(asctime)s] %(levelname)s - %(message)s')
    
    cleaner = TestFileCleanup()
    count, files = cleaner.clean_all_test_files()
    
    print(f"Cleaned {count} test files:")
    for file in files:
        print(f"  - {file}")
    
    if count == 0:
        print("No test files found to clean.")
