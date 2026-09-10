"""
StickerFlow — Modal Dialogs
All dialogs are modal CustomTkinter toplevel windows.
"""

import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk

from ui.theme import COLORS, FONTS, PAD, RADIUS


def _center_on_parent(window: ctk.CTkToplevel, parent: tk.Misc) -> None:
    """Position *window* centred over *parent*."""
    window.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    ww = window.winfo_width()
    wh = window.winfo_height()
    x = px + (pw - ww) // 2
    y = py + (ph - wh) // 2
    window.geometry(f"+{x}+{y}")


# ── FFmpeg Missing Dialog ─────────────────────────────────────────────────────

def show_ffmpeg_missing_dialog(
    parent: tk.Misc,
    on_browse: Callable[[], None],
) -> None:
    """
    Show a blocking dialog explaining that FFmpeg is missing.
    Provides a link to docs and a 'Browse for FFmpeg' button.
    """
    dlg = ctk.CTkToplevel(parent)
    dlg.title("FFmpeg Not Found")
    dlg.resizable(False, False)
    dlg.configure(fg_color=COLORS["bg_app"])
    dlg.grab_set()

    ctk.CTkLabel(
        dlg,
        text="⚠  FFmpeg Not Found",
        font=FONTS["heading"],
        text_color=COLORS["warning"],
    ).pack(padx=PAD["xl"], pady=(PAD["xl"], PAD["sm"]))

    ctk.CTkLabel(
        dlg,
        text=(
            "Video processing requires FFmpeg to be installed.\n"
            "Static image processing will still work.\n\n"
            "Install FFmpeg from https://ffmpeg.org/download.html\n"
            "and add it to your system PATH,\n"
            "or use the button below to locate it manually."
        ),
        font=FONTS["body"],
        text_color=COLORS["text_primary"],
        justify="left",
        wraplength=340,
    ).pack(padx=PAD["xl"], pady=PAD["sm"])

    btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
    btn_frame.pack(padx=PAD["xl"], pady=(PAD["sm"], PAD["xl"]))

    ctk.CTkButton(
        btn_frame,
        text="Browse for FFmpeg…",
        command=lambda: [on_browse(), dlg.destroy()],
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        corner_radius=RADIUS["pill"],
        font=FONTS["body_bold"],
    ).pack(side="left", padx=PAD["sm"])

    ctk.CTkButton(
        btn_frame,
        text="Close",
        command=dlg.destroy,
        fg_color=COLORS["bg_input"],
        hover_color=COLORS["bg_input_hover"],
        corner_radius=RADIUS["pill"],
        font=FONTS["body"],
    ).pack(side="left", padx=PAD["sm"])

    _center_on_parent(dlg, parent)
    dlg.wait_window()


# ── rembg Consent Dialog ──────────────────────────────────────────────────────

def show_rembg_consent_dialog(
    parent: tk.Misc,
    on_confirm: Callable[[], None],
) -> bool:
    """
    Show a consent dialog before the first rembg model use.
    Returns True if user confirmed, False if cancelled.
    """
    confirmed = [False]

    dlg = ctk.CTkToplevel(parent)
    dlg.title("AI Model Download Required")
    dlg.resizable(False, False)
    dlg.configure(fg_color=COLORS["bg_app"])
    dlg.grab_set()

    ctk.CTkLabel(
        dlg,
        text="AI Background Removal",
        font=FONTS["heading"],
        text_color=COLORS["accent"],
    ).pack(padx=PAD["xl"], pady=(PAD["xl"], PAD["sm"]))

    ctk.CTkLabel(
        dlg,
        text=(
            "AI background removal requires downloading the u2net model\n"
            "(approximately 170 MB) on first use.\n\n"
            "An internet connection is required for the initial download.\n"
            "Subsequent uses will work offline.\n\n"
            "Would you like to proceed?"
        ),
        font=FONTS["body"],
        text_color=COLORS["text_primary"],
        justify="left",
        wraplength=340,
    ).pack(padx=PAD["xl"], pady=PAD["sm"])

    btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
    btn_frame.pack(padx=PAD["xl"], pady=(PAD["sm"], PAD["xl"]))

    def _confirm():
        confirmed[0] = True
        dlg.destroy()
        on_confirm()

    ctk.CTkButton(
        btn_frame,
        text="Download & Continue",
        command=_confirm,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        corner_radius=RADIUS["pill"],
        font=FONTS["body_bold"],
    ).pack(side="left", padx=PAD["sm"])

    ctk.CTkButton(
        btn_frame,
        text="Cancel",
        command=dlg.destroy,
        fg_color=COLORS["bg_input"],
        hover_color=COLORS["bg_input_hover"],
        corner_radius=RADIUS["pill"],
        font=FONTS["body"],
    ).pack(side="left", padx=PAD["sm"])

    _center_on_parent(dlg, parent)
    dlg.wait_window()
    return confirmed[0]


