"""
OCR pipeline using pytesseract + pdf2image + OpenCV preprocessing.
Handles: scanned PDFs, image files (PNG, JPG, TIFF).
"""
from __future__ import annotations

import logging
import numpy as np

from ingestion.models import PageOCRResult

logger = logging.getLogger(__name__)

# Tesseract configuration: LSTM engine + assume uniform block of text
TESSERACT_CONFIG = "--oem 3 --psm 6 -l eng"


def preprocess_image(img: np.ndarray) -> np.ndarray:
    """Apply image preprocessing to improve OCR accuracy.
    
    Steps: grayscale → binarise → denoise → deskew → upscale if needed.
    """
    import cv2

    # 1. Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # 2. Apply Otsu's thresholding (binarisation)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3. Denoise
    denoised = cv2.fastNlMeansDenoising(binary, h=10)

    # 4. Check resolution and upscale if needed (below 300 DPI equivalent)
    h, w = denoised.shape[:2]
    if h < 2000 or w < 1500:  # Rough check for low-res
        scale = max(2000 / h, 1.0)
        if scale > 1.0:
            denoised = cv2.resize(
                denoised, None, fx=scale, fy=scale,
                interpolation=cv2.INTER_CUBIC
            )
            logger.info(f"Upscaled image by {scale:.1f}x for better OCR")

    # 5. Try deskew (catch all exceptions - deskew can fail on blank/noise pages)
    try:
        from deskew import determine_skew
        from scipy.ndimage import rotate

        angle = determine_skew(denoised)
        if angle is not None and abs(angle) > 0.5:
            denoised = rotate(denoised, angle, reshape=False,
                            order=0, mode='constant', cval=255).astype(np.uint8)
            logger.info(f"Deskewed image by {angle:.2f} degrees")
    except Exception as e:
        logger.debug(f"Deskew skipped: {e}")

    return denoised


def ocr_page(image: np.ndarray) -> PageOCRResult:
    """Run OCR on a single preprocessed image and return structured result."""
    import pytesseract
    from pytesseract import Output
    from config import TESSERACT_CMD, MIN_OCR_CONFIDENCE

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

    try:
        data = pytesseract.image_to_data(
            image, config=TESSERACT_CONFIG, output_type=Output.DICT
        )

        # Extract confidence values, filter -1 (non-text regions)
        confidences = [int(c) for c in data['conf'] if int(c) != -1]
        confidence = float(np.mean(confidences)) if confidences else 0.0

        # Extract text tokens
        words = [t.strip() for t in data['text'] if t.strip()]
        text = " ".join(words)

        if not text:
            logger.warning("OCR produced no text from page")
            text = "[OCR FAILED - NO TEXT EXTRACTED]"
            confidence = 0.0

        word_count = len(words)
        is_low_confidence = confidence < MIN_OCR_CONFIDENCE

        return PageOCRResult(
            page_number=0,  # Will be set by caller
            text=text,
            confidence=round(confidence, 2),
            word_count=word_count,
            is_low_confidence=is_low_confidence
        )

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return PageOCRResult(
            page_number=0,
            text="[OCR FAILED - NO TEXT EXTRACTED]",
            confidence=0.0,
            word_count=0,
            is_low_confidence=True
        )


def ocr_pdf(pdf_path: str) -> list[PageOCRResult]:
    """Process a scanned PDF through OCR, returning per-page results."""
    from pdf2image import convert_from_path

    try:
        images = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        raise RuntimeError(
            f"pdf2image failed — is Poppler installed? Error: {e}\n"
            "Install: choco install poppler  (Windows)\n"
            "         brew install poppler   (macOS)\n"
            "         apt-get install poppler-utils (Linux)"
        )

    results = []
    for i, pil_image in enumerate(images):
        logger.info(f"OCR processing page {i + 1}/{len(images)}")
        img = np.array(pil_image)
        preprocessed = preprocess_image(img)
        result = ocr_page(preprocessed)
        result.page_number = i + 1
        results.append(result)

    return results


def ocr_image(image_path: str) -> list[PageOCRResult]:
    """Process a single image file through OCR."""
    import cv2

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image file: {image_path}")

    preprocessed = preprocess_image(img)
    result = ocr_page(preprocessed)
    result.page_number = 1
    return [result]
