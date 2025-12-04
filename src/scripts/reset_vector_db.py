import os
import sys
from sqlalchemy import create_engine, text

def reset_vector_db():
    # Use the internal container URL structure or environment variable
    db_url = os.getenv("POSTGRES_URL")
    if not db_url:
        # Fallback for default dev environment
        db_url = "postgresql+psycopg://devagent:atomicpass@db:5432/devagent_db"

    # Ensure we are using the correct driver for sync connection if needed
    if "postgresql+psycopg2://" in db_url:
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+psycopg://")

    collection_name = os.getenv("PGVECTOR_COLLECTION_NAME", "code_collection")

    print(f"Connecting to database to drop table: {collection_name}")

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Drop the table and its associated index/types if they exist
            print(f"Dropping table {collection_name}...")
            conn.execute(text(f"DROP TABLE IF EXISTS {collection_name} CASCADE;"))

            # Also drop the embeddings table if it was created by older langchain versions
            # Some versions used 'langchain_pg_embedding' or similar
            conn.execute(text("DROP TABLE IF EXISTS langchain_pg_embedding CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS langchain_pg_collection CASCADE;"))

            conn.commit()
            print("Tables dropped successfully.")

    except Exception as e:
        print(f"Error resetting database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_vector_db()
