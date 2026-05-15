"""File type handlers for document processing.

This package was split out from a single ``file_handlers.py`` module.  The
public surface remains identical — every name that used to live at module
top level is re-exported here, so existing
``from app.utils.file_handlers import X`` imports keep working.
"""

from app.utils.file_handlers.base import ExtractResult, FileHandler
from app.utils.file_handlers.docx import DocxFileHandler
from app.utils.file_handlers.factory import FileHandlerFactory, process_file
from app.utils.file_handlers.fb2 import FB2FileHandler
from app.utils.file_handlers.markdown import MarkdownFileHandler
from app.utils.file_handlers.pdf import PDFExtractionProfile, PDFFileHandler
from app.utils.file_handlers.text import TextFileHandler

__all__ = [
    "ExtractResult",
    "FileHandler",
    "TextFileHandler",
    "MarkdownFileHandler",
    "FB2FileHandler",
    "DocxFileHandler",
    "PDFExtractionProfile",
    "PDFFileHandler",
    "FileHandlerFactory",
    "process_file",
]
