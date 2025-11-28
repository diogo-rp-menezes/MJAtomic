from typing import Any, AsyncIterator, Iterator, List, Optional, Sequence, Tuple
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from sqlalchemy.orm import Session
from src.core.database import SessionLocal
from src.core.orm_models import DBCheckpoint
import pickle

class PostgresSaver(BaseCheckpointSaver):
    """
    A checkpoint saver that stores graph state in PostgreSQL using SQLAlchemy.
    """
    def __init__(self):
        # We don't keep a session open, we open one per operation
        pass

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")

        db = SessionLocal()
        try:
            query = db.query(DBCheckpoint).filter(DBCheckpoint.thread_id == thread_id)

            if checkpoint_id:
                query = query.filter(DBCheckpoint.checkpoint_id == checkpoint_id)
            else:
                # Get latest by created_at desc? Or just rely on logic?
                # LangGraph usually manages IDs. Let's sort by created_at just in case.
                # Actually, we should probably sort by checkpoint_id if it's lexicographically sortable or rely on metadata.
                # For now, assume DB order or implementation details.
                pass

            # We need the latest checkpoint
            # Since checkpoint_id is usually a UUID or hash, sorting might be tricky without a sequence number.
            # But created_at helps.
            ckpt_row = query.order_by(DBCheckpoint.created_at.desc()).first()

            if ckpt_row:
                return CheckpointTuple(
                    config=config,
                    checkpoint=pickle.loads(ckpt_row.checkpoint),
                    metadata=pickle.loads(ckpt_row.metadata_) if ckpt_row.metadata_ else {},
                    parent_config={"configurable": {"thread_id": thread_id, "checkpoint_id": ckpt_row.parent_checkpoint_id}} if ckpt_row.parent_checkpoint_id else None
                )
            return None
        finally:
            db.close()

    def list(self, config: Optional[RunnableConfig], *, filter: Optional[dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        # Basic implementation for listing checkpoints
        db = SessionLocal()
        try:
            query = db.query(DBCheckpoint)
            if config:
                thread_id = config["configurable"]["thread_id"]
                query = query.filter(DBCheckpoint.thread_id == thread_id)

            if limit:
                query = query.limit(limit)

            for row in query.all():
                yield CheckpointTuple(
                    config={"configurable": {"thread_id": row.thread_id, "checkpoint_id": row.checkpoint_id}},
                    checkpoint=pickle.loads(row.checkpoint),
                    metadata=pickle.loads(row.metadata_) if row.metadata_ else {},
                    parent_config={"configurable": {"thread_id": row.thread_id, "checkpoint_id": row.parent_checkpoint_id}} if row.parent_checkpoint_id else None
                )
        finally:
            db.close()

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict[str, Any]) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id") # Previous ID

        db = SessionLocal()
        try:
            db_ckpt = DBCheckpoint(
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                parent_checkpoint_id=parent_checkpoint_id,
                type="pickle",
                checkpoint=pickle.dumps(checkpoint),
                metadata_=pickle.dumps(metadata)
            )
            db.merge(db_ckpt) # Upsert
            db.commit()
        finally:
            db.close()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }
