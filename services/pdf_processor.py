import os
import tempfile
from typing import List
from pdf2image import convert_from_path
from PIL import Image
import asyncio
from pathlib import Path

from config import config

class PDFProcessor:
    """Service for processing PDF files and extracting pages as images"""
    
    def __init__(self):
        self.temp_dir = config.TEMP_DIR
        
    async def extract_pages(self, pdf_path: str) -> List[str]:
        """
        Extract all pages from PDF and save as images
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of paths to extracted page images
        """
        try:
            # Create unique directory for this PDF's pages
            pdf_name = Path(pdf_path).stem
            pages_dir = os.path.join(self.temp_dir, pdf_name)
            os.makedirs(pages_dir, exist_ok=True)
            
            # Convert PDF pages to images
            pages = await asyncio.get_event_loop().run_in_executor(
                None, self._convert_pdf_to_images, pdf_path, pages_dir
            )
            
            return pages
            
        except Exception as e:
            raise Exception(f"Error extracting pages from PDF: {str(e)}")
    
    def _convert_pdf_to_images(self, pdf_path: str, output_dir: str) -> List[str]:
        """Convert PDF to images synchronously"""
        try:
            # Convert PDF to images
            images = convert_from_path(
                pdf_path,
                dpi=300,  # High DPI for better quality
                fmt='PNG'
            )
            
            page_paths = []
            
            for i, image in enumerate(images):
                # Save each page as PNG
                page_path = os.path.join(output_dir, f"page_{i+1:03d}.png")
                
                # Optimize image size while maintaining quality
                image = self._optimize_image(image)
                image.save(page_path, "PNG", optimize=True)
                
                page_paths.append(page_path)
            
            return page_paths
            
        except Exception as e:
            raise Exception(f"Error converting PDF to images: {str(e)}")
    
    def _optimize_image(self, image: Image.Image, max_width: int = 1200) -> Image.Image:
        """Optimize image size for web display while maintaining quality"""
        # Get current dimensions
        width, height = image.size
        
        # Resize if too large
        if width > max_width:
            ratio = max_width / width
            new_height = int(height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
    
    async def get_page_info(self, pdf_path: str) -> dict:
        """Get basic information about the PDF"""
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(pdf_path)
            
            return {
                "total_pages": len(reader.pages),
                "title": reader.metadata.title if reader.metadata and reader.metadata.title else None,
                "author": reader.metadata.author if reader.metadata and reader.metadata.author else None,
                "file_size": os.path.getsize(pdf_path)
            }
            
        except Exception as e:
            raise Exception(f"Error reading PDF info: {str(e)}")
    
    def cleanup_pages(self, page_paths: List[str]):
        """Clean up extracted page files"""
        for page_path in page_paths:
            try:
                if os.path.exists(page_path):
                    os.remove(page_path)
            except Exception as e:
                print(f"Error cleaning up page {page_path}: {e}")
        
        # Try to remove the directory if empty
        try:
            if page_paths:
                pages_dir = os.path.dirname(page_paths[0])
                if os.path.exists(pages_dir) and not os.listdir(pages_dir):
                    os.rmdir(pages_dir)
        except Exception as e:
            print(f"Error cleaning up pages directory: {e}") 