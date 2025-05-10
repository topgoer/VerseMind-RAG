# filepath: d:\Github\VerseMind-RAG\backend\tests\test_pdf_extraction.py
import os
import sys
import json
import pytest
import tempfile
import time
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, AsyncMock
import io
from fastapi import UploadFile  # Import UploadFile

# Add the parent directory to the path so we can import the app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.services.chunk_service import ChunkService
from app.services.load_service import LoadService
from app.services.parse_service import ParseService

# Helper function to run async code in tests
def run_async(coro):
    return asyncio.run(coro)

# Helper function to create a mock UploadFile
def create_mock_upload_file(file_path: str) -> AsyncMock:  # Return AsyncMock
    """Creates a mock FastAPI UploadFile object from a file path."""
    file_name = os.path.basename(file_path)
    # Read the file content into bytes
    with open(file_path, "rb") as f:
        file_content_bytes = f.read()

    # Create the main mock for UploadFile using AsyncMock and spec
    # spec=UploadFile ensures the mock adheres to the UploadFile interface
    mock_upload_file = AsyncMock(spec=UploadFile)
    mock_upload_file.filename = file_name
    # Configure the async methods directly on the AsyncMock
    # .read() should be awaitable and return bytes
    mock_upload_file.read = AsyncMock(return_value=file_content_bytes)
    # .seek() should be awaitable and return the new position (or None/0)
    mock_upload_file.seek = AsyncMock(return_value=0)
    # Add close method if needed
    mock_upload_file.close = AsyncMock()

    return mock_upload_file

# Basic PDF extraction test (MVP)
@pytest.mark.asyncio  # Mark test as async
async def test_pdf_extraction(document_cleanup):  # Make test async and use the document_cleanup fixture
    """Test PDF extraction functionality using a dynamically generated PDF"""
    pdf_path = None  # Initialize pdf_path
    document_id = None  # Initialize document_id
    
    try:
        # Create a temporary PDF file for testing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
            # Make sure we close the file before writing to it
            tmp_file.close()
            
            # Generate a simple PDF with reportlab
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter

            c = canvas.Canvas(pdf_path, pagesize=letter)
            c.drawString(100, 750, "VerseMind-RAG Test Document")
            c.drawString(100, 700, "This is a test PDF document created for testing PDF extraction.")
            c.drawString(100, 650, "This document contains multiple lines of text.")
            c.drawString(100, 600, "The PDF parser should be able to extract this text correctly.")
            c.drawString(100, 550, "This test verifies that the PDF extraction functionality works.")
            c.save()

            # Initialize services needed for testing
            load_service = LoadService()
            chunk_service = ChunkService()

            # Create mock UploadFile
            mock_upload_file = create_mock_upload_file(pdf_path)
            
            # Load the PDF file using the mock object
            load_result = await load_service.load_document(mock_upload_file)
            document_id = load_result.get("id")  # Get the ID from the load result
            assert document_id is not None, "Document loading failed to return id"
            
            # Print info to help with debugging
            print(f"Test PDF path: {pdf_path}")
            print(f"Document ID: {document_id}")
            
            # Set a test environment marker to enable test file handling
            os.environ['TEST_ENV'] = 'true'
            
            # Store the temp file name in a way that includes the document_id for easier matching
            new_test_path = os.path.join(os.path.dirname(pdf_path), f"{document_id}_{os.path.basename(pdf_path)}")
            try:
                # Make a copy with the ID in the filename to help with lookup
                import shutil
                shutil.copy2(pdf_path, new_test_path)
                print(f"Created test copy with ID in filename: {new_test_path}")
            except Exception as e:
                print(f"Warning: Could not create test copy: {e}")
                # Not critical if this fails

            # Chunk the document using the correct method and strategy
            chunk_result = chunk_service.create_chunks(document_id, strategy="char_count", chunk_size=200, overlap=50)  # Use create_chunks and specify strategy

            # Basic validation checks
            assert chunk_result is not None, "Document chunking failed"
            assert "result_file" in chunk_result, "Chunk result missing result_file key"

            # Verify chunks were created by checking the result file
            chunks_path = os.path.join(chunk_service.chunks_dir, chunk_result["result_file"])
            assert os.path.exists(chunks_path), f"Chunks file not created at {chunks_path}"

            with open(chunks_path, "r", encoding="utf-8") as f:
                chunks_data = json.load(f)

            assert "chunks" in chunks_data, "No chunks key in the chunks data"
            assert len(chunks_data["chunks"]) > 0, "Empty chunks list"

            # Verify that expected text was extracted
            all_text = ""
            for chunk in chunks_data["chunks"]:
                all_text += chunk.get("content", "")

            expected_texts = [
                "VerseMind-RAG Test Document",
                "test PDF document",
                "multiple lines of text",
                "extract this text correctly"
            ]

            for expected_text in expected_texts:
                assert expected_text in all_text, f"Expected text '{expected_text}' not found in extracted content: {all_text[:500]}..."  # Show partial content on failure
            print(f"Successfully extracted and chunked the PDF into file: {chunk_result['result_file']}")
    except Exception as e:
        print(f"PDF extraction test failed with exception: {str(e)}")        
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        raise
    finally:
        # Clean up immediately after the test
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
                print(f"Cleaned up temporary PDF: {pdf_path}")
            except Exception as e:
                print(f"Failed to clean up temporary file {pdf_path}: {str(e)}")
                
        # Clean up all files related to this document using document_cleanup fixture
        if document_id:
            cleaned_count = document_cleanup(document_id)
            print(f"Cleaned up {cleaned_count} files for document {document_id}")


