import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
from flask import current_app
from .vector_db import search_similar, create_tables_for_db
import logging

logger = logging.getLogger(__name__)

def search_similar_chunks(query_text: str, db_name: str, top_k=8):
    """Retrieve the top-k most relevant text chunks for a query using embeddings."""
    try:
        # Generate embedding for query
        query_embedding = get_embeddings_from_gemini([query_text])[0]

        # Search in specified database
        similar_chunks = search_similar(db_name, query_embedding, top_k)

        # Combine chunks into context
        context = " ".join(similar_chunks)
        return context if context else "No relevant documents found"
    except Exception as e:
        logger.error(f"Error searching similar chunks: {e}")
        return "Error retrieving context"

def generate_content_from_model(prompt: str) -> str:
    """Generate content using Vertex AI Gemini model."""
    try:
        vertexai.init(project=current_app.config['AI_PROJECT'], location=current_app.config['AI_LOCATION'])
        model = GenerativeModel(current_app.config['GENERATIVE_AI_MODEL'])
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"AI service error: {e}")
        return f"AI service unavailable: {str(e)}"

def get_embeddings_from_gemini(chunks: list[str]):
    """Generate embeddings for text chunks."""
    vertexai.init(project=current_app.config['AI_PROJECT'], location=current_app.config['AI_LOCATION'])
    model = TextEmbeddingModel.from_pretrained("text-embedding-005")

    embeddings = []
    for chunk in chunks:
        result = model.get_embeddings([chunk])
        embeddings.append(result[0].values)
    return embeddings

def chunk_text_divider(text: str, max_chars: int = 2000, overlap: int = 200):
    """Split text into overlapping chunks."""
    import re
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + max_chars
        chunk = text[start:end]

        if end < text_length:
            period_index = text.rfind('.', start, end)
            if period_index != -1 and (end - period_index) < 300:
                end = period_index + 1
                chunk = text[start:end]

        chunks.append(chunk.strip())
        start = end - overlap

    return chunks