"""
Supabase Storage Service for Image Files

Handles uploading/downloading image files to/from Supabase Storage buckets.
This is more efficient and cost-effective than storing binary data in the database.

Benefits:
- Cheaper storage costs (~$0.021/GB vs ~$0.125/GB for database)
- Faster delivery via CDN
- No base64 encoding overhead
- Automatic image optimization and resizing (if configured)
"""
from supabase import create_client, Client
from config import Config
from typing import Optional, BinaryIO
from utils.logger import get_logger
import uuid
from pathlib import Path

logger = get_logger(__name__)


class StorageService:
    """
    Service for managing file storage in Supabase Storage
    
    Images are stored in a public bucket and accessed via public URLs.
    Text files continue to be stored in the database.
    """
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.bucket_name = Config.SUPABASE_STORAGE_BUCKET
        self._initialized = False
        
        # Initialize client if credentials are available
        if Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
            try:
                self.supabase = create_client(
                    Config.SUPABASE_URL,
                    Config.SUPABASE_SERVICE_KEY
                )
                self._initialized = True
                logger.info(f"Supabase Storage initialized with bucket: {self.bucket_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase Storage: {e}")
                logger.warning("Images will be stored as base64 in database (fallback mode)")
    
    def is_available(self) -> bool:
        """Check if storage service is available"""
        return self._initialized and self.supabase is not None
    
    def _get_file_path(self, user_id: str, chat_id: str, filename: str) -> str:
        """
        Generate storage path for a file
        
        Format: {user_id}/{chat_id}/{filename}
        This ensures file isolation between users and chats
        """
        return f"{user_id}/{chat_id}/{filename}"
    
    def upload_image(
        self,
        user_id: str,
        chat_id: str,
        filename: str,
        file_data: bytes,
        content_type: str = "image/png"
    ) -> Optional[str]:
        """
        Upload an image to Supabase Storage
        
        Args:
            user_id: User ID
            chat_id: Chat ID
            filename: Original filename
            file_data: Raw image bytes
            content_type: MIME type (e.g., 'image/png', 'image/jpeg')
        
        Returns:
            Public URL of the uploaded image, or None if upload failed
        """
        if not self.is_available():
            logger.warning("Storage service not available, cannot upload image")
            return None
        
        try:
            # Generate storage path
            storage_path = self._get_file_path(user_id, chat_id, filename)
            
            # Upload file to storage bucket
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_data,
                file_options={
                    "content-type": content_type,
                    "cache-control": "3600",  # Cache for 1 hour
                    "upsert": "true"  # Overwrite if exists
                }
            )
            
            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            logger.info(f"Uploaded image {filename} to storage: {public_url}")
            return public_url
        
        except Exception as e:
            logger.error(f"Failed to upload image {filename} to storage: {e}", exc_info=True)
            return None
    
    def delete_image(self, user_id: str, chat_id: str, filename: str) -> bool:
        """
        Delete an image from Supabase Storage
        
        Args:
            user_id: User ID
            chat_id: Chat ID
            filename: Original filename
        
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("Storage service not available, cannot delete image")
            return False
        
        try:
            storage_path = self._get_file_path(user_id, chat_id, filename)
            
            self.supabase.storage.from_(self.bucket_name).remove([storage_path])
            
            logger.info(f"Deleted image from storage: {storage_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete image {filename} from storage: {e}", exc_info=True)
            return False
    
    def get_public_url(self, user_id: str, chat_id: str, filename: str) -> Optional[str]:
        """
        Get the public URL for an uploaded image
        
        Args:
            user_id: User ID
            chat_id: Chat ID
            filename: Original filename
        
        Returns:
            Public URL of the image, or None if not available
        """
        if not self.is_available():
            return None
        
        try:
            storage_path = self._get_file_path(user_id, chat_id, filename)
            return self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
        except Exception as e:
            logger.error(f"Failed to get public URL for {filename}: {e}")
            return None
    
    def ensure_bucket_exists(self) -> bool:
        """
        Ensure the storage bucket exists (create if it doesn't)
        
        This should be called during application startup.
        
        Returns:
            True if bucket exists or was created, False otherwise
        """
        if not self.is_available():
            logger.warning("Storage service not available, cannot check bucket")
            return False
        
        try:
            # Try to list buckets to see if ours exists
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if self.bucket_name in bucket_names:
                logger.info(f"Storage bucket '{self.bucket_name}' already exists")
                return True
            
            # Create bucket if it doesn't exist
            self.supabase.storage.create_bucket(
                self.bucket_name,
                options={
                    "public": True,  # Public bucket for easier access
                    "file_size_limit": 52428800,  # 50MB limit
                    "allowed_mime_types": [
                        "image/png",
                        "image/jpeg",
                        "image/jpg",
                        "image/gif",
                        "image/webp",
                        "image/svg+xml"
                    ]
                }
            )
            
            logger.info(f"Created storage bucket '{self.bucket_name}'")
            return True
        
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}", exc_info=True)
            return False


# Global storage service instance
storage_service = StorageService()