@pytest.mark.asyncio
async def test_parsing_strategies(document_cleanup):
    """Test different parsing strategies for PDF documents"""
    pdf_path = None
    document_id = None
    load_service = None
    chunk_service = None
    
    try:
        # Create a temporary PDF file for testing with multiple pages
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
            # Generate a simple PDF with reportlab
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter

            c = canvas.Canvas(pdf_path, pagesize=letter)
            # Page 1
            c.drawString(100, 750, "Test Document: Parsing Strategies")
            c.drawString(100, 700, "Chapter 1: Introduction")
            c.drawString(100, 650, "This is the introduction to our test document.")
            c.drawString(100, 600, "It contains multiple pages and headings for testing.")
            c.showPage()
            # Page 2
            c.drawString(100, 750, "Chapter 2: Methods")
            c.drawString(100, 700, "This section describes the methods used.")
            c.drawString(100, 650, "2.1 Data Collection")
            c.drawString(100, 600, "Data was collected using various techniques.")
            c.showPage()
            # Page 3
            c.drawString(100, 750, "Chapter 3: Results")
            c.drawString(100, 700, "The results of our analysis are presented here.")
            c.drawString(100, 650, "3.1 Main Findings")
            c.drawString(100, 600, "Several interesting patterns were discovered.")
            c.save()

            # Initialize services needed for testing
            load_service = LoadService()
            chunk_service = ChunkService()
            
            # Create mock UploadFile
            mock_upload_file = create_mock_upload_file(pdf_path)
            
            # Load the PDF file
            load_result = await load_service.load_document(mock_upload_file)
            document_id = load_result.get("id")  # Changed from "document_id" to "id"
            assert document_id is not None, "Document loading failed"

            # Test different chunking strategies
            strategies_to_test = ["char_count", "paragraph", "heading"]
            results = {}

            for strategy in strategies_to_test:
                print(f"\nTesting strategy: {strategy}")
                chunk_result = chunk_service.create_chunks(document_id, strategy=strategy, chunk_size=150, overlap=30)
                assert chunk_result is not None, f"Chunking failed for strategy {strategy}"
                assert "result_file" in chunk_result, f"Chunk result missing result_file for strategy {strategy}"
                results[strategy] = chunk_result                # No need to track files for cleanup - document_cleanup will handle it

                # Basic validation: Check if chunk file exists and has chunks
                chunks_path = os.path.join(chunk_service.chunks_dir, chunk_result["result_file"])
                assert os.path.exists(chunks_path), f"Chunks file not created for strategy {strategy}"
                with open(chunks_path, "r", encoding="utf-8") as f:
                    chunks_data = json.load(f)
                assert "chunks" in chunks_data, f"No chunks key in chunks data for strategy {strategy}"
                assert len(chunks_data["chunks"]) > 0, f"Empty chunks list for strategy {strategy}"
                print(f"Strategy {strategy} created {len(chunks_data['chunks'])} chunks.")
                
    except Exception as e:
        print(f"Parsing strategies test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Clean up immediately after testing all strategies
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
                print(f"Cleaned up temporary PDF: {pdf_path}")
            except Exception as e:
                print(f"Failed to clean up temporary file {pdf_path}: {str(e)}")
                
        # Clean up all document-related files right away
        if document_id:
            cleaned_count = document_cleanup(document_id)
            print(f"Cleaned up {cleaned_count} files for document {document_id}")


@pytest.mark.asyncio
async def test_pdf_extraction_edge_cases(document_cleanup):
    """Test PDF extraction handling of edge cases like empty or very small PDFs"""
    pdf_path_empty = None
    pdf_path_small = None
    doc_id_empty = None
    doc_id_small = None

    load_service = LoadService()  # Initialize services outside try blocks
    chunk_service = ChunkService()

    try:
        # --- Test with empty PDF ---
        print("\nTesting empty PDF...")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file_empty:
            pdf_path_empty = tmp_file_empty.name
            # Generate an empty PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(pdf_path_empty, pagesize=letter)
            c.save()
            
            # Create mock UploadFile for empty PDF
            mock_upload_file_empty = create_mock_upload_file(pdf_path_empty)
            
            # Load the empty PDF file
            load_result_empty = await load_service.load_document(mock_upload_file_empty)
            doc_id_empty = load_result_empty.get("id")  # Changed from "document_id" to "id"
            assert doc_id_empty is not None, "Empty PDF loading failed"

            # Chunk the empty document (should not fail, might produce 0 chunks)
            chunk_result_empty = chunk_service.create_chunks(doc_id_empty, strategy="char_count")
            assert chunk_result_empty is not None, "Chunking empty PDF failed"
            assert "result_file" in chunk_result_empty, "Chunk result missing result_file for empty PDF"
            chunk_file_empty = os.path.join(chunk_service.chunks_dir, chunk_result_empty["result_file"])

            assert os.path.exists(chunk_file_empty), "Chunks file not created for empty PDF"
            with open(chunk_file_empty, "r", encoding="utf-8") as f:
                chunks_data_empty = json.load(f)
            assert "chunks" in chunks_data_empty, "No chunks key in chunks data for empty PDF"
            # Allow 0 or 1 chunk for empty PDF, check content if 1 chunk exists
            assert len(chunks_data_empty.get("chunks", [])) <= 1, "Expected 0 or 1 chunk for empty PDF"
            if len(chunks_data_empty.get("chunks", [])) == 1:
                # Check if content is empty or just contains page markers/whitespace
                content = chunks_data_empty["chunks"][0].get("content", "").strip()
                assert content == "" or content.startswith("[页码:"), f"Chunk for empty PDF is not empty: {content[:100]}..."
            print("Empty PDF processed successfully.")
            
        # --- Test with very small PDF ---
        print("\nTesting small PDF...")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file_small:
            pdf_path_small = tmp_file_small.name
            # Close the file before writing to it to avoid sharing violations
            tmp_file_small.close()
            # Wait a moment to ensure creation time will be different
            time.sleep(0.5)
            
            # Generate a small PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(pdf_path_small, pagesize=letter)
            small_text = "Tiny."
            c.drawString(100, 750, small_text)
            c.save()

            # Create mock UploadFile for small PDF
            mock_upload_file_small = create_mock_upload_file(pdf_path_small)
            
            # Make sure the file exists and is readable
            assert os.path.exists(pdf_path_small), f"Small test PDF not found at {pdf_path_small}"
            print(f"Created small test PDF at: {pdf_path_small}")
            
            # Load the small PDF file
            load_result_small = await load_service.load_document(mock_upload_file_small)
            doc_id_small = load_result_small.get("id")  # Changed from "document_id" to "id"
            assert doc_id_small is not None, "Small PDF loading failed"

            # Chunk the small document
            chunk_result_small = chunk_service.create_chunks(doc_id_small, strategy="char_count", chunk_size=100)  # Use small chunk size
            assert chunk_result_small is not None, "Chunking small PDF failed"
            assert "result_file" in chunk_result_small, "Chunk result missing result_file for small PDF"
            chunk_file_small = os.path.join(chunk_service.chunks_dir, chunk_result_small["result_file"])

            assert os.path.exists(chunk_file_small), "Chunks file not created for small PDF"
            with open(chunk_file_small, "r", encoding="utf-8") as f:
                chunks_data_small = json.load(f)
            assert "chunks" in chunks_data_small, "No chunks key in chunks data for small PDF"
            assert len(chunks_data_small["chunks"]) == 1, "Expected exactly 1 chunk for small PDF"            # Check if the small text is present, potentially with page marker
            chunk_content = chunks_data_small["chunks"][0].get("content", "")
            assert small_text in chunk_content, f"Small PDF content mismatch. Expected '{small_text}' in '{chunk_content}'"
            print("Small PDF processed successfully.")
            
    except Exception as e:
        print(f"Edge case test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Clean up resources immediately after each test
        # First handle empty PDF test
        if pdf_path_empty and os.path.exists(pdf_path_empty):
            try:
                os.unlink(pdf_path_empty)
                print(f"Cleaned up temporary PDF: {pdf_path_empty}")
            except Exception as e:
                print(f"Failed to clean up temporary file {pdf_path_empty}: {str(e)}")
                
        if doc_id_empty:
            cleaned_count = document_cleanup(doc_id_empty)
            print(f"Cleaned up {cleaned_count} files for document {doc_id_empty}")
              # Then handle small PDF test resources
        if pdf_path_small and os.path.exists(pdf_path_small):
            try:
                os.unlink(pdf_path_small)
                print(f"Cleaned up temporary PDF: {pdf_path_small}")
            except Exception as e:
                print(f"Failed to clean up temporary file {pdf_path_small}: {str(e)}")
                
        if doc_id_small:
            cleaned_count = document_cleanup(doc_id_small)
            print(f"Cleaned up {cleaned_count} files for document {doc_id_small}")


@pytest.mark.asyncio
async def test_pdf_extraction_edge_cases_improved(document_cleanup):
    """Test PDF extraction handling of edge cases like empty or very small PDFs, with immediate cleanup"""
    load_service = LoadService()  # Initialize services outside try blocks
    chunk_service = ChunkService()

    # --- Test with empty PDF ---
    pdf_path_empty = None
    doc_id_empty = None
    
    try:
        print("\nTesting empty PDF...")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file_empty:
            pdf_path_empty = tmp_file_empty.name
            # Generate an empty PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(pdf_path_empty, pagesize=letter)
            c.save()
            
            # Create mock UploadFile for empty PDF
            mock_upload_file_empty = create_mock_upload_file(pdf_path_empty)
            
            # Load the empty PDF file
            load_result_empty = await load_service.load_document(mock_upload_file_empty)
            doc_id_empty = load_result_empty.get("id")
            assert doc_id_empty is not None, "Empty PDF loading failed"

            # Chunk the empty document (should not fail, might produce 0 chunks)
            chunk_result_empty = chunk_service.create_chunks(doc_id_empty, strategy="char_count")
            assert chunk_result_empty is not None, "Chunking empty PDF failed"
            assert "result_file" in chunk_result_empty, "Chunk result missing result_file for empty PDF"
            chunk_file_empty = os.path.join(chunk_service.chunks_dir, chunk_result_empty["result_file"])

            assert os.path.exists(chunk_file_empty), "Chunks file not created for empty PDF"
            with open(chunk_file_empty, "r", encoding="utf-8") as f:
                chunks_data_empty = json.load(f)
            assert "chunks" in chunks_data_empty, "No chunks key in chunks data for empty PDF"
            # Allow 0 or 1 chunk for empty PDF, check content if 1 chunk exists
            assert len(chunks_data_empty.get("chunks", [])) <= 1, "Expected 0 or 1 chunk for empty PDF"
            if len(chunks_data_empty.get("chunks", [])) == 1:
                # Check if content is empty or just contains page markers/whitespace
                content = chunks_data_empty["chunks"][0].get("content", "").strip()
                assert content == "" or content.startswith("[页码:"), f"Chunk for empty PDF is not empty: {content[:100]}..."
            print("Empty PDF processed successfully.")
            
        # Clean up empty PDF test files immediately
        if pdf_path_empty and os.path.exists(pdf_path_empty):
            try:
                os.unlink(pdf_path_empty)
                print(f"Cleaned up empty PDF immediately: {pdf_path_empty}")
            except Exception as e:
                print(f"Failed to clean up empty PDF file {pdf_path_empty}: {str(e)}")
                
        if doc_id_empty:
            cleaned_count = document_cleanup(doc_id_empty)
            print(f"Cleaned up {cleaned_count} files for document {doc_id_empty} immediately")
    
    except Exception as e:
        print(f"Empty PDF test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    # --- Test with very small PDF ---
    pdf_path_small = None
    doc_id_small = None
    
    try:
        print("\nTesting small PDF...")
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file_small:
            pdf_path_small = tmp_file_small.name
            # Close the file before writing to it to avoid sharing violations
            tmp_file_small.close()
            # Wait a moment to ensure creation time will be different
            time.sleep(0.5)
            
            # Generate a small PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(pdf_path_small, pagesize=letter)
            small_text = "Tiny."
            c.drawString(100, 750, small_text)
            c.save()

            # Create mock UploadFile for small PDF
            mock_upload_file_small = create_mock_upload_file(pdf_path_small)
            
            # Make sure the file exists and is readable
            assert os.path.exists(pdf_path_small), f"Small test PDF not found at {pdf_path_small}"
            print(f"Created small test PDF at: {pdf_path_small}")
            
            # Load the small PDF file
            load_result_small = await load_service.load_document(mock_upload_file_small)
            doc_id_small = load_result_small.get("id")
            assert doc_id_small is not None, "Small PDF loading failed"

            # Chunk the small document
            chunk_result_small = chunk_service.create_chunks(doc_id_small, strategy="char_count", chunk_size=100)
            assert chunk_result_small is not None, "Chunking small PDF failed"
            assert "result_file" in chunk_result_small, "Chunk result missing result_file for small PDF"
            chunk_file_small = os.path.join(chunk_service.chunks_dir, chunk_result_small["result_file"])

            assert os.path.exists(chunk_file_small), "Chunks file not created for small PDF"
            with open(chunk_file_small, "r", encoding="utf-8") as f:
                chunks_data_small = json.load(f)
            assert "chunks" in chunks_data_small, "No chunks key in chunks data for small PDF"
            assert len(chunks_data_small["chunks"]) == 1, "Expected exactly 1 chunk for small PDF"
            # Check if the small text is present, potentially with page marker
            chunk_content = chunks_data_small["chunks"][0].get("content", "")
            assert small_text in chunk_content, f"Small PDF content mismatch. Expected '{small_text}' in '{chunk_content}'"
            print("Small PDF processed successfully.")
        
        # Clean up small PDF test files immediately
        if pdf_path_small and os.path.exists(pdf_path_small):
            try:
                os.unlink(pdf_path_small)
                print(f"Cleaned up small PDF immediately: {pdf_path_small}")
            except Exception as e:
                print(f"Failed to clean up small PDF file {pdf_path_small}: {str(e)}")
                
        if doc_id_small:
            cleaned_count = document_cleanup(doc_id_small)
            print(f"Cleaned up {cleaned_count} files for document {doc_id_small} immediately")
    
    except Exception as e:
        print(f"Small PDF test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
