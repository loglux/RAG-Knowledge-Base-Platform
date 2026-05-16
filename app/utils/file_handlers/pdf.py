"""PDF file handler using PyMuPDF (fitz)."""

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from app.models.enums import FileType
from app.utils.file_handlers.base import ExtractResult, FileHandler
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PDFExtractionProfile:
    """Per-document extraction parameters derived by _profile_document().

    Three fields can be overridden from outside (admin settings → KB → call site):
    ``table_strategy``, ``size_ratio_threshold`` (heading sensitivity), and
    ``min_doc_length``. The rest are either auto-derived per page or constants
    that are not worth surfacing.
    """

    # y0 threshold as fraction of page height — blocks starting above this are
    # treated as headers and dropped. 0.0 means "don't filter top". The real
    # value is derived per-document from confirmed running headers; this
    # default applies only when no running headers were detected.
    header_zone_fraction: float = 0.0
    # y0 threshold as fraction of page height — blocks starting here or below are
    # treated as footers and dropped. 1.0 means "don't filter bottom".
    footer_zone_fraction: float = 1.0
    # Normalised texts of confirmed running headers — excluded from text and headings
    running_header_texts: frozenset = field(default_factory=frozenset)
    # Font size ratio above which a block qualifies as a size-based heading
    size_ratio_threshold: float = 1.15
    # First-line bold fraction to qualify as a bold heading
    bold_fraction_threshold: float = 0.85
    # First-line length range [min, max) for bold headings
    bold_min_chars: int = 5
    bold_max_chars: int = 120
    # Heading texts appearing >= this many times kept only at first occurrence
    repeat_threshold: int = 4
    # PyMuPDF find_tables strategy: 'lines' (visible borders) or 'text' (gaps)
    table_strategy: str = "lines"
    # Minimum chars in extracted text before rejecting the PDF as scanned
    min_doc_length: int = 100


# Fields user can override from settings (anything not listed is auto-derived
# or considered an internal heuristic that is not yet user-facing).
OVERRIDABLE_PROFILE_FIELDS = (
    "table_strategy",
    "size_ratio_threshold",
    "min_doc_length",
)


