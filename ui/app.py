"""
StickerFlow — Main Application Window
Assembles all UI panels into the complete application.
All UI operations run on the main thread; heavy work runs in Worker threads
that post results via a queue polled with root.after().
"""

import logging
import os
import platform
import queue
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk
from PIL import Image

from config import (
    APP_NAME,
    APP_VERSION,
    LEGAL_DISCLAIMER,
    RIGHTS_NOTICE,
    STROKE_WIDTH_OPTIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from core.ffmpeg_helper import FFmpegNotFoundError, check_webp_support, find_ffmpeg
from core.image_processor import ProcessingMode, ProcessingOptions, process_image
from core.settings import UserSettings
from core.video_processor import (
    CropMode,
    VideoProcessingOptions,
    VideoProcessingError,
    process_video,
)
from core.webp_validator import validate_animated_webp, validate_static_webp
from ui.components import (
    DropZone,
    PreviewCanvas,
    ProgressSection,
    SectionCard,
    Separator,
    StatusBadge,
    Tooltip,
)
from ui.dialogs import (
    show_error_dialog,
    show_ffmpeg_missing_dialog,
    show_manual_guide_dialog,
    show_rembg_consent_dialog,
    show_warning_dialog,
)
from ui.theme import (
    COLORS,
    CTK_APPEARANCE,
    CTK_THEME,
    FONTS,
    PAD,
    RADIUS,
    STATUS_EXCEED,
    STATUS_NONE,
    STATUS_OK,
    STATUS_WARN,
)
from utils.file_validation import FileValidationError, is_image, is_video, validate_file
from utils.paths import get_log_dir
from utils.threading_worker import MsgType, Worker, WorkerMessage

logger = logging.getLogger("stickerflow.ui")


class StickerFlowApp:
    """
    Main application class. Owns the CTk window and all widget state.
    """

    QUEUE_POLL_MS = 50   # How often to poll the worker queue (ms)

    def __init__(
        self,
        settings: UserSettings,
        msg_queue: queue.Queue,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._settings = settings
        self._msg_queue = msg_queue
        self._log = logger or logging.getLogger("stickerflow.ui")

        # State
        self._selected_file: Optional[Path] = None
        self._is_video: bool = False
        self._output_path: Optional[Path] = None
        self._worker: Optional[Worker] = None
        self._ffmpeg_caps: dict = {}
        self._preview_image: Optional[Image.Image] = None

        # rembg consent tracking
        self._rembg_consent_given: bool = False

        # CTk setup
        ctk.set_appearance_mode(CTK_APPEARANCE)
        ctk.set_default_color_theme(CTK_THEME)

        self._root = ctk.CTk()
        self._root.title(f"{APP_NAME} v{APP_VERSION}")
        self._root.minsize(860, 700)
        self._root.configure(fg_color=COLORS["bg_app"])

        self._build_ui()
        self._probe_ffmpeg()

    def run(self) -> None:
        """Start the Tkinter main loop."""
        self._root.mainloop()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Build the complete window layout."""
        # Root grid: left column (controls), right column (preview)
        self._root.columnconfigure(0, weight=1, minsize=440)
        self._root.columnconfigure(1, weight=0, minsize=300)
        self._root.rowconfigure(0, weight=1)

        # ── Left column ──────────────────────────────────────────────────────
        left = ctk.CTkScrollableFrame(
            self._root,
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_separator"],
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(PAD["md"], PAD["sm"]), pady=PAD["md"])
        left.columnconfigure(0, weight=1)

        self._build_header(left)
        self._build_drop_zone(left)
        self._build_settings_panel(left)
        self._build_process_section(left)
        self._build_result_section(left)
        self._build_footer(left)

        # ── Right column (preview) ────────────────────────────────────────────
        right = ctk.CTkFrame(
            self._root,
            fg_color="transparent",
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(0, PAD["md"]), pady=PAD["md"])
        self._build_preview_panel(right)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self, parent) -> None:
        card = SectionCard(parent)
        card.grid(row=0, column=0, sticky="ew", pady=(0, PAD["sm"]))

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=PAD["md"], pady=(PAD["md"], PAD["xs"]))

        ctk.CTkLabel(
            top,
            text=f"✦ {APP_NAME}",
            font=("Inter", 22, "bold"),
            text_color=COLORS["accent"],
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text=f"v{APP_VERSION}",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(PAD["sm"], 0), pady=(6, 0))

        ctk.CTkLabel(
            card,
            text="WhatsApp-Compatible Sticker Asset Studio",
            font=FONTS["subtitle"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(anchor="w", padx=PAD["md"], pady=(0, PAD["xs"]))

        # Status indicators row
        status_row = ctk.CTkFrame(card, fg_color="transparent")
        status_row.pack(anchor="w", padx=PAD["md"], pady=(0, PAD["md"]))

        self._ffmpeg_indicator = self._make_indicator(status_row, "FFmpeg", "checking…")
        self._rembg_indicator = self._make_indicator(status_row, "rembg", "checking…")

    def _make_indicator(self, parent, label: str, initial: str) -> ctk.CTkLabel:
        frame = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_input"],
            corner_radius=RADIUS["pill"],
        )
        frame.pack(side="left", padx=(0, PAD["sm"]))
        ctk.CTkLabel(
            frame,
            text=f"  {label}: ",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(side="left")
        indicator = ctk.CTkLabel(
            frame,
            text=f"{initial}  ",
            font=("Inter", 11, "bold"),
            text_color=COLORS["text_muted"],
        )
        indicator.pack(side="left")
        return indicator

    # ── Drop Zone ─────────────────────────────────────────────────────────────

    def _build_drop_zone(self, parent) -> None:
        self._drop_zone = DropZone(
            parent,
            on_file_selected=self._on_file_selected,
            supported_types="PNG · JPG · WEBP · BMP · MP4 · MOV · WEBM · GIF",
        )
        self._drop_zone.grid(
            row=1, column=0, sticky="ew",
            pady=(0, PAD["sm"]), ipady=PAD["sm"]
        )

    # ── Settings Panel ────────────────────────────────────────────────────────

    def _build_settings_panel(self, parent) -> None:
        self._settings_card = SectionCard(parent, title="Settings")
        self._settings_card.grid(row=2, column=0, sticky="ew", pady=(0, PAD["sm"]))

        # --- Image settings ---
        self._img_settings = ctk.CTkFrame(
            self._settings_card, fg_color="transparent"
        )
        self._img_settings.pack(fill="x", padx=PAD["md"], pady=(PAD["sm"], 0))

        ctk.CTkLabel(
            self._img_settings,
            text="Processing Mode",
            font=FONTS["body_bold"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, PAD["xs"]))

        self._mode_var = tk.StringVar(value="keep")
        modes = [
            ("Keep background", "keep"),
            ("AI background removal", "remove"),
            ("AI removal + white stroke", "stroke"),
        ]
        for i, (label, val) in enumerate(modes):
            rb = ctk.CTkRadioButton(
                self._img_settings,
                text=label,
                variable=self._mode_var,
                value=val,
                font=FONTS["body"],
                text_color=COLORS["text_primary"],
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                command=self._on_mode_changed,
            )
            rb.grid(row=i + 1, column=0, sticky="w", pady=2)

        # Stroke width
        self._stroke_frame = ctk.CTkFrame(
            self._img_settings, fg_color="transparent"
        )
        self._stroke_frame.grid(row=4, column=0, sticky="w", pady=(PAD["xs"], 0))
        ctk.CTkLabel(
            self._stroke_frame,
            text="Stroke width:",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=(PAD["lg"], PAD["sm"]))
        self._stroke_var = tk.IntVar(value=3)
        for w in STROKE_WIDTH_OPTIONS:
            ctk.CTkRadioButton(
                self._stroke_frame,
                text=f"{w}px",
                variable=self._stroke_var,
                value=w,
                font=FONTS["small"],
                text_color=COLORS["text_primary"],
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
            ).pack(side="left", padx=PAD["sm"])

        # Safe area toggle
        self._safe_area_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self._img_settings,
            text="Apply safe area padding (recommended)",
            variable=self._safe_area_var,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
        ).grid(row=5, column=0, sticky="w", pady=(PAD["sm"], PAD["md"]))

        # --- Video settings (hidden until video is loaded) ---
        self._video_settings = ctk.CTkFrame(
            self._settings_card, fg_color="transparent"
        )
        # Not packed initially; shown when video is loaded

        ctk.CTkLabel(
            self._video_settings,
            text="Video Trim",
            font=FONTS["body_bold"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, PAD["xs"]))

        ctk.CTkLabel(
            self._video_settings, text="Start (s):",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0, sticky="w")
        self._start_var = tk.StringVar(value="0.0")
        ctk.CTkEntry(
            self._video_settings, textvariable=self._start_var,
            width=80, fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        ).grid(row=1, column=1, padx=(PAD["xs"], PAD["md"]))

        ctk.CTkLabel(
            self._video_settings, text="End (s):",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
        ).grid(row=1, column=2, sticky="w")
        self._end_var = tk.StringVar(value="3.0")
        ctk.CTkEntry(
            self._video_settings, textvariable=self._end_var,
            width=80, fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        ).grid(row=1, column=3, padx=PAD["xs"])

        ctk.CTkLabel(
            self._video_settings,
            text="Max 3 seconds  ·  Cover crop fills 512×512  ·  Audio removed automatically",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
            wraplength=380,
            justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(PAD["xs"], PAD["sm"]))

        self._crop_var = tk.StringVar(value="cover")
        ctk.CTkLabel(
            self._video_settings, text="Crop Mode:",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
        ).grid(row=3, column=0, sticky="w", pady=(PAD["xs"], 0))
        ctk.CTkRadioButton(
            self._video_settings, text="Cover crop", variable=self._crop_var,
            value="cover", font=FONTS["small"], text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
        ).grid(row=3, column=1, padx=PAD["xs"])
        self._fit_rb = ctk.CTkRadioButton(
            self._video_settings, text="Fit + pad", variable=self._crop_var,
            value="fit", font=FONTS["small"], text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
        )
        self._fit_rb.grid(row=3, column=2, padx=PAD["xs"], pady=(0, PAD["sm"]))

    # ── Process Section ───────────────────────────────────────────────────────

    def _build_process_section(self, parent) -> None:
        card = SectionCard(parent)
        card.grid(row=3, column=0, sticky="ew", pady=(0, PAD["sm"]))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD["md"], pady=PAD["md"])

        self._create_btn = ctk.CTkButton(
            btn_row,
            text="✦ Create Sticker",
            command=self._start_processing,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=RADIUS["pill"],
            font=("Inter", 14, "bold"),
            height=44,
            state="disabled",
        )
        self._create_btn.pack(side="left", expand=True, fill="x", padx=(0, PAD["sm"]))

        self._cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            command=self._cancel_processing,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["error"],
            corner_radius=RADIUS["pill"],
            font=FONTS["body"],
            height=44,
            width=100,
            state="disabled",
        )
        self._cancel_btn.pack(side="left")

        self._progress = ProgressSection(card)
        self._progress.pack(fill="x", padx=PAD["md"], pady=(0, PAD["md"]))

    # ── Result Section ────────────────────────────────────────────────────────

    def _build_result_section(self, parent) -> None:
        self._result_card = SectionCard(parent, title="Result")
        self._result_card.grid(row=4, column=0, sticky="ew", pady=(0, PAD["sm"]))

        inner = ctk.CTkFrame(self._result_card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD["md"], pady=(PAD["xs"], PAD["md"]))

        # File name + size
        info_row = ctk.CTkFrame(inner, fg_color="transparent")
        info_row.pack(fill="x")

        self._result_name_label = ctk.CTkLabel(
            info_row,
            text="—",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self._result_name_label.pack(side="left")

        self._result_size_label = ctk.CTkLabel(
            info_row,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        )
        self._result_size_label.pack(side="right")

        # Status badge
        self._status_badge = StatusBadge(inner)
        self._status_badge.pack(anchor="w", pady=(PAD["xs"], PAD["sm"]))

        # Action buttons row
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x")

        self._show_folder_btn = ctk.CTkButton(
            btn_row,
            text="Show in Folder",
            command=self._show_in_folder,
            fg_color=COLORS["bg_panel"],
            hover_color=COLORS["bg_panel_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["md"],
            font=FONTS["body"],
            state="disabled",
        )
        self._show_folder_btn.pack(side="left", padx=(0, PAD["sm"]))

        self._clipboard_btn = ctk.CTkButton(
            btn_row,
            text="Copy to Clipboard",
            command=self._copy_to_clipboard,
            fg_color=COLORS["bg_panel"],
            hover_color=COLORS["bg_panel_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["md"],
            font=FONTS["body"],
            state="disabled",
        )
        self._clipboard_btn.pack(side="left", padx=(0, PAD["sm"]))

        self._guide_btn = ctk.CTkButton(
            btn_row,
            text="Import Guide",
            command=lambda: show_manual_guide_dialog(self._root),
            fg_color=COLORS["bg_panel"],
            hover_color=COLORS["bg_panel_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["md"],
            font=FONTS["body"],
        )
        self._guide_btn.pack(side="left")

        # Warnings display
        self._warnings_label = ctk.CTkLabel(
            inner,
            text="",
            font=FONTS["small"],
            text_color=COLORS["warning"],
            wraplength=400,
            justify="left",
            anchor="w",
        )
        self._warnings_label.pack(anchor="w", pady=(PAD["xs"], 0))

    # ── Preview Panel (right column) ──────────────────────────────────────────

    def _build_preview_panel(self, parent) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            parent,
            text="Preview",
            font=FONTS["heading"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, PAD["xs"]))

        self._preview = PreviewCanvas(parent, size=272)
        self._preview.grid(row=1, column=0, sticky="n")

        self._safe_area_check = ctk.CTkCheckBox(
            parent,
            text="Show safe area guide",
            variable=tk.BooleanVar(value=False),
            command=self._toggle_safe_area_guide,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
        )
        self._safe_area_check.grid(row=2, column=0, sticky="w", pady=(PAD["xs"], 0))

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self, parent) -> None:
        footer = ctk.CTkFrame(parent, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", pady=(0, PAD["xs"]))
        ctk.CTkLabel(
            footer,
            text=LEGAL_DISCLAIMER,
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
            wraplength=420,
            justify="left",
        ).pack(anchor="w")

    # ── FFmpeg Probe ──────────────────────────────────────────────────────────

    def _probe_ffmpeg(self) -> None:
        """Check FFmpeg availability in background and update status indicators."""
        def _probe(cancel_event, progress_queue, **_):
            caps = check_webp_support(self._settings.get_ffmpeg_path())
            return caps

        worker = Worker(target=_probe, queue=self._msg_queue)
        worker.start()

        def _poll():
            try:
                while True:
                    msg: WorkerMessage = self._msg_queue.get_nowait()
                    if msg.msg_type == MsgType.RESULT:
                        self._ffmpeg_caps = msg.payload.get("data", {})
                        self._update_ffmpeg_indicator()
                        self._update_rembg_indicator()
                        return
                    elif msg.msg_type == MsgType.DONE:
                        return
            except queue.Empty:
                pass
            self._root.after(200, _poll)

        self._root.after(200, _poll)

    def _update_ffmpeg_indicator(self) -> None:
        caps = self._ffmpeg_caps
        if caps.get("ffmpeg_ok"):
            self._ffmpeg_indicator.configure(
                text="✓ Ready  ", text_color=COLORS["success"]
            )
        else:
            self._ffmpeg_indicator.configure(
                text="✗ Not found  ", text_color=COLORS["error"]
            )
            # Disable video processing options
            if hasattr(self, "_fit_rb"):
                self._fit_rb.configure(state="disabled")
            Tooltip(
                self._ffmpeg_indicator,
                "FFmpeg not found. Install it and restart, or set the path in Settings.",
            )

        # Disable fit+pad if alpha not supported
        if not caps.get("alpha_webp") and hasattr(self, "_fit_rb"):
            self._fit_rb.configure(state="disabled")
            Tooltip(
                self._fit_rb,
                "Fit+pad mode requires alpha WebP support. "
                "Your FFmpeg version may not support it.",
            )

    def _update_rembg_indicator(self) -> None:
        from ai.background_remover import is_rembg_available
        available, reason = is_rembg_available()
        if available:
            self._rembg_indicator.configure(
                text="✓ Ready  ", text_color=COLORS["success"]
            )
        else:
            self._rembg_indicator.configure(
                text="✗ Not installed  ", text_color=COLORS["warning"]
            )
            Tooltip(self._rembg_indicator, reason)

    # ── File Selection ────────────────────────────────────────────────────────

    def _on_file_selected(self, path: str) -> None:
        try:
            validated = validate_file(path)
        except FileValidationError as exc:
            show_error_dialog(
                self._root,
                "Invalid File",
                str(exc),
                log_path=str(get_log_dir() / "stickerflow.log"),
            )
            return

        self._selected_file = validated
        self._is_video = is_video(validated)

        # Update drop zone label
        self._drop_zone.set_active_file(str(validated))

        # Switch settings panel
        if self._is_video:
            self._img_settings.pack_forget()
            self._video_settings.pack(fill="x", padx=PAD["md"], pady=PAD["sm"])
            if not self._ffmpeg_caps.get("ffmpeg_ok"):
                show_error_dialog(
                    self._root,
                    "FFmpeg Required",
                    "Video processing requires FFmpeg. Please install it first.",
                    log_path=str(get_log_dir() / "stickerflow.log"),
                )
        else:
            self._video_settings.pack_forget()
            self._img_settings.pack(fill="x", padx=PAD["md"], pady=PAD["sm"])

        # Load preview
        self._load_preview(validated)

        # Enable create button
        self._create_btn.configure(state="normal")

        logger.info("File selected: %s (video=%s)", validated.name, self._is_video)

    def _load_preview(self, path: Path) -> None:
        """Load a thumbnail preview. For videos, shows the first frame via FFmpeg."""
        try:
            if is_image(path):
                img = Image.open(path)
                img.thumbnail((272, 272), Image.Resampling.LANCZOS)
                self._preview.set_image(img)
            else:
                # Try to extract first frame with FFmpeg
                self._preview.set_image(None)
                self._preview.set_image(
                    self._extract_video_thumbnail(path)
                )
        except Exception as exc:
            logger.warning("Could not load preview: %s", exc)
            self._preview.set_image(None)

    def _extract_video_thumbnail(self, path: Path) -> Optional[Image.Image]:
        import tempfile
        if not self._ffmpeg_caps.get("ffmpeg_ok"):
            return None
        try:
            ffmpeg_bin = find_ffmpeg(self._settings.get_ffmpeg_path())
            with tempfile.TemporaryDirectory() as tmp:
                thumb_path = Path(tmp) / "thumb.png"
                subprocess.run(
                    [ffmpeg_bin, "-y", "-i", str(path), "-vframes", "1",
                     "-q:v", "2", str(thumb_path)],
                    capture_output=True, timeout=10, shell=False,
                )
                if thumb_path.exists():
                    img = Image.open(thumb_path).copy()
                    img.thumbnail((272, 272), Image.Resampling.LANCZOS)
                    return img
        except Exception as exc:
            logger.warning("Video thumbnail extraction failed: %s", exc)
        return None

    # ── Mode Change ───────────────────────────────────────────────────────────

    def _on_mode_changed(self) -> None:
        mode = self._mode_var.get()
        is_stroke = mode == "stroke"
        # Show/hide stroke width selector
        if is_stroke:
            self._stroke_frame.grid()
        else:
            self._stroke_frame.grid_remove()

    def _toggle_safe_area_guide(self) -> None:
        show = self._safe_area_check.cget("variable").get()
        self._preview.set_show_safe_area(show)

    # ── Processing ────────────────────────────────────────────────────────────

    def _start_processing(self) -> None:
        if not self._selected_file:
            return

        # Check rembg consent if needed
        mode = self._mode_var.get()
        if mode in ("remove", "stroke") and not self._rembg_consent_given:
            from ai.background_remover import is_rembg_available
            available, _ = is_rembg_available()
            if available:
                confirmed = show_rembg_consent_dialog(self._root, lambda: None)
                if not confirmed:
                    return
                self._rembg_consent_given = True

        # Determine output path
        targets = self._settings.get_whatsapp_targets()
        output_dir = self._settings.get_output_dir()
        stem = self._selected_file.stem
        self._output_path = output_dir / f"{stem}_sticker.webp"

        # Build processing kwargs
        if self._is_video:
            if not self._ffmpeg_caps.get("ffmpeg_ok"):
                show_error_dialog(
                    self._root, "FFmpeg Required",
                    "FFmpeg must be installed to process video files.",
                )
                return
            kwargs = self._build_video_kwargs(targets)
        else:
            kwargs = self._build_image_kwargs(targets)

        # Start worker
        self._set_processing_state(True)
        self._progress.reset()
        self._warnings_label.configure(text="")

        worker_queue: queue.Queue = queue.Queue()
        self._worker = Worker(
            target=self._processing_target,
            args=(self._selected_file, self._output_path),
            kwargs=kwargs,
            queue=worker_queue,
        )
        self._worker.start()
        self._root.after(self.QUEUE_POLL_MS, lambda: self._poll_worker(worker_queue))

    def _build_image_kwargs(self, targets: dict) -> dict:
        mode_map = {
            "keep": ProcessingMode.KEEP_BACKGROUND,
            "remove": ProcessingMode.REMOVE_BACKGROUND,
            "stroke": ProcessingMode.REMOVE_BACKGROUND_STROKE,
        }
        return {
            "options": ProcessingOptions(
                mode=mode_map[self._mode_var.get()],
                canvas_size=targets["canvas_size"],
                safe_area_size=targets["safe_area_size"],
                padding_px=targets["padding_px"],
                stroke_width=self._stroke_var.get(),
                max_file_kb=targets["static_max_kb"],
                apply_safe_area=self._safe_area_var.get(),
            ),
            "is_video": False,
        }

    def _build_video_kwargs(self, targets: dict) -> dict:
        try:
            start = float(self._start_var.get())
            end = float(self._end_var.get())
        except ValueError:
            start, end = 0.0, 3.0

        crop_mode = (
            CropMode.FIT_PAD
            if self._crop_var.get() == "fit" and self._ffmpeg_caps.get("alpha_webp")
            else CropMode.COVER_CROP
        )

        return {
            "options": VideoProcessingOptions(
                start_sec=start,
                end_sec=end,
                crop_mode=crop_mode,
                canvas_size=targets["canvas_size"],
                fps=targets["animated_default_fps"],
                loop=targets["loop"],
                max_duration_sec=targets["animated_max_duration_sec"],
                max_file_kb=targets["animated_max_kb"],
                ffmpeg_path=self._settings.get_ffmpeg_path(),
                ffprobe_path=self._settings.get_ffprobe_path(),
                alpha_webp_supported=self._ffmpeg_caps.get("alpha_webp", False),
            ),
            "is_video": True,
        }

    @staticmethod
    def _processing_target(
        input_path: Path,
        output_path: Path,
        options=None,
        is_video: bool = False,
        cancel_event=None,
        progress_queue=None,
    ):
        """Static method called in the worker thread."""
        if is_video:
            return process_video(
                input_path, output_path, options,
                cancel_event=cancel_event,
                progress_queue=progress_queue,
            )
        else:
            return process_image(
                input_path, output_path, options,
                cancel_event=cancel_event,
                progress_queue=progress_queue,
            )

    def _poll_worker(self, worker_queue: queue.Queue) -> None:
        """Poll the worker queue and dispatch messages to the UI."""
        try:
            while True:
                msg: WorkerMessage = worker_queue.get_nowait()

                if msg.msg_type == MsgType.PROGRESS:
                    self._progress.set_progress(
                        msg.payload.get("value", 0),
                        msg.payload.get("text", ""),
                    )
                elif msg.msg_type == MsgType.STATUS:
                    self._progress.set_text(msg.payload.get("text", ""))
                elif msg.msg_type == MsgType.RESULT:
                    self._on_processing_complete(msg.payload.get("data"))
                    return
                elif msg.msg_type == MsgType.ERROR:
                    self._on_processing_error(
                        msg.payload.get("message", "Unknown error"),
                        msg.payload.get("detail", ""),
                    )
                    return
                elif msg.msg_type == MsgType.CANCELLED:
                    self._on_processing_cancelled()
                    return
                elif msg.msg_type == MsgType.DONE:
                    self._set_processing_state(False)
                    return
        except queue.Empty:
            pass
        self._root.after(self.QUEUE_POLL_MS, lambda: self._poll_worker(worker_queue))

    def _cancel_processing(self) -> None:
        if self._worker:
            self._worker.cancel()
            self._progress.set_text("Cancelling…")

    def _on_processing_complete(self, result) -> None:
        self._set_processing_state(False)
        self._progress.set_progress(1.0, "Done!")

        if result is None:
            return

        # Validate output
        targets = self._settings.get_whatsapp_targets()
        if self._is_video:
            val = validate_animated_webp(
                result.output_path,
                canvas_size=targets["canvas_size"],
                max_kb=targets["animated_max_kb"],
                max_duration_sec=targets["animated_max_duration_sec"],
            )
        else:
            val = validate_static_webp(
                result.output_path,
                canvas_size=targets["canvas_size"],
                max_kb=targets["static_max_kb"],
            )

        # Determine status badge
        if val.errors:
            badge = STATUS_EXCEED
        elif val.warnings or (hasattr(result, "warnings") and result.warnings):
            badge = STATUS_WARN
        else:
            badge = STATUS_OK

        self._status_badge.set_status(*badge)
        self._result_name_label.configure(text=result.output_path.name)

        max_kb = targets["animated_max_kb"] if self._is_video else targets["static_max_kb"]
        self._result_size_label.configure(
            text=f"{result.size_kb:.1f} KB / {max_kb} KB"
        )

        # Combine warnings
        all_warnings = list(getattr(result, "warnings", [])) + val.warnings + val.errors
        if all_warnings:
            self._warnings_label.configure(text="\n".join(f"⚠ {w}" for w in all_warnings))

        # Enable action buttons
        self._show_folder_btn.configure(state="normal")
        self._output_path = result.output_path

        # Clipboard: only for static images
        if not self._is_video:
            from clipboard import get_clipboard_backend
            cb = get_clipboard_backend()
            if cb.is_supported():
                self._clipboard_btn.configure(state="normal")
            else:
                self._clipboard_btn.configure(state="disabled")
                Tooltip(
                    self._clipboard_btn,
                    "Clipboard image copy is not supported on this system.\n"
                    f"Reason: {cb.unavailable_reason}",
                )

        # Update preview with output
        try:
            img = Image.open(result.output_path)
            self._preview.set_image(img)
        except Exception:
            pass

        logger.info(
            "Processing complete: %s (%.1f KB, status=%s)",
            result.output_path.name, result.size_kb, badge[0],
        )

    def _on_processing_error(self, message: str, detail: str) -> None:
        self._set_processing_state(False)
        self._progress.set_text("Error.")
        show_error_dialog(
            self._root,
            "Processing Failed",
            message,
            detail=detail,
            log_path=str(get_log_dir() / "stickerflow.log"),
        )

    def _on_processing_cancelled(self) -> None:
        self._set_processing_state(False)
        self._progress.reset()
        self._progress.set_text("Processing cancelled.")

    def _set_processing_state(self, processing: bool) -> None:
        state_create = "disabled" if processing else "normal"
        state_cancel = "normal" if processing else "disabled"
        self._create_btn.configure(
            state="disabled" if processing else (
                "normal" if self._selected_file else "disabled"
            )
        )
        self._cancel_btn.configure(state=state_cancel)
        if processing:
            self._progress.set_indeterminate("Preparing…")

    # ── Result Actions ────────────────────────────────────────────────────────

    def _show_in_folder(self) -> None:
        if not self._output_path or not self._output_path.exists():
            return
        folder = str(self._output_path.parent)
        sys_ = platform.system()
        try:
            if sys_ == "Windows":
                subprocess.run(
                    ["explorer", "/select,", str(self._output_path)],
                    shell=False,
                )
            elif sys_ == "Darwin":
                subprocess.run(
                    ["open", "-R", str(self._output_path)],
                    shell=False,
                )
            else:
                subprocess.run(["xdg-open", folder], shell=False)
        except Exception as exc:
            logger.warning("Could not open folder: %s", exc)

    def _copy_to_clipboard(self) -> None:
        if not self._output_path or not self._output_path.exists():
            return
        from clipboard import get_clipboard_backend
        cb = get_clipboard_backend()
        try:
            img = Image.open(self._output_path).convert("RGBA")
            cb.copy_image_png(img)
            self._progress.set_text(
                "Copied! Note: WhatsApp may receive this as a regular image, not a sticker."
            )
        except Exception as exc:
            show_error_dialog(
                self._root,
                "Clipboard Error",
                f"Could not copy to clipboard: {exc}",
                log_path=str(get_log_dir() / "stickerflow.log"),
            )
