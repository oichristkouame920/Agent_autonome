"""Thèmes et personnalisation visuelle locale pour AgentLocal V12.5.

Ce module ne touche jamais aux permissions ni aux actions. Il transforme uniquement
les préférences d'apparence de l'hôte en palette Tkinter sûre.
"""
from __future__ import annotations

import copy
import re

BASE_THEME = {
    "bg": "#F6F8FC", "sidebar": "#101A2E", "sidebar_hover": "#192946", "sidebar_active": "#214A7B",
    "card": "#FFFFFF", "card_alt": "#FBFCFF", "border": "#E4E9F2", "text": "#172033", "muted": "#68758A",
    "accent": "#356AE6", "accent_hover": "#2859C6", "accent_2": "#6D5CE7", "teal": "#0E9384", "gold": "#D69E2E",
    "success": "#16845B", "warning": "#B86E16", "danger": "#B43C39", "soft_accent": "#EBF1FF",
    "soft_lavender": "#F0EEFF", "soft_teal": "#E8F7F4", "soft_gold": "#FFF7E4", "soft_success": "#EAF8F1",
    "soft_warning": "#FFF4E5", "soft_neutral": "#F1F4F8", "quote_bg": "#FFF9EC", "conversation": "#FCFDFF",
}

THEMES = {
    "agentlocal": {},
    "minimal": {"bg": "#F8FAFC", "sidebar": "#1F2937", "sidebar_hover": "#374151", "sidebar_active": "#4B5563", "accent": "#334155", "accent_hover": "#1E293B", "accent_2": "#64748B", "border": "#E5E7EB"},
    "blue_night": {"bg": "#F4F7FB", "sidebar": "#0B1739", "sidebar_hover": "#132A59", "sidebar_active": "#1E4E8C", "accent": "#2563EB", "accent_hover": "#1D4ED8", "accent_2": "#4F46E5"},
    "dark": {"bg": "#0F172A", "sidebar": "#020617", "sidebar_hover": "#111827", "sidebar_active": "#1E3A5F", "card": "#111827", "card_alt": "#172033", "border": "#263244", "text": "#F1F5F9", "muted": "#94A3B8", "accent": "#60A5FA", "accent_hover": "#3B82F6", "accent_2": "#A78BFA", "soft_accent": "#172554", "soft_lavender": "#2E1065", "soft_teal": "#042F2E", "soft_gold": "#422006", "soft_success": "#052E16", "soft_warning": "#431407", "soft_neutral": "#1E293B", "quote_bg": "#1C1917", "conversation": "#0B1220"},
    "nature": {"bg": "#F4F8F4", "sidebar": "#153A32", "sidebar_hover": "#245447", "sidebar_active": "#2F6B58", "accent": "#2F855A", "accent_hover": "#276749", "accent_2": "#4C7A62", "teal": "#238C77", "soft_accent": "#E6F4EA", "soft_teal": "#E3F3EE", "quote_bg": "#F7F4E8"},
    "violet": {"bg": "#F8F6FC", "sidebar": "#24123D", "sidebar_hover": "#38205A", "sidebar_active": "#54327E", "accent": "#7C3AED", "accent_hover": "#6D28D9", "accent_2": "#A855F7", "soft_accent": "#F2EAFE", "soft_lavender": "#F3E8FF"},
    "enterprise": {"bg": "#F5F7FA", "sidebar": "#17212B", "sidebar_hover": "#253444", "sidebar_active": "#31516F", "accent": "#28638F", "accent_hover": "#214F72", "accent_2": "#4B6F8C", "border": "#DDE4EA"},
    "windows": {"bg": "#F3F3F3", "sidebar": "#202020", "sidebar_hover": "#2B2B2B", "sidebar_active": "#005A9E", "accent": "#0078D4", "accent_hover": "#005A9E", "accent_2": "#4CC2FF", "border": "#E0E0E0"},
}

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _hex(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text.upper() if _HEX.fullmatch(text) else fallback


def build_palette(appearance: dict | None) -> dict:
    appearance = appearance if isinstance(appearance, dict) else {}
    name = str(appearance.get("theme", "agentlocal")).strip().lower()
    palette = copy.deepcopy(BASE_THEME)
    palette.update(THEMES.get(name, THEMES["agentlocal"]))
    accent_raw = str(appearance.get("accent_color", "") or "").strip().upper()
    sidebar_raw = str(appearance.get("sidebar_color", "") or "").strip().upper()
    card_raw = str(appearance.get("card_color", "") or "").strip().upper()
    # Les anciennes préférences V12.4 contiennent les couleurs du thème AgentLocal.
    # Lorsqu'un autre thème est choisi, ces valeurs historiques sont considérées
    # comme des valeurs par défaut et ne doivent pas écraser le nouveau preset.
    if name == "agentlocal" or accent_raw not in {"", BASE_THEME["accent"].upper()}:
        palette["accent"] = _hex(accent_raw, palette["accent"])
    if name == "agentlocal" or sidebar_raw not in {"", BASE_THEME["sidebar"].upper()}:
        palette["sidebar"] = _hex(sidebar_raw, palette["sidebar"])
    if name == "agentlocal" or card_raw not in {"", BASE_THEME["card"].upper()}:
        palette["card"] = _hex(card_raw, palette["card"])
    # Les couleurs dérivées restent sûres et lisibles; elles peuvent être personnalisées
    # dans une future version sans faire dépendre la sécurité du thème.
    return palette


def theme_names() -> tuple[str, ...]:
    return tuple(THEMES)
