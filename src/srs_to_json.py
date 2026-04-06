"""
SRS to JSON Parser (Stage 1)
=============================
Parses raw SRS text into a structured JSON format using SpaCy NLP
and regex pattern matching. Designed for SRS documents following the
standard numbered-section template format.

Supported SRS Structure:
    1. Introduction (1.1 Purpose, 1.2 Scope, 1.3 Definitions)
    2. Overall Description (2.1-2.5)
    3. System Features (3.1 Functional, 3.2 Non-Functional)
    4. External Interfaces
    5. System Attributes (5.1-5.4)
    6. Out of Scope
"""

import re
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

import spacy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Known technology keywords for detection
KNOWN_TECHNOLOGIES = {
    "next.js", "react", "angular", "vue.js", "vue", "svelte", "nuxt.js",
    "node.js", "express", "fastapi", "django", "flask", "spring boot",
    "prisma", "sequelize", "typeorm", "mongoose", "sqlalchemy",
    "mongodb", "postgresql", "mysql", "sqlite", "redis", "firebase",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "typescript", "javascript", "python", "java", "go", "rust", "c#",
    "graphql", "rest", "grpc", "websocket",
    "tailwindcss", "tailwind", "bootstrap", "material ui", "chakra ui",
    "jest", "cypress", "playwright", "vitest",
    "git", "github", "gitlab", "bitbucket",
    "stripe", "paypal", "twilio", "sendgrid",
    "jwt", "oauth", "oauth2", "auth0",
}

# Regex patterns for section detection
SECTION_HEADING_PATTERN = re.compile(
    r"^#{1,4}\s*(\d+(?:\.\d+)*)\s+(.+)$", re.MULTILINE
)

# FR/NFR ID patterns — match markdown headings, bold text, or both combined
# Handles: "### FR-01: Title", "**FR-01: Title**", "#### **FR-01: Title**"
FR_PATTERN = re.compile(
    r"^(?:#{1,4}\s+)?(?:\*{2})?\s*(FR[-\s]?\d+):?\s*(.+?)\s*\*{0,2}\s*$",
    re.MULTILINE | re.IGNORECASE,
)
NFR_PATTERN = re.compile(
    r"^(?:#{1,4}\s+)?(?:\*{2})?\s*(NFR[-\s]?\d+):?\s*(.+?)\s*\*{0,2}\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Bullet point pattern
BULLET_PATTERN = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)

