"""Reads a photo of a paper attendance sheet with Claude vision.

The model returns a typed `ExtractedSheet` (structured output), which
`attendance_service.scan_sheet` then validates and saves. Keeping the Claude call here,
behind `read_sheet_image`, lets tests swap in a fake reader.
"""

import base64
import io
import logging
from collections.abc import Callable

import anthropic
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.errors import AppError, ExternalServiceError

logger = logging.getLogger("app.sheet_reader")

MAX_IMAGE_EDGE = 2400  # px; keeps handwriting legible while staying under API image limits


# --------------------------------------------------------------------------- output schema


class ExtractedColumn(BaseModel):
    subject_code: str = Field(description="Subject code from the header, e.g. 'APP II'")
    subject_name: str | None = Field(description="Full subject name from the legend, if shown")
    date: str = Field(description="Date of the column as YYYY-MM-DD")
    session: int = Field(description="Session number under the subject (1 or 2)")


class ExtractedStudent(BaseModel):
    row_number: int
    student_id: str = Field(description="Student ID exactly as printed, keeping leading zeros")
    full_name_khmer: str | None
    full_name_latin: str
    gender: str | None = Field(description="'M' or 'F' as printed")
    marks: list[str] = Field(description="One entry per column: '✓', 'P', '' (blank) or '?'")


class ExtractedSheet(BaseModel):
    faculty: str | None
    program: str | None
    major: str | None
    academic_year: int | None = Field(description="'Year' on the sheet, e.g. 4")
    semester: int | None = Field(description="1 or 2 (Roman numerals converted)")
    week: int | None
    room: str | None
    columns: list[ExtractedColumn]
    students: list[ExtractedStudent]
    notes: str | None = Field(description="Anything unclear or unusual about the sheet")


SheetReader = Callable[[bytes], ExtractedSheet]


PROMPT = """You are reading a photo of a university weekly attendance sheet. Transcribe it exactly.

Header: copy faculty, program, major, year (as academic_year), semester (Roman numerals -> 1/2),
week number and room.

Columns: the mark grid is grouped by date (DD/MM/YY on the sheet; output YYYY-MM-DD, year 20YY),
each with a subject code and session numbers (usually 1 and 2). Output one column per
date+subject+session, left to right. Leave out any column that is shaded/greyed out (no class) or
where no student has any mark. Take subject_name from the abbreviation legend if present.

Students: one entry per numbered row that has a student; skip empty numbered rows.
- student_id: copy every digit exactly, including leading zeros. Do not guess.
- Names: copy the Khmer and Latin names as printed.
- gender: 'M' or 'F' as printed.
- marks: exactly one entry per output column, in the same order:
  '✓' for any tick or check mark, 'P' for a letter P (any colour),
  '' for an empty cell, '?' if you genuinely cannot tell.

Use notes to mention anything you were unsure about (row number and column)."""


# --------------------------------------------------------------------------- image prep


def prepare_image(data: bytes) -> tuple[str, str]:
    """Validate, auto-rotate and downscale the photo; return (media_type, base64 data)."""
    try:
        image = Image.open(io.BytesIO(data))
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise AppError("The file is not a readable image (use JPG, PNG or WebP).",
                       code="invalid_image") from exc

    image = image.convert("RGB")
    image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return "image/jpeg", base64.standard_b64encode(buffer.getvalue()).decode("ascii")


# --------------------------------------------------------------------------- Claude call


def read_sheet_image(data: bytes) -> ExtractedSheet:
    settings = get_settings()
    media_type, image_b64 = prepare_image(data)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None, max_retries=2)

    try:
        response = client.beta.messages.parse(
            model=settings.attendance_scan_model,
            max_tokens=20000,
            timeout=300,
            output_config={"effort": "high"},
            # On a safety refusal, the API retries on a recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
            output_format=ExtractedSheet,
        )
    except anthropic.AuthenticationError as exc:
        raise AppError(
            "The Anthropic API key was rejected. Check ANTHROPIC_API_KEY in .env and restart the backend.",
            code="scan_not_configured",
        ) from exc
    except TypeError as exc:
        # Raised by the SDK before sending when no credentials can be found.
        if "authentication method" not in str(exc):
            raise
        raise AppError(
            "Sheet scanning is not configured: set ANTHROPIC_API_KEY in .env and restart the backend.",
            code="scan_not_configured",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise ExternalServiceError("The reading service is busy. Try again in a minute.",
                                   code="scan_rate_limited") from exc
    except anthropic.BadRequestError as exc:
        logger.warning("Claude rejected the scan request: %s", exc.message)
        raise ExternalServiceError("The image could not be processed. Try a clearer or smaller photo.",
                                   code="scan_rejected") from exc
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        logger.exception("Claude request failed")
        raise ExternalServiceError("Could not reach the reading service. Try again later.",
                                   code="scan_unavailable") from exc

    logger.info("Scan request %s: stop_reason=%s usage=%s",
                response._request_id, response.stop_reason, response.usage)

    if response.stop_reason == "refusal":
        raise ExternalServiceError("The reading service declined this image.", code="scan_refused")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise ExternalServiceError("The sheet could not be read completely. Try a clearer photo.",
                                   code="scan_incomplete")
    return response.parsed_output


def get_sheet_reader() -> SheetReader:
    """FastAPI dependency selected by SHEET_READER; tests override it with a fake reader."""
    if get_settings().sheet_reader.lower() == "claude":
        return read_sheet_image
    from app.services.offline_reader import read_sheet_offline

    return read_sheet_offline
