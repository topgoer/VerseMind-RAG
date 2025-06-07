"""
Global pytest configuration for the VerseMind-RAG test suite.
This file contains fixtures that can be used by all tests.
"""

import pytest
import os
import sys
from pathlib import Path
from app.utils.test_cleanup import TestFileCleanup, cleanup_test_files

# Add the parent directory to sys.path to ensure imports work correctly
sys.path.append(str(Path(__file__).parent.parent))

# Set the TEST_ENV environment variable to enable test-specific behavior
os.environ['TEST_ENV'] = 'true'


@pytest.fixture(scope="session")
def cleanup_all_test_files():
    """
    Fixture to clean up all test files at the end of the test session.
    This can help keep the workspace clean between test runs.

    Usage:
        def test_something(cleanup_all_test_files):
            # The fixture doesn't need to be used explicitly
            # It will clean up test files after all tests are done
            ...
    """
    # Yield to let the tests run
    yield

    # After all tests, clean up all test files
    print("\nCleaning up all test files after test session...")
    count, _ = cleanup_test_files()
    if count > 0:
        print(f"Cleaned {count} test files.")
    else:
        print("No test files needed cleaning.")


@pytest.fixture
def document_cleanup():
    """
    Fixture to provide a function that cleans up files for a specific document ID.
    This is useful for cleaning up after tests that create document-specific files.

    Usage:
        def test_something(document_cleanup):
            # Test that creates a document
            document_id = "abc123"
            ...
            # Clean up just this document's files
            document_cleanup(document_id)
    """
    created_document_ids = []

    def _cleanup(document_id=None):
        """Clean up test files for a specific document ID or all created documents"""
        nonlocal created_document_ids

        if document_id:
            if document_id not in created_document_ids:
                created_document_ids.append(document_id)
            count, _ = cleanup_test_files(document_id)
            return count
        else:
            # Clean up all documents that were tracked during the test
            total = 0
            for doc_id in created_document_ids:
                count, _ = cleanup_test_files(doc_id)
                total += count
            created_document_ids = []  # Reset the list
            return total

    # Provide the cleanup function to the test
    yield _cleanup

    # After the test finishes, clean up any documents that weren't explicitly cleaned
    if created_document_ids:
        print(f"\nCleaning up {len(created_document_ids)} document(s) after test...")
        for doc_id in created_document_ids:
            count, _ = cleanup_test_files(doc_id)
            if count > 0:
                print(f"  - Cleaned {count} files for document {doc_id}")


@pytest.fixture
def cleaner():
    """
    Fixture to provide a TestFileCleanup instance that can be used directly.
    This is useful for tests that need more control over the cleanup process.

    Usage:
        def test_something(cleaner):
            # Test code here
            ...
            # Get document IDs from files
            document_ids = cleaner.get_document_ids_from_files()
            # Clean up specific files or directories
            cleaner.clean_document_files("abc123")
    """
    return TestFileCleanup()