class PDFFileHandler(FileHandler):
    """Handler for PDF files (.pdf).

    Uses PyMuPDF (fitz) directly for text extraction, with find_tables()
    to detect tables and render them as Markdown (preserving empty cells).
    Text blocks that overlap with detected table regions are skipped so
    they are not duplicated. Items are merged in vertical order.

    Heading detection uses font-size relative to the page median: blocks
    whose maximum span font size is noticeably larger than the median are
    treated as headings; level is estimated from the relative size.

    Scanned (image-only) PDFs are detected and rejected with a clear error.
    """

    def can_handle(self, file_type: FileType) -> bool:
        return file_type == FileType.PDF

    @staticmethod
    def _to_bytes(content: Union[str, bytes]) -> bytes:
        if isinstance(content, str):
            return content.encode("utf-8")
        return content

    @staticmethod
    def _normalize_block_text(block) -> str:
        """Return normalised single-line text for a PyMuPDF dict block.

        Concatenates span texts with no separator (matching PyMuPDF's own
        layout where word spacing is embedded inside span text), then collapses
        whitespace.  Used identically in _profile_document() and _extract_pdf()
        so that running-header lookup keys are guaranteed to match.
        """
        import re as _re

        raw = "".join(
            s.get("text", "") for ln in block.get("lines", []) for s in ln.get("spans", [])
        )
        return _re.sub(r"\s+", " ", raw).strip()

    @staticmethod
    def _profile_document(
        doc, overrides: Optional[Dict[str, Any]] = None
    ) -> "PDFExtractionProfile":
        """Scan document structure to derive per-document extraction parameters.

        Detects running headers/footers (text appearing on ≥30% of pages) and
        derives zone fractions that cleanly exclude them from extraction.

        Args:
            doc: Open fitz.Document instance.
            overrides: Optional dict with admin/KB-level overrides for
                ``OVERRIDABLE_PROFILE_FIELDS``. None or missing keys keep
                built-in defaults.
        """
        from collections import defaultdict

        import fitz

        page_count = len(doc)
        if page_count == 0:
            return PDFExtractionProfile()

        SCAN_ZONE = 0.10  # fraction of page height to scan for headers/footers
        REPEAT_FRAC = 0.30  # text on >= this fraction of pages → running element
        MARGIN_PT = 4.0  # extra clearance added to derived cutoff

        top_blocks: dict = defaultdict(list)  # normalised_text → [(y0, y1), …]
        bottom_blocks: dict = defaultdict(list)
        page_heights: list = []

        for page in doc:
            h = page.rect.height
            page_heights.append(h)
            top_cut = h * SCAN_ZONE
            bottom_cut = h * (1.0 - SCAN_ZONE)

            for b in page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", []):
                if b.get("type") != 0:
                    continue
                y0, y1 = b["bbox"][1], b["bbox"][3]
                text = PDFFileHandler._normalize_block_text(b)
                if not text:
                    continue
                if y0 < top_cut:
                    top_blocks[text].append((y0, y1))
                if y1 > bottom_cut:
                    bottom_blocks[text].append((y0, y1))

        repeat_threshold = max(3, page_count * REPEAT_FRAC)
        median_h = statistics.median(page_heights) if page_heights else 800.0

        # Derive header zone from confirmed running headers
        running_header_texts: set = set()
        header_y1_max = 0.0
        for text, coords in top_blocks.items():
            if len(coords) >= repeat_threshold:
                running_header_texts.add(text)
                header_y1_max = max(header_y1_max, max(y1 for _, y1 in coords))

        # When no running headers were confirmed, do NOT apply a blanket
        # top-of-page filter. The earlier 0.04 default would silently eat real
        # headings sitting in the top ~33 pt strip (e.g. "Question N – X marks"
        # in OU exam papers), with no benefit when there is nothing repetitive
        # to remove. Same reasoning for the footer zone.
        header_zone_fraction = (
            min((header_y1_max + MARGIN_PT) / median_h, 0.10) if running_header_texts else 0.0
        )

        # Derive footer zone from confirmed running footers
        footer_y0_min = median_h
        for text, coords in bottom_blocks.items():
            if len(coords) >= repeat_threshold:
                footer_y0_min = min(footer_y0_min, min(y0 for y0, _ in coords))

        footer_zone_fraction = (
            max((footer_y0_min - MARGIN_PT) / median_h, 0.85) if footer_y0_min < median_h else 1.0
        )

        # Apply external overrides on top of auto-derived values.
        # We only honour keys in OVERRIDABLE_PROFILE_FIELDS so a stray dict
        # cannot smuggle in arbitrary attributes.
        override_kwargs: Dict[str, Any] = {}
        if overrides:
            for key in OVERRIDABLE_PROFILE_FIELDS:
                value = overrides.get(key)
                if value is not None:
                    override_kwargs[key] = value

        return PDFExtractionProfile(
            header_zone_fraction=header_zone_fraction,
            footer_zone_fraction=footer_zone_fraction,
            running_header_texts=frozenset(running_header_texts),
            **override_kwargs,
        )

    @staticmethod
    def _extract_footer_page_number(page) -> Optional[int]:
        """Try to extract the printed (logical) page number from a PDF page footer."""
        import re

        rect = page.rect
        footer_rect = type(rect)(0, rect.height * 0.95, rect.width, rect.height)
        text = page.get_text("text", clip=footer_rect).strip()
        if not text:
            return None
        for line in reversed(text.splitlines()):
            line = line.strip()
            if re.fullmatch(r"\d{1,4}", line):
                return int(line)
        return None

    @staticmethod
    def _rows_to_markdown(rows: List[List]) -> str:
        """Convert a list-of-lists table (from find_tables) to a Markdown table."""
        if not rows:
            return ""

        def cell(v: Any) -> str:
            return str(v).replace("|", "\\|").strip() if v is not None else ""

        header = [cell(c) for c in rows[0]]
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        for row in rows[1:]:
            cells = [cell(c) for c in row]
            # Pad or trim to match header width
            while len(cells) < len(header):
                cells.append("")
            lines.append("| " + " | ".join(cells[: len(header)]) + " |")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_chars(text: str) -> str:
        """Char-level sanitization used while accumulating per-item offsets.

        Performs the same filtering as utils.validators.sanitize_text_content
        (drop null bytes, drop C0/C1 control chars except \\n and \\t, allow
        printable ASCII and >U+009F) but without the trailing .strip().

        Applying char filtering per item *before* computing offsets keeps
        heading/page positions consistent with the final text: any chars
        removed here are also absent from the offset accumulator.
        """
        text = text.replace("\x00", "")
        return "".join(
            c for c in text if c == "\n" or c == "\t" or (0x20 <= ord(c) <= 0x7E) or ord(c) > 0x9F
        )

    @staticmethod
    def _detect_column_gutter(items: List[tuple], page_width: float) -> Optional[float]:
        """Detect the x-coordinate of a vertical gutter on a multi-column page.

        Looks at block center-x values. If the largest gap between consecutive
        sorted centers is wide enough (>= 15% of page width) and each side
        carries at least 3 blocks, the midpoint of that gap is the gutter.

        Args:
            items: Sequence of (y0, x0, x1, text) tuples for the page.
            page_width: Page width in points.

        Returns:
            x-coordinate of the gutter, or None if the page is single-column
            (or detection is unreliable due to too few blocks).
        """
        if len(items) < 6:
            return None

        centers = sorted((it[1] + it[2]) / 2 for it in items)
        max_gap = 0.0
        max_gap_x = 0.0
        for i in range(1, len(centers)):
            gap = centers[i] - centers[i - 1]
            if gap > max_gap:
                max_gap = gap
                max_gap_x = (centers[i] + centers[i - 1]) / 2

        if max_gap < page_width * 0.15:
            return None

        left = sum(1 for c in centers if c < max_gap_x)
        right = len(centers) - left
        if left < 3 or right < 3:
            return None

        return max_gap_x

    @staticmethod
    def _sort_blocks_by_column(
        items: List[tuple],
        gutter_x: float,
        page_width: float,
    ) -> List[tuple]:
        """Sort blocks in column-aware reading order.

        Blocks are classified as left / right / spanning relative to the gutter.
        A spanning block crosses the gutter AND is wider than ~1.2× a typical
        column (>= 60% of page width) — it breaks the column flow at its y0.

        Reading order: for each band between consecutive spanning blocks,
        emit all left-column blocks (sorted by y0), then all right-column
        blocks (sorted by y0); then the spanning block itself.

        Args:
            items: List of (y0, x0, x1, text) tuples.
            gutter_x: Gutter x-coordinate from _detect_column_gutter.
            page_width: Page width in points (used to set spanning threshold).

        Returns:
            Items reordered into reading order.
        """
        col_width_est = page_width / 2.0
        spanning_threshold = col_width_est * 1.2

        spanning: List[tuple] = []
        left: List[tuple] = []
        right: List[tuple] = []
        for it in items:
            x0, x1 = it[1], it[2]
            block_width = x1 - x0
            crosses_gutter = x0 < gutter_x < x1
            if crosses_gutter and block_width >= spanning_threshold:
                spanning.append(it)
            elif (x0 + x1) / 2 < gutter_x:
                left.append(it)
            else:
                right.append(it)

        left.sort(key=lambda t: t[0])
        right.sort(key=lambda t: t[0])
        spanning.sort(key=lambda t: t[0])

        result: List[tuple] = []
        prev_band_y = float("-inf")
        for span in spanning:
            span_y0 = span[0]
            for it in left:
                if prev_band_y < it[0] < span_y0:
                    result.append(it)
            for it in right:
                if prev_band_y < it[0] < span_y0:
                    result.append(it)
            result.append(span)
            prev_band_y = span_y0

        for it in left:
            if it[0] >= prev_band_y:
                result.append(it)
        for it in right:
            if it[0] >= prev_band_y:
                result.append(it)

        return result

    def _extract_pdf(
        self,
        content: bytes,
        profile_overrides: Optional[Dict[str, Any]] = None,
    ):
        """Extract (text, heading_map, page_map).

        For each page:
          1. Detect tables with find_tables(strategy=profile.table_strategy)
             and render as Markdown.
          2. Extract text blocks via get_text("dict"), skipping blocks that
             overlap ≥40% with a table region.
          3. Detect column layout and merge blocks in reading order:
             single-column pages sort by y; multi-column pages sort
             left-column → right-column with spanning elements breaking flow.
          4. Detect headings by comparing block font sizes to the page median.

        page_map: [[char_offset, physical_page, logical_page_or_null], ...]

        Args:
            content: Raw PDF bytes.
            profile_overrides: Optional dict that may override
                ``table_strategy``, ``size_ratio_threshold``, ``min_doc_length``.
                None or missing keys fall back to per-document auto-detection
                or built-in defaults.
        """
        import re

        import fitz

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise ValueError(f"Cannot open PDF: {exc}") from exc

        has_text = any(page.get_text("text").strip() for page in doc)
        if not has_text:
            doc.close()
            raise ValueError(
                "No text could be extracted from this PDF. "
                "It may be a scanned document — OCR is not supported yet."
            )

        profile = self._profile_document(doc, overrides=profile_overrides)
        logger.info(
            "PDF profile: header_zone=%.3f footer_zone=%.3f running_headers=%d",
            profile.header_zone_fraction,
            profile.footer_zone_fraction,
            len(profile.running_header_texts),
        )

        text_parts: List[str] = []
        headings: List[Dict[str, Any]] = []
        page_map: List[List] = []
        current_pos = 0
        multi_column_pages = 0

        for page in doc:
            page_num = page.number + 1
            page_start_pos = current_pos

            # ── 1. Detect tables ──────────────────────────────────────────
            table_rects: List[Any] = []  # fitz.Rect objects
            # (y0, x0, x1, markdown_string, heading_info_or_None) — tables are never headings
            table_items: List = []
            try:
                tabs = page.find_tables(strategy=profile.table_strategy)
                for tab in tabs.tables:
                    rows = tab.extract()
                    if rows and len(rows) >= 2:
                        tr = fitz.Rect(tab.bbox)
                        table_rects.append(tr)
                        md = self._rows_to_markdown(rows)
                        table_items.append((tab.bbox[1], tab.bbox[0], tab.bbox[2], md, None))
            except Exception as exc:
                logger.warning("PDF table extraction failed on a page: %s", exc)

            # ── 2. Extract text blocks, skipping table regions ────────────
            # (y0, x0, x1, text, heading_info_or_None) where heading_info=(level, text)
            text_items: List = []
            all_font_sizes: List[float] = []
            # (y0, x0, x1, block_text, max_font_size, first_line_text,
            #  first_line_bold_chars, first_line_total_chars)
            block_info: List = []

            page_h = page.rect.height
            header_cutoff = page_h * profile.header_zone_fraction
            footer_cutoff = page_h * profile.footer_zone_fraction

            try:
                block_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
                for block in block_dict.get("blocks", []):
                    if block.get("type") != 0:
                        continue
                    brect = fitz.Rect(block["bbox"])

                    # Skip running-header and footer strips.
                    # Use y0 (block start) for the header zone so blocks that
                    # start inside the strip are filtered even if they extend
                    # slightly below the cutoff.
                    if brect.y0 < header_cutoff or brect.y0 >= footer_cutoff:
                        continue

                    # Skip blocks whose normalised text is a confirmed running header
                    if profile.running_header_texts:
                        if self._normalize_block_text(block) in profile.running_header_texts:
                            continue

                    # Skip if block overlaps substantially with a table
                    in_table = False
                    for trect in table_rects:
                        inter = brect & trect
                        if (
                            not inter.is_empty
                            and brect.get_area() > 0
                            and inter.get_area() / brect.get_area() >= 0.4
                        ):
                            in_table = True
                            break
                    if in_table:
                        continue

                    lines_text: List[str] = []
                    max_size = 0.0
                    first_line_text = ""
                    first_line_bold = 0
                    first_line_total = 0
                    for line in block.get("lines", []):
                        line_text = "".join(s.get("text", "") for s in line.get("spans", []))
                        is_first = not first_line_text and line_text.strip()
                        if line_text.strip():
                            lines_text.append(line_text.rstrip())
                            if is_first:
                                first_line_text = line_text.strip()
                        for span in line.get("spans", []):
                            sz = span.get("size", 0)
                            if sz > 0:
                                all_font_sizes.append(sz)
                                if sz > max_size:
                                    max_size = sz
                            if is_first:
                                n = len(span.get("text", ""))
                                first_line_total += n
                                if span.get("flags", 0) & 0b10000:  # bold bit
                                    first_line_bold += n

                    if lines_text:
                        block_text = "\n".join(lines_text)
                        block_info.append(
                            (
                                block["bbox"][1],
                                block["bbox"][0],
                                block["bbox"][2],
                                block_text,
                                max_size,
                                first_line_text,
                                first_line_bold,
                                first_line_total,
                            )
                        )
            except Exception as exc:
                logger.warning("PDF block parsing failed, falling back to plain text: %s", exc)
                fallback = page.get_text("text")
                if fallback.strip():
                    text_items.append((0.0, 0.0, page.rect.width, fallback, None))

            # ── 3. Heading detection: font-size or bold first line ─────────
            # Heading info is attached to each text item so that, after the
            # column-aware sort, headings can be emitted with character
            # offsets matching their actual position in the page text.
            median_size = statistics.median(all_font_sizes) if all_font_sizes else 0.0

            for (
                y0,
                x0,
                x1,
                block_text,
                max_size,
                first_line_text,
                fl_bold,
                fl_total,
            ) in block_info:
                # Size-based: any font in block noticeably larger than median
                is_size_heading = (
                    median_size > 0 and max_size > median_size * profile.size_ratio_threshold
                )

                # Bold-based: first non-empty line of block is sufficiently bold
                # and short enough to be a heading (not a paragraph opening)
                fl_bold_fraction = fl_bold / fl_total if fl_total > 0 else 0.0
                is_bold_heading = (
                    fl_bold_fraction >= profile.bold_fraction_threshold
                    and profile.bold_min_chars <= len(first_line_text) < profile.bold_max_chars
                )

                heading_info: Optional[tuple] = None
                if is_size_heading:
                    ratio = max_size / median_size
                    level = 1 if ratio >= 2.0 else (2 if ratio >= 1.5 else 3)
                    heading_text = re.sub(r"\s+", " ", block_text.strip())
                    if (
                        heading_text
                        and len(heading_text) < 200
                        and not re.fullmatch(r"\d+", heading_text)
                    ):
                        heading_info = (level, heading_text)
                elif is_bold_heading:
                    heading_text = re.sub(r"\s+", " ", first_line_text)
                    # Skip pure-number headings (page numbers, margin section
                    # numbers like "1", "2", "85" that weren't caught by the
                    # header/footer zone filter)
                    if heading_text and not re.fullmatch(r"\d+", heading_text):
                        heading_info = (2, heading_text)

                text_items.append((y0, x0, x1, block_text, heading_info))

            # ── 4. Merge items and build page text ────────────────────────
            combined = text_items + table_items
            gutter = self._detect_column_gutter(combined, page.rect.width)
            if gutter is not None:
                all_items = self._sort_blocks_by_column(combined, gutter, page.rect.width)
                multi_column_pages += 1
            else:
                all_items = sorted(combined, key=lambda x: x[0])

            # Walk sorted items: accumulate per-page offset, emit headings at
            # correct positions, build page_text.  Each item contributes
            # len(text) + 2 chars to the next item's offset (\n\n separator).
            # Items are sanitized *before* offset accumulation so positions
            # remain valid in the final text.
            page_text_parts: List[str] = []
            offset_in_page = 0
            for item in all_items:
                item_text = self._sanitize_chars(item[3])
                item_heading = item[4]
                if item_heading is not None:
                    level, heading_text = item_heading
                    headings.append(
                        {
                            "pos": page_start_pos + offset_in_page,
                            "level": level,
                            "text": heading_text,
                        }
                    )
                page_text_parts.append(item_text)
                offset_in_page += len(item_text) + 2

            page_text = "\n\n".join(page_text_parts)
            if not page_text.strip():
                continue

            logical_num = self._extract_footer_page_number(page)
            text_parts.append(page_text)
            page_map.append([page_start_pos, page_num, logical_num])
            current_pos += len(page_text) + 2  # +2 for \n\n page separator

        doc.close()

        if multi_column_pages:
            logger.info(
                "PDF: detected multi-column layout on %d/%d pages",
                multi_column_pages,
                len(page_map),
            )

        # ── Deduplicate running headers ───────────────────────────────────
        # Heading texts that repeat on many pages are running headers (e.g.
        # "Unit 9", chapter titles in the margin).  Keep the first occurrence
        # and drop the rest so they don't pollute section_path in every chunk.
        repeat_threshold = profile.repeat_threshold
        text_counts: Dict[str, int] = {}
        for h in headings:
            text_counts[h["text"]] = text_counts.get(h["text"], 0) + 1
        seen: set = set()
        filtered: List[Dict[str, Any]] = []
        for h in headings:
            t = h["text"]
            if text_counts[t] >= repeat_threshold:
                if t not in seen:
                    seen.add(t)
                    filtered.append(h)  # keep only first occurrence
            else:
                filtered.append(h)
        headings = filtered

        # Per-item chars were already sanitized inside the page loop so
        # positions in `headings` / `page_map` map straight into full_text.
        # Re-applying sanitize_text_content here would strip leading/trailing
        # whitespace from full_text and silently shift every recorded offset.
        full_text = "\n\n".join(text_parts)

        if len(full_text.strip()) < profile.min_doc_length:
            raise ValueError(
                f"Extracted text is too short (< {profile.min_doc_length} chars). "
                "This PDF may be a scanned document — OCR is not supported yet."
            )

        return full_text, headings, page_map

    def extract_text(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        logger.debug("Extracting text from .pdf file")
        text, _, _ = self._extract_pdf(self._to_bytes(content))
        return text

    def extract_heading_map(self, content: Union[str, bytes]) -> List[Dict[str, Any]]:
        """Extract heading positions from a PDF for structural metadata indexing."""
        _, headings, _ = self._extract_pdf(self._to_bytes(content))
        return headings

    def extract_page_map(self, content: Union[str, bytes]) -> List[List[int]]:
        """Extract page boundary map: [[char_offset, page_number], ...] (1-indexed).

        Each entry marks the character offset in the extracted text where a new
        page begins.  Use _get_page_for_char() in document_processor to look up
        the page number for any chunk by its start_char.
        """
        _, _, page_map = self._extract_pdf(self._to_bytes(content))
        return page_map

    def extract_metadata(self, content: Union[str, bytes], filename: str) -> Dict[str, Any]:
        import fitz

        try:
            doc = fitz.open(stream=self._to_bytes(content), filetype="pdf")
        except Exception as exc:
            logger.warning("Failed to open PDF for metadata extraction: %s", exc)
            return {"file_type": "pdf", "filename": filename}

        meta = doc.metadata or {}
        page_count = doc.page_count
        doc.close()

        return {
            "file_type": "pdf",
            "filename": filename,
            "page_count": page_count,
            "title": meta.get("title") or None,
            "author": meta.get("author") or None,
            "creator": meta.get("creator") or None,
        }

    def extract_all(
        self,
        content: Union[str, bytes],
        filename: str,
        profile_overrides: Optional[Dict[str, Any]] = None,
    ) -> ExtractResult:
        """One-pass PDF extraction: text + headings + page_map + metadata.

        Replaces four separate parses (extract_metadata, extract_text,
        extract_heading_map, extract_page_map) with a single _extract_pdf
        invocation plus a lightweight metadata read.

        Args:
            content: PDF bytes (or str, decoded).
            filename: Original filename — recorded in metadata only.
            profile_overrides: Optional dict with admin/KB overrides for
                ``OVERRIDABLE_PROFILE_FIELDS``.
        """
        content_bytes = self._to_bytes(content)
        text, headings, page_map = self._extract_pdf(content_bytes, profile_overrides)
        metadata = self.extract_metadata(content_bytes, filename)
        return ExtractResult(
            text=text,
            metadata=metadata,
            headings=headings if headings else None,
            page_map=page_map if page_map else None,
        )
