"""
SRS to JSON Parser (Stage 1)
=============================
Parses raw SRS text into a structured JSON format using SpaCy NLP
and regex pattern matching.

The parser is intentionally tolerant of two common input styles:
1. Markdown-heavy SRS files with headings like `### 3.1 Functional Requirements`
2. Plain-text SRS files with headings like `3.1 Functional Requirements`

It also supports requirement blocks that:
- use explicit `Requirements` / `Acceptance Criteria` labels
- only contain bullet points under `FR-01: Title`
- use plain colon-separated definition and environment lines
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import Any

import spacy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_TECHNOLOGIES = {
    "next.js", "react", "angular", "vue.js", "vue", "svelte", "nuxt.js",
    "node.js", "express", "fastapi", "django", "flask", "spring boot",
    "spring", "nestjs", "laravel", "ruby on rails",
    "prisma", "sequelize", "typeorm", "mongoose", "sqlalchemy",
    "mongodb", "postgresql", "mysql", "sqlite", "redis", "firebase",
    "docker", "kubernetes", "aws", "gcp", "azure", "google cloud",
    "typescript", "javascript", "python", "java", "go", "rust", "c#",
    "graphql", "rest", "restful", "grpc", "websocket",
    "tailwindcss", "tailwind", "bootstrap", "material ui", "chakra ui",
    "jest", "cypress", "playwright", "vitest",
    "git", "github", "gitlab", "bitbucket",
    "stripe", "paypal", "twilio", "sendgrid",
    "jwt", "oauth", "oauth2", "auth0", "sso", "bcrypt",
    "aws", "azure", "google cloud", "aws lambda",
}

SECTION_HEADING_PATTERN = re.compile(
    r"^\s*(?:#{1,6}\s*)?(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$",
    re.MULTILINE,
)

REQUIREMENT_HEADING_PATTERN = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*{0,2})\s*((?:FR|NFR)[-\s]?\d+)\s*:\s*(.+?)\s*(?:\*{0,2})\s*$",
    re.MULTILINE | re.IGNORECASE,
)

BULLET_PATTERN = re.compile(r"^\s*[-*•]\s+(.+?)\s*$", re.MULTILINE)
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
KEY_VALUE_LINE_PATTERN = re.compile(r"^\s*[-*•]?\s*(.+?)\s*:\s+(.+?)\s*$")
LABEL_ONLY_PATTERN = re.compile(
    r"^\s*[-*•]?\s*(?:\*{0,2})?(Requirements|Acceptance Criteria)(?:\*{0,2})?\s*:?\s*$",
    re.IGNORECASE,
)
LABEL_WITH_VALUE_PATTERN = re.compile(
    r"^\s*[-*•]?\s*(?:\*{0,2})?(Requirements|Acceptance Criteria)(?:\*{0,2})?\s*:?\s*(.+?)\s*$",
    re.IGNORECASE,
)

KNOWN_ACTOR_TERMS = {
    "admin", "administrator", "manager", "employee", "user", "customer",
    "doctor", "patient", "supplier", "vendor", "hr", "hrm", "finance",
    "sales", "support", "system", "accounts payable personnel",
}

EXCLUDED_DEFINITION_TERMS = {"api", "ui", "ux", "url", "http", "https"}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FunctionalRequirement:
    """Represents a single functional requirement with its details."""

    title: str = ""
    requirements: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass
class NonFunctionalRequirement:
    """Represents a single non-functional requirement."""

    title: str = ""
    requirements: list[str] = field(default_factory=list)


@dataclass
class SRSDocument:
    """Structured representation of a parsed SRS document."""

    title: str = ""
    description: str = ""
    technologies: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)
    user_classes: dict[str, str] = field(default_factory=dict)
    definitions: dict[str, str] = field(default_factory=dict)
    modules: list[str] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    operating_environment: dict[str, str] = field(default_factory=dict)
    external_interfaces: dict[str, list[str]] = field(default_factory=dict)
    functional_requirements: dict[str, FunctionalRequirement] = field(
        default_factory=dict
    )
    non_functional_requirements: dict[str, NonFunctionalRequirement] = field(
        default_factory=dict
    )
    system_attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dictionary suitable for JSON serialization."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=2)
def _load_spacy_model(spacy_model: str):
    """Cache SpaCy model loading so API requests do not reload the model."""
    logger.info("Loading SpaCy model: %s", spacy_model)
    return spacy.load(spacy_model)


def _normalize_whitespace_lines(text: str) -> str:
    """Normalize line endings and trim noisy spacing."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = text.replace("\ufeff", "")
    text = text.replace("•", "-")
    lines = [line.rstrip() for line in text.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _normalize_key(text: str) -> str:
    """Convert section titles into stable dictionary keys."""
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


def _clean_inline_markup(text: str) -> str:
    """Strip lightweight markdown formatting without removing text content."""
    cleaned = text.strip()
    cleaned = cleaned.strip("*")
    cleaned = re.sub(r"^[-*]\s+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" :")


def _clean_requirement_sentence(text: str) -> str:
    """Normalize a requirement bullet or sentence."""
    cleaned = _clean_inline_markup(text)
    cleaned = cleaned.rstrip(".")
    return cleaned


def _split_sentences(text: str) -> list[str]:
    """Split plain text blocks into sentence-like items."""
    pieces = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9])|\n+", text.strip())
    results: list[str] = []
    for piece in pieces:
        cleaned = _clean_requirement_sentence(piece)
        if cleaned and len(cleaned) > 3:
            results.append(cleaned)
    return results


