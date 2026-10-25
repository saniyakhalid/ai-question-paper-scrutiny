import os
from typing import Optional

class DocumentService:
    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
        
        ext = os.path.splitext(file_path)[1].lower()
        text = ""

        try:
            if ext == ".pdf":
                import pymupdf
                doc = pymupdf.open(file_path)
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()
            elif ext == ".docx":
                import docx
                doc = docx.Document(file_path)
                for p in doc.paragraphs:
                    text += p.text + "\n"
            elif ext == ".pptx":
                try:
                    import pptx
                    prs = pptx.Presentation(file_path)
                    for slide in prs.slides:
                        for shape in slide.shapes:
                            if hasattr(shape, "text"):
                                text += shape.text + "\n"
                except Exception:
                    text = ""
            elif ext in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            else:
                text = ""
        except Exception:
            text = ""

        return text.strip()

document_service = DocumentService()