# Bold text pattern (for extracting key terms)
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")


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
    modules: list[str] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    operating_environment: dict[str, str] = field(default_factory=dict)
    functional_requirements: dict[str, FunctionalRequirement] = field(
        default_factory=dict
    )
    non_functional_requirements: dict[str, NonFunctionalRequirement] = field(
        default_factory=dict
    )
    system_attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dictionary suitable for JSON serialization."""
        data = asdict(self)
        return data

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Parser Class
# ---------------------------------------------------------------------------

class SRSParser:
    """
    Parses raw SRS text into a structured SRSDocument.

    Uses SpaCy for NLP tasks (sentence detection, entity recognition)
    and regex patterns for section/requirement extraction.
    """

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        """
        Initialize the parser.

        Args:
            spacy_model: Name of the SpaCy model to load.
        """
        logger.info("Loading SpaCy model: %s", spacy_model)
        try:
            self.nlp = spacy.load(spacy_model)
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
        logger.info("Starting SRS parsing (%d characters)", len(text))

        doc = SRSDocument()

        # Split document into sections
        sections = self._split_into_sections(text)
        logger.debug("Found %d sections", len(sections))

        # Extract fields from each section
        self._extract_title(text, doc)
        self._extract_purpose(sections, doc)
        self._extract_scope(sections, doc)
        self._extract_definitions_and_actors(sections, doc)
        self._extract_product_features(sections, doc)
        self._extract_user_classes(sections, doc)
        self._extract_operating_environment(sections, doc)
        self._extract_constraints(sections, doc)
        self._extract_functional_requirements(text, doc)
        self._extract_non_functional_requirements(text, doc)
        self._extract_system_attributes(sections, doc)
        self._extract_out_of_scope(sections, doc)

        # Use SpaCy for technology detection across full text
        self._detect_technologies(text, doc)

        # Deduplicate lists
        doc.actors = list(dict.fromkeys(doc.actors))
        doc.technologies = list(dict.fromkeys(doc.technologies))
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

    def _split_into_sections(self, text: str) -> dict[str, str]:
        """
        Split the document into sections based on numbered headings.

        Returns a dict mapping section numbers (e.g., '1.1', '2.3')
        to their content text.
        """
        sections: dict[str, str] = {}
        matches = list(SECTION_HEADING_PATTERN.finditer(text))

        for i, match in enumerate(matches):
            section_num = match.group(1)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            sections[section_num] = content

        return sections

    # -------------------------------------------------------------------
    # Field Extractors
    # -------------------------------------------------------------------

    def _extract_title(self, text: str, doc: SRSDocument) -> None:
        """Extract the document title from the main heading."""
        # Look for the first top-level heading
        title_match = re.search(
            r"^#\s+.*?(?:SRS|Software Requirements).*?for\s+(.+)$",
            text,
            re.MULTILINE | re.IGNORECASE,
        )
        if title_match:
            doc.title = title_match.group(1).strip()
            return

        # Fallback: first heading
        heading_match = re.search(r"^#+\s+(.+)$", text, re.MULTILINE)
        if heading_match:
            doc.title = heading_match.group(1).strip()

    def _extract_purpose(self, sections: dict[str, str], doc: SRSDocument) -> None:
        """Extract description from section 1.1 (Purpose)."""
        content = sections.get("1.1", "")
        if not content:
            return

        # Get the descriptive text (skip the heading line)
        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        if lines:
            doc.description = " ".join(lines)

    def _extract_scope(self, sections: dict[str, str], doc: SRSDocument) -> None:
        """Extract scope items from section 1.2."""
        content = sections.get("1.2", "")
        if not content:
            return

        # Extract bullet points as scope items
        bullets = BULLET_PATTERN.findall(content)
        if bullets:
            doc.scope = [b.strip() for b in bullets]
            return

        # Fallback: parse comma-separated features from text
        # Look for feature-listing sentences
        nlp_doc = self.nlp(content)
        for sent in nlp_doc.sents:
            sent_text = sent.text.strip()
            # Look for sentences listing features
            if any(
                kw in sent_text.lower()
                for kw in ["provide", "include", "features", "will"]
            ):
                # Extract items after keywords like "provide" or commas
                parts = re.split(r",\s*(?:and\s+)?", sent_text)
                for part in parts:
                    cleaned = re.sub(
                        r"^.*?(?:provide|include|features)\s+", "", part, flags=re.IGNORECASE
                    ).strip(" .")
                    if cleaned and len(cleaned) > 3:
                        doc.scope.append(cleaned)

    def _extract_definitions_and_actors(
        self, sections: dict[str, str], doc: SRSDocument
    ) -> None:
        """Extract actors and definitions from section 1.3."""
        content = sections.get("1.3", "")
        if not content:
            return

        # Pattern: **Term**: Description
        for match in BOLD_PATTERN.finditer(content):
            term = match.group(1).strip()
            # Skip non-actor terms
            if term.lower() in ("api", "srs", "ui", "ux", "url", "http", "https"):
                continue
            doc.actors.append(term)

    def _extract_product_features(
        self, sections: dict[str, str], doc: SRSDocument
    ) -> None:
        """Extract modules from section 2.2 (Product Features)."""
        content = sections.get("2.2", "")
        if not content:
            return

        # Pattern: **Feature Name**: Description (from bullet list)
        for match in BOLD_PATTERN.finditer(content):
            feature = match.group(1).strip()
            if feature and len(feature) > 2:
                doc.modules.append(feature)

    def _extract_user_classes(
        self, sections: dict[str, str], doc: SRSDocument
    ) -> None:
        """Extract additional actors from section 2.3 (User Classes)."""
        content = sections.get("2.3", "")
        if not content:
            return

        for match in BOLD_PATTERN.finditer(content):
            actor = match.group(1).strip()
            if actor.lower() not in ("api", "srs"):
                doc.actors.append(actor)

    def _extract_operating_environment(
        self, sections: dict[str, str], doc: SRSDocument
    ) -> None:
        """Extract operating environment from section 2.4."""
        content = sections.get("2.4", "")
        if not content:
            return

        # Look for **Category**: Description pattern
        lines = content.split("\n")
        for line in lines:
            bold_match = re.search(r"\*\*(.+?)\*\*:?\s*(.+)", line)
            if bold_match:
                key = bold_match.group(1).strip().lower()
                value = bold_match.group(2).strip()
                doc.operating_environment[key] = value

    def _extract_constraints(
        self, sections: dict[str, str], doc: SRSDocument
    ) -> None:
        """Extract constraints from section 2.5."""
        content = sections.get("2.5", "")
        if not content:
            return

        bullets = BULLET_PATTERN.findall(content)
        if bullets:
            doc.constraints = [b.strip() for b in bullets]
        else:
            # Sentence-based extraction
            nlp_doc = self.nlp(content)
            for sent in nlp_doc.sents:
                sent_text = sent.text.strip()
                if sent_text and not sent_text.startswith("#"):
                    doc.constraints.append(sent_text)

    def _extract_functional_requirements(
        self, text: str, doc: SRSDocument
    ) -> None:
        """Extract all functional requirements (FR-XX) with their details."""
        matches = list(FR_PATTERN.finditer(text))

        for i, match in enumerate(matches):
            fr_id = self._normalize_req_id(match.group(1))
            fr_title = match.group(2).strip().rstrip(":")

            # Get content between this FR and the next FR/NFR/section
            start = match.end()
            end = self._find_next_boundary(text, start, matches, i)
            content = text[start:end]

            fr = FunctionalRequirement(title=fr_title)
            fr.requirements = self._extract_requirement_list(content, "Requirements")
            fr.acceptance_criteria = self._extract_requirement_list(
                content, "Acceptance Criteria"
            )

            doc.functional_requirements[fr_id] = fr
            logger.debug("Extracted %s: %s (%d reqs, %d ACs)",
                         fr_id, fr_title,
                         len(fr.requirements), len(fr.acceptance_criteria))

    def _extract_non_functional_requirements(
        self, text: str, doc: SRSDocument
    ) -> None:
        """Extract all non-functional requirements (NFR-XX)."""
        matches = list(NFR_PATTERN.finditer(text))

        for i, match in enumerate(matches):
            nfr_id = self._normalize_req_id(match.group(1))
            nfr_title = match.group(2).strip().rstrip(":")

            start = match.end()
            end = self._find_next_boundary(text, start, matches, i)
            content = text[start:end]

            nfr = NonFunctionalRequirement(title=nfr_title)
            nfr.requirements = self._extract_requirement_list(content, "Requirements")

            doc.non_functional_requirements[nfr_id] = nfr
            logger.debug("Extracted %s: %s (%d reqs)",
                         nfr_id, nfr_title, len(nfr.requirements))

    def _extract_system_attributes(
        self, sections: dict[str, str], doc: SRSDocument
    ) -> None:
        """Extract system attributes from section 5.x."""
        attribute_map = {
            "5.1": "reliability",
            "5.2": "scalability",
            "5.3": "security",
            "5.4": "maintainability",
        }

        for section_num, attr_name in attribute_map.items():
            content = sections.get(section_num, "")
            if not content:
                continue

            # Get descriptive text (skip headings)
            lines = [
                line.strip()
                for line in content.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]

            if lines:
                doc.system_attributes[attr_name] = " ".join(lines)

    def _extract_out_of_scope(
        self, sections: dict[str, str], doc: SRSDocument
    ) -> None:
        """Extract out-of-scope items from section 6."""
        content = sections.get("6", "")
        if not content:
            return

        bullets = BULLET_PATTERN.findall(content)
        if bullets:
            doc.out_of_scope = [b.strip().rstrip(".") for b in bullets]
        else:
            # Sentence-based extraction
            nlp_doc = self.nlp(content)
            for sent in nlp_doc.sents:
                sent_text = sent.text.strip().rstrip(".")
                if sent_text and not sent_text.startswith("#"):
                    doc.out_of_scope.append(sent_text)

    # -------------------------------------------------------------------
    # Technology Detection
    # -------------------------------------------------------------------

    def _detect_technologies(self, text: str, doc: SRSDocument) -> None:
        """Detect technology names in the full document text."""
        text_lower = text.lower()

        # Match against known technology list
        for tech in KNOWN_TECHNOLOGIES:
            if tech in text_lower:
                # Find the original casing from the text
                pattern = re.compile(re.escape(tech), re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    doc.technologies.append(match.group(0))

        # Also extract bold terms from scope/environment sections
        # that look like technology names (capitalized, short)
        for match in BOLD_PATTERN.finditer(text):
            term = match.group(1).strip()
            if (
                term.lower() in KNOWN_TECHNOLOGIES
                and term not in doc.technologies
            ):
                doc.technologies.append(term)

    # -------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------

    @staticmethod
    def _normalize_req_id(raw_id: str) -> str:
        """Normalize requirement IDs (e.g., 'FR 01' → 'FR-01')."""
        cleaned = re.sub(r"[-\s]+", "-", raw_id.strip().upper())
        return cleaned

    @staticmethod
    def _find_next_boundary(
        text: str,
        start: int,
        matches: list[re.Match],
        current_idx: int,
    ) -> int:
        """Find the end boundary for a requirement section."""
        # Next FR/NFR match
        if current_idx + 1 < len(matches):
            return matches[current_idx + 1].start()

        # Next major section heading
        next_section = re.search(
            r"^#{1,4}\s*\d+(?:\.\d+)*\s+",
            text[start:],
            re.MULTILINE,
        )
        if next_section:
            return start + next_section.start()

        return len(text)

    @staticmethod
    def _extract_requirement_list(content: str, section_name: str) -> list[str]:
        """
        Extract a list of items under a specific sub-section.

        Handles two formats:
          1. Bullet lists:  - item one\n - item two
          2. Continuous text: sentences separated by line breaks or periods

        Args:
            content: Text content to search within.
            section_name: Name of the sub-section (e.g., 'Requirements').

        Returns:
            List of extracted requirement strings.
        """
        # --- Try bullet-list format first ---
        pattern_bullets = re.compile(
            rf"\*?\*?{re.escape(section_name)}\*?\*?:?\s*\n((?:\s*[-*•].+\n?)+)",
            re.IGNORECASE,
        )
        match = pattern_bullets.search(content)
        if match:
            bullet_text = match.group(1)
            items = BULLET_PATTERN.findall(bullet_text)
            return [item.strip().rstrip(".") for item in items if item.strip()]

        # --- Fallback: continuous-text / inline format ---
        # Match the section header followed by any text block until the next
        # bold header or end of content.
        pattern_text = re.compile(
            rf"\*?\*?{re.escape(section_name)}\*?\*?:?\s*\n(.*?)(?=\n\s*[-*]\s*\*\*|$)",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern_text.search(content)
        if not match:
            return []

        block = match.group(1).strip()
        if not block:
            return []

        # Split on sentence boundaries (line breaks or periods followed by
        # an uppercase letter) to produce individual requirement items.
        raw_items = re.split(r"\n+|(?<=\.)\s+(?=[A-Z])", block)
        results = []
        for item in raw_items:
            cleaned = item.strip().rstrip(".")
            # Skip very short fragments or sub-heading artifacts
            if cleaned and len(cleaned) > 10 and not cleaned.startswith("**"):
                results.append(cleaned)

        return results


# ---------------------------------------------------------------------------
# Module-Level Convenience Function
# ---------------------------------------------------------------------------

def parse_srs(text: str, spacy_model: str = "en_core_web_sm") -> SRSDocument:
    """
    Parse SRS text into a structured document.

    Convenience function that creates a parser instance and parses the text.

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

    # Add parent to path for sibling imports
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

    # Output
    output_json = srs_doc.to_json(indent=2)
    print(output_json)

    # Optionally save
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
        output_path.write_text(output_json, encoding="utf-8")
        print(f"\nSaved to: {output_path}")
