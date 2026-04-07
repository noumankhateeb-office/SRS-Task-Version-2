# SRS -> Tasks Generator

An ML pipeline that converts Software Requirements Specification (SRS) documents into actionable development tasks.

## Architecture

```text
SRS PDF/Text -> [PyMuPDF] -> Raw Text -> [SpaCy + Regex] -> Structured JSON -> [Qwen2.5-7B-Instruct + LoRA] -> Tasks JSON
                              Stage 1: Parsing                              Stage 2: Generation
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Prepare Training Data

Training data lives in `data/training/` as individual JSON files. Each file is a JSON object with:
- `input`: Structured SRS JSON including title, description, technologies, actors, constraints, non-functional requirements, and functional requirements
- `output`: Tasks grouped by requirement ID

Holdout evaluation data lives separately in `data/evaluation/` and must not be used during training.

The parser and training pipeline support both:
- Markdown SRS files with headings like `### 3.1 Functional Requirements`
- Plain enterprise SRS files with headings like `3.1 Functional Requirements`

Use `samples/sample_srs_erp.md` as the reference enterprise template.

If you want to regenerate the bundled synthetic training samples with the richer schema:

```bash
python scripts/generate_samples.py
```

This regenerates both datasets:
- `data/training/` for training-only samples
- `data/evaluation/` for unseen holdout files prefixed with `eval_`

The evaluation set is intentionally generated from separate domains and is not mirrored from the UI sample SRS files in `samples/`.

### 3. Train the Model

```bash
python src/train.py --data data/training --eval-data data/evaluation --epochs 15
```

The training pipeline now uses a separate holdout evaluation dataset instead of splitting the training folder internally.

Options:
- `--data PATH` - Path to training data directory or JSONL file (default: `data/training/`)
- `--eval-data PATH` - Path to holdout evaluation directory or JSONL file (default: `data/evaluation/`)
- `--output PATH` - Where to save the model (default: `models/srs-task-adapter/`)
- `--epochs N` - Number of epochs (default: 15)
- `--batch-size N` - Batch size (default: 4, reduce to 2 if out of memory)
- `--lr FLOAT` - Learning rate (default: `3e-4`)

### 4. Generate Tasks

From a PDF:

```bash
python src/generate.py --pdf path/to/srs.pdf
```

From a text file:

```bash
python src/generate.py --file path/to/srs.md
```

From raw text:

```bash
python src/generate.py --input "The system shall allow users to..."
```

From pre-parsed JSON:

```bash
python src/generate.py --json path/to/srs.json
```

Tasks are saved to `output/tasks.json` by default.

### 5. Evaluate the Model

```bash
python src/evaluate.py --eval-data data/evaluation --adapter models/srs-task-adapter
```

This writes a timestamped report into `evaluation_results/` with:
- generated predictions for each evaluation file
- `summary.json` containing numeric metrics
- `report.md` with readable findings and recommendations

### 6. Run API Server

```bash
python src/server.py
```

Endpoints:
- `POST /parse-srs` - Upload SRS PDF/TXT/MD and get structured JSON
- `POST /generate-tasks` - Upload SRS PDF/TXT/MD and get generated tasks
- `POST /parse-srs-text` - Parse raw SRS text to JSON
- `POST /generate-tasks-text` - Generate tasks from raw SRS text
- `GET /health` - Health check

API runs at `http://localhost:8000`. Interactive docs are available at `http://localhost:8000/docs`.

## Stage 1: SRS Parser

Parse an SRS document into structured JSON without generating tasks:

```bash
python src/srs_to_json.py path/to/srs.pdf
python src/srs_to_json.py path/to/srs.md output.json
```

## Validation

Run the parser smoke tests:

```bash
python -m unittest discover -s tests -v
```

## Project Structure

```text
SRS-Task-Generator/
|-- data/
|   `-- training/                 # Training data (JSON files)
|   `-- evaluation/               # Holdout evaluation data (JSON files)
|-- uploads/                      # Uploaded SRS PDFs and text files
|-- output/                       # Generated task JSONs
|-- evaluation_results/           # Timestamped evaluation reports
|-- samples/                      # Example SRS inputs, including ERP template
|-- scripts/
|   `-- generate_samples.py       # Synthetic sample generation
|-- src/
|   |-- pdf_parser.py             # PDF/text extraction
|   |-- srs_to_json.py            # Stage 1: SRS -> structured JSON
|   |-- prepare_data.py           # Training data preparation
|   |-- train.py                  # Model fine-tuning
|   |-- evaluate.py               # Holdout evaluation and reporting
|   |-- generate.py               # Full pipeline inference
|   `-- server.py                 # FastAPI REST server
|-- tests/
|   `-- test_srs_parser.py        # Parser smoke tests
|-- models/                       # Saved model weights
|-- requirements.txt
`-- README.md
```

## Task Output Format

Each generated task contains:

```json
{
  "title": "Build Login API Endpoint",
  "description": "Create POST /api/auth/login...",
  "priority": "high",
  "type": "backend",
  "related_requirement": "FR-01",
  "acceptance_criteria": [
    "Validation, authorization, and error handling are covered",
    "The implementation is testable and documented for integration"
  ]
}
```

- `priority`: `high`, `medium`, `low`
- `type`: `backend`, `frontend`, `database`, `testing`
- `related_requirement`: Links the task back to the FR/NFR ID
- `acceptance_criteria`: Definition of done for the task itself

## Requirements

- Python 3.11+
- 4-6 GB RAM for training
- NVIDIA GPU optional for faster training