# ── Error Dialog ──────────────────────────────────────────────────────────────

def show_error_dialog(
    parent: tk.Misc,
    title: str,
    message: str,
    detail: Optional[str] = None,
    log_path: Optional[str] = None,
) -> None:
    """
    Display an error dialog. Shows a simple message with an optional
    'Show Details' expandable section and a log file hint.
    """
    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.configure(fg_color=COLORS["bg_app"])
    dlg.grab_set()

    ctk.CTkLabel(
        dlg,
        text=f"✕  {title}",
        font=FONTS["heading"],
        text_color=COLORS["error"],
    ).pack(padx=PAD["xl"], pady=(PAD["xl"], PAD["sm"]))

    ctk.CTkLabel(
        dlg,
        text=message,
        font=FONTS["body"],
        text_color=COLORS["text_primary"],
        justify="left",
        wraplength=380,
    ).pack(padx=PAD["xl"], pady=PAD["sm"])

    if log_path:
        ctk.CTkLabel(
            dlg,
            text=f"Details written to log:\n{log_path}",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
            justify="left",
            wraplength=380,
        ).pack(padx=PAD["xl"], pady=(0, PAD["sm"]))

    if detail:
        detail_visible = [False]
        detail_frame = ctk.CTkFrame(dlg, fg_color=COLORS["bg_input"], corner_radius=RADIUS["sm"])

        def _toggle_detail():
            if detail_visible[0]:
                detail_frame.pack_forget()
                detail_visible[0] = False
                toggle_btn.configure(text="▸ Show technical details")
            else:
                detail_frame.pack(padx=PAD["xl"], pady=(0, PAD["sm"]), fill="x")
                detail_visible[0] = True
                toggle_btn.configure(text="▾ Hide technical details")

        toggle_btn = ctk.CTkButton(
            dlg,
            text="▸ Show technical details",
            command=_toggle_detail,
            fg_color="transparent",
            hover_color=COLORS["bg_input"],
            text_color=COLORS["text_secondary"],
            font=FONTS["small"],
            anchor="w",
        )
        toggle_btn.pack(padx=PAD["xl"], anchor="w")

        detail_text = tk.Text(
            detail_frame,
            height=6,
            bg=COLORS["bg_input"],
            fg=COLORS["text_secondary"],
            font=("Courier New", 10),
            relief="flat",
            wrap="word",
            state="disabled",
            bd=0,
        )
        detail_text.pack(padx=PAD["sm"], pady=PAD["sm"], fill="x")
        detail_text.configure(state="normal")
        detail_text.insert("end", detail[-1000:])  # last 1000 chars
        detail_text.configure(state="disabled")

    ctk.CTkButton(
        dlg,
        text="OK",
        command=dlg.destroy,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        corner_radius=RADIUS["pill"],
        font=FONTS["body_bold"],
        width=120,
    ).pack(pady=(PAD["sm"], PAD["xl"]))

    _center_on_parent(dlg, parent)
    dlg.wait_window()


# ── WhatsApp Manual Guide Dialog ──────────────────────────────────────────────

