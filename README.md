# SRS → Tasks Generator

An ML pipeline that converts Software Requirements Specification (SRS) documents into actionable development tasks.

## Architecture

```
SRS PDF/Text → [PyMuPDF] → Raw Text → [SpaCy + Regex] → Structured JSON → [FLAN-T5-base + LoRA] → Tasks JSON
                              Stage 1: Parsing                              Stage 2: Generation
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Prepare Training Data

Training data lives in `data/samples/` as individual JSON files. Each file is a JSON object with:
- `input`: Structured SRS JSON (title, technologies, functional_requirements, etc.)
- `output`: Array of task objects (title, description, priority, type, related_requirement)

Add your own examples as new `.json` files in the same directory. **Minimum 20-30 examples recommended.**

### 3. Train the Model

```bash
python src/train.py --data data/samples --epochs 15
```

Options:
- `--data PATH` — Path to training data directory or JSONL file (default: `data/samples/`)
- `--output PATH` — Where to save the model (default: `models/srs-task-adapter/`)
- `--epochs N` — Training epochs (default: 15)
- `--batch-size N` — Batch size (default: 4, reduce to 2 if out of memory)
- `--lr FLOAT` — Learning rate (default: 3e-4)

### 4. Generate Tasks

**From a PDF:**
```bash
python src/generate.py --pdf path/to/srs.pdf
```

**From a text file:**
```bash
python src/generate.py --file path/to/srs.md
```

**From raw text:**
```bash
python src/generate.py --input "The system shall allow users to..."
```

**From pre-parsed JSON:**
```bash
python src/generate.py --json path/to/srs.json
```

Tasks are saved to `output/tasks.json` by default.

### 5. Run API Server

```bash
python src/server.py
```

Endpoints:
- `POST /parse-srs` — Upload SRS PDF → get structured JSON (Stage 1 only)
- `POST /generate-tasks` — Upload SRS PDF → get development tasks (full pipeline)
- `GET /health` — Health check

API runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Stage 1: SRS Parser (standalone)

Parse an SRS document into structured JSON without generating tasks:

```bash
python src/srs_to_json.py path/to/srs.pdf
python src/srs_to_json.py path/to/srs.md output.json
```

## Project Structure

```
SRS-Task Generator/
├── data/
│   └── samples/                  # Training data (individual JSON files)
│       ├── 01_ecommerce_login.json
│       ├── 02_ecommerce_registration.json
│       └── ...                   # Add your own examples here
├── uploads/                  # Uploaded SRS PDFs
├── output/                   # Generated task JSONs
├── src/
│   ├── pdf_parser.py         # PDF text extraction
│   ├── srs_to_json.py        # Stage 1: SRS → structured JSON
│   ├── prepare_data.py       # Training data preparation
│   ├── train.py              # Model fine-tuning
│   ├── generate.py           # Full pipeline inference
│   └── server.py             # FastAPI REST server
├── models/                   # Saved model weights
├── requirements.txt
└── README.md
```

## Task Output Format

Each generated task contains:

```json
{
  "title": "Build Login API Endpoint",
  "description": "Create POST /api/auth/login...",
  "priority": "high",
  "type": "backend",
  "related_requirement": "FR-01"
}
```

- **priority**: `high`, `medium`, `low`
- **type**: `backend`, `frontend`, `database`, `testing`
- **related_requirement**: Links back to the FR/NFR ID

## Requirements

- Python 3.11+
- 4-6 GB RAM for training
- NVIDIA GPU optional (speeds up training 10-20x)
# SRS-Task-Generator
# SRS-Task-Version-2
