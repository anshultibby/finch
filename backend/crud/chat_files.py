"""
CRUD operations for chat files (database-backed)
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.chat_models import ChatFile
import logging

logger = logging.getLogger(__name__)


def delete_chat_file(
    db: Session,
    chat_id: str,
    filename: str
) -> bool:
    """Delete a file from a chat"""
    file_obj = db.query(ChatFile).filter(
        and_(
            ChatFile.chat_id == chat_id,
            ChatFile.filename == filename
        )
    ).first()
    
    if file_obj:
        db.delete(file_obj)
        db.commit()
        logger.info(f"Deleted chat file: {filename} from chat {chat_id}")
        return True
    
    return False