def show_manual_guide_dialog(parent: tk.Misc) -> None:
    """Show the WhatsApp manual import guide as a scrollable dialog."""
    dlg = ctk.CTkToplevel(parent)
    dlg.title("WhatsApp Manual Import Guide")
    dlg.geometry("480x520")
    dlg.configure(fg_color=COLORS["bg_app"])
    dlg.grab_set()

    ctk.CTkLabel(
        dlg,
        text="WhatsApp Manual Import Guide",
        font=FONTS["heading"],
        text_color=COLORS["accent"],
    ).pack(padx=PAD["xl"], pady=(PAD["xl"], PAD["sm"]))

    scroll_frame = ctk.CTkScrollableFrame(
        dlg, fg_color=COLORS["bg_panel"], corner_radius=RADIUS["md"]
    )
    scroll_frame.pack(padx=PAD["md"], pady=PAD["sm"], fill="both", expand=True)

    guide_text = (
        "STATIC STICKER — Possible workflow:\n\n"
        "1. Produce a static sticker in StickerFlow.\n"
        "2. Save the output WebP file.\n"
        "3. If WhatsApp Web/Desktop supports it, try pasting the file\n"
        "   directly into a chat. It may be sent as a sticker.\n"
        "4. If paste does not work as a sticker, transfer the file\n"
        "   to your phone.\n"
        "5. Use a third-party sticker app or WhatsApp's built-in\n"
        "   sticker creator (if available) to import it.\n\n"
        "ANIMATED STICKER — Possible workflow:\n\n"
        "1. Produce an animated WebP in StickerFlow.\n"
        "2. Check: file size ≤ 500 KB, dimensions 512×512, duration ≤ 3 s.\n"
        "3. Transfer the file to your phone.\n"
        "4. Use a sticker pack app or WhatsApp's sticker creator\n"
        "   to add it to a sticker pack.\n"
        "5. If WhatsApp does not accept it directly as a sticker,\n"
        "   this app's scope is limited to asset production.\n\n"
        "⚠  IMPORTANT DISCLAIMER:\n\n"
        "WhatsApp's sticker acceptance behaviour varies by version\n"
        "across Desktop, Web, and Mobile. The outputs produced by\n"
        "StickerFlow must be manually tested in your target\n"
        "WhatsApp environment.\n\n"
        "This application is not officially affiliated with WhatsApp.\n"
        "It only produces sticker-compatible media assets."
    )

    ctk.CTkLabel(
        scroll_frame,
        text=guide_text,
        font=FONTS["body"],
        text_color=COLORS["text_primary"],
        justify="left",
        anchor="nw",
        wraplength=400,
    ).pack(padx=PAD["md"], pady=PAD["md"], anchor="nw")

    ctk.CTkButton(
        dlg,
        text="Close",
        command=dlg.destroy,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        corner_radius=RADIUS["pill"],
        font=FONTS["body_bold"],
        width=120,
    ).pack(pady=PAD["md"])

    _center_on_parent(dlg, parent)
    dlg.wait_window()


# ── Warning Dialog ────────────────────────────────────────────────────────────

def show_warning_dialog(
    parent: tk.Misc,
    title: str,
    message: str,
    on_confirm: Optional[Callable] = None,
    confirm_text: str = "Continue Anyway",
    cancel_text: str = "Cancel",
) -> bool:
    """
    Show a warning with Confirm / Cancel buttons.
    Returns True if user clicked Confirm.
    """
    confirmed = [False]

    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.configure(fg_color=COLORS["bg_app"])
    dlg.grab_set()

    ctk.CTkLabel(
        dlg,
        text=f"⚠  {title}",
        font=FONTS["heading"],
        text_color=COLORS["warning"],
    ).pack(padx=PAD["xl"], pady=(PAD["xl"], PAD["sm"]))

    ctk.CTkLabel(
        dlg,
        text=message,
        font=FONTS["body"],
        text_color=COLORS["text_primary"],
        justify="left",
        wraplength=360,
    ).pack(padx=PAD["xl"], pady=PAD["sm"])

    btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
    btn_frame.pack(padx=PAD["xl"], pady=(PAD["sm"], PAD["xl"]))

    def _confirm():
        confirmed[0] = True
        if on_confirm:
            on_confirm()
        dlg.destroy()

    ctk.CTkButton(
        btn_frame,
        text=confirm_text,
        command=_confirm,
        fg_color=COLORS["warning"],
        hover_color=COLORS["accent_hover"],
        text_color="#000000",
        corner_radius=RADIUS["pill"],
        font=FONTS["body_bold"],
    ).pack(side="left", padx=PAD["sm"])

    ctk.CTkButton(
        btn_frame,
        text=cancel_text,
        command=dlg.destroy,
        fg_color=COLORS["bg_input"],
        hover_color=COLORS["bg_input_hover"],
        corner_radius=RADIUS["pill"],
        font=FONTS["body"],
    ).pack(side="left", padx=PAD["sm"])

    _center_on_parent(dlg, parent)
    dlg.wait_window()
    return confirmed[0]
