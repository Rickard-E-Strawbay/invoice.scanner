"""
Processors Package

Handles document processing logic for each stage of the pipeline.

PROCESSORS:
    image_processor: Image preprocessing and normalization
    ocr_processor: Optical character recognition (Tesseract, PaddleOCR)
    llm_processor: Multi-provider LLM integration (OpenAI, Gemini, Anthropic)
    data_extractor: Invoice data extraction and normalization
    validator: Quality validation and scoring

USAGE:
    from processors.image_processor import ImageProcessor
    from processors.ocr_processor import OCRProcessor

    img_proc = ImageProcessor()
    result = img_proc.preprocess(document_id, source_path, output_dir)
"""

__all__ = [
    'image_processor',
    'ocr_processor',
    'llm_processor',
    'data_extractor',
    'validator',
]
