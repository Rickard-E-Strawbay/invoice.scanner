"""
OCR PROCESSOR - Optical Character Recognition

Denna processor extraherar text från bilder och PDFs.
Det stöder två OCR-engines:
- Tesseract (CPU, snabbt, lagre accuracy)
- PaddleOCR (CPU/GPU, bättre accuracy, kan accelereras)

GPU ACCELERATION:
    PaddleOCR kan dra nytta av CUDA om GPU finns:
    - Enable via environment: PADDLE_DEVICE=gpu
    - Dockerfile.ml har CUDA base image förberedd
    - Performance: ~10x snabbare med GPU

PROCESS:
    1. Konvertera PDF till bilder (om nödvändigt)
    2. Förbättra bildkvalitet (contrast, brightness)
    3. Anropa OCR engine
    4. Post-process och normalisera text
    5. Returnera extraherad text + confidence scores

METRICS:
    CPU Tesseract:  ~2 sek per sida
    CPU PaddleOCR:  ~3 sek per sida
    GPU PaddleOCR:  ~0.3 sek per sida (10x snabbare!)
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

# Try to import PaddleOCR (GPU-capable)
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logger.warning("PaddleOCR not available, using Tesseract fallback")

# Try to import pdf2image for PDF handling
try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("pdf2image not available, PDF support disabled")


class OCRProcessor:
    """
    OCR processor med support för CPU/GPU acceleration.
    
    Engine valg:
    - 'tesseract': Snabbt, stabilt, lagre accuracy (CPU only)
    - 'paddleocr': Bättre accuracy, GPU-capable (rekommenderad)
    """
    
    def __init__(self, engine: str = 'paddleocr'):
        """
        Initialize OCR processor
        
        Args:
            engine: 'tesseract' eller 'paddleocr'
        """
        self.engine = engine
        self.paddle_ocr = None
        
        if engine == 'paddleocr' and PADDLE_AVAILABLE:
            # Initialize PaddleOCR
            # GPU detection happens automatically
            try:
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=True,  # Detect rotated documents
                    lang='en',  # Add 'sv' for Swedish when available
                    use_gpu=self._check_gpu_available()
                )
                logger.info(f"PaddleOCR initialized (GPU: {self._check_gpu_available()})")
            except Exception as e:
                logger.warning(f"Failed to initialize PaddleOCR: {e}, falling back to Tesseract")
                self.engine = 'tesseract'
        
        if engine == 'tesseract':
            # Check Tesseract installation
            try:
                pytesseract.get_tesseract_version()
                logger.info("Tesseract OCR initialized")
            except Exception as e:
                logger.error(f"Tesseract not installed: {e}")
    
    def _check_gpu_available(self) -> bool:
        """
        Check if GPU (CUDA) is available for PaddleOCR
        
        PaddleOCR uses PyTorch backend which can automatically detect GPU.
        """
        try:
            import torch
            available = torch.cuda.is_available()
            if available:
                logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
            return available
        except ImportError:
            logger.warning("PyTorch not available for GPU detection")
            return False
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from image or PDF
        
        Args:
            file_path: Path to image (.jpg, .png) or PDF
        
        Returns:
            {
                'text': 'Extracted text...',
                'pages': [{'text': '...', 'confidence': 0.95}, ...],
                'overall_confidence': 0.93,
                'language': 'en',
                'engine_used': 'paddleocr',
                'gpu_used': True,
                'processing_time': 2.5,
                'warnings': []
            }
        """
        
        import time
        start_time = time.time()
        warnings = []
        
        try:
            file_path = Path(file_path)
            
            # Determine file type
            if file_path.suffix.lower() in ['.pdf']:
                pages = self._handle_pdf(str(file_path))
            else:
                pages = self._handle_image(str(file_path))
            
            if not pages:
                return {
                    'error': 'No pages extracted',
                    'text': '',
                    'pages': [],
                    'overall_confidence': 0.0,
                    'warnings': warnings
                }
            
            # Extract text from all pages
            all_text = []
            page_results = []
            confidences = []
            
            for page_num, page_data in enumerate(pages, 1):
                if self.engine == 'paddleocr':
                    result = self._paddle_extract(page_data)
                else:
                    result = self._tesseract_extract(page_data)
                
                page_results.append({
                    'page': page_num,
                    'text': result['text'],
                    'confidence': result['confidence'],
                    'boxes': result.get('boxes', [])
                })
                
                all_text.append(result['text'])
                confidences.append(result['confidence'])
            
            processing_time = time.time() - start_time
            
            return {
                'text': '\n\n---PAGE BREAK---\n\n'.join(all_text),
                'pages': page_results,
                'overall_confidence': np.mean(confidences) if confidences else 0.0,
                'language': 'en',
                'engine_used': self.engine,
                'gpu_used': self._check_gpu_available() and self.engine == 'paddleocr',
                'processing_time': processing_time,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                'error': str(e),
                'text': '',
                'pages': [],
                'overall_confidence': 0.0,
                'engine_used': self.engine,
                'gpu_used': False,
                'warnings': [str(e)]
            }
    
    def _handle_pdf(self, pdf_path: str) -> List[np.ndarray]:
        """Convert PDF to images"""
        if not PDF_SUPPORT:
            raise RuntimeError("PDF support not available (install pdf2image)")
        
        try:
            logger.info(f"Converting PDF: {pdf_path}")
            images = convert_from_path(pdf_path, dpi=300)
            return [np.array(img) for img in images]
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            raise
    
    def _handle_image(self, image_path: str) -> List[np.ndarray]:
        """Load image"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image: {image_path}")
            return [img]
        except Exception as e:
            logger.error(f"Image loading failed: {e}")
            raise
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Improve image quality before OCR
        
        - Increase contrast
        - Reduce noise
        - Auto-rotate if necessary
        """
        
        # Convert to grayscale
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Increase contrast with CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        image = clahe.apply(image)
        
        # Reduce noise
        image = cv2.fastNlMeansDenoising(image, h=10)
        
        return image
    
    def _paddle_extract(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text using PaddleOCR"""
        
        if not self.paddle_ocr:
            raise RuntimeError("PaddleOCR not initialized")
        
        try:
            # Improve image
            image = self._preprocess_image(image)
            
            # OCR
            results = self.paddle_ocr.ocr(image, cls=True)
            
            if not results or not results[0]:
                return {'text': '', 'confidence': 0.0, 'boxes': []}
            
            # Parse results
            text_lines = []
            confidences = []
            boxes = []
            
            for line in results[0]:
                box = line[0]
                text = line[1][0]
                conf = line[1][1]
                
                text_lines.append(text)
                confidences.append(conf)
                boxes.append({
                    'text': text,
                    'confidence': conf,
                    'bbox': box
                })
            
            return {
                'text': '\n'.join(text_lines),
                'confidence': np.mean(confidences) if confidences else 0.0,
                'boxes': boxes
            }
            
        except Exception as e:
            logger.error(f"PaddleOCR extraction failed: {e}")
            raise
    
    def _tesseract_extract(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text using Tesseract"""
        
        try:
            # Improve image
            image = self._preprocess_image(image)
            
            # Tesseract configuration
            custom_config = r'--oem 3 --psm 6'
            
            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Get confidence (Tesseract ger per-word confidence)
            data = pytesseract.image_to_data(image, output_type='dict')
            
            if data['conf']:
                confidences = [int(c) for c in data['conf'] if c != '-1']
                confidence = np.mean(confidences) / 100.0 if confidences else 0.0
            else:
                confidence = 0.0
            
            return {
                'text': text,
                'confidence': confidence,
                'boxes': []
            }
            
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            raise
