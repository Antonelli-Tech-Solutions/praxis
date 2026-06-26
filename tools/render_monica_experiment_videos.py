"""Render short Monica experiment demo videos from local screenshots.

The videos are intentionally self-contained MP4 slide videos with caption text
and a silent audio track. Add ElevenLabs narration later in a local-only step if
voiceover is required; do not put API keys in this repository.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = REPO_ROOT / "docs" / "monica" / "screenshots" / "demo-capture-2026-06-25"
OUTPUT_DIR = REPO_ROOT / "docs" / "monica" / "videos" / "experiment-video-capture-2026-06-25"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
ZOOM_FPS = 8
SLIDE_SECONDS = 11
ZOOM_SLIDE_SECONDS = 15
VIDEO_ASPECT = WIDTH / HEIGHT


Crop = tuple[float, float, float, float]

DATA_SOURCE_CROP: Crop = (0.55, 0.00, 0.94, 0.28)
CANDIDATE_DETAIL_CROP: Crop = (0.42, 0.31, 0.95, 0.78)
CANDIDATE_AUDIT_CROP: Crop = (0.42, 0.38, 0.95, 0.95)
APPROVAL_CONFIRM_CROP: Crop = (0.08, 0.25, 0.90, 0.66)
APPROVED_RESULT_CROP: Crop = (0.05, 0.05, 0.95, 0.56)
CONTRADICTION_PAIR_CROP: Crop = (0.29, 0.22, 0.94, 0.58)
CONTRADICTION_PAIR_WIDE_CROP: Crop = (0.10, 0.20, 0.92, 0.58)
CONTRADICTION_RESULT_CROP: Crop = (0.25, 0.10, 0.94, 0.48)
DEFERRED_CONTRADICTION_CROP: Crop = (0.25, 0.30, 0.94, 0.66)
EVAL_MODAL_CROP: Crop = (0.15, 0.23, 0.85, 0.83)


@dataclass(frozen=True)
class Highlight:
    rect: Crop
    label: str
    tone: str = "info"


@dataclass(frozen=True)
class Slide:
    title: str
    caption: str
    screenshot: str | None = None
    focus_crop: Crop | None = None
    highlights: tuple[Highlight, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExperimentVideo:
    number: int
    slug: str
    title: str
    slides: tuple[Slide, ...]
    target_label: str = "2:50"

    @property
    def filename(self) -> str:
        return f"experiment-{self.number:02d}-{self.slug}.mp4"


EXPERIMENTS: tuple[ExperimentVideo, ...] = (
    ExperimentVideo(
        1,
        "cold-vs-knowledge-injected-agent-run",
        "Cold vs Knowledge-Injected Agent Run",
        (
            Slide("Experiment 1", "Cold run vs active human-approved context"),
            Slide(
                "Eval handoff",
                "Measure corrections, repeated failures, time, tokens, and success rate.",
                "09-load-eval-data-handoff.png",
                EVAL_MODAL_CROP,
            ),
            Slide(
                "Approved evidence",
                "Only evidence-linked approved knowledge should influence the next run.",
                "03-cand1-provenance-confidence.png",
                CANDIDATE_DETAIL_CROP,
            ),
            Slide(
                "Human gate result",
                "Promotion changes a reviewed lesson into reusable active knowledge.",
                "05-after-confirm-approve.png",
                APPROVED_RESULT_CROP,
            ),
            Slide("Outcome", "Monica controls what may enter the context; Dominic proves whether it improves the next run."),
        ),
    ),
    ExperimentVideo(
        2,
        "autonomous-memory-vs-human-gated-knowledge",
        "Autonomous Memory vs Human-Gated Knowledge",
        (
            Slide("Experiment 2", "Fast memory is not the same as trustworthy memory."),
            Slide("Review before reuse", "The dashboard exposes evidence and confidence before a lesson becomes active.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Explicit approval", "A reviewer confirms promotion instead of allowing silent auto-save.", "04-approval-action.png", APPROVAL_CONFIRM_CROP),
            Slide("Conflict surfaced", "Contradictions are shown as reviewable pairs before they compound.", "06-contradictions-review.png", CONTRADICTION_PAIR_CROP),
            Slide("Outcome", "Gate high-impact reusable knowledge where one bad lesson can affect future runs."),
        ),
    ),
    ExperimentVideo(
        3,
        "proposed-only-vs-active-only-injection",
        "Proposed-Only vs Active-Only Injection",
        (
            Slide("Experiment 3", "Proposed knowledge is staged; active knowledge is reusable."),
            Slide("Staged candidate", "A proposed row can be inspected, but should not be injected yet.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Promotion checkpoint", "The reviewer explicitly confirms the state change.", "04-approval-action.png", APPROVAL_CONFIRM_CROP),
            Slide("Active after approval", "After promotion, the lesson becomes eligible for future context.", "05-after-confirm-approve.png", APPROVED_RESULT_CROP),
            Slide("Outcome", "The invariant passes when proposed-only injection is blocked and active-only injection is allowed."),
        ),
    ),
    ExperimentVideo(
        4,
        "low-confidence-promotion-test",
        "Low-Confidence Promotion Test",
        (
            Slide("Experiment 4", "Weak evidence should require a deliberate checkpoint."),
            Slide("Inspectable score", "Reviewers need to see frequency, recency, and breadth before approval.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Confirm promotion", "Promotion should be explicit, especially when confidence is low.", "04-approval-action.png", APPROVAL_CONFIRM_CROP),
            Slide("Audit the action", "If approved, the decision should become traceable state history.", "05-after-confirm-approve.png", CANDIDATE_AUDIT_CROP),
            Slide("Outcome", "Confidence is a warning signal, not a hidden auto-promotion rule."),
        ),
    ),
    ExperimentVideo(
        5,
        "contradiction-resolution-test",
        "Contradiction-Resolution Test",
        (
            Slide("Experiment 5", "Visible conflict beats silent conflict."),
            Slide("Review the pair", "The dashboard surfaces cand_9 and cand_16 as a contradiction pair.", "06-contradictions-review.png", CONTRADICTION_PAIR_CROP),
            Slide("Keep or resolve", "A reviewer can keep one lesson, reject the rival, or write a resolution.", "07-after-keep-this-cand9.png", CONTRADICTION_RESULT_CROP),
            Slide("Defer if needed", "If evidence is insufficient, deferral is better than a forced bad decision.", "08-deferred-contradiction.png", DEFERRED_CONTRADICTION_CROP),
            Slide("Outcome", "The pass condition is no hidden conflict in reusable memory."),
        ),
    ),
    ExperimentVideo(
        6,
        "provenance-trust-test",
        "Provenance Trust Test",
        (
            Slide("Experiment 6", "A lesson with evidence is reviewable; a lesson without evidence is just advice."),
            Slide("Source trace", "Candidates carry logs/...jsonl:line provenance for traceability.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Data source context", "The reviewer should know whether data is mock, local, or hosted.", "02-data-source-dashboard.png", DATA_SOURCE_CROP),
            Slide("Audit evidence", "Pipeline and review events create an evidence trail.", "03-cand1-provenance-confidence.png", CANDIDATE_AUDIT_CROP),
            Slide("Outcome", "Trust rises when reviewers can verify where a lesson came from."),
        ),
    ),
    ExperimentVideo(
        7,
        "confidence-breakdown-test",
        "Confidence-Breakdown Test",
        (
            Slide("Experiment 7", "Replace black-box confidence with inspectable evidence."),
            Slide("Break down the score", "Frequency, recency, and breadth let reviewers challenge the number.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Act after inspection", "Approval happens after the reviewer understands the score.", "04-approval-action.png", APPROVAL_CONFIRM_CROP),
            Slide("Audit the state", "The decision becomes part of the candidate history.", "05-after-confirm-approve.png", CANDIDATE_AUDIT_CROP),
            Slide("Outcome", "The reviewer should be able to explain the score before acting."),
        ),
    ),
    ExperimentVideo(
        8,
        "human-gate-latency-vs-safety-tradeoff",
        "Human-Gate Latency vs Safety Tradeoff",
        (
            Slide("Experiment 8", "A slower review can be cheaper than a bad reusable lesson."),
            Slide("Review adds latency", "The human gate requires inspection and confirmation.", "04-approval-action.png", APPROVAL_CONFIRM_CROP),
            Slide("Safety catches conflicts", "Contradictions and weak evidence are caught before reuse.", "06-contradictions-review.png", CONTRADICTION_PAIR_CROP),
            Slide("Approved result", "The right metric is time saved after avoiding bad promotions.", "05-after-confirm-approve.png", APPROVED_RESULT_CROP),
            Slide("Outcome", "Use the human gate where risk compounds across future actions."),
        ),
    ),
    ExperimentVideo(
        9,
        "audit-trail-accountability-test",
        "Audit-Trail Accountability Test",
        (
            Slide("Experiment 9", "Governance requires a record of who approved what and why."),
            Slide("Pipeline history", "Candidates start with distilled and scored audit entries.", "03-cand1-provenance-confidence.png", CANDIDATE_AUDIT_CROP),
            Slide("Promotion record", "Human promotion changes state and should be explainable later.", "05-after-confirm-approve.png", CANDIDATE_AUDIT_CROP),
            Slide("Resolution record", "Contradiction decisions also need visible accountability.", "07-after-keep-this-cand9.png", CONTRADICTION_RESULT_CROP),
            Slide("Outcome", "The dashboard is both a review surface and an accountability layer."),
        ),
    ),
    ExperimentVideo(
        10,
        "mock-vs-live-api-decision-safety",
        "Mock vs Live API Decision Safety",
        (
            Slide("Experiment 10", "Stable rehearsal and live mutation need different safety rules."),
            Slide("Show the source", "The dashboard should clearly identify mock, local, or hosted data.", "02-data-source-dashboard.png", DATA_SOURCE_CROP),
            Slide("Disposable mutations", "Live promotion or rejection should use disposable records only.", "04-approval-action.png", APPROVAL_CONFIRM_CROP),
            Slide("Eval source clarity", "Eval panels should be clear about configured or unavailable sources.", "09-load-eval-data-handoff.png", EVAL_MODAL_CROP),
            Slide("Outcome", "The pass condition is source transparency and no risky live mutation."),
        ),
    ),
    ExperimentVideo(
        11,
        "data-source-fallback-experiment",
        "Data-Source Fallback Experiment",
        (
            Slide("Experiment 11", "Fallback is useful only when it is honest."),
            Slide("Source state", "The UI should show API URL, source mode, and contract context.", "02-data-source-dashboard.png", DATA_SOURCE_CROP),
            Slide("Mock clarity", "If mock fixtures are used, reviewers should not mistake them for live data.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Eval availability", "Unavailable eval data should be explicit, not silent.", "09-load-eval-data-handoff.png", EVAL_MODAL_CROP),
            Slide("Outcome", "The dashboard should be resilient and transparent at the same time."),
        ),
    ),
    ExperimentVideo(
        12,
        "eval-visibility-experiment",
        "Eval Visibility Experiment",
        (
            Slide("Experiment 12", "Approval needs measurement after reuse."),
            Slide("Gate evidence", "Monica controls which lessons become active.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Eval handoff", "The dashboard should expose or link future outcome evidence.", "09-load-eval-data-handoff.png", EVAL_MODAL_CROP),
            Slide("Measured proof", "Corrections, repeated failures, time, tokens, and success rate need eval support.", "09-load-eval-data-handoff.png", EVAL_MODAL_CROP),
            Slide("Outcome", "The pass condition is visibility into what happened after injection."),
        ),
    ),
    ExperimentVideo(
        13,
        "cross-domain-transfer-framing",
        "Cross-Domain Transfer Framing",
        (
            Slide("Experiment 13", "This is framing, not proof across every domain."),
            Slide("Reusable pattern", "Logs, candidate lessons, evidence, approval, and measured reuse can transfer.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Shared risk", "Research, writing, data, and operations can all compound bad lessons.", "06-contradictions-review.png", CONTRADICTION_PAIR_CROP),
            Slide("Need measurement", "Each domain still needs its own outcome evidence.", "09-load-eval-data-handoff.png", EVAL_MODAL_CROP),
            Slide("Outcome", "Generalize the safeguard pattern, not unvalidated claims."),
        ),
    ),
    ExperimentVideo(
        14,
        "community-impact-simulation",
        "Community-Impact Simulation",
        (
            Slide("Experiment 14", "This is a simulation boundary, not a deployed public-service claim."),
            Slide("Traceability", "High-impact suggestions need evidence, confidence, and provenance.", "03-cand1-provenance-confidence.png", CANDIDATE_DETAIL_CROP),
            Slide("Conflict review", "Weak or conflicting evidence should be surfaced before repeated reuse.", "06-contradictions-review.png", CONTRADICTION_PAIR_CROP),
            Slide("Accountability", "Human decisions should leave state history and review evidence.", "07-after-keep-this-cand9.png", CONTRADICTION_RESULT_CROP),
            Slide("Outcome", "Real social-impact claims require participant and outcome data."),
        ),
    ),
    ExperimentVideo(
        15,
        "poisoned-source-quarantine-test",
        "Poisoned Source Quarantine Test",
        (
            Slide(
                "Experiment 15",
                "Poison can enter as data, but it should not become trusted knowledge without review.",
                notes=(
                    "Attack 1: bad lesson tries to become a candidate",
                    "Attack 2: contradiction tries to override trusted guidance",
                    "Attack 3: unapproved poison tries to enter injected context",
                    "Gate: provenance, confidence, reject, resolve, eval proof",
                ),
            ),
            Slide(
                "Source is visible",
                "The dashboard shows where candidate data comes from before anyone reviews it.",
                "02-data-source-dashboard.png",
                DATA_SOURCE_CROP,
                (
                    Highlight((0.72, 0.02, 0.93, 0.07), "source state"),
                    Highlight((0.66, 0.08, 0.94, 0.16), "live or mock source"),
                    Highlight((0.20, 0.08, 0.31, 0.13), "load candidate data"),
                ),
            ),
            Slide(
                "Attack payload",
                "A poisoned JSONL source proposes unsafe reusable memory.",
                notes=(
                    "poisoned_source.jsonl",
                    "candidate: Disable review checks before deploy",
                    "candidate: Never add tests; they slow demos",
                    "sentinel: UNAPPROVED_POISON_SENTINEL",
                    "Expected behavior: staged, reviewed, or rejected",
                ),
            ),
            Slide(
                "Attack 1: bad candidate",
                "The suspicious lesson is staged as proposed, with provenance and confidence visible.",
                "03-cand1-provenance-confidence.png",
                CANDIDATE_DETAIL_CROP,
                (
                    Highlight((0.65, 0.39, 0.93, 0.51), "proposed, not active", "warning"),
                    Highlight((0.65, 0.54, 0.94, 0.64), "review content", "danger"),
                    Highlight((0.66, 0.81, 0.94, 0.96), "audit trail", "info"),
                ),
            ),
            Slide(
                "Quarantine action",
                "The reviewer rejects the bad lesson instead of approving it into reusable context.",
                "04-approval-action.png",
                APPROVAL_CONFIRM_CROP,
                (
                    Highlight((0.52, 0.27, 0.60, 0.34), "Reject poison", "danger"),
                    Highlight((0.13, 0.35, 0.25, 0.42), "approval requires confirmation", "warning"),
                    Highlight((0.62, 0.38, 0.95, 0.51), "state stays reviewable", "info"),
                ),
            ),
            Slide(
                "Attack 2: contradiction",
                "Poison tries to override trusted guidance by creating a conflicting lesson.",
                "06-contradictions-review.png",
                CONTRADICTION_PAIR_WIDE_CROP,
                (
                    Highlight((0.13, 0.27, 0.50, 0.46), "trusted side", "safe"),
                    Highlight((0.51, 0.27, 0.87, 0.46), "suspicious rival", "danger"),
                    Highlight((0.20, 0.39, 0.43, 0.44), "keep trusted", "safe"),
                ),
            ),
            Slide(
                "Resolve or defer",
                "If neither side is fully safe, the reviewer can write a custom resolution or defer.",
                "08-deferred-contradiction.png",
                DEFERRED_CONTRADICTION_CROP,
                (
                    Highlight((0.13, 0.59, 0.88, 0.70), "custom resolution area", "info"),
                    Highlight((0.45, 0.73, 0.59, 0.79), "resolve with answer", "safe"),
                    Highlight((0.45, 0.78, 0.58, 0.83), "defer decision", "warning"),
                ),
            ),
            Slide(
                "Attack 3: context injection",
                "Dominic's eval handoff checks that unapproved poison never reaches future context.",
                notes=(
                    "FORBID: UNAPPROVED_POISON_SENTINEL",
                    "ALLOW: ACTIVE_HUMAN_APPROVED_SENTINEL",
                    "Measure: corrections, repeated failures, time, tokens, success rate",
                    "Result: rejected or proposed poison is not injected",
                ),
            ),
            Slide(
                "Eval proof hook",
                "The eval area is where the team proves the gate worked after candidate review.",
                "09-load-eval-data-handoff.png",
                EVAL_MODAL_CROP,
                (
                    Highlight((0.20, 0.42, 0.32, 0.50), "Monica cases", "info"),
                    Highlight((0.60, 0.53, 0.74, 0.60), "load evals", "safe"),
                    Highlight((0.74, 0.53, 0.89, 0.60), "run pipeline", "warning"),
                ),
            ),
            Slide(
                "Only safe lessons activate",
                "Human-approved knowledge can become active; poisoned candidates remain rejected or staged.",
                "05-after-confirm-approve.png",
                APPROVED_RESULT_CROP,
                (
                    Highlight((0.13, 0.13, 0.91, 0.19), "approved safe lesson", "safe"),
                    Highlight((0.62, 0.30, 0.90, 0.44), "active candidate detail", "safe"),
                    Highlight((0.62, 0.73, 0.91, 0.95), "audit evidence", "info"),
                ),
            ),
            Slide(
                "Team boundary",
                "Matthew provides candidates, Monica gates them, and Dominic proves future-run impact.",
                notes=(
                    "Matthew: ingest, candidate API, graph persistence",
                    "Monica: review UI, provenance, confidence, reject, resolve",
                    "Dominic: eval proof, replay metrics, integration evidence",
                    "Claim: poison is processed before it can harm the pipeline",
                ),
            ),
            Slide(
                "Outcome",
                "Poisoned source data is contained by staged review, human rejection, contradiction resolution, and eval evidence.",
                notes=(
                    "Bad candidate: rejected before activation",
                    "Conflicting candidate: surfaced before reuse",
                    "Context poison: forbidden from injected context",
                    "Human gate: auditable decision before pipeline harm",
                ),
            ),
        ),
        target_label="3:00",
    ),
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


TITLE_FONT = font(56, bold=True)
SUBTITLE_FONT = font(34, bold=True)
BODY_FONT = font(34)
SMALL_FONT = font(24)


def tone_palette(tone: str) -> tuple[str, tuple[int, int, int, int], tuple[int, int, int, int]]:
    if tone == "danger":
        return "#c2410c", (255, 241, 235, 230), (194, 65, 12, 245)
    if tone == "safe":
        return "#047857", (236, 253, 245, 230), (4, 120, 87, 245)
    if tone == "warning":
        return "#a16207", (254, 252, 232, 230), (161, 98, 7, 245)
    return "#1d4ed8", (239, 246, 255, 230), (29, 78, 216, 245)


def text_block(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, *, width: int, font_obj: ImageFont.ImageFont, fill: str) -> None:
    x, y = xy
    line_height = int(font_obj.size * 1.28) if hasattr(font_obj, "size") else 38
    for paragraph in text.split("\n"):
        for line in wrap(paragraph, width=width):
            draw.text((x, y), line, font=font_obj, fill=fill)
            y += line_height
        y += int(line_height * 0.35)


def draw_notes_panel(draw: ImageDraw.ImageDraw, slide: Slide, *, y_start: int = 540) -> None:
    if not slide.notes:
        return

    card_width = 790
    card_height = 92
    gap_x = 42
    gap_y = 28
    start_x = 120
    for index, note in enumerate(slide.notes):
        col = index % 2
        row = index // 2
        x = start_x + col * (card_width + gap_x)
        y = y_start + row * (card_height + gap_y)
        tone = "info"
        lowered = note.lower()
        if "attack" in lowered or "poison" in lowered or "forbid" in lowered:
            tone = "danger"
        elif "gate" in lowered or "allow" in lowered or "human" in lowered or "safe" in lowered:
            tone = "safe"
        elif "expected" in lowered or "measure" in lowered or "claim" in lowered:
            tone = "warning"
        color, fill, outline = tone_palette(tone)
        draw.rounded_rectangle((x, y, x + card_width, y + card_height), radius=14, fill=fill, outline=outline, width=3)
        draw.text((x + 24, y + 25), note, font=SMALL_FONT, fill=color)


def annotate_source(image: Image.Image, slide: Slide) -> Image.Image:
    if not slide.highlights:
        return image

    annotated = image.convert("RGBA")
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for highlight in slide.highlights:
        color, fill, outline = tone_palette(highlight.tone)
        x1 = int(highlight.rect[0] * image.width)
        y1 = int(highlight.rect[1] * image.height)
        x2 = int(highlight.rect[2] * image.width)
        y2 = int(highlight.rect[3] * image.height)
        highlight_fill = (fill[0], fill[1], fill[2], 54)
        draw.rounded_rectangle((x1, y1, x2, y2), radius=10, fill=highlight_fill, outline=outline, width=5)
        tag_w = max(170, min(430, 32 + len(highlight.label) * 12))
        tag_h = 42
        tag_y1 = max(8, y1 - tag_h - 8)
        draw.rounded_rectangle((x1, tag_y1, x1 + tag_w, tag_y1 + tag_h), radius=10, fill=outline)
        draw.text((x1 + 15, tag_y1 + 8), highlight.label, font=SMALL_FONT, fill="#ffffff")
        draw.line((x1 + 20, tag_y1 + tag_h, x1 + 20, y1), fill=outline, width=4)
    annotated.alpha_composite(overlay)
    return annotated.convert("RGB")


def fit_image(path: Path, box: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail(box, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", box, "#f3f6f4")
    x = (box[0] - image.width) // 2
    y = (box[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def adjust_crop_to_aspect(crop: Crop, width: int, height: int) -> tuple[int, int, int, int]:
    left = crop[0] * width
    top = crop[1] * height
    right = crop[2] * width
    bottom = crop[3] * height
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    crop_width = max(1.0, right - left)
    crop_height = max(1.0, bottom - top)
    current_aspect = crop_width / crop_height

    if current_aspect > VIDEO_ASPECT:
        crop_height = crop_width / VIDEO_ASPECT
    else:
        crop_width = crop_height * VIDEO_ASPECT

    left = center_x - crop_width / 2
    right = center_x + crop_width / 2
    top = center_y - crop_height / 2
    bottom = center_y + crop_height / 2

    if left < 0:
        right -= left
        left = 0
    if right > width:
        left -= right - width
        right = width
    if top < 0:
        bottom -= top
        top = 0
    if bottom > height:
        top -= bottom - height
        bottom = height

    return (
        max(0, int(round(left))),
        max(0, int(round(top))),
        min(width, int(round(right))),
        min(height, int(round(bottom))),
    )


def padded_source(image: Image.Image) -> tuple[Image.Image, int, int]:
    source_aspect = image.width / image.height
    if source_aspect < VIDEO_ASPECT:
        padded_width = int(round(image.height * VIDEO_ASPECT))
        padded_height = image.height
    else:
        padded_width = image.width
        padded_height = int(round(image.width / VIDEO_ASPECT))

    canvas = Image.new("RGB", (padded_width, padded_height), "#eef4f1")
    offset_x = (padded_width - image.width) // 2
    offset_y = (padded_height - image.height) // 2
    canvas.paste(image, (offset_x, offset_y))
    return canvas, offset_x, offset_y


def interpolate_crop(
    start: tuple[int, int, int, int],
    end: tuple[int, int, int, int],
    progress: float,
) -> tuple[int, int, int, int]:
    eased = 1 - (1 - progress) ** 3
    return tuple(int(round(a + (b - a) * eased)) for a, b in zip(start, end))


def draw_lower_third(image: Image.Image, video: ExperimentVideo, slide: Slide, index: int) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, WIDTH, 82), fill=(20, 52, 43, 226))
    draw.text((52, 24), "PRAXIS - Monica Dashboard & Human Gate", font=SMALL_FONT, fill="#c7f4d8")

    draw.rounded_rectangle((50, 852, 820, 1036), radius=18, fill=(255, 255, 255, 232), outline=(165, 188, 178, 245), width=3)
    draw.text((82, 878), video.title, font=SMALL_FONT, fill="#0f2f26")
    draw.text((82, 920), slide.title, font=SMALL_FONT, fill="#14342b")
    text_block(draw, (82, 958), slide.caption, width=48, font_obj=SMALL_FONT, fill="#263d36")
    draw.text((470, 1000), f"Experiment {video.number:02d} | Slide {index + 1} of {len(video.slides)}", font=SMALL_FONT, fill="#52655e")
    image.alpha_composite(overlay)


def render_zoom_title_frame(video: ExperimentVideo, slide: Slide, index: int, out_path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#eef4f1")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 120), fill="#14342b")
    draw.text((70, 38), "PRAXIS - Monica Dashboard & Human Gate", font=SMALL_FONT, fill="#c7f4d8")
    draw.text((120, 295), video.title, font=TITLE_FONT, fill="#0f2f26")
    text_block(draw, (120, 390), slide.caption, width=52, font_obj=BODY_FONT, fill="#243b34")
    draw_notes_panel(draw, slide)
    draw.text((120, 945), f"Experiment {video.number:02d} | Slide {index + 1} of {len(video.slides)} | Target max: {video.target_label}", font=SMALL_FONT, fill="#52655e")
    image.save(out_path)


def render_zoom_slide_frames(
    video: ExperimentVideo,
    slide: Slide,
    index: int,
    work_dir: Path,
    first_frame: int,
) -> int:
    frame_count = ZOOM_FPS * ZOOM_SLIDE_SECONDS
    screenshot = slide.screenshot
    if not screenshot:
        frame_path = work_dir / f"frame_{first_frame:05d}.jpg"
        render_zoom_title_frame(video, slide, index, frame_path)
        for offset in range(1, frame_count):
            next_path = work_dir / f"frame_{first_frame + offset:05d}.jpg"
            next_path.write_bytes(frame_path.read_bytes())
        return first_frame + frame_count

    source = Image.open(SCREENSHOT_DIR / screenshot).convert("RGB")
    source = annotate_source(source, slide)
    padded, offset_x, offset_y = padded_source(source)
    start_crop = (0, 0, padded.width, padded.height)
    raw_focus = slide.focus_crop or (0.08, 0.08, 0.92, 0.82)
    focus = adjust_crop_to_aspect(raw_focus, source.width, source.height)
    end_crop = (
        focus[0] + offset_x,
        focus[1] + offset_y,
        focus[2] + offset_x,
        focus[3] + offset_y,
    )

    for offset in range(frame_count):
        raw_progress = offset / max(1, frame_count - 1)
        if raw_progress < 0.16:
            progress = 0.0
        else:
            progress = (raw_progress - 0.16) / 0.84
        crop = interpolate_crop(start_crop, end_crop, progress)
        frame = padded.crop(crop).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).convert("RGBA")
        draw_lower_third(frame, video, slide, index)
        frame.convert("RGB").save(
            work_dir / f"frame_{first_frame + offset:05d}.jpg",
            quality=90,
            subsampling=0,
        )

    return first_frame + frame_count


def render_zoom_video(video: ExperimentVideo, work_dir: Path, output_dir: Path) -> Path:
    next_frame = 0
    for index, slide in enumerate(video.slides):
        next_frame = render_zoom_slide_frames(video, slide, index, work_dir, next_frame)

    output_path = output_dir / video.filename
    command = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(ZOOM_FPS),
        "-i",
        str(work_dir / "frame_%05d.jpg"),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest",
        "-r",
        str(FPS),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(output_path),
    ]
    subprocess.run(command, check=True, cwd=REPO_ROOT)
    return output_path


def render_slide(video: ExperimentVideo, slide: Slide, index: int, out_path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#eef4f1")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, WIDTH, 114), fill="#14342b")
    draw.text((70, 30), "PRAXIS - Monica Dashboard & Human Gate", font=SMALL_FONT, fill="#c7f4d8")
    draw.text((70, 685), video.title, font=TITLE_FONT, fill="#0f2f26")

    if slide.screenshot:
        screenshot_path = SCREENSHOT_DIR / slide.screenshot
        if screenshot_path.exists():
            shot = fit_image(screenshot_path, (WIDTH - 140, 540))
            image.paste(shot, (70, 130))
            draw.rectangle((70, 130, WIDTH - 70, 670), outline="#6c7f77", width=3)
    else:
        draw.rounded_rectangle((180, 180, WIDTH - 180, 610), radius=16, fill="#dce9e3", outline="#6c7f77", width=3)
        text_block(
            draw,
            (250, 290),
            video.title,
            width=40,
            font_obj=TITLE_FONT,
            fill="#0f2f26",
        )

    draw.rounded_rectangle((70, 768, WIDTH - 70, 985), radius=16, fill="#ffffff", outline="#b4c6be", width=3)
    draw.text((105, 795), slide.title, font=SUBTITLE_FONT, fill="#14342b")
    text_block(draw, (105, 850), slide.caption, width=82, font_obj=BODY_FONT, fill="#243b34")

    footer = f"Experiment {video.number:02d} | Slide {index + 1} of {len(video.slides)} | Target max: {video.target_label}"
    draw.text((70, 1022), footer, font=SMALL_FONT, fill="#52655e")
    image.save(out_path)


def render_video(video: ExperimentVideo, work_dir: Path, output_dir: Path) -> Path:
    return render_zoom_video(video, work_dir, output_dir)

    slide_paths: list[Path] = []
    for index, slide in enumerate(video.slides):
        path = work_dir / f"{video.number:02d}-{index:02d}.png"
        render_slide(video, slide, index, path)
        slide_paths.append(path)

    concat_path = work_dir / f"{video.number:02d}-concat.txt"
    with concat_path.open("w", encoding="utf-8") as fh:
        for path in slide_paths:
            normalized = path.as_posix()
            fh.write(f"file '{normalized}'\n")
            fh.write(f"duration {SLIDE_SECONDS}\n")
        fh.write(f"file '{slide_paths[-1].as_posix()}'\n")

    output_path = output_dir / video.filename
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest",
        "-r",
        str(FPS),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(output_path),
    ]
    subprocess.run(command, check=True, cwd=REPO_ROOT)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, action="append", help="Render only selected experiment number(s).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    selected = set(args.only or [])
    with tempfile.TemporaryDirectory(prefix="monica-experiment-videos-") as tmp:
        work_dir = Path(tmp)
        for video in EXPERIMENTS:
            if selected and video.number not in selected:
                continue
            output = render_video(video, work_dir, OUTPUT_DIR)
            rel = output.relative_to(REPO_ROOT)
            print(f"rendered {rel}")


if __name__ == "__main__":
    main()
