import peewee as pw
from peewee import PostgresqlDatabase
from pgvector.peewee import VectorField
import numpy as np
from flask import current_app
import logging
import uuid

logger = logging.getLogger(__name__)

# Global database instances
db_instances = {}

def get_database(db_name):
    """Get or create a Peewee database instance for the given database name."""
    if db_name not in db_instances:
        db_config = current_app.config['VECTOR_DATABASES'].get(db_name)
        if not db_config:
            raise ValueError(f"Database '{db_name}' not configured")
        db_instances[db_name] = PostgresqlDatabase(
            db_config['NAME'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            host=db_config['HOST'],
            port=db_config['PORT']
        )
    return db_instances[db_name]

class BaseModel(pw.Model):
    class Meta:
        database = None  # Will be set dynamically

class DocumentEmbedding(BaseModel):
    id = pw.UUIDField(primary_key=True, default=uuid.uuid4)
    process_task_id = pw.UUIDField()
    chunk_index = pw.IntegerField()
    text_chunk = pw.TextField()
    embedding = VectorField(dimensions=768)
    data = pw.TextField(null=True)

    class Meta:
        table_name = 'document_embeddings'

def create_tables_for_db(db_name):
    """Create tables for the specified database."""
    db = get_database(db_name)
    DocumentEmbedding.bind(db)
    with db:
        db.execute_sql("CREATE EXTENSION IF NOT EXISTS vector;")
        db.create_tables([DocumentEmbedding], safe=True)
    
    # Create index outside transaction
    db.execute_sql("DROP INDEX IF EXISTS documentembedding_embedding;")
    db.execute_sql("CREATE INDEX IF NOT EXISTS documentembedding_embedding_idx ON document_embeddings USING hnsw (embedding vector_cosine_ops);")

def insert_embeddings(db_name, process_task_id, chunks, embeddings):
    """Insert embeddings into the specified database."""
    db = get_database(db_name)
    DocumentEmbedding.bind(db)
    
    logger.info(f"Database connection status: {not db.is_closed()}")
    logger.info(f"Preparing to insert {len(chunks)} chunks with {len(embeddings)} embeddings")

    try:
        with db.atomic():
            data = [
                {
                    'process_task_id': str(process_task_id),
                    'chunk_index': i,
                    'text_chunk': chunk,
                    'embedding': embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
                }
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
            ]
            result = DocumentEmbedding.insert_many(data).execute()
            logger.info(f"Insert operation result: {result}")
            logger.info(f"Successfully inserted {len(data)} records")
    except Exception as e:
        logger.error(f"Error during database insertion: {e}")
        raise

def search_similar(db_name, query_embedding, top_k=8):
    """Search for similar embeddings in the specified database."""
    db = get_database(db_name)
    DocumentEmbedding.bind(db)

    embedding_vector = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding

    query = (DocumentEmbedding
             .select(DocumentEmbedding.text_chunk)
             .order_by(DocumentEmbedding.embedding.cosine_distance(embedding_vector))
             .limit(top_k))

    results = [row.text_chunk for row in query]
    return results

def verify_insertion(db_name, process_task_id):
    """Verify if data was inserted for the given process_task_id."""
    db = get_database(db_name)
    DocumentEmbedding.bind(db)
    
    count = DocumentEmbedding.select().where(DocumentEmbedding.process_task_id == str(process_task_id)).count()
    logger.info(f"Found {count} records for process_task_id: {process_task_id}")
    return count

def close_all_connections():
    """Close all database connections."""
    for db in db_instances.values():
        if not db.is_closed():
            db.close()
    db_instances.clear()