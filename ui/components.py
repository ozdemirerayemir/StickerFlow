"""
StickerFlow — Reusable UI Components
All widgets use the StickerFlow dark theme tokens from ui/theme.py.
"""

import tkinter as tk
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image, ImageTk

from ui.theme import COLORS, FONTS, PAD, RADIUS


# ── Checkerboard Preview Canvas ───────────────────────────────────────────────

class PreviewCanvas(ctk.CTkFrame):
    """
    Displays a preview image on a checkerboard background (to show transparency).
    Optionally overlays a safe-area guide rectangle.
    """

    CHECKER_SIZE = 12
    CHECKER_DARK  = "#1E1E2E"
    CHECKER_LIGHT = "#2A2A3E"

    def __init__(
        self,
        master,
        size: int = 256,
        show_safe_area: bool = False,
        **kwargs,
    ):
        super().__init__(
            master,
            width=size,
            height=size,
            fg_color=COLORS["bg_panel"],
            corner_radius=RADIUS["md"],
            **kwargs,
        )
        self._size = size
        self._show_safe_area = show_safe_area
        self._tk_image: Optional[ImageTk.PhotoImage] = None

        self._canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            bg=self.CHECKER_DARK,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(expand=True, fill="both", padx=0, pady=0)
        self._draw_checkerboard()

    def _draw_checkerboard(self) -> None:
        cs = self.CHECKER_SIZE
        for row in range(0, self._size, cs):
            for col in range(0, self._size, cs):
                if (row // cs + col // cs) % 2 == 0:
                    self._canvas.create_rectangle(
                        col, row, col + cs, row + cs,
                        fill=self.CHECKER_LIGHT,
                        outline="",
                    )

    def set_image(self, pil_image: Optional[Image.Image]) -> None:
        """Display *pil_image* centred on the checkerboard. None clears the preview."""
        # Remove existing image
        self._canvas.delete("preview")
        self._tk_image = None

        if pil_image is None:
            return

        # Scale image to fit canvas while preserving aspect ratio
        thumb = pil_image.copy()
        thumb.thumbnail((self._size, self._size), Image.Resampling.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(thumb)
        x = self._size // 2
        y = self._size // 2
        self._canvas.create_image(x, y, anchor="center", image=self._tk_image, tags="preview")

        if self._show_safe_area:
            self._draw_safe_area_guide()

    def _draw_safe_area_guide(self) -> None:
        self._canvas.delete("safe_area")
        margin = int(self._size * (16 / 512))  # proportional padding
        self._canvas.create_rectangle(
            margin, margin,
            self._size - margin, self._size - margin,
            outline="#6C63FF",
            dash=(4, 4),
            width=1,
            tags="safe_area",
        )

    def set_show_safe_area(self, show: bool) -> None:
        self._show_safe_area = show
        if show:
            self._draw_safe_area_guide()
        else:
            self._canvas.delete("safe_area")


# ── Drop Zone ─────────────────────────────────────────────────────────────────

class DropZone(ctk.CTkFrame):
    """
    Drag-and-drop zone. If tkinterdnd2 is available, enables real DnD.
    Always provides a 'Select File' button as fallback.
    """

    def __init__(
        self,
        master,
        on_file_selected: Callable[[str], None],
        supported_types: str = "Images & Videos",
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=COLORS["bg_input"],
            corner_radius=RADIUS["lg"],
            border_width=2,
            border_color=COLORS["dropzone_border"],
            **kwargs,
        )
        self._callback = on_file_selected
        self._dnd_available = False

        # Layout
        self._icon_label = ctk.CTkLabel(
            self, text="⬇", font=("Inter", 36), text_color=COLORS["accent"]
        )
        self._icon_label.pack(pady=(PAD["lg"], PAD["sm"]))

        self._hint_label = ctk.CTkLabel(
            self,
            text="Drag & drop a file here",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
        )
        self._hint_label.pack()

        self._types_label = ctk.CTkLabel(
            self,
            text=f"Supported: {supported_types}",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        )
        self._types_label.pack(pady=(PAD["xs"], PAD["sm"]))

        self._btn = ctk.CTkButton(
            self,
            text="Select File",
            command=self._open_file_dialog,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=RADIUS["pill"],
            font=FONTS["body_bold"],
            width=140,
        )
        self._btn.pack(pady=(0, PAD["lg"]))

        self._try_enable_dnd()

    def _try_enable_dnd(self) -> None:
        try:
            from tkinterdnd2 import DND_FILES  # type: ignore[import]
            self.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            self.dnd_bind("<<Drop>>", self._on_dnd_drop)  # type: ignore[attr-defined]
            self.dnd_bind("<<DragEnter>>", self._on_drag_enter)  # type: ignore[attr-defined]
            self.dnd_bind("<<DragLeave>>", self._on_drag_leave)  # type: ignore[attr-defined]
            self._dnd_available = True
            self._hint_label.configure(text="Drag & drop a file here")
        except Exception:
            self._hint_label.configure(text="Click below to select a file")

    def _on_dnd_drop(self, event) -> None:
        self._restore_border()
        # tkinterdnd2 wraps paths in braces if they contain spaces
        path = event.data.strip("{}")
        self._callback(path)

    def _on_drag_enter(self, event) -> None:
        self.configure(border_color=COLORS["dropzone_active"])

    def _on_drag_leave(self, event) -> None:
        self._restore_border()

    def _restore_border(self) -> None:
        self.configure(border_color=COLORS["dropzone_border"])

    def _open_file_dialog(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select an image or video",
            filetypes=[
                ("Supported files", "*.png *.jpg *.jpeg *.webp *.bmp *.mp4 *.mov *.webm *.gif"),
                ("Images", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("Videos", "*.mp4 *.mov *.webm *.gif"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._callback(path)

    def set_active_file(self, filename: str) -> None:
        """Update hint text to show the currently loaded file."""
        self._hint_label.configure(text=f"Loaded: {Path(filename).name}")
        self._types_label.configure(text="Drop another file to replace")


# ── Status Badge ──────────────────────────────────────────────────────────────

class StatusBadge(ctk.CTkFrame):
    """Coloured badge label showing OK / WARNING / LIMIT EXCEEDED."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs,
        )
        self._label = ctk.CTkLabel(
            self,
            text="",
            font=FONTS["badge"],
            text_color=COLORS["text_muted"],
            corner_radius=RADIUS["sm"],
        )
        self._label.pack()

    def set_status(self, label: str, color: str) -> None:
        self._label.configure(text=f"  {label}  ", text_color=color)


# ── Progress Section ──────────────────────────────────────────────────────────

class ProgressSection(ctk.CTkFrame):
    """Combines a progress bar and a status message label."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._bar = ctk.CTkProgressBar(
            self,
            mode="determinate",
            progress_color=COLORS["accent"],
            fg_color=COLORS["bg_input"],
            height=8,
            corner_radius=RADIUS["pill"],
        )
        self._bar.set(0)
        self._bar.pack(fill="x", pady=(0, PAD["xs"]))

        self._label = ctk.CTkLabel(
            self,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self._label.pack()

    def set_progress(self, value: float, text: str = "") -> None:
        self._bar.configure(mode="determinate")
        self._bar.set(max(0.0, min(1.0, value)))
        if text:
            self._label.configure(text=text)

    def set_indeterminate(self, text: str = "Processing…") -> None:
        self._bar.configure(mode="indeterminate")
        self._bar.start()
        self._label.configure(text=text)

    def stop_indeterminate(self) -> None:
        self._bar.stop()
        self._bar.configure(mode="determinate")
        self._bar.set(0)

    def reset(self) -> None:
        self.stop_indeterminate()
        self._label.configure(text="")

    def set_text(self, text: str) -> None:
        self._label.configure(text=text)


# ── Section Card ─────────────────────────────────────────────────────────────

class SectionCard(ctk.CTkFrame):
    """A rounded card panel with an optional section heading."""

    def __init__(self, master, title: str = "", **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["bg_panel"],
            corner_radius=RADIUS["lg"],
            **kwargs,
        )
        if title:
            ctk.CTkLabel(
                self,
                text=title,
                font=FONTS["heading"],
                text_color=COLORS["text_secondary"],
                anchor="w",
            ).pack(anchor="w", padx=PAD["md"], pady=(PAD["md"], 0))

    @property
    def inner(self) -> "SectionCard":
        return self


# ── Labelled Separator ────────────────────────────────────────────────────────

class Separator(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            height=1,
            fg_color=COLORS["bg_separator"],
            **kwargs,
        )


# ── Tooltip ──────────────────────────────────────────────────────────────────

class Tooltip:
    """Simple tooltip that appears on hover."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._tip_window: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None) -> None:
        if self._tip_window:
            return
        x = self._widget.winfo_rootx() + 20
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tip_window = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw,
            text=self._text,
            background="#1A1D2E",
            foreground="#F0F2FF",
            font=("Inter", 10),
            relief="flat",
            padx=8,
            pady=4,
        ).pack()

    def _hide(self, _event=None) -> None:
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None
