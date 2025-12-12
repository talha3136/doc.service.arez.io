import os
import uuid
import tempfile
import shutil
import requests
from PyPDF2 import PdfReader, PdfWriter
from google.cloud import documentai
from .ai_service import get_embeddings_from_gemini, chunk_text_divider
from .vector_db import insert_embeddings, create_tables_for_db, verify_insertion
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def process_document_task(process_task_id: str, file_url: str, db_name: str):
    """Process document and create embeddings."""
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"procdoc_{process_task_id}_")
        local_file_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_file.pdf")

        # Download file
        response = requests.get(file_url, stream=True)
        response.raise_for_status()

        with open(local_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Check number of pages
        reader = PdfReader(local_file_path)
        num_pages = len(reader.pages)

        if num_pages <= 10:
            # Process as single document
            result = process_single_pdf(process_task_id, local_file_path, db_name)
        else:
            # Split into chunks of 10 pages
            results = []
            for start_page in range(0, num_pages, 10):
                end_page = min(start_page + 10, num_pages)
                sub_file_path = os.path.join(temp_dir, f"chunk_{start_page}_{end_page}.pdf")

                # Create sub-PDF
                writer = PdfWriter()
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                with open(sub_file_path, 'wb') as f:
                    writer.write(f)

                # Process chunk
                chunk_result = process_single_pdf(process_task_id, sub_file_path, db_name)
                results.append(chunk_result)

            # Aggregate results
            total_chunks = sum(r["chunks_created"] for r in results)
            total_embeddings = sum(r["embeddings_created"] for r in results)
            combined_text = " ".join(r["text"] for r in results)[:2000]
            result = {
                "text": combined_text,
                "chunks_created": total_chunks,
                "embeddings_created": total_embeddings
            }

        return result

    except Exception as e:
        logger.error(f"Error processing document {process_task_id}: {e}")
        raise
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

def process_single_pdf(process_task_id: str, file_path: str, db_name: str):
    """Process a single PDF file."""
    # Process with Document AI
    extracted_text = extract_text_with_docai(file_path)

    # Create embeddings
    chunks = chunk_text_divider(extracted_text, max_chars=2000, overlap=200)
    embeddings = get_embeddings_from_gemini(chunks)

    # Ensure table exists and store embeddings in specified database
    logger.info(f"Creating tables for db: {db_name}")
    create_tables_for_db(db_name)
    logger.info(f"Inserting {len(embeddings)} embeddings for task: {process_task_id}")
    insert_embeddings(db_name, process_task_id, chunks, embeddings)

    # Verify insertion
    inserted_count = verify_insertion(db_name, process_task_id)
    logger.info(f"Verification: {inserted_count} records found for task: {process_task_id}")

    return {
        "text": extracted_text[:2000],  # Summary
        "chunks_created": len(chunks),
        "embeddings_created": len(embeddings)
    }

def extract_text_with_docai(file_path: str) -> str:
    """Extract text using Google Document AI."""
    try:
        client = documentai.DocumentProcessorServiceClient()
        name = f"projects/{current_app.config['DOCUMENT_AI_PROJECT']}/locations/{current_app.config['DOCUMENT_AI_LOCATION']}/processors/{current_app.config['DOCUMENT_AI_PROCESSOR_ID']}"

        with open(file_path, "rb") as f:
            content = f.read()

        raw_document = documentai.RawDocument(content=content, mime_type="application/pdf")
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)

        response = client.process_document(request=request)
        return response.document.text or ""

    except Exception as e:
        logger.error(f"Document AI extraction failed: {e}")
        return "Text extraction failed"