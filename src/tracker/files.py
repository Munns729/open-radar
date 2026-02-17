import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
import aiofiles
from pypdf import PdfReader

from src.core.config import settings

logger = logging.getLogger(__name__)

UPLOAD_DIR = settings.data_dir / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class FileManager:
    """Handles file uploads and text extraction for the Tracker Agent."""
    
    @staticmethod
    async def save_file(company_id: int, file: UploadFile) -> tuple[str, str]:
        """
        Save uploaded file to disk.
        Returns (storage_path, filename).
        """
        company_dir = UPLOAD_DIR / str(company_id)
        company_dir.mkdir(exist_ok=True)
        
        # Sanitize filename (basic)
        filename = Path(file.filename).name
        storage_path = company_dir / filename
        
        async with aiofiles.open(storage_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            
        return str(storage_path), filename

    @staticmethod
    def extract_text(file_path: str, file_type: str) -> Optional[str]:
        """
        Extract text content from file based on type.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None
            
        try:
            if file_type.lower() == 'pdf':
                return FileManager._read_pdf(path)
            elif file_type.lower() in ['txt', 'md', 'csv']:
                return path.read_text(encoding='utf-8', errors='ignore')
            else:
                logger.warning(f"Unsupported file type for text extraction: {file_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return None

    @staticmethod
    def _read_pdf(path: Path) -> str:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
