"""
PDF Parser Module
=================
Extracts clean text content from SRS PDF documents using PyMuPDF (fitz).
Handles multi-page documents, cleans extracted text, and removes artifacts
like headers, footers, and page numbers.
"""

import re
import logging
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """
    Extract and clean text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Cleaned text content from all pages.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If the file is not a valid PDF or contains no text.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {pdf_path.suffix}")

    logger.info("Extracting text from: %s", pdf_path.name)

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        raise ValueError(f"Failed to open PDF: {e}") from e

    pages_text: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            cleaned = _clean_page_text(text, page_num)
            pages_text.append(cleaned)
            logger.debug("Page %d: extracted %d characters", page_num, len(cleaned))

    doc.close()

    if not pages_text:
        raise ValueError("PDF contains no extractable text content.")

    full_text = "\n\n".join(pages_text)
    full_text = _normalize_whitespace(full_text)

    logger.info(
        "Extraction complete: %d pages, %d characters total",
        len(pages_text),
        len(full_text),
    )

    return full_text


def _clean_page_text(text: str, page_num: int) -> str:
    """
    Clean text extracted from a single PDF page.

    Removes common artifacts like page numbers, headers/footers,
    and fixes broken line breaks from PDF column formatting.

    Args:
        text: Raw text from a single page.
        page_num: Page number (for context-aware cleaning).

    Returns:
        Cleaned page text.
    """
    lines = text.split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines (will be normalized later)
        if not stripped:
            cleaned_lines.append("")
            continue

        # Skip standalone page numbers (e.g., "1", "Page 1", "- 2 -")
        if _is_page_number(stripped, page_num):
            continue

        # Skip common header/footer patterns
        if _is_header_footer(stripped):
            continue

        cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)


def _is_page_number(line: str, page_num: int) -> bool:
    """Check if a line is just a page number."""
    # Standalone number
    if re.match(r"^\d{1,3}$", line):
        return True

    # "Page X" or "Page X of Y"
    if re.match(r"^page\s+\d+(\s+of\s+\d+)?$", line, re.IGNORECASE):
        return True

    # "- X -" format
    if re.match(r"^-\s*\d+\s*-$", line):
        return True

    return False


def _is_header_footer(line: str) -> bool:
    """Check if a line is a common header or footer artifact."""
    lower = line.lower()

    # Common footer patterns
    footer_patterns = [
        r"^confidential\b",
        r"^copyright\b",
        r"^all rights reserved",
        r"^\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}$",  # Date-only lines
    ]

    return any(re.match(pattern, lower) for pattern in footer_patterns)


def _normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in the full document text.

    - Collapses 3+ consecutive newlines into 2
    - Strips trailing whitespace from each line
    - Removes leading/trailing whitespace from the document
    """
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def extract_text_from_file(file_path: str | Path) -> str:
    """
    Extract text from either a PDF or plain text file.

    Args:
        file_path: Path to the file (PDF or .txt/.md).

    Returns:
        Text content of the file.
    """
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)

    # For text-based files, read directly
    if file_path.suffix.lower() in (".txt", ".md", ".text", ".markdown"):
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info("Reading text file: %s", file_path.name)
        return file_path.read_text(encoding="utf-8")

    raise ValueError(
        f"Unsupported file format: {file_path.suffix}. "
        "Supported formats: .pdf, .txt, .md"
    )


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <path_to_pdf>")
        sys.exit(1)

    text = extract_text_from_file(sys.argv[1])
    print(f"\n{'='*60}")
    print(f"Extracted {len(text)} characters:")
    print(f"{'='*60}\n")
    print(text[:2000])
    if len(text) > 2000:
        print(f"\n... ({len(text) - 2000} more characters)")
