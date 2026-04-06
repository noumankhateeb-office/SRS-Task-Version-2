"""
FastAPI Server
===============
REST API server for the SRS → Tasks pipeline.

Endpoints:
    POST /parse-srs        — Upload PDF → returns structured SRS JSON (Stage 1)
    POST /generate-tasks   — Upload PDF → returns generated tasks (Full pipeline)
    GET  /health           — Health check

Usage:
    python src/server.py
    # or
    uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
"""

import json
import logging
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from pdf_parser import extract_text_from_file
from srs_to_json import parse_srs
from generate import TaskGenerator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
STATIC_DIR = PROJECT_ROOT / "static"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SRS Task Generator API",
    description="Convert SRS documents into development tasks using ML.",
    version="1.0.0",
)

# CORS — allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files (HTML/CSS/JS)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global task generator instance (loaded once at startup)
_generator: TaskGenerator | None = None


def get_generator() -> TaskGenerator:
    """Get or initialize the TaskGenerator singleton."""
    global _generator
    if _generator is None:
        logger.info("Initializing TaskGenerator...")
        _generator = TaskGenerator()
        _generator.load_model()
        logger.info("TaskGenerator ready.")
    return _generator


# ---------------------------------------------------------------------------
# Startup Event
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """Load the model at server startup."""
    logger.info("Server starting up — loading model...")
    try:
        get_generator()
    except Exception as e:
        logger.warning(
            "Model not loaded at startup (adapter may not exist yet): %s", e
        )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

async def _save_upload(file: UploadFile) -> Path:
    """
    Save an uploaded file to the uploads directory.

    Args:
        file: Uploaded file from the request.

    Returns:
        Path to the saved file.

    Raises:
        HTTPException: If the file type is not supported.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {extension}. "
                f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            ),
        )

    # Save to uploads directory
    save_path = UPLOADS_DIR / file.filename
    content = await file.read()

    save_path.write_bytes(content)
    logger.info("Saved uploaded file: %s (%d bytes)", save_path.name, len(content))

    return save_path


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML page."""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        from fastapi.responses import HTMLResponse
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return {"message": "SRS Task Generator API. Docs at /docs"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": _generator is not None and _generator.model is not None,
    }


@app.post("/parse-srs")
async def parse_srs_endpoint(file: UploadFile = File(...)):
    """
    Parse an SRS document into structured JSON (Stage 1 only).

    Upload a PDF, TXT, or MD file containing an SRS document.
    Returns the structured JSON representation.

    Args:
        file: SRS document file (PDF, TXT, or MD).

    Returns:
        Structured SRS JSON.
    """
    try:
        file_path = await _save_upload(file)

        # Extract text
        raw_text = extract_text_from_file(file_path)
        logger.info("Extracted %d characters from %s", len(raw_text), file.filename)

        # Parse to JSON
        srs_doc = parse_srs(raw_text)
        result = srs_doc.to_dict()

        return JSONResponse(
            content={
                "status": "success",
                "filename": file.filename,
                "srs": result,
            }
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error parsing SRS document")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/generate-tasks")
async def generate_tasks_endpoint(file: UploadFile = File(...)):
    """
    Generate development tasks from an SRS document (Full pipeline).

    Upload a PDF, TXT, or MD file containing an SRS document.
    Returns the generated development tasks.

    Args:
        file: SRS document file (PDF, TXT, or MD).

    Returns:
        Generated development tasks as JSON.
    """
    try:
        generator = get_generator()
        file_path = await _save_upload(file)

        # Full pipeline
        tasks = generator.generate_from_pdf(file_path)

        return JSONResponse(
            content={
                "status": "success",
                "filename": file.filename,
                "task_count": len(tasks),
                "tasks": tasks,
            }
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error generating tasks")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/parse-srs-text")
async def parse_srs_text_endpoint(body: dict):
    """
    Parse plain SRS text into structured JSON (Stage 1 only).

    Args:
        body: JSON body with 'text' field containing raw SRS text.

    Returns:
        Structured SRS JSON.
    """
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")

    try:
        srs_doc = parse_srs(text)
        result = srs_doc.to_dict()
        return JSONResponse(content={"status": "success", "srs": result})

    except Exception as e:
        logger.exception("Error parsing SRS text")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/generate-tasks-text")
async def generate_tasks_text_endpoint(body: dict):
    """
    Generate tasks from plain SRS text (Full pipeline).

    Args:
        body: JSON body with 'text' field containing raw SRS text.

    Returns:
        Generated development tasks as JSON.
    """
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")

    try:
        generator = get_generator()
        tasks = generator.generate_from_text(text)
        return JSONResponse(
            content={
                "status": "success",
                "task_count": len(tasks),
                "tasks": tasks,
            }
        )

    except Exception as e:
        logger.exception("Error generating tasks from text")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ---------------------------------------------------------------------------
# Run Server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Starting SRS Task Generator API server...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
