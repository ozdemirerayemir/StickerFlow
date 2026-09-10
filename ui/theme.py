"""
StickerFlow — Dark Theme & Style Tokens
Centralises all colours, fonts, and spacing used across the UI.
"""

# ── Colour palette ────────────────────────────────────────────────────────────
COLORS = {
    # Backgrounds
    "bg_app":          "#0F1117",   # main window background
    "bg_panel":        "#1A1D2E",   # card / panel background
    "bg_panel_hover":  "#1F2236",
    "bg_input":        "#12151F",   # input fields, drop zones
    "bg_input_hover":  "#1C2035",
    "bg_separator":    "#252840",

    # Accent
    "accent":          "#6C63FF",   # primary purple
    "accent_hover":    "#7D75FF",
    "accent_dark":     "#4E47CC",

    # Semantic
    "success":         "#4ADE80",   # green — OK status
    "warning":         "#FACC15",   # yellow — WARNING status
    "error":           "#F87171",   # red — LIMIT EXCEEDED / error
    "info":            "#60A5FA",   # blue — informational

    # Text
    "text_primary":    "#F0F2FF",
    "text_secondary":  "#9B9EC8",
    "text_muted":      "#5C6082",
    "text_disabled":   "#3E4160",

    # Borders
    "border":          "#2D3158",
    "border_active":   "#6C63FF",

    # Drop zone
    "dropzone_border": "#3D4170",
    "dropzone_active": "#6C63FF",
}

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONTS = {
    "title":        ("Inter", 20, "bold"),
    "subtitle":     ("Inter", 13, "normal"),
    "heading":      ("Inter", 14, "bold"),
    "body":         ("Inter", 12, "normal"),
    "body_bold":    ("Inter", 12, "bold"),
    "small":        ("Inter", 11, "normal"),
    "mono":         ("Courier New", 11, "normal"),
    "label":        ("Inter", 11, "normal"),
    "badge":        ("Inter", 10, "bold"),
}

# ── Spacing ───────────────────────────────────────────────────────────────────
PAD = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
}

# ── Corner radii ──────────────────────────────────────────────────────────────
RADIUS = {
    "sm": 6,
    "md": 10,
    "lg": 16,
    "pill": 999,
}

# ── Status badge labels & colours ─────────────────────────────────────────────
STATUS_OK      = ("OK",             COLORS["success"])
STATUS_WARN    = ("WARNING",        COLORS["warning"])
STATUS_EXCEED  = ("LIMIT EXCEEDED", COLORS["error"])
STATUS_NONE    = ("",               COLORS["text_muted"])

# ── CustomTkinter appearance ───────────────────────────────────────────────────
CTK_APPEARANCE = "dark"
CTK_THEME      = "dark-blue"