# ---------------------------------------------------------------------------
# Parser Class
# ---------------------------------------------------------------------------

class SRSParser:
    """
    Parses raw SRS text into a structured SRSDocument.

    Uses SpaCy for sentence detection and regex/line parsing for
    section extraction. The parser is schema-oriented rather than
    markdown-only so it can tolerate enterprise SRS variants.
    """

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        """Initialize the parser."""
        try:
            self.nlp = _load_spacy_model(spacy_model)
        except OSError:
            logger.error(
                "SpaCy model '%s' not found. "
                "Install it with: python -m spacy download %s",
                spacy_model,
                spacy_model,
            )
            raise

    def parse(self, text: str) -> SRSDocument:
        """
        Parse raw SRS text into a structured SRSDocument.

        Args:
            text: Raw text content of the SRS document.

        Returns:
            Structured SRSDocument with all extracted fields.
        """
        normalized_text = _normalize_whitespace_lines(text)
        logger.info("Starting SRS parsing (%d characters)", len(normalized_text))

        doc = SRSDocument()
        sections = self._split_into_sections(normalized_text)

        self._extract_title(normalized_text, doc)
        self._extract_purpose(sections, doc)
        self._extract_scope(sections, doc)
        self._extract_definitions_and_actors(sections, doc)
        self._extract_product_features(sections, doc)
        self._extract_user_classes(sections, doc)
        self._extract_operating_environment(sections, doc)
        self._extract_constraints(sections, doc)
        self._extract_requirement_sections(normalized_text, doc)
        self._extract_external_interfaces(sections, doc)
        self._extract_system_attributes(sections, doc)
        self._extract_out_of_scope(sections, doc)
        self._detect_technologies(normalized_text, doc)

        doc.actors = list(dict.fromkeys(doc.actors))
        doc.technologies = list(dict.fromkeys(doc.technologies))
        doc.modules = list(dict.fromkeys(doc.modules))
        doc.scope = list(dict.fromkeys(doc.scope))
        doc.constraints = list(dict.fromkeys(doc.constraints))
        doc.out_of_scope = list(dict.fromkeys(doc.out_of_scope))

        logger.info(
            "Parsing complete: %d FRs, %d NFRs, %d actors, %d technologies",
            len(doc.functional_requirements),
            len(doc.non_functional_requirements),
            len(doc.actors),
            len(doc.technologies),
        )
        return doc

    # -------------------------------------------------------------------
    # Section Splitting
    # -------------------------------------------------------------------

    def _split_into_sections(self, text: str) -> dict[str, dict[str, str]]:
        """
        Split the document into numbered sections.

        Returns:
            Dict like {"1.1": {"title": "Purpose", "content": "..."}}.
        """
        sections: dict[str, dict[str, str]] = {}
        matches = list(SECTION_HEADING_PATTERN.finditer(text))

        for index, match in enumerate(matches):
            section_num = match.group(1)
            title = _clean_inline_markup(match.group(2))

            # Skip lines that are really FR/NFR headers disguised as section text.
            if section_num.upper().startswith(("FR", "NFR")):
                continue

            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            sections[section_num] = {"title": title, "content": content}

        return sections

    def _find_section_content(
        self,
        sections: dict[str, dict[str, str]],
        section_number: str,
        title_contains: str | None = None,
    ) -> str:
        """Find section content by exact section number or title fragment."""
        if section_number in sections:
            return sections[section_number]["content"]

        if title_contains:
            needle = title_contains.lower()
            for section in sections.values():
                if needle in section["title"].lower():
                    return section["content"]

        return ""

    # -------------------------------------------------------------------
    # Top-level Field Extraction
    # -------------------------------------------------------------------

    def _extract_title(self, text: str, doc: SRSDocument) -> None:
        """Extract the document title from the opening line or heading."""
        title_match = re.search(
            r"Software Requirements Specification\s*\(SRS\)\s*for\s+(.+)$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if title_match:
            doc.title = title_match.group(1).strip()
            return

        title_match = re.search(
            r"Software Requirements Specification\s+for\s+(.+)$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if title_match:
            doc.title = title_match.group(1).strip()
            return

        for line in text.splitlines():
            stripped = line.strip(" -")
            if stripped and not SECTION_HEADING_PATTERN.match(stripped):
                doc.title = stripped.lstrip("#").strip()
                return

    def _extract_purpose(self, sections: dict[str, dict[str, str]], doc: SRSDocument) -> None:
        """Extract description from section 1.1 Purpose."""
        content = self._find_section_content(sections, "1.1", "purpose")
        if not content:
            return

        lines = self._extract_text_lines(content)
        if lines:
            doc.description = " ".join(lines)

    def _extract_scope(self, sections: dict[str, dict[str, str]], doc: SRSDocument) -> None:
        """Extract scope items from section 1.2 Scope."""
        content = self._find_section_content(sections, "1.2", "scope")
        if not content:
            return

        items = self._extract_list_items(content)
        if items:
            doc.scope = items
            return

        # Fallback: split scope prose into likely capabilities.
        for line in self._extract_text_lines(content):
            if any(keyword in line.lower() for keyword in ("provide", "support", "include", "allow")):
                parts = re.split(r",\s*|\band\b\s+", line)
                for part in parts:
                    cleaned = re.sub(
                        r"^.*?\b(?:provide|support|include|allow(?: users)? to|will)\b\s*",
                        "",
                        part,
                        flags=re.IGNORECASE,
                    ).strip(" .")
                    if cleaned and len(cleaned) > 3:
                        doc.scope.append(cleaned)

    def _extract_definitions_and_actors(
        self,
        sections: dict[str, dict[str, str]],
        doc: SRSDocument,
    ) -> None:
        """Extract definitions and role-like actors from section 1.3."""
        content = self._find_section_content(
            sections,
            "1.3",
            "definitions",
        )
        if not content:
            return

        for key, value in self._extract_key_value_pairs(content).items():
            doc.definitions[key] = value
            key_lower = key.lower()
            if key_lower in EXCLUDED_DEFINITION_TERMS:
                continue
            if (
                key_lower in KNOWN_ACTOR_TERMS
                or any(word in key_lower for word in ("user", "manager", "admin", "employee", "staff", "customer"))
            ):
                doc.actors.append(key)

    def _extract_product_features(
        self,
        sections: dict[str, dict[str, str]],
        doc: SRSDocument,
    ) -> None:
        """Extract product features/modules from section 2.2."""
        content = self._find_section_content(sections, "2.2", "product features")
        if not content:
            return

        feature_items = self._extract_list_items(content)
        if feature_items:
            normalized_features: list[str] = []
            for item in feature_items:
                if ":" in item:
                    item = item.split(":", 1)[0]
                normalized_features.append(_clean_inline_markup(item))
            doc.modules = self._dedupe(normalized_features)
            return

        for key in self._extract_key_value_pairs(content):
            doc.modules.append(key)

        if doc.modules:
            return

        doc.modules = self._extract_text_lines(content)

    def _extract_user_classes(
        self,
        sections: dict[str, dict[str, str]],
        doc: SRSDocument,
    ) -> None:
        """Extract user classes from section 2.3."""
        content = self._find_section_content(sections, "2.3", "user classes")
        if not content:
            return

        pairs = self._extract_key_value_pairs(content)
        if pairs:
            for key, value in pairs.items():
                doc.user_classes[key] = value
                doc.actors.append(key)
            return

        for item in self._extract_list_items(content):
            doc.actors.append(item)

    def _extract_operating_environment(
        self,
        sections: dict[str, dict[str, str]],
        doc: SRSDocument,
    ) -> None:
        """Extract operating environment from section 2.4."""
        content = self._find_section_content(sections, "2.4", "operating environment")
        if not content:
            return

        pairs = self._extract_key_value_pairs(content)
        if pairs:
            doc.operating_environment = {
                _normalize_key(key): value for key, value in pairs.items()
            }

    def _extract_constraints(
        self,
        sections: dict[str, dict[str, str]],
        doc: SRSDocument,
    ) -> None:
        """Extract constraints from section 2.5."""
        content = self._find_section_content(sections, "2.5", "constraints")
        if not content:
            return

        items = self._extract_list_items(content)
        if items:
            doc.constraints = items
            return

        doc.constraints = self._extract_text_lines(content)

    # -------------------------------------------------------------------
    # Requirements
    # -------------------------------------------------------------------

    def _extract_requirement_sections(self, text: str, doc: SRSDocument) -> None:
        """Extract FR and NFR sections from the full document text."""
        matches = list(REQUIREMENT_HEADING_PATTERN.finditer(text))

        for index, match in enumerate(matches):
            req_id = self._normalize_req_id(match.group(1))
            title = _clean_inline_markup(match.group(2).rstrip(":"))
            start = match.end()
            end = self._find_requirement_boundary(text, start, matches, index)
            body = text[start:end].strip()
            requirements, acceptance = self._parse_requirement_body(body)

            if req_id.startswith("NFR"):
                doc.non_functional_requirements[req_id] = NonFunctionalRequirement(
                    title=title,
                    requirements=requirements,
                )
            else:
                doc.functional_requirements[req_id] = FunctionalRequirement(
                    title=title,
                    requirements=requirements,
                    acceptance_criteria=acceptance,
                )

    def _find_requirement_boundary(
        self,
        text: str,
        start: int,
        matches: list[re.Match[str]],
        current_index: int,
    ) -> int:
        """Find the end of a requirement block."""
        if current_index + 1 < len(matches):
            return matches[current_index + 1].start()

        next_section = SECTION_HEADING_PATTERN.search(text, start)
        if next_section:
            return next_section.start()

        return len(text)

    def _parse_requirement_body(self, body: str) -> tuple[list[str], list[str]]:
        """Parse requirements and acceptance criteria from a requirement block."""
        if not body:
            return [], []

        requirements: list[str] = []
        acceptance: list[str] = []
        current_section: str | None = None
        saw_labels = False

        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            label_match = LABEL_ONLY_PATTERN.match(line)
            if label_match:
                current_section = label_match.group(1).lower()
                saw_labels = True
                continue

            inline_label_match = LABEL_WITH_VALUE_PATTERN.match(line)
            if inline_label_match:
                current_section = inline_label_match.group(1).lower()
                saw_labels = True
                remainder = self._normalize_requirement_line(inline_label_match.group(2))
                if remainder:
                    if current_section == "acceptance criteria":
                        acceptance.append(remainder)
                    else:
                        requirements.append(remainder)
                continue

            target = requirements
            if current_section == "acceptance criteria":
                target = acceptance

            item = self._normalize_requirement_line(line)
            if not item:
                continue

            if current_section is None and saw_labels:
                target = requirements
            target.append(item)

        if saw_labels:
            return self._dedupe(requirements), self._dedupe(acceptance)

        bullets = self._extract_list_items(body)
        if bullets:
            return self._dedupe(bullets), []

        sentences = self._extract_text_lines(body)
        return self._dedupe(sentences), []

    def _normalize_requirement_line(self, line: str) -> str:
        """Normalize a raw requirement line or bullet."""
        cleaned = re.sub(r"^\s*[-*•]\s+", "", line).strip()
        if not cleaned:
            return ""

        if cleaned in {"---", "***"}:
            return ""

        if SECTION_HEADING_PATTERN.match(cleaned) or REQUIREMENT_HEADING_PATTERN.match(cleaned):
            return ""

        # Skip repeated label lines that slipped past pattern matching.
        if LABEL_ONLY_PATTERN.match(cleaned):
            return ""

        return _clean_requirement_sentence(cleaned)

    # -------------------------------------------------------------------
    # External interfaces / system attributes / out of scope
    # -------------------------------------------------------------------

    def _extract_external_interfaces(
        self,
        sections: dict[str, dict[str, str]],
        doc: SRSDocument,
    ) -> None:
        """Extract external interface sections under 4.x."""
        for section_num, section in sections.items():
            if not section_num.startswith("4."):
                continue

            key = _normalize_key(section["title"])
            items = self._extract_list_items(section["content"])
            if items:
                doc.external_interfaces[key] = items
            else:
                lines = self._extract_text_lines(section["content"])
                if lines:
                    doc.external_interfaces[key] = lines

    def _extract_system_attributes(
        self,
        sections: dict[str, dict[str, str]],
        doc: SRSDocument,
    ) -> None:
        """Extract system attributes from section 5.x."""
        attribute_map = {
            "5.1": "reliability",
            "5.2": "scalability",
            "5.3": "security",
            "5.4": "maintainability",
        }

        for section_num, attribute_name in attribute_map.items():
            content = self._find_section_content(sections, section_num)
            if not content:
                continue

            items = self._extract_list_items(content)
            if items:
                doc.system_attributes[attribute_name] = "; ".join(items)
                continue

            lines = self._extract_text_lines(content)
            if lines:
                doc.system_attributes[attribute_name] = " ".join(lines)

    def _extract_out_of_scope(
        self,
        sections: dict[str, dict[str, str]],
        doc: SRSDocument,
    ) -> None:
        """Extract out-of-scope items from section 6."""
        content = self._find_section_content(sections, "6", "out of scope")
        if not content:
            return

        items = self._extract_list_items(content)
        if items:
            doc.out_of_scope = items
            return

        doc.out_of_scope = self._extract_text_lines(content)

    # -------------------------------------------------------------------
    # Technology detection / generic text helpers
    # -------------------------------------------------------------------

    def _detect_technologies(self, text: str, doc: SRSDocument) -> None:
        """Detect technology names in the full document text."""
        text_lower = text.lower()
        for tech in KNOWN_TECHNOLOGIES:
            if tech in text_lower:
                pattern = re.compile(re.escape(tech), re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    doc.technologies.append(match.group(0))

        for match in BOLD_PATTERN.finditer(text):
            term = match.group(1).strip()
            if term.lower() in KNOWN_TECHNOLOGIES and term not in doc.technologies:
                doc.technologies.append(term)

    def _extract_list_items(self, content: str) -> list[str]:
        """Extract bullet-like items from a text block."""
        items = [_clean_requirement_sentence(item) for item in BULLET_PATTERN.findall(content)]
        return [item for item in items if item]

    def _extract_text_lines(self, content: str) -> list[str]:
        """Extract non-heading prose lines as normalized sentences/items."""
        lines: list[str] = []

        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if SECTION_HEADING_PATTERN.match(stripped):
                continue
            if REQUIREMENT_HEADING_PATTERN.match(stripped):
                continue
            label_match = LABEL_ONLY_PATTERN.match(stripped)
            if label_match:
                continue

            bullet_match = re.match(r"^\s*[-*•]\s+(.+?)\s*$", stripped)
            if bullet_match:
                cleaned = _clean_requirement_sentence(bullet_match.group(1))
                if cleaned:
                    lines.append(cleaned)
                continue

            cleaned = _clean_inline_markup(stripped)
            if cleaned:
                lines.extend(_split_sentences(cleaned))

        return self._dedupe(lines)

    def _extract_key_value_pairs(self, content: str) -> dict[str, str]:
        """Extract `Key: Value` pairs from a section."""
        pairs: dict[str, str] = {}
        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue

            match = KEY_VALUE_LINE_PATTERN.match(stripped)
            if not match:
                continue

            key = _clean_inline_markup(match.group(1))
            value = _clean_inline_markup(match.group(2))
            if key and value:
                pairs[key] = value

        return pairs

    @staticmethod
    def _normalize_req_id(raw_id: str) -> str:
        """Normalize requirement IDs (e.g., `FR 01` -> `FR-01`)."""
        cleaned = re.sub(r"[-\s]+", "-", raw_id.strip().upper())
        return cleaned

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        """Preserve order while removing duplicates and empties."""
        return list(dict.fromkeys(item for item in items if item))


# ---------------------------------------------------------------------------
# Module-Level Convenience Function
# ---------------------------------------------------------------------------

def parse_srs(text: str, spacy_model: str = "en_core_web_sm") -> SRSDocument:
    """
    Parse SRS text into a structured document.

    Args:
        text: Raw SRS document text.
        spacy_model: SpaCy model name to use.

    Returns:
        Parsed SRSDocument.
    """
    parser = SRSParser(spacy_model=spacy_model)
    return parser.parse(text)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from pdf_parser import extract_text_from_file

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python srs_to_json.py <path_to_srs_file>")
        print("Supported formats: .pdf, .txt, .md")
        sys.exit(1)

    file_path = sys.argv[1]
    raw_text = extract_text_from_file(file_path)
    srs_doc = parse_srs(raw_text)

    output_json = srs_doc.to_json(indent=2)
    print(output_json)

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
        output_path.write_text(output_json, encoding="utf-8")
        print(f"\nSaved to: {output_path}")
