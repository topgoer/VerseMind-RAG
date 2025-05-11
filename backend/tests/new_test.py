import pytest
import os
import tempfile
import shutil
import json
import time
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from app.services.load_service import LoadService
from app.services.chunk_service import ChunkService

def create_mock_upload_file(filename, content=b""):
    """Create a mock upload file for testing"""
    # Create a proper mock object with the necessary attributes
    class MockUploadFile:
        def __init__(self, filename, file_content=b""):
            self.filename = filename
            # If filename is a real file path, read its content
            if os.path.exists(filename) and os.path.isfile(filename):
                try:
                    with open(filename, "rb") as f:
                        file_content = f.read()
                except Exception as e:
                    print(f"Warning: Could not read file {filename}: {str(e)}")
                    # Use empty content as fallback
                    file_content = b""
            
            self.file = BytesIO(file_content)
            self.size = len(file_content)
            
        async def read(self):
            self.file.seek(0)
            return self.file.read()
            
        async def seek(self, offset):
            self.file.seek(offset)
            return self.file.tell()
            
        async def close(self):
            pass
    
    return MockUploadFile(filename, content)

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
