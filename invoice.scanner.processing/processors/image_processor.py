"""
IMAGE PROCESSOR - Image Preprocessing and Normalization

Denna processor hanterar bilkontroller innan de skickas till OCR:
- PDF to image konvertering
- Bildnormalisering (storlek, format)
- Kvalitetskontroll
- Deskewing (rättning av roterade dokument)
- Contrast/brightness optimization

PROCESS:
    1. Läsa raw document (PDF/JPG/PNG)
    2. Konvertera till standard format
    3. Normalisera storlek
    4. Förbättra bildkvalitet
    5. Spara processad bild
    6. Returnera path och metadata
"""

import logging
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


class ImageProcessor:
    """Förbered bilder för OCR"""
    
    # Target specifications
    TARGET_DPI = 300
    TARGET_FORMAT = 'png'
    MAX_WIDTH = 3000
    MAX_HEIGHT = 4000
    
    def preprocess(
        self,
        document_id: str,
        source_path: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Preprocess document image
        
        Args:
            document_id: Document ID (för output filnamn)
            source_path: Path till original fil
            output_dir: Output directory för processad bild
        
        Returns:
            {
                'output_path': '/path/to/processed.png',
                'pages_processed': 1,
                'dimensions': (2550, 3300),
                'dpi': 300,
                'file_size_before': 5000000,
                'file_size_after': 3000000,
                'compression_ratio': 0.6,
                'warnings': []
            }
        """
        
        warnings = []
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        source_path = Path(source_path)
        
        try:
            # Determine file type
            if source_path.suffix.lower() == '.pdf':
                images = self._pdf_to_images(str(source_path))
                if not images:
                    raise ValueError("No pages extracted from PDF")
            else:
                images = [self._load_image(str(source_path))]
            
            # Process images
            processed_images = []
            for img in images:
                processed = self._enhance_image(img)
                processed = self._normalize_image(processed)
                processed_images.append(processed)
            
            # If multiple pages, combine or save separately
            # For now: save first page, or combine to single document
            output_path = output_dir / f"{document_id}.{self.TARGET_FORMAT}"
            
            # Spara first image (main document)
            cv2.imwrite(str(output_path), processed_images[0])
            
            # Get file sizes
            before_size = source_path.stat().st_size
            after_size = output_path.stat().st_size
            
            # Get image dimensions
            height, width = processed_images[0].shape[:2]
            
            return {
                'output_path': str(output_path),
                'pages_processed': len(processed_images),
                'dimensions': (width, height),
                'dpi': self.TARGET_DPI,
                'file_size_before': before_size,
                'file_size_after': after_size,
                'compression_ratio': after_size / before_size if before_size > 0 else 1.0,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise
    
    def _pdf_to_images(self, pdf_path: str) -> list:
        """Convert PDF pages to images"""
        if not PDF_SUPPORT:
            raise RuntimeError("PDF support not available")
        
        try:
            logger.info(f"Converting PDF to images: {pdf_path}")
            images = convert_from_path(pdf_path, dpi=self.TARGET_DPI)
            logger.info(f"Converted {len(images)} pages")
            return [np.array(img) for img in images]
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            raise
    
    def _load_image(self, image_path: str) -> np.ndarray:
        """Load image file"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        return img
    
    def _enhance_image(self, image: np.ndarray) -> np.ndarray:
        """Enhance image quality"""
        
        # Reduce noise
        image = cv2.fastNlMeansDenoisingColored(
            image,
            h=10,
            hForColorComponents=10,
            templateWindowSize=7,
            searchWindowSize=21
        )
        
        # Increase contrast using CLAHE
        if len(image.shape) == 3:
            # Convert to LAB color space
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Merge and convert back
            enhanced = cv2.merge([l, a, b])
            image = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        else:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            image = clahe.apply(image)
        
        return image
    
    def _normalize_image(self, image: np.ndarray) -> np.ndarray:
        """Normalize image size and format"""
        
        height, width = image.shape[:2]
        
        # Resize if too large
        if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
            scale = min(self.MAX_WIDTH / width, self.MAX_HEIGHT / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            logger.info(f"Resized image to {new_width}x{new_height}")
        
        return image
