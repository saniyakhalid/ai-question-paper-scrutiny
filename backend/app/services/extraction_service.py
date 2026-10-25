import os
import re
import logging
import tempfile

try:
    import pymupdf as fitz
except ImportError:
    import fitz

import docx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ScannedDocumentException(ValueError):
    """Raised when an uploaded document contains no readable text layer (e.g. scanned image)."""

    pass


class DocumentExtractionService:
    @staticmethod
    def resolve_path(file_path: str) -> str:
        if os.path.exists(file_path):
            return file_path
        # Try relative to backend
        candidate = os.path.join("backend", file_path)
        if os.path.exists(candidate):
            return candidate
        # Try relative to settings.UPLOAD_DIR
        base = os.path.basename(file_path)
        candidate2 = os.path.join(settings.UPLOAD_DIR, base)
        if os.path.exists(candidate2):
            return candidate2
        # Try inside backend/uploads
        candidate3 = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", base)
        if os.path.exists(candidate3):
            return os.path.abspath(candidate3)
        return file_path

    @staticmethod
    def extract_text(file_path: str, file_type: str = "") -> str:
        resolved = DocumentExtractionService.resolve_path(file_path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = os.path.splitext(resolved)[1].lower()

        if file_ext == ".pdf" or file_type == "application/pdf" or file_type == "pdf":
            return DocumentExtractionService._extract_from_pdf(resolved)
        elif file_ext == ".docx" or "wordprocessingml" in file_type or file_type in [
            "docx",
            "doc",
        ]:
            return DocumentExtractionService._extract_from_docx(resolved)
        elif file_ext == ".txt" or file_type == "txt":
            with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if not content.strip():
                    raise ScannedDocumentException("The uploaded text document is completely empty.")
                return content
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    @staticmethod
    def _page_text(page) -> str:
        # Use natural reading order from PyMuPDF
        txt = (page.get_text("text") or "").strip()
        if txt:
            return txt
        # Fallback to sorted blocks if default text was empty
        try:
            blocks = page.get_text("blocks") or []
            blocks = sorted(blocks, key=lambda b: (round(b[1], 1), round(b[0], 1)))
            parts = [b[4].strip() for b in blocks if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()]
            if parts:
                return "\n".join(parts)
        except Exception:
            pass
        return ""

    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        text_content = []
        doc = fitz.open(file_path)
        total_pages = len(doc)

        for page in doc:
            page_text = DocumentExtractionService._page_text(page)
            if page_text:
                text_content.append(page_text)

        doc.close()

        combined_text = "\n\n".join(text_content).strip()
        alphanumeric_chars = re.sub(r"[^a-zA-Z0-9]", "", combined_text)

        if len(alphanumeric_chars) < 30 and total_pages > 0:
            ocr_text = DocumentExtractionService._attempt_ocr(file_path)
            if ocr_text and len(re.sub(r"[^a-zA-Z0-9]", "", ocr_text)) >= 30:
                return ocr_text

            raise ScannedDocumentException(
                "Scanned/image-based PDF detected. OCR is required for reliable extraction. "
                "Please upload a text-searchable PDF or Word (.docx) document, "
                "or install Tesseract OCR on this server."
            )

        return combined_text

    @staticmethod
    def _attempt_ocr(file_path: str) -> str:
        """Try RapidOCR (standalone ONNX), then PyMuPDF OCR, then pytesseract."""
        # 1) RapidOCR (standalone ONNX, completely offline, zero external binaries needed)
        try:
            from rapidocr_onnxruntime import RapidOCR

            engine = RapidOCR()
            doc = fitz.open(file_path)
            ocr_pages = []
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                result, _ = engine(img_bytes)
                if result:
                    page_lines = [r[1] for r in result if r and len(r) > 1 and r[1].strip()]
                    if page_lines:
                        ocr_pages.append("\n".join(page_lines))
            doc.close()
            joined = "\n\n".join(ocr_pages).strip()
            if len(re.sub(r"[^a-zA-Z0-9]", "", joined)) >= 30:
                return joined
        except Exception as e:
            logger.debug(f"RapidOCR unavailable: {e}")

        # 2) Built-in PyMuPDF OCR (needs Tesseract)
        try:
            doc = fitz.open(file_path)
            ocr_pages = []
            for page in doc:
                try:
                    tp = page.get_textpage_ocr(language="eng", dpi=300)
                    text = page.get_text("text", textpage=tp)
                    if text and text.strip():
                        ocr_pages.append(text.strip())
                except Exception as e:
                    logger.debug(f"page OCR failed: {e}")
                    break
            doc.close()
            joined = "\n\n".join(ocr_pages)
            if len(re.sub(r"[^a-zA-Z0-9]", "", joined)) >= 30:
                return joined
        except Exception as e:
            logger.debug(f"PyMuPDF OCR unavailable: {e}")

        # 3) Render pages and run pytesseract
        try:
            import pytesseract
            from PIL import Image

            doc = fitz.open(file_path)
            ocr_pages = []
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                    pix.save(tmp_path)
                try:
                    img = Image.open(tmp_path)
                    text = pytesseract.image_to_string(img) or ""
                    if text.strip():
                        ocr_pages.append(text.strip())
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            doc.close()
            return "\n\n".join(ocr_pages)
        except Exception as e:
            logger.debug(f"pytesseract OCR unavailable: {e}")
            return ""

    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        try:
            doc = docx.Document(file_path)
        except Exception as e:
            raise ValueError(f"Malformed or unreadable DOCX file: {e}")

        text_content = []

        for para in doc.paragraphs:
            if para.text and para.text.strip():
                text_content.append(para.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_cells = [
                    cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()
                ]
                deduped = []
                for c in row_cells:
                    if not deduped or deduped[-1] != c:
                        deduped.append(c)
                if deduped:
                    text_content.append(" | ".join(deduped))

        combined = "\n".join(text_content).strip()
        if not combined:
            raise ScannedDocumentException("No readable text found in the uploaded DOCX document.")
        return combined
