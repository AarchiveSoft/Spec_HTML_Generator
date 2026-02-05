# specs_editor.py
# Requirements: Python 3.9+  ->  pip install PySide6 requests packaging

import sys, os
import threading
import re
import json
import html as _html
from datetime import datetime
from PySide6.QtCore import Qt, QSize, QTimer, Signal, QPoint, Slot, QThread, QStandardPaths, QUrl
from PySide6.QtGui import (
    QAction, QKeySequence, QTextCharFormat, QTextCursor, QTextListFormat,
    QFont, QColor, QGuiApplication, QFontDatabase, QClipboard, QPalette, QIcon, QPixmap, QDesktopServices, QMovie
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QColorDialog, QCheckBox, QFrame, QSizePolicy, QScrollArea, QGridLayout,
    QToolButton, QSpacerItem, QProgressDialog, QDialog, QDialogButtonBox, QLayout
)

# Web scraping deps (optional until used)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup, Comment

# Translation deps (optional until used)
try:
    import argostranslate.package as argos_package
    import argostranslate.translate as argos_translate
    ARGOS_AVAILABLE = True
except ImportError:
    ARGOS_AVAILABLE = False

try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False

try:
    import langid
    LANGID_AVAILABLE = True
except ImportError:
    LANGID_AVAILABLE = False

# Import auto-update module (graceful fallback if not available)
try:
    import auto_update
    AUTO_UPDATE_AVAILABLE = True
except ImportError:
    AUTO_UPDATE_AVAILABLE = False

APP_TITLE = "Claudias Listenwichtel"

DEFAULT_HEADER_LEFT  = "Kategorie"
DEFAULT_HEADER_RIGHT = "Details"
DEFAULT_EXPORT_TITLE = "Technische_Daten"
ACCENT = "#006B8D"
HEADER_ROW_STYLE = "fill"  # "text" or "fill"
SCRAPE_HEADLESS = False
SCRAPE_HEADLESS_MODE = "old"  # "new" or "old"

SECTION_ROW_TEXT_COLOR = ACCENT if HEADER_ROW_STYLE == "text" else "#ffffff"
SECTION_ROW_BG_COLOR = "transparent" if HEADER_ROW_STYLE == "text" else ACCENT

EXPORT_HEADER_TEXT_COLOR = ACCENT if HEADER_ROW_STYLE == "text" else "#ffffff"
EXPORT_HEADER_BG_COLOR = "transparent" if HEADER_ROW_STYLE == "text" else ACCENT
EXPORT_HEADER_FONT_SIZE_PX = 16
EXPORT_SECTION_FONT_SIZE_PX = 16
EXPORT_HEADER_PADDING_Y_PX = 10
EXPORT_SECTION_PADDING_Y_PX = 10
EXPORT_HEADER_CENTER = False

SCRAPE_EXCLUDE_KEYS = {
    "eans inkl. varianten und bundles",
    "unverb. preisempfehlung*",
    "internet-preis",
    "optionales zubehör",
}
SCRAPE_EXCLUDE_SECTIONS = {
    "weiterführende links",
}

ARGOS_MODEL_DIR = "argos_models"
ARGOS_LANG_FROM = "de"
ARGOS_LANG_TO = "fr"
LANG_DETECT_MIN_PROB = 0.3
FASTTEXT_MODEL_DIR = "fasttext_models"
FASTTEXT_LANG_MODEL = "lid.176.ftz"
TRANSLATION_DEBUG = os.environ.get("SPEC_TRANSLATE_DEBUG") == "1"
GERMAN_HINT_RE = re.compile(
    r"(?:\b(und|oder|mit|für|ohne|nicht|kein|keine|einen|eine|der|die|das|von|bis|nach|über|unter|bei|auf|aus|mehr|weniger|zwischen|funktion|sucher|optisch|extern|betriebsbereit|farbkanal|synchronzeit|kleinbild|gesicht)\b|[äöüÄÖÜß])",
    re.IGNORECASE
)
FR_POST_EDITS = {
    "petite image": "plein format",
    "crop facteur": "facteur de recadrage",
}

PROTECTED_TOKEN_PATTERNS = [
    r"\b[A-Z0-9][A-Z0-9\-_/\.]{2,}\b",  # acronyms/model codes (USB, HDMI, NP-FZ100)
    r"\bISO\s?\d+(?:[\-–]\d+)?\b",
    r"\b\d+(?:[.,]\d+)?\s?(?:mm|cm|m|µm|nm|°|s|EV|W|Wh|mAh|GHz|MHz|K|Bit|bits|B/s|BpS|fps)\b",
    r"\b\d+(?:[.,]\d+)?\s?[x×]\s?\d+(?:[.,]\d+)?\b",  # resolutions
    r"\b\d+(?:[.,]\d+)?\s?(?:MBit/s|Mbit/s|Mb/s|Mbps|Gb/s|Gbps)\b",
    r"\b(?:RAW|JPG|JPEG|HEIF|PNG|TIFF|DCF|EXIF)\b",
    r"\b(?:Wi-Fi|WLAN|Bluetooth|NFC|USB|HDMI|LAN)\b",
    r"\b(?:UHS\s?I|UHS\s?II|CFexpress|SDHC|SDXC|SD)\b",
    r"\b(?:XAVC|H\.264|H\.265|HEVC|AVC)\b",
    r"\b(?:NTSC|PAL)\b",
]

def _build_protected_regex():
    return re.compile("|".join(f"(?:{p})" for p in PROTECTED_TOKEN_PATTERNS), re.IGNORECASE)

_PROTECTED_RE = _build_protected_regex()

def _mask_protected_tokens(text: str) -> tuple[str, list[str]]:
    if not text:
        return text, []
    tokens = []
    def _repl(m):
        tokens.append(m.group(0))
        return f"<<T{len(tokens)-1}>>"
    return _PROTECTED_RE.sub(_repl, text), tokens

def _unmask_protected_tokens(text: str, tokens: list[str]) -> str:
    if not tokens:
        return text
    out = text
    for i, tok in enumerate(tokens):
        out = out.replace(f"<<T{i}>>", tok)
    return out

SPEC_TABLE_CSS = """
<style type="text/css">
table.specs{width:100%;border-collapse:collapse;font-family:Arial, Helvetica, sans-serif;font-size:14px;}
.specs th,.specs td{border:1px solid #ddd;padding:8px;vertical-align:top;box-sizing:border-box;}
.specs th{background:#f5f5f5;text-align:right;width:30%;}
.specs th.category, .specs thead th:last-child{text-align:left;}
.specs tr:nth-child(even){background:#fafafa;}
.specs thead th{
    color: __HEADER_COLOR__;
    font-size: __HEADER_FONT_PX__px;
    padding-top: __HEADER_PAD_Y_PX__px;
    padding-bottom: __HEADER_PAD_Y_PX__px;
    background: __HEADER_BG__;
}
.specs thead th:first-child{text-align:__HEADER_ALIGN_LEFT__;}
.specs thead th:last-child{text-align:__HEADER_ALIGN_RIGHT__;}

/* Make all rich content inherit the table font/size */
.specs td,.specs td *{font-family:inherit !important;font-size:inherit !important;line-height:1.4;}

/* Lists stay inside the cell border and wrap nicely */
.specs td ul,.specs td ol{margin:6px 0;padding-left:1.25em;list-style-position:outside;}
.specs td li{margin:0.15em 0;}
.specs td p{margin:0.3em 0;}
.specs td *{max-width:100%;word-break:break-word;overflow-wrap:anywhere;}
</style>
""".strip()
SPEC_TABLE_CSS = (SPEC_TABLE_CSS
    .replace("__HEADER_COLOR__", EXPORT_HEADER_TEXT_COLOR)
    .replace("__HEADER_FONT_PX__", str(EXPORT_HEADER_FONT_SIZE_PX))
    .replace("__HEADER_PAD_Y_PX__", str(EXPORT_HEADER_PADDING_Y_PX))
    .replace("__HEADER_BG__", EXPORT_HEADER_BG_COLOR)
    .replace("__HEADER_ALIGN_LEFT__", "center" if EXPORT_HEADER_CENTER else "right")
    .replace("__HEADER_ALIGN_RIGHT__", "center" if EXPORT_HEADER_CENTER else "left")
)
SPEC_TABLE_CSS = SPEC_TABLE_CSS.replace(
    "</style>",
    f".specs tr.section th.section{{text-align:center;font-weight:700;"
    f"color:{SECTION_ROW_TEXT_COLOR};background:{SECTION_ROW_BG_COLOR};"
    f"font-size:{EXPORT_SECTION_FONT_SIZE_PX}px;"
    f"padding-top:{EXPORT_SECTION_PADDING_Y_PX}px;"
    f"padding-bottom:{EXPORT_SECTION_PADDING_Y_PX}px;}}\n</style>"
)


# ---------- helpers / theme ----------
def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def try_set_modern_app_font():
    families = set(QFontDatabase.families())
    for name in ("Aptos", "Segoe UI Variable", "Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue"):
        if name in families:
            QGuiApplication.setFont(QFont(name, 10))
            return

def apply_brand_theme(app: QApplication):
    pal = app.palette()
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.Link, QColor(ACCENT))
    pal.setColor(QPalette.LinkVisited, QColor(ACCENT).darker(110))
    app.setPalette(pal)
    app.setStyleSheet(f"""
    QLabel[class="section"] {{
        color: {ACCENT}; font-weight: 700; font-size: 20px; padding: 6px 0;
    }}
    QFrame[frameShape="4"] {{
        color: {ACCENT};
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                                    stop:0 rgba(0,0,0,0),
                                    stop:0.5 {ACCENT},
                                    stop:1 rgba(0,0,0,0));
        min-height: 1px; max-height: 1px; border: none; margin: 10px 0;
    }}
    QToolBar#formatToolbar {{
        border: none; padding: 8px 10px; border-right: 1px solid rgba(0,0,0,0.08);
    }}
    QToolBar#formatToolbar QToolButton {{
        padding: 6px 12px; border-radius: 8px;
        border: 1px solid {ACCENT}; background: {ACCENT};
        color: #ffffff; margin: 6px 0; font-weight: 600;
    }}
    QToolBar#formatToolbar QToolButton:hover  {{ background: rgba(0,108,140,0.92); }}
    QToolBar#formatToolbar QToolButton:pressed{{ background: rgba(0,108,140,0.84); }}

    .KVTable QLineEdit, .KVTable QTextEdit {{
        border: 1px solid rgba(0,0,0,0.18);
        border-radius: 0; padding: 8px 10px; background: palette(base);
    }}
    .KVTable QLineEdit:focus, .KVTable QTextEdit:focus {{
        border: 2px solid {ACCENT}; outline: none;
    }}
    .HeaderCell {{ font-weight: 700; background: #f5f5f5; }}
    .InputRow QLineEdit, .InputRow QTextEdit {{
        background: rgba(0,108,140,0.06);
        border: 1px solid rgba(0,108,140,0.30);
    }}

    /* Primary (big) */
    QPushButton#primaryButton {{
        border: 1px solid {ACCENT}; background: rgba(0,108,140,0.10);
        color: palette(text); font-weight: 600; padding: 10px 16px; border-radius: 10px;
    }}
    QPushButton#primaryButton:hover  {{ background: rgba(0,108,140,0.18); }}
    QPushButton#primaryButton:pressed{{ background: rgba(0,108,140,0.24); }}

    /* Small accent buttons (for paste buttons) */
    QPushButton#accentSmall {{
        border: 1px solid {ACCENT};
        background: {ACCENT};
        color: #ffffff;
        font-weight: 600;
        padding: 6px 10px;   /* smaller than primary */
        border-radius: 8px;
        margin: 0;
    }}
    QPushButton#accentSmall:hover  {{ background: rgba(0,108,140,0.92); }}
    QPushButton#accentSmall:pressed{{ background: rgba(0,108,140,0.84); }}

    QToolButton.rowAction {{
        border: 1px solid rgba(0,0,0,0.18);
        border-radius: 6px; padding: 6px 8px; background: palette(button);
        margin-left: 6px;
    }}
    QToolButton.rowAction:hover  {{ background: rgba(0,0,0,0.04); }}
    QToolButton.rowAction:pressed{{ background: rgba(0,0,0,0.08); }}

    QScrollBar:vertical {{ width: 12px; background: transparent; margin: 2px; }}
    QScrollBar::handle:vertical {{ min-height: 24px; border-radius: 6px; background: rgba(0,0,0,0.18); }}
    QScrollBar::handle:vertical:hover {{ background: rgba(0,0,0,0.28); }}

    QStatusBar {{ border-top: 1px solid rgba(0,0,0,0.08); }}
    /* Panel around format toolbar */
    QFrame#formatPanel {{
        border: 1px solid #006c8c;
        border-radius: 12px;
        background: rgba(0,108,140,0.10);
    }}
    
    /* Panel header pill */
    QLabel#formatPanelTitle {{
        color: #ffffff;
        background: #006c8c;
        font-weight: 700;
        padding: 6px 10px;
        border-radius: 8px;
    }}
    
    /* Keep toolbar tidy inside the panel */
    QFrame#formatPanel QToolBar#formatToolbar {{
        border: none;
        padding: 6px 4px;
    }}
    QFrame#formatPanel QToolBar#formatToolbar QToolButton {{
        margin: 4px 0;
    }}
    /* Category rows in the editor */
    .CategoryCell {{
        font-weight: 700;
        background: rgba(0,108,140,0.14);
        border: 1px solid rgba(0,108,140,0.35);
        padding: 8px 10px;
    }}

    /* Section/header rows in the editor */
    .SectionCell {{
        font-weight: 700;
        text-align: center;
        color: {SECTION_ROW_TEXT_COLOR};
        background: {SECTION_ROW_BG_COLOR};
        border: 1px solid rgba(0,108,140,0.35);
        padding: 8px 10px;
    }}
    
    /* Category rows in exported HTML (table) */
    .specs tr.cat th.category {{
        background:#e9f3f6;
        border-color:#c8dde5;
        text-transform:none;       /* change to uppercase if you prefer */
        letter-spacing:.2px;
    }}
    """)

def make_separator() -> QFrame:
    line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); return line

def _escape_html(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

def _normalize_for_paste(t: str) -> str:
    # Map ß/ẞ → ss/SS (idempotent)
    return (t or "").replace("ß", "ss").replace("ẞ", "SS")

def _load_fr_translations():
    # Optional external mapping file: {"Deutsch": "Francais", ...}
    candidates = [
        resource_path("translations_fr.json"),
        os.path.join(os.path.abspath("."), "translations_fr.json"),
    ]
    path = next((p for p in candidates if p and os.path.exists(p)), None)
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): str(v) for k, v in (data or {}).items() if str(k)}
    except Exception:
        return {}

def _load_fr_post_edits():
    path = resource_path("translations_fr_post.json")
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): str(v) for k, v in (data or {}).items() if str(k)}
    except Exception:
        return {}

_FR_TRANSLATIONS = {
    # Core headers
    "Kategorie": "Catégorie",
    "Details": "Détails",
    # Common yes/no
    "ja": "oui",
    "nein": "non",
    "kein": "aucun",
    "keine": "aucune",
    # Common section/label terms (expand via translations_fr.json as needed)
    "Modell": "Modèle",
    "Markteinführung": "Lancement sur le marché",
    "Nachfolgermodell": "Modèle successeur",
    "Kameraklasse(n)": "Classe(s) d’appareil",
    "Elektronik": "Électronique",
    "Sensor": "Capteur",
    "Pixelpitch": "Pas de pixel",
    "Fotoauflösung": "Résolution photo",
    "Bildformate": "Formats d’image",
    "Farbtiefe": "Profondeur de couleur",
    "Metadaten": "Métadonnées",
    "Videoauflösung": "Résolution vidéo",
    "HDR-Video": "Vidéo HDR",
    "Videoformat": "Format vidéo",
    "All-Intra-Aufzeichnung": "Enregistrement All-Intra",
    "Audioformat (Video)": "Format audio (vidéo)",
    "Objektiv": "Objectif",
    "Objektivanschluss": "Monture d’objectif",
    "Fokussierung": "Mise au point",
    "Autofokusart": "Type d’autofocus",
    "AF-Erkennungsfunktion": "Fonction de détection AF",
    "Schärfenkontrolle": "Contrôle de la netteté",
    "Sucher und Monitor": "Viseur et écran",
    "Monitor": "Écran",
    "Videosucher": "Viseur électronique",
    "Belichtung": "Exposition",
    "Belichtungsmessung": "Mesure de l’exposition",
    "Belichtungszeiten": "Vitesses d’obturation",
    "Belichtungssteuerung": "Commande d’exposition",
    "Belichtungsreihenfunktion": "Fonction de bracketing d’exposition",
    "Belichtungskorrektur": "Correction d’exposition",
    "Lichtempfindlichkeit": "Sensibilité",
    "Fernzugriff": "Accès à distance",
    "Weissabgleich": "Balance des blancs",
    "Farbraum": "Espace colorimétrique",
    "Serienaufnahmen": "Prises de vue en rafale",
    "Selbstauslöser": "Retardateur",
    "Timer": "Minuterie",
    "Aufnahmefunktionen": "Fonctions de prise de vue",
    "Blitzgerät": "Flash",
    "Blitz": "Flash",
    "Blitzreichweite": "Portée du flash",
    "Blitzfunktionen": "Fonctions flash",
    "Ausstattung": "Équipement",
    "Bildstabilisator": "Stabilisateur d’image",
    "Speicher": "Mémoire",
    "Zweiter Speicherkartensteckplatz": "Deuxième emplacement pour carte mémoire",
    "Zweiter Speicherkartenslot": "Deuxième emplacement pour carte mémoire",
    "zweiter Speicherkartenslot": "Deuxième emplacement pour carte mémoire",
    "GPS-Funktion": "Fonction GPS",
    "Mikrofon": "Microphone",
    "Netzteil": "Bloc d’alimentation",
    "Netztteil": "Bloc d’alimentation",
    "Stromversorgung": "Alimentation",
    "Wiedergabefunktionen": "Fonctions de lecture",
    "Wiedergabe-Funktionen": "Fonctions de lecture",
    "Bildeinstellungen": "Paramètres d’image",
    "Bildparameter": "Paramètres d’image",
    "Spezialfunktionen": "Fonctions spéciales",
    "Sonder-Funktionen": "Fonctions spéciales",
    "USB-Typ": "Type USB",
    "Drahtlos": "Sans fil",
    "Datenschnittstelle": "Interface de données",
    "Daten-Schnittstelle": "Interface de données",
    "AV-Anschlüsse": "Connectiques AV",
    "HDMI-Output": "HDMI propre",
    "HDMI-Output-Auflösungen": "Résolutions HDMI propre",
    "HDMI-Output-Farbraum": "Espace colorimétrique HDMI propre",
    "HDMI-Output-Bemerkungen": "Remarques HDMI propre",
    "Clean HDMI": "Clean HDMI",
    "Clean HDMI Auflösungen": "Résolutions HDMI propre",
    "Clean HDMI Farbraum": "Espace colorimétrique HDMI propre",
    "Clean HDMI Anmerkungen": "Remarques HDMI propre",
    "Webcam-Funktion": "Fonction webcam",
    "Direktdruckunterstützung": "Procédés d’impression directe pris en charge",
    "Unterstützte Direkt-Druck-Verfahren": "Procédés d’impression directe pris en charge",
    "Stativgewinde": "Filetage pour trépied",
    "Gehäuse": "Boîtier",
    "Besonderheiten und Sonstiges": "Particularités et divers",
    "Abmessungen und Gewicht": "Dimensions et poids",
    "Grösse und Gewicht": "Dimensions et poids",
    "Abmessungen B x H x T": "Dimensions L x H x P",
    "Gewicht": "Poids",
    "Sonstiges": "Divers",
    "Mitgeliefertes Zubehör": "Accessoires fournis",
    "mitgeliefertes Zubehör": "Accessoires fournis",
    "Timecode": "Timecode",
}

_ARGOS_READY = False
_ARGOS_TRANSLATOR = None
_ARGOS_CHAIN = None
_FASTTEXT_MODEL = None

def _find_argos_model_file() -> str | None:
    candidates = [
        resource_path(ARGOS_MODEL_DIR),
        os.path.join(os.path.abspath("."), ARGOS_MODEL_DIR),
    ]
    for base in candidates:
        if not base or not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            if name.lower().endswith(".argosmodel"):
                return os.path.join(base, name)
    return None

def _ensure_argos_translator() -> bool:
    global _ARGOS_READY, _ARGOS_TRANSLATOR
    global _ARGOS_CHAIN
    if _ARGOS_READY and (_ARGOS_TRANSLATOR or _ARGOS_CHAIN):
        return True
    if not ARGOS_AVAILABLE:
        _tr_log("Argos not available (import failed).")
        return False
    try:
        langs = argos_translate.get_installed_languages()
        _tr_log(f"Argos installed langs: {[l.code for l in langs]}")
        def _get_lang(code: str):
            return next((l for l in langs if l.code == code), None)

        def _refresh_langs():
            nonlocal langs
            langs = argos_translate.get_installed_languages()

        # Try direct de->fr
        src = _get_lang(ARGOS_LANG_FROM)
        dst = _get_lang(ARGOS_LANG_TO)
        if src and dst:
            try:
                _ARGOS_TRANSLATOR = src.get_translation(dst)
                _ARGOS_CHAIN = None
                _ARGOS_READY = True
                return True
            except Exception:
                pass

        # Install any bundled models (if not already installed)
        model_path = _find_argos_model_file()
        if model_path:
            try:
                _tr_log(f"Installing Argos model from {model_path}")
                argos_package.install_from_path(model_path)
                _refresh_langs()
            except Exception:
                pass

        # Try direct again after install
        src = _get_lang(ARGOS_LANG_FROM)
        dst = _get_lang(ARGOS_LANG_TO)
        if src and dst:
            try:
                _ARGOS_TRANSLATOR = src.get_translation(dst)
                _ARGOS_CHAIN = None
                _ARGOS_READY = True
                return True
            except Exception:
                pass

        # Fallback: pivot de->en->fr
        src_de = _get_lang("de")
        mid_en = _get_lang("en")
        dst_fr = _get_lang("fr")
        if src_de and mid_en and dst_fr:
            try:
                _tr_log("Using Argos pivot de->en->fr")
                tr_de_en = src_de.get_translation(mid_en)
                tr_en_fr = mid_en.get_translation(dst_fr)
                _ARGOS_CHAIN = (tr_de_en, tr_en_fr)
                _ARGOS_TRANSLATOR = None
                _ARGOS_READY = True
                return True
            except Exception:
                pass

        return False
    except Exception:
        return False

def _load_fasttext_model() -> bool:
    global _FASTTEXT_MODEL
    if _FASTTEXT_MODEL is not None:
        return True
    if not FASTTEXT_AVAILABLE:
        _tr_log("fastText not available (import failed).")
        return False
    candidates = [
        os.path.join(resource_path(FASTTEXT_MODEL_DIR), FASTTEXT_LANG_MODEL),
        os.path.join(os.path.abspath("."), FASTTEXT_MODEL_DIR, FASTTEXT_LANG_MODEL),
    ]
    model_path = next((p for p in candidates if p and os.path.exists(p)), None)
    if not model_path:
        _tr_log("fastText model not found.")
        return False
    try:
        _FASTTEXT_MODEL = fasttext.load_model(model_path)
        _tr_log(f"fastText model loaded: {model_path}")
        return True
    except Exception:
        _FASTTEXT_MODEL = None
        return False

def _detect_language(text: str) -> tuple[str | None, float]:
    if not _load_fasttext_model():
        if not LANGID_AVAILABLE:
            return None, 0.0
        try:
            lang, score = langid.classify(text)
            _tr_log(f"Lang detect (langid): '{text[:60]}' -> {lang} ({score:.2f})")
            return lang, float(score)
        except Exception:
            _tr_log("Lang detect error (langid).")
            return None, 0.0
    try:
        sample = re.sub(r"\s+", " ", text.strip())[:1000]
        try:
            labels, probs = _FASTTEXT_MODEL.predict(sample, k=1)
        except Exception:
            sample = sample.encode("utf-8", "ignore").decode("utf-8")
            labels, probs = _FASTTEXT_MODEL.predict(sample, k=1)
        if not labels:
            return None, 0.0
        lang = labels[0].replace("__label__", "")
        prob = float(probs[0]) if probs else 0.0
        _tr_log(f"Lang detect: '{sample[:60]}' -> {lang} ({prob:.2f})")
        return lang, prob
    except Exception:
        _tr_log("Lang detect error (fasttext).")
        if LANGID_AVAILABLE:
            try:
                lang, score = langid.classify(text)
                _tr_log(f"Lang detect (langid): '{text[:60]}' -> {lang} ({score:.2f})")
                return lang, float(score)
            except Exception:
                _tr_log("Lang detect error (langid).")
        return None, 0.0

def _is_german_text(text: str) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    # Heuristic: German hints
    if GERMAN_HINT_RE.search(stripped):
        return True
    lang, prob = _detect_language(stripped)
    if lang in ("de", "deu") and prob >= LANG_DETECT_MIN_PROB:
        return True
    return False

def _should_translate_text(text: str, block_german: bool = False) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    # Skip mostly numbers/symbols
    if re.fullmatch(r"[\d\s\W]+", stripped):
        return False
    # Skip very short tokens without letters
    if not re.search(r"[A-Za-zÀ-ÿÄÖÜäöüß]", stripped):
        return False
    if block_german:
        return True
    return _is_german_text(stripped)

def _apply_post_edits(text: str, post_edits: dict) -> str:
    if not text or not post_edits:
        return text
    out = text
    for src, dst in post_edits.items():
        if not src:
            continue
        out = re.sub(r"(?i)" + re.escape(src), dst, out)
    return out

def _translate_plain_text(text: str, mapping: dict, post_edits: dict, block_german: bool = False) -> tuple[str, bool, bool]:
    """
    Returns (translated_text, did_translate, was_german)
    """
    if text in mapping:
        mapped = _apply_post_edits(mapping[text], post_edits)
        return mapped, True, False
    was_german = _should_translate_text(text, block_german=block_german)
    if not was_german:
        _tr_log(f"Skip (not German): {text[:80]}")
        edited = _apply_post_edits(text, post_edits)
        if edited != text:
            return edited, True, False
        return text, False, False
    if not _ensure_argos_translator():
        _tr_log("Argos not ready; skip translation.")
        edited = _apply_post_edits(text, post_edits)
        if edited != text:
            return edited, True, True
        return text, False, True
    try:
        masked, tokens = _mask_protected_tokens(text)
        if _ARGOS_TRANSLATOR:
            _tr_log("Translate via Argos direct.")
            translated = _ARGOS_TRANSLATOR.translate(masked)
        elif _ARGOS_CHAIN:
            _tr_log("Translate via Argos pivot.")
            mid = _ARGOS_CHAIN[0].translate(masked)
            translated = _ARGOS_CHAIN[1].translate(mid)
        else:
            return text, False, True
        if translated:
            translated = _unmask_protected_tokens(translated, tokens)
            translated = _apply_post_edits(translated, post_edits)
            if translated.strip() != text.strip():
                return translated, True, True
    except Exception:
        pass
    edited = _apply_post_edits(text, post_edits)
    if edited != text:
        return edited, True, True
    return text, False, True

def _translate_html_fragment(html: str, mapping: dict, post_edits: dict) -> str:
    if not html:
        return html
    soup = BeautifulSoup(html, "html.parser")
    # Decide at fragment level to reduce missed German nodes
    raw_texts = [t.strip() for t in soup.find_all(string=True) if t and t.strip()]
    visible_text = " ".join(raw_texts)
    block_german = False
    if len(visible_text) >= 20:
        block_german = _is_german_text(visible_text)
    if not block_german:
        for t in raw_texts:
            if _is_german_text(t):
                block_german = True
                break
        _tr_log(f"Block detect: '{visible_text[:80]}' -> german={block_german}")
    translated_nodes = 0
    for node in soup.find_all(string=True):
        if isinstance(node, Comment):
            continue
        parent = node.parent
        if parent and parent.name in ("style", "script"):
            continue
        raw = str(node)
        if not raw.strip():
            continue
        leading = re.match(r"^\s*", raw).group(0)
        trailing = re.match(r".*?(\s*)$", raw, re.DOTALL).group(1)
        core = raw.strip()
        translated, did, _ = _translate_plain_text(core, mapping, post_edits, block_german=block_german)
        if did:
            translated_nodes += 1
            node.replace_with(f"{leading}{translated}{trailing}")
    _tr_log(f"HTML fragment translated nodes: {translated_nodes}")
    if soup.body:
        return "".join(str(x) for x in soup.body.contents)
    return str(soup)

def _build_table_from_snapshot(snapshot, left_h, right_h, translate_label_fn, translate_value_fn):
    lines = []
    lines.append(SPEC_TABLE_CSS)
    lines.append('<table border="1" class="specs">')
    lines.append("\t<thead>")
    lines.append("\t\t<tr>")
    lines.append(f"\t\t\t<th>{_escape_html(translate_label_fn(left_h))}</th>")
    lines.append(f"\t\t\t<th>{_escape_html(translate_label_fn(right_h))}</th>")
    lines.append("\t\t</tr>")
    lines.append("\t</thead>")
    lines.append("\t<tbody>")

    for kind, a, b in snapshot:
        if kind == "section":
            title = _escape_html(translate_label_fn(a))
            lines.append('\t\t<tr class="section">')
            lines.append(f'\t\t\t<th class="section" colspan="2">{title}</th>')
            lines.append('\t\t</tr>')
        elif kind == "cat":
            title = _escape_html(translate_label_fn(a))
            lines.append('\t\t<tr class="cat">')
            lines.append(f'\t\t\t<th class="category" colspan="2">{title}</th>')
            lines.append('\t\t</tr>')
        else:
            k = _escape_html(translate_label_fn(a))
            v = translate_value_fn(b)
            if not (k or v):
                continue
            lines.append("\t\t<tr>")
            lines.append(f"\t\t\t<th>{k}</th>")
            lines.append(f"\t\t\t<td>{v}</td>")
            lines.append("\t\t</tr>")

    lines.append("\t</tbody>")
    lines.append("</table>")
    return "\n".join(lines)

class ExportWorker(QThread):
    finished = Signal(dict)

    def __init__(self, snapshot, left_h, right_h, path_de, path_fr, parent=None):
        super().__init__(parent)
        self.snapshot = snapshot
        self.left_h = left_h
        self.right_h = right_h
        self.path_de = path_de
        self.path_fr = path_fr

    def run(self):
        result = {"ok": False, "error": None, "missing": [], "argos": False, "fasttext": False}
        try:
            mapping = dict(_FR_TRANSLATIONS)
            mapping.update(_load_fr_translations())
            post_edits = dict(FR_POST_EDITS)
            post_edits.update(_load_fr_post_edits())
            argos_ready = _ensure_argos_translator()
            fasttext_ready = _load_fasttext_model()
            result["argos"] = argos_ready
            result["fasttext"] = fasttext_ready

            missing_fr = []

            def _translate_label(text: str) -> str:
                translated, did, was_german = _translate_plain_text(text, mapping, post_edits)
                if was_german and not did and text not in missing_fr:
                    missing_fr.append(text)
                return translated

            def _translate_value(value_html: str) -> str:
                return _translate_html_fragment(value_html, mapping, post_edits)

            out = _build_table_from_snapshot(
                self.snapshot, self.left_h, self.right_h, lambda s: s, lambda s: s
            )
            out = _normalize_for_paste(out)
            out_fr = _build_table_from_snapshot(
                self.snapshot, self.left_h, self.right_h, _translate_label, _translate_value
            )

            with open(self.path_de, "w", encoding="utf-8") as f:
                f.write(out)
            with open(self.path_fr, "w", encoding="utf-8") as f:
                f.write(out_fr)

            result["ok"] = True
            result["missing"] = missing_fr
        except Exception as e:
            result["error"] = str(e)
        self.finished.emit(result)

def _sanitize_value_html(html: str) -> str:
    # remove only font-family/font-size and Qt-specific noise from inline styles
    def _clean_style(m):
        style = m.group(1)
        style = re.sub(r'(?:^|;)\s*(font-family|font-size)\s*:\s*[^;]+;?', ';', style, flags=re.I)
        style = re.sub(r'(?:^|;)\s*-qt-[^;]+;?', ';', style, flags=re.I)
        style = re.sub(r';{2,}', ';', style).strip(' ;')
        return f' style="{style}"' if style else ''
    html = re.sub(r'\sstyle="([^"]*)"', _clean_style, html, flags=re.I)
    # drop spans that became empty after cleaning
    html = re.sub(r'<span(?:\sstyle="")?\s*>(.*?)</span>', r'\1', html, flags=re.I|re.S)
    return html

def _scrape_log(msg: str):
    try:
        os.makedirs("output", exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join("output", "scrape.log"), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def _tr_log(msg: str):
    if not TRANSLATION_DEBUG:
        return
    try:
        os.makedirs("output", exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join("output", "translate.log"), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def _clean_scraped_value(raw_text: str) -> str:
    # Normalize and split into lines
    txt = _normalize_for_paste(raw_text or "")
    lines = [ln.strip() for ln in txt.splitlines()]
    lines = [ln for ln in lines if ln]

    merged = []
    for ln in lines:
        low = ln.lower()
        if "weitere" in low:
            continue
        if low == "vergleichen":
            continue
        if ln in ("(", ")"):
            continue

        if merged:
            prev = merged[-1]
            # join parenthetical fragments
            if ln.startswith("("):
                merged[-1] = f"{prev} {ln}"
                continue
            # join numeric parts after a parenthetical (e.g., ") 30")
            if re.match(r"^\d+$", ln) and prev.endswith(")"):
                merged[-1] = f"{prev} {ln}"
                continue
            # join codecs into parentheses
            if ln.startswith("Codec "):
                merged[-1] = f"{prev} ({ln})"
                continue
            # join resolution fragments like "8.640 x" + "5.760"
            if prev.rstrip().endswith("x") and re.match(r"^\d", ln):
                merged[-1] = f"{prev} {ln}"
                continue
            # join frame rate fragment like "30p" or "30p,"
            if re.match(r"^\d+p,?$", ln):
                merged[-1] = f"{prev} {ln}"
                continue
            # join lone "p" after a number
            if ln in ("p", "P") and re.search(r"\b\d+$", prev):
                merged[-1] = f"{prev}{ln}"
                continue
            # join after trailing comma
            if prev.endswith(","):
                merged[-1] = f"{prev} {ln}"
                continue

        merged.append(ln)

    # split at semicolons into separate lines
    final_lines = []
    for ln in merged:
        parts = [p.strip() for p in ln.split(";") if p.strip()]
        if parts:
            final_lines.extend(parts)

    # collapse multiple spaces
    final_lines = [re.sub(r"\s+", " ", ln) for ln in final_lines]
    return "\n".join(final_lines)


# ---------- Rich text + auto-grow ----------
class RichTextArea(QTextEdit):
    confirm = Signal()   # Ctrl+Enter

    def keyPressEvent(self, e):
        if (e.key() in (Qt.Key_Return, Qt.Key_Enter)) and (e.modifiers() & Qt.ControlModifier):
            self.confirm.emit(); return
        super().keyPressEvent(e)

    # --- force plain-text paste everywhere (Ctrl+V, context menu, drops, programmatic) ---
    def insertFromMimeData(self, source):
        text = source.text()
        if text:
            self.insertPlainText(_normalize_for_paste(text))  # <— add
        else:
            super().insertFromMimeData(source)

    def paste(self):
        cb = QApplication.clipboard()
        self.insertPlainText(_normalize_for_paste(cb.text() or ""))  # <— add

    def toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if self.fontWeight() != QFont.Bold else QFont.Normal)
        self.mergeCurrentCharFormat(fmt)

    def toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.fontItalic())
        self.mergeCurrentCharFormat(fmt)

    def pick_color(self):
        c = QColorDialog.getColor(self.textColor(), self, "Textfarbe wählen")
        if c.isValid():
            fmt = QTextCharFormat(); fmt.setForeground(c); self.mergeCurrentCharFormat(fmt)

    def toggle_bullets(self):
        cur = self.textCursor()
        if cur.currentList():
            lst = cur.currentList()
            if lst:
                block_fmt = cur.blockFormat(); block_fmt.setIndent(0)
                cur.mergeBlockFormat(block_fmt); lst.remove(cur.block())
        else:
            lst_fmt = QTextListFormat(); lst_fmt.setStyle(QTextListFormat.ListDisc)
            cur.createList(lst_fmt)

class AutoGrowTextEdit(RichTextArea):
    """Fixed baseline (min_lines) that grows up to max_lines; after that, it scrolls."""
    heightChanged = Signal(int)

    def __init__(self, min_lines=3, max_lines=12, parent=None):
        super().__init__(parent)
        self._min_lines = min_lines
        self._max_lines = max_lines
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.document().contentsChanged.connect(self._update_height)
        self._update_height()

    def resizeEvent(self, e):
        self.document().setTextWidth(self.viewport().width())
        super().resizeEvent(e)
        self._update_height()

    def _natural_height(self):
        fm = self.fontMetrics()
        line = fm.lineSpacing()
        margin = self.document().documentMargin()
        doc_h = self.document().size().height()
        min_h = int(line * self._min_lines + margin * 2 + 6)
        max_h = int(line * self._max_lines + margin * 2 + 6)
        nat = int(doc_h + margin * 2 + 6)
        return max(min_h, min(nat, max_h)), min_h, max_h

    def _update_height(self):
        h, _, _ = self._natural_height()
        if abs(self.height() - h) > 2:
            self.setFixedHeight(h)
            self.heightChanged.emit(h)

class PlainPasteLineEdit(QLineEdit):
    """QLineEdit that always pastes plain text, collapsing whitespace."""

    def insertFromMimeData(self, source):
        text = source.text()  # ignore rich content
        t = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\u00A0", " ")
        t = re.sub(r"\s+", " ", t).strip()  # single line
        t = _normalize_for_paste(t)  # <— add
        self.insert(t)

class PlainPasteTextEdit(AutoGrowTextEdit):
    """TextEdit that keeps rich editing (bold, bullets) but pastes as plain text.
       Trims only leading/trailing *newlines* so multi-line stays intact."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptRichText(True)  # you still can format after pasting

    def insertFromMimeData(self, source):
        text = source.text()  # ignore rich content/HTML
        t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        t = t.strip("\n")
        t = _normalize_for_paste(t)  # <— add
        self.insertPlainText(t)

# ---------- Entry row with actions ----------
class EntryRow(QWidget):
    requestDelete = Signal(object)
    requestMoveUp = Signal(object)
    requestMoveDown = Signal(object)

    def __init__(self, key_text: str, value_html: str, icons: dict[str, QIcon], parent=None):
        super().__init__(parent)
        self.setProperty("class", "KVTable")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.row_layout = QHBoxLayout(self)
        self.row_layout.setContentsMargins(0,0,0,0)
        self.row_layout.setSpacing(0)

        self.key = QLineEdit(key_text)
        # Keep keys bold in the table rows as well
        kf = self.key.font()
        kf.setBold(True)
        self.key.setFont(kf)
        self.key.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        self.val = AutoGrowTextEdit(min_lines=3, max_lines=12)
        self.val.setAcceptRichText(True)

        if value_html:
            # If we were given full HTML (with <html>), keep it intact.
            s = value_html.strip().lower()
            if s.startswith("<html"):
                self.val.setHtml(value_html)
            else:
                # Inner-fragment case: wrap lightly so Qt parses it as rich text
                self.val.setHtml(f"<div>{value_html}</div>")

        self.val.heightChanged.connect(self._sync_key_height)
        self._sync_key_height(self.val.height())

        actions = QWidget()
        a_lay = QHBoxLayout(actions)
        a_lay.setContentsMargins(6, 0, 0, 0)
        a_lay.setSpacing(6)

        self.btn_up = QToolButton()
        self.btn_up.setIcon(icons.get("up", QIcon()))
        self.btn_up.setToolTip("Nach oben")
        self.btn_up.setProperty("class", "rowAction")
        self.btn_up.clicked.connect(lambda: self.requestMoveUp.emit(self))

        self.btn_down = QToolButton()
        self.btn_down.setIcon(icons.get("down", QIcon()))
        self.btn_down.setToolTip("Nach unten")
        self.btn_down.setProperty("class", "rowAction")
        self.btn_down.clicked.connect(lambda: self.requestMoveDown.emit(self))

        self.btn_del = QToolButton()
        self.btn_del.setIcon(icons.get("delete", QIcon()))
        self.btn_del.setToolTip("Eintrag löschen")
        self.btn_del.setProperty("class", "rowAction")
        self.btn_del.clicked.connect(lambda: self.requestDelete.emit(self))

        a_lay.addWidget(self.btn_up)
        a_lay.addWidget(self.btn_down)
        a_lay.addWidget(self.btn_del)

        self.row_layout.addWidget(self.key, 1)
        self.row_layout.addSpacing(1)
        self.row_layout.addWidget(self.val, 2)
        self.row_layout.addSpacing(1)
        self.row_layout.addWidget(actions, 0)

    def _sync_key_height(self, h: int):
        self.key.setFixedHeight(h)

    def key_plain(self) -> str:
        return self.key.text().strip()

    def val_html(self) -> str:
        cur = self.val.textCursor();
        cur.select(QTextCursor.Document)
        frag = cur.selection().toHtml()
        start = frag.find("<body")
        if start == -1:
            return _escape_html(self.val.toPlainText()).replace("\n", "<br />")
        start = frag.find(">", start)
        end = frag.rfind("</body>")
        if start == -1 or end == -1:
            return _escape_html(self.val.toPlainText()).replace("\n", "<br />")
        inner = frag[start + 1:end].strip()
        return _sanitize_value_html(inner)  # <— apply the cleaner


class CategoryRow(QWidget):
    requestDelete = Signal(object)
    requestMoveUp = Signal(object)
    requestMoveDown = Signal(object)
    requestFocusToKey = Signal()  # NEW: ask MainWindow to focus the key input

    def __init__(self, title_text: str, icons: dict[str, QIcon], parent=None):
        super().__init__(parent)
        self.setProperty("class", "KVTable")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.title = QLineEdit(title_text or "Neuer Abschnitt")
        f = self.title.font(); f.setBold(True); self.title.setFont(f)
        self.title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.title.setProperty("class", "CategoryCell")
        self.title.setFixedHeight(36)  # visually consistent, tweak if you like

        # ENTER inside the title commits and requests focus back to key input
        self.title.returnPressed.connect(self._on_return_pressed)

        actions = QWidget()
        a_lay = QHBoxLayout(actions)
        a_lay.setContentsMargins(6, 0, 0, 0)
        a_lay.setSpacing(6)

        self.btn_up = QToolButton();   self.btn_up.setIcon(icons.get("up", QIcon()))
        self.btn_down = QToolButton(); self.btn_down.setIcon(icons.get("down", QIcon()))
        self.btn_del = QToolButton();  self.btn_del.setIcon(icons.get("delete", QIcon()))
        for b, tip in ((self.btn_up, "Nach oben"), (self.btn_down, "Nach unten"), (self.btn_del, "Eintrag löschen")):
            b.setProperty("class", "rowAction"); b.setToolTip(tip)
        self.btn_up.clicked.connect(lambda: self.requestMoveUp.emit(self))
        self.btn_down.clicked.connect(lambda: self.requestMoveDown.emit(self))
        self.btn_del.clicked.connect(lambda: self.requestDelete.emit(self))
        a_lay.addWidget(self.btn_up); a_lay.addWidget(self.btn_down); a_lay.addWidget(self.btn_del)

        # Stretch 3 to visually span both "key" (1) and "value" (2) columns
        lay.addWidget(self.title, 3)
        lay.addSpacing(1)
        lay.addWidget(actions, 0)

    def _on_return_pressed(self):
        # finish edit + bounce focus to the main key input
        self.title.clearFocus()
        self.requestFocusToKey.emit()

    def title_plain(self) -> str:
        return self.title.text().strip()


class HeaderRow(QWidget):
    requestDelete = Signal(object)
    requestMoveUp = Signal(object)
    requestMoveDown = Signal(object)
    requestFocusToKey = Signal()

    def __init__(self, title_text: str, icons: dict[str, QIcon], parent=None):
        super().__init__(parent)
        self.setProperty("class", "KVTable")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.title = QLineEdit(title_text or "Neuer Abschnitt")
        f = self.title.font(); f.setBold(True); self.title.setFont(f)
        self.title.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.title.setProperty("class", "SectionCell")
        self.title.setFixedHeight(36)
        self.title.returnPressed.connect(self._on_return_pressed)

        actions = QWidget()
        a_lay = QHBoxLayout(actions)
        a_lay.setContentsMargins(6, 0, 0, 0)
        a_lay.setSpacing(6)

        self.btn_up = QToolButton();   self.btn_up.setIcon(icons.get("up", QIcon()))
        self.btn_down = QToolButton(); self.btn_down.setIcon(icons.get("down", QIcon()))
        self.btn_del = QToolButton();  self.btn_del.setIcon(icons.get("delete", QIcon()))
        for b, tip in ((self.btn_up, "Nach oben"), (self.btn_down, "Nach unten"), (self.btn_del, "Eintrag löschen")):
            b.setProperty("class", "rowAction"); b.setToolTip(tip)
        self.btn_up.clicked.connect(lambda: self.requestMoveUp.emit(self))
        self.btn_down.clicked.connect(lambda: self.requestMoveDown.emit(self))
        self.btn_del.clicked.connect(lambda: self.requestDelete.emit(self))
        a_lay.addWidget(self.btn_up); a_lay.addWidget(self.btn_down); a_lay.addWidget(self.btn_del)

        lay.addWidget(self.title, 3)
        lay.addSpacing(1)
        lay.addWidget(actions, 0)

    def _on_return_pressed(self):
        self.title.clearFocus()
        self.requestFocusToKey.emit()

    def header_plain(self) -> str:
        return self.title.text().strip()


class ScrapeWorker(QThread):
    finished = Signal(list)  # list of tuples: ("section", title) or ("kv", key, value_html)
    error = Signal(str)
    progress = Signal(int, int)  # current, total

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        driver = None
        try:
            _scrape_log(f"Start scrape: {self.url}")
            def _build_chrome_options(headless_mode: str | None):
                o = ChromeOptions()
                if headless_mode:
                    o.add_argument(f"--headless={headless_mode}")
                o.add_argument("--disable-gpu")
                o.add_argument("--no-sandbox")
                o.add_argument("--disable-dev-shm-usage")
                o.add_argument("--window-size=1280,800")
                return o

            def _build_edge_options(headless_mode: str | None):
                o = EdgeOptions()
                if headless_mode:
                    o.add_argument(f"--headless={headless_mode}")
                o.add_argument("--disable-gpu")
                o.add_argument("--no-sandbox")
                o.add_argument("--disable-dev-shm-usage")
                o.add_argument("--window-size=1280,800")
                return o

            # Selenium Manager (bundled) resolves driver automatically.
            try:
                headless_mode = SCRAPE_HEADLESS_MODE if SCRAPE_HEADLESS else None
                driver = webdriver.Chrome(options=_build_chrome_options(headless_mode))
            except WebDriverException as e:
                _scrape_log(f"Chrome start failed ({SCRAPE_HEADLESS_MODE}): {e}")
                # Retry with alternate headless mode
                if SCRAPE_HEADLESS:
                    alt = "new" if SCRAPE_HEADLESS_MODE == "old" else "old"
                    try:
                        driver = webdriver.Chrome(options=_build_chrome_options(alt))
                    except WebDriverException as e_alt:
                        _scrape_log(f"Chrome start failed ({alt}): {e_alt}")
                        e = e_alt

                if not driver:
                    # Fallback to Edge (also supported by Selenium Manager)
                    try:
                        headless_mode = SCRAPE_HEADLESS_MODE if SCRAPE_HEADLESS else None
                        driver = webdriver.Edge(options=_build_edge_options(headless_mode))
                    except WebDriverException as e2:
                        _scrape_log(f"Edge start failed ({SCRAPE_HEADLESS_MODE}): {e2}")
                        if SCRAPE_HEADLESS:
                            alt = "new" if SCRAPE_HEADLESS_MODE == "old" else "old"
                            try:
                                driver = webdriver.Edge(options=_build_edge_options(alt))
                            except WebDriverException as e3:
                                _scrape_log(f"Edge start failed ({alt}): {e3}")
                                self.error.emit(f"Chrome/Edge Treiberfehler:\n{e}\n\n{e3}")
                                return
                        else:
                            self.error.emit(f"Chrome/Edge Treiberfehler:\n{e}\n\n{e2}")
                            return

            driver.get(self.url)
            _scrape_log("Page loaded, waiting for .dkDataSheet")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".dkDataSheet"))
            )
            _scrape_log(".dkDataSheet found")

            if self._cancel:
                self.finished.emit([])
                return

            soup = BeautifulSoup(driver.page_source, "html.parser")
            sheet = soup.select_one(".dkDataSheet")
            if not sheet:
                _scrape_log("No .dkDataSheet in page source")
                self.error.emit("Keine .dkDataSheet Tabelle gefunden.")
                return

            rows = []
            skip_section = False
            trs = sheet.select("tbody tr")
            total = len(trs)
            _scrape_log(f"Found {total} <tr> rows")
            self.progress.emit(0, total)

            for i, tr in enumerate(trs):
                if self._cancel:
                    self.finished.emit([])
                    return

                header_cell = tr.select_one('td.colLegende1[colspan="2"] h3')
                if header_cell:
                    title = _normalize_for_paste(header_cell.get_text(strip=True))
                    if title:
                        if title.lower() in SCRAPE_EXCLUDE_SECTIONS:
                            skip_section = True
                        else:
                            skip_section = False
                            rows.append(("section", title))
                    continue

                key_cell = tr.select_one("td.colLegende1")
                val_cell = tr.select_one("td.colData1")
                if key_cell and val_cell:
                    if skip_section:
                        continue
                    key = _normalize_for_paste(key_cell.get_text(strip=True))
                    if not key:
                        continue
                    if key.lower() in SCRAPE_EXCLUDE_KEYS:
                        continue
                    raw_val = val_cell.get_text("\n", strip=True)
                    clean_val = _clean_scraped_value(raw_val)
                    if clean_val:
                        if key.lower() == "besonderheiten und sonstiges":
                            items = [ln.strip() for ln in clean_val.splitlines() if ln.strip()]
                            li_html = "".join(f"<li>{_escape_html(it)}</li>" for it in items)
                            value_html = f"<ul>{li_html}</ul>"
                        else:
                            value_html = _escape_html(clean_val).replace("\n", "<br />")
                        rows.append(("kv", key, value_html))

                self.progress.emit(i + 1, total)

            _scrape_log(f"Parsed {len(rows)} rows (sections + kv)")
            self.finished.emit(rows)
        except Exception as e:
            _scrape_log(f"Scrape exception: {e}")
            self.error.emit(str(e))
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass


# ---------- Main window ----------
class MainWindow(QMainWindow):
    updateFound = Signal(object)
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(resource_path("icons\\icon_gra.ico")))

        # Start auto-update check in background (silent)
        self._start_update_check()
        self.resize(1120, 860)
        try_set_modern_app_font()
        apply_brand_theme(QApplication.instance())

        # --- Icons (row actions + toolbar) ---
        self.icons = {
            "bold"  : QIcon(resource_path("icons/bold.svg")),
            "italic": QIcon(resource_path("icons/italic.svg")),
            "color" : QIcon(resource_path("icons/color.svg")),
            "list"  : QIcon(resource_path("icons/list.svg")),
            "up"    : QIcon(resource_path("icons/up_arrow.svg")),
            "down"  : QIcon(resource_path("icons/down_arrow.svg")),
            "delete": QIcon(resource_path("icons/bin.svg")),
        }

        # --- Actions (format) ---
        act_bold = QAction(self.icons["bold"], "", self);
        act_bold.setToolTip("Fett (Ctrl+B)")
        act_italic = QAction(self.icons["italic"], "", self);
        act_italic.setToolTip("Kursiv (Ctrl+I)")
        act_color = QAction(self.icons["color"], "", self);
        act_color.setToolTip("Textfarbe wählen")
        act_list = QAction(self.icons["list"], "", self);
        act_list.setToolTip("Liste (Ctrl+Shift+8)")
        act_bold.setShortcut(QKeySequence.Bold);
        act_bold.triggered.connect(self.on_bold)
        act_italic.setShortcut(QKeySequence.Italic);
        act_italic.triggered.connect(self.on_italic)
        act_list.setShortcut("Ctrl+Shift+8");
        act_list.triggered.connect(self.on_bullets)
        act_color.triggered.connect(self.on_color)

        # Helper: one-action toolbar so our existing CSS (QToolBar#formatToolbar QToolButton) still applies
        def make_toolbar_for(act: QAction) -> QToolBar:
            tb = QToolBar()
            tb.setObjectName("formatToolbar")
            tb.setOrientation(Qt.Horizontal)
            tb.setIconSize(QSize(18, 18))
            tb.setMovable(False);
            tb.setFloatable(False)
            tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
            tb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            tb.addAction(act)
            return tb

        tb_bold = make_toolbar_for(act_bold)
        tb_italic = make_toolbar_for(act_italic)
        tb_color = make_toolbar_for(act_color)
        tb_list = make_toolbar_for(act_list)

        # --- Frame with header ("Format") around a centered 2×2 grid of toolbars ---
        format_panel = QFrame()
        format_panel.setObjectName("formatPanel")
        format_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        fmt_layout = QVBoxLayout(format_panel)
        fmt_layout.setContentsMargins(10, 10, 10, 10)
        fmt_layout.setSpacing(8)

        fmt_title = QLabel("Format")
        fmt_title.setObjectName("formatPanelTitle")
        fmt_title.setAlignment(Qt.AlignHCenter)
        fmt_layout.addWidget(fmt_title, 0)

        fmt_grid_holder = QWidget()
        fmt_grid = QGridLayout(fmt_grid_holder)
        fmt_grid.setContentsMargins(0, 0, 0, 0)
        fmt_grid.setHorizontalSpacing(10)
        fmt_grid.setVerticalSpacing(10)
        fmt_grid.addWidget(tb_bold, 0, 0)
        fmt_grid.addWidget(tb_italic, 0, 1)
        fmt_grid.addWidget(tb_color, 1, 0)
        fmt_grid.addWidget(tb_list, 1, 1)

        # --- Section button ---
        self.btn_section = QPushButton("Abschnitt")
        self.btn_section.setObjectName("accentSmall")
        self.btn_section.setToolTip("Abschnitts-Überschrift eingeben")
        self.btn_section.setCheckable(True)
        self.btn_section.toggled.connect(self._on_section_toggled)

        # open button
        open_button = QPushButton("Öffnen...")
        open_button.setObjectName("primaryButton")
        open_button.setShortcut(QKeySequence.Open)
        open_button.clicked.connect(self.load_from_file)

        # online search button
        self.btn_online = QPushButton("Online suchen")
        self.btn_online.setObjectName("primaryButton")
        self.btn_online.clicked.connect(self._on_online_search)

        # clear button
        self.btn_clear = QPushButton("Alles löschen")
        self.btn_clear.setObjectName("primaryButton")
        self.btn_clear.clicked.connect(self._on_clear_all)

        # center the grid horizontally in the frame
        center_row = QHBoxLayout()
        center_row.setContentsMargins(0, 0, 0, 0)
        center_row.addStretch(1)
        center_row.addWidget(fmt_grid_holder)
        center_row.addStretch(1)
        fmt_layout.addLayout(center_row, 1)

        # Compute a fixed width so the robot panel can match it
        fmt_margins = fmt_layout.contentsMargins()
        fmt_width = max(
            150,
            fmt_grid_holder.sizeHint().width() + fmt_margins.left() + fmt_margins.right()
        )
        format_panel.setFixedWidth(fmt_width)

        # --- Robot panel (left, below format panel; same width) ---
        robot_panel = QFrame()
        robot_panel.setObjectName("robotPanel")
        robot_panel.setFixedWidth(fmt_width)
        rp_layout = QVBoxLayout(robot_panel)
        rp_layout.setContentsMargins(0, 0, 10, 10)
        rp_layout.setSpacing(0)
        robo_label = QLabel()
        robo_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignBottom)
        rp = resource_path("icons/robot_with_bubble_100px.png")
        if os.path.exists(rp):
            robo_label.setPixmap(QPixmap(rp))
        rp_layout.addStretch(1)
        rp_layout.addWidget(robo_label, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)

        # --- Main content ---
        central = QWidget();
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 20, 18, 20)
        outer.setSpacing(18)

        # Title
        title_row = QVBoxLayout();
        title_row.setSpacing(12)
        title_label = QLabel("Titel:")
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_label.setStyleSheet("""
            color: #006c8c;   
            font-weight: bold;
            font-size: 20px;
        """)
        self.title_in = QLineEdit(DEFAULT_EXPORT_TITLE)
        self.title_in.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_row.addWidget(title_label);
        title_row.addWidget(self.title_in)
        holder_layout = QHBoxLayout()
        holder_layout.addStretch()
        holder_layout.addLayout(title_row)
        holder_layout.addStretch()
        outer.addLayout(holder_layout)
        outer.addWidget(make_separator())

        # --- Unified table block ---
        block = QHBoxLayout();
        block.setSpacing(12)

        # LEFT COLUMN: format panel + robot panel stacked
        left_holder = QWidget()
        left_holder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        lh_layout = QVBoxLayout(left_holder)
        lh_layout.setContentsMargins(0, 0, 0, 0)
        lh_layout.setSpacing(12)
        lh_layout.addWidget(open_button)
        lh_layout.addWidget(self.btn_online)
        lh_layout.addWidget(self.btn_clear)
        lh_layout.addWidget(format_panel, 0)
        lh_layout.addWidget(self.btn_section)
        lh_layout.addWidget(robot_panel, 1, Qt.AlignBottom)
        block.addWidget(left_holder, 0)

        # RIGHT COLUMN: table shell (grid + scroll + footer)
        shell = QVBoxLayout();
        shell.setSpacing(12)

        # --- Table grid: headers + input + paste in one layout ---
        table = QWidget();
        table.setProperty("class", "KVTable")
        table_grid = QGridLayout(table)
        table_grid.setContentsMargins(3, 3, 3, 3)
        table_grid.setHorizontalSpacing(1)
        table_grid.setVerticalSpacing(0)

        def vline():
            ln = QFrame()
            ln.setFrameShape(QFrame.VLine)
            ln.setFrameShadow(QFrame.Plain)
            ln.setStyleSheet("background: #006c8c; min-width:1px; max-width:1px;")
            return ln

        table_grid.setColumnStretch(0, 1)
        table_grid.setColumnStretch(2, 2)
        table_grid.setColumnStretch(4, 0)

        # Row 0: headers
        self.hdr_left = QLineEdit(DEFAULT_HEADER_LEFT);
        self.hdr_left.setReadOnly(True)
        self.hdr_right = QLineEdit(DEFAULT_HEADER_RIGHT);
        self.hdr_right.setReadOnly(True)
        for e in (self.hdr_left, self.hdr_right):
            if e == self.hdr_left:
                e.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
            else:
                e.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            e.setProperty("class", "HeaderCell")
        hdr_actions = QWidget()
        ha = QHBoxLayout(hdr_actions);
        ha.setContentsMargins(6, 0, 0, 0);
        ha.setSpacing(0)
        self.chk_hdr_edit = QCheckBox("Bearbeiten")
        self.chk_hdr_edit.setToolTip("Überschriften bearbeiten")
        self.chk_hdr_edit.toggled.connect(self._on_hdr_edit_toggled)
        ha.addWidget(self.chk_hdr_edit)

        table_grid.addWidget(self.hdr_left, 0, 0)
        table_grid.addWidget(vline(), 0, 1)
        table_grid.addWidget(self.hdr_right, 0, 2)
        table_grid.addWidget(vline(), 0, 3)
        table_grid.addWidget(hdr_actions, 0, 4, Qt.AlignVCenter)

        # Row 1: inputs (toggle between key/value vs section header)
        self.key_in = PlainPasteLineEdit()
        self.key_in.setPlaceholderText("Schlüssel Eingeben")
        _f = self.key_in.font()
        _f.setBold(True)
        self.key_in.setFont(_f)
        self.key_in.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.val_in = PlainPasteTextEdit(min_lines=3, max_lines=12)
        self.val_in.setPlaceholderText("Wert Eingeben (Ctrl+Enter bestätigt)")
        self.header_in = PlainPasteLineEdit()
        self.header_in.setPlaceholderText("Abschnittstitel eingeben")
        hf = self.header_in.font(); hf.setBold(True); self.header_in.setFont(hf)
        self.header_in.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.header_in.setProperty("class", "SectionCell")
        self.header_in.hide()

        self.confirm_btn = QPushButton("Bestätigen");
        self.confirm_btn.setObjectName("primaryButton")
        self.confirm_btn.clicked.connect(self.confirm_current_input)
        self.key_in.returnPressed.connect(self.confirm_current_input)
        self.val_in.confirm.connect(self.confirm_current_input)
        self.header_in.returnPressed.connect(self.confirm_current_input)
        self.val_in.heightChanged.connect(lambda h: self.key_in.setFixedHeight(h))
        self.key_in.setFixedHeight(self.val_in.height())

        self.vline_inputs_mid = vline()
        self.vline_inputs_right = vline()
        table_grid.addWidget(self.key_in, 1, 0)
        table_grid.addWidget(self.vline_inputs_mid, 1, 1)
        table_grid.addWidget(self.val_in, 1, 2)
        table_grid.addWidget(self.header_in, 1, 0, 1, 3)
        table_grid.addWidget(self.vline_inputs_right, 1, 3)
        table_grid.addWidget(self.confirm_btn, 1, 4, Qt.AlignVCenter)

        # Row 2: paste buttons (toggle)
        self.btn_paste_key = QPushButton("Schlüssel einfügen (Zwischenablage)")
        self.btn_paste_val = QPushButton("Wert einfügen (Zwischenablage)")
        self.btn_paste_section = QPushButton("Abschnitt einfügen (Zwischenablage)")
        for b in (self.btn_paste_key, self.btn_paste_val, self.btn_paste_section):
            b.setObjectName("accentSmall")
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_paste_key.clicked.connect(self.paste_key_plain)
        self.btn_paste_val.clicked.connect(self.paste_value_plain)
        self.btn_paste_section.clicked.connect(self.paste_section_plain)
        self.btn_paste_section.hide()

        confirm_width = self.confirm_btn.sizeHint().width()
        confirm_spacer = QSpacerItem(confirm_width, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.vline_paste_mid = vline()
        self.vline_paste_right = vline()
        table_grid.addWidget(self.btn_paste_key, 2, 0, Qt.AlignTop)
        table_grid.addWidget(self.vline_paste_mid, 2, 1)
        table_grid.addWidget(self.btn_paste_val, 2, 2, Qt.AlignTop)
        table_grid.addWidget(self.btn_paste_section, 2, 0, 1, 3, Qt.AlignTop)
        table_grid.addWidget(self.vline_paste_right, 2, 3)
        table_grid.addItem(confirm_spacer, 2, 4, Qt.AlignTop)

        paste_h = max(self.btn_paste_key.sizeHint().height(), self.btn_paste_val.sizeHint().height(),
                      self.btn_paste_section.sizeHint().height())
        table_grid.setRowMinimumHeight(2, paste_h)
        table_grid.setRowStretch(2, 0)
        shell.addWidget(table)

        self.input_mode = "kv"

        # Rows area (scrolls when necessary) — wrapper with bottom stretch
        rows_frame = QWidget()
        rows_frame.setProperty("class", "KVTable")

        self.rows_v = QVBoxLayout(rows_frame)
        self.rows_v.setContentsMargins(0, 0, 0, 0)
        self.rows_v.setSpacing(10)
        # no need to set AlignTop; the wrapper’s stretch handles the extra space
        self.rows_widgets = []

        # wrapper that absorbs extra height below the rows
        rows_wrap = QWidget()
        wrap_v = QVBoxLayout(rows_wrap)
        wrap_v.setContentsMargins(0, 0, 0, 0)
        wrap_v.setSpacing(0)
        wrap_v.addWidget(rows_frame, 0)  # natural height of rows
        wrap_v.addStretch(1)  # eat surplus height at the bottom

        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(rows_wrap)  # << important: set wrapper, not rows_frame

        # optional: make the scroll area the thing that grows in the right column
        self.scroll.setMaximumHeight(520)
        shell.addWidget(self.scroll)
        shell.setStretchFactor(self.scroll, 1)

        # Footer (export)
        footer = QHBoxLayout();
        footer.setSpacing(12)
        self.chk_only_de = QCheckBox("Nur Deutsch")
        self.chk_only_de.setToolTip("Nur die deutsche Version exportieren")
        self.btn_export = QPushButton("Exportieren");
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_table_only)
        footer.addStretch(1);
        footer.addWidget(self.chk_only_de, alignment=Qt.AlignBottom)
        footer.addWidget(self.btn_export, alignment=Qt.AlignBottom)
        shell.addLayout(footer)

        # Compose
        block.addLayout(shell, 1)
        outer.addLayout(block)

        self.updateFound.connect(self._show_update_dialog_slot)
        self.statusBar().showMessage("Bereit")

    # ---------- Auto-Update Methods ----------
    def _start_update_check(self):
        """Start silent background update check."""
        if not AUTO_UPDATE_AVAILABLE:
            return
        # Use QTimer to delay check slightly after window shows
        QTimer.singleShot(2000, self._do_update_check)

    def _do_update_check(self):
        """Perform the actual update check."""
        if not AUTO_UPDATE_AVAILABLE:
            return
        def _worker():
            try:
                has_update, info = auto_update.check_for_updates_blocking()
                if has_update and info:
                    self.updateFound.emit(info)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    @Slot(object)
    def _show_update_dialog_slot(self, version_info):
        """Slot to show update dialog on main thread."""
        if not AUTO_UPDATE_AVAILABLE:
            return
        try:
            auto_update.show_update_dialog(version_info, parent=self)
        except Exception:
            pass

    def add_category_row(self):
        row = CategoryRow("Neuer Abschnitt", self.icons)
        row.requestDelete.connect(self._row_delete)
        row.requestMoveUp.connect(self._row_move_up)
        row.requestMoveDown.connect(self._row_move_down)

        row.requestFocusToKey.connect(lambda: self.key_in.setFocus(Qt.OtherFocusReason))

        self.rows_widgets.append(row)
        self.rows_v.addWidget(row)
        # focus it for immediate editing
        row.title.setFocus()
        row.title.selectAll()

        self._scroll_row_bottom_into_view(row)

        QTimer.singleShot(0, row.title.setFocus)

    def _on_online_search(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Online suchen")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("🡇   digitalkamera.de öffnen   🡇")
        title.setStyleSheet("""
            background-color: #006B8D;
            color: #FFFFFF;
            padding: 6px;
            font-weight: bold;
            border-radius: 10px;
            box-shadow: 2px 2px 3px #FFFFFF;
        """)
        title.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_cams = QPushButton("Kameras")
        btn_cams.setStyleSheet("""
            background-color: #006B8D;
            color: #FFFFFF;
            font-weight: bold;  
            padding: 6px;
        """)
        btn_lenses = QPushButton("Objektive")
        btn_lenses.setStyleSheet("""
            background-color: #006B8D;
            color: #FFFFFF;
            font-weight: bold;  
            padding: 6px;
        """)
        btn_row.addWidget(btn_cams)
        btn_row.addWidget(btn_lenses)
        layout.addLayout(btn_row)

        def _open_digitalkamera(url: str):
            QDesktopServices.openUrl(QUrl(url))

        btn_cams.clicked.connect(
            lambda: _open_digitalkamera("https://www.digitalkamera.de/Kamera/Schnellzugriff.aspx")
        )
        btn_lenses.clicked.connect(
            lambda: _open_digitalkamera("https://www.digitalkamera.de/Objektiv/Schnellzugriff.aspx")
        )

        input_label = QLabel("Link zu digitalkamera.de Datenblatt:")
        url_in = QLineEdit()
        url_in.setPlaceholderText("https://www.digitalkamera.de/...")
        layout.addWidget(input_label)
        layout.addWidget(url_in)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons, alignment=Qt.AlignCenter)

        if dialog.exec() != QDialog.Accepted:
            return

        url = (url_in.text() or "").strip()
        if not url:
            return
        if "https://www.digitalkamera.de" not in url:
            QMessageBox.warning(
                self, "Ungültige URL",
                "Bitte eine URL von https://www.digitalkamera.de eingeben."
            )
            return

        self._start_scrape(url)

    def _start_scrape(self, url: str):
        if getattr(self, "_scrape_worker", None):
            return

        self.btn_online.setEnabled(False)
        self._scrape_canceled = False
        self._scrape_progress = QProgressDialog(
            "Spezifikationen werden geladen…", "Abbrechen", 0, 0, self
        )
        self._scrape_progress.setWindowModality(Qt.WindowModal)
        self._scrape_progress.setMinimumDuration(0)
        self._scrape_progress.setAutoClose(True)
        self._scrape_progress.setAutoReset(True)
        self._scrape_progress.setValue(0)
        self._scrape_progress.show()

        self._scrape_worker = ScrapeWorker(url, self)
        self._scrape_worker.finished.connect(self._scrape_finished)
        self._scrape_worker.error.connect(self._scrape_error)
        self._scrape_worker.progress.connect(self._scrape_progress_update)
        self._scrape_progress.canceled.connect(self._scrape_cancel)
        self._scrape_worker.start()

    def _scrape_cancel(self):
        w = getattr(self, "_scrape_worker", None)
        if w:
            self._scrape_canceled = True
            _scrape_log("UI: cancel requested by user")
            w.cancel()

    def _scrape_finished(self, rows: list):
        try:
            print(f"[SCRAPE] finished signal, rows={len(rows) if rows else 0}")
            _scrape_log(f"UI: finished signal, rows={len(rows) if rows else 0}")

            if getattr(self, "_scrape_progress", None):
                print("[SCRAPE] closing progress dialog")
                _scrape_log("UI: closing progress dialog")
                self._scrape_progress.close()

            print("[SCRAPE] enabling button, clearing worker")
            _scrape_log("UI: enabling button, clearing worker")
            self.btn_online.setEnabled(True)
            self._scrape_worker = None

            if getattr(self, "_scrape_canceled", False) and not rows:
                print("[SCRAPE] canceled with no rows -> return")
                _scrape_log("UI: canceled with no rows -> return")
                return

            if not rows:
                _scrape_log("No rows parsed, showing empty dialog")
                print("[SCRAPE] no rows parsed -> showing dialog")
                QMessageBox.information(self, "Keine Daten", "Keine Spezifikationen gefunden.")
                return

            _scrape_log(f"Populate UI with {len(rows)} rows")
            print(f"[SCRAPE] populating UI with {len(rows)} rows")

            for idx, item in enumerate(rows):
                if not item:
                    print(f"[SCRAPE] skip empty item at {idx}")
                    continue
                if item[0] == "section":
                    print(f"[SCRAPE] add section at {idx}: {item[1][:60]}")
                    row = HeaderRow(item[1], self.icons)
                else:
                    print(f"[SCRAPE] add kv at {idx}: {item[1][:60]}")
                    row = EntryRow(item[1], item[2], self.icons)

                row.requestDelete.connect(self._row_delete)
                row.requestMoveUp.connect(self._row_move_up)
                row.requestMoveDown.connect(self._row_move_down)
                if hasattr(row, "requestFocusToKey"):
                    row.requestFocusToKey.connect(lambda: self.key_in.setFocus(Qt.OtherFocusReason))

                self.rows_widgets.append(row)
                self.rows_v.addWidget(row)

            print("[SCRAPE] populate complete, scrolling into view")
            _scrape_log("UI: populate complete, scrolling into view")
            self._scroll_row_bottom_into_view(self.rows_widgets[-1] if self.rows_widgets else None)
        except Exception as e:
            _scrape_log(f"UI populate exception: {e}")
            print(f"[SCRAPE] UI populate exception: {e}")
            QMessageBox.critical(self, "Scraping fehlgeschlagen", str(e))
            return

    def _scrape_error(self, msg: str):
        if getattr(self, "_scrape_progress", None):
            self._scrape_progress.close()
        self.btn_online.setEnabled(True)
        self._scrape_worker = None
        QMessageBox.critical(self, "Scraping fehlgeschlagen", msg)

    def _scrape_progress_update(self, current: int, total: int):
        if not getattr(self, "_scrape_progress", None):
            return
        if total > 0:
            if self._scrape_progress.maximum() != total:
                self._scrape_progress.setRange(0, total)
            self._scrape_progress.setValue(current)
            self._scrape_progress.setLabelText(
                f"Spezifikationen werden geladen… {current}/{total}"
            )

    def _on_clear_all(self):
        res = QMessageBox.question(
            self,
            "Alles löschen",
            "Alle Einträge und Überschriften löschen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return

        self.rows_widgets.clear()
        while self.rows_v.count():
            item = self.rows_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        self.key_in.clear()
        self.val_in.clear()
        self.header_in.clear()
        self.btn_section.setChecked(False)
        self._set_input_mode("kv")
        self.key_in.setFocus()

    def _on_section_toggled(self, checked: bool):
        self._set_input_mode("section" if checked else "kv")

    def _set_input_mode(self, mode: str):
        if mode == self.input_mode:
            return
        self.input_mode = mode
        is_section = mode == "section"
        self.key_in.setVisible(not is_section)
        self.val_in.setVisible(not is_section)
        self.vline_inputs_mid.setVisible(not is_section)
        self.header_in.setVisible(is_section)
        self.btn_paste_key.setVisible(not is_section)
        self.btn_paste_val.setVisible(not is_section)
        self.vline_paste_mid.setVisible(not is_section)
        self.btn_paste_section.setVisible(is_section)
        if is_section:
            self.header_in.setFocus(Qt.OtherFocusReason)
            self.header_in.selectAll()
        else:
            self.key_in.setFocus(Qt.OtherFocusReason)

    # Place a QToolBar inside a QWidget so layouts ca
    # n size it vertically
    def _build_toolbar_widget(self, tb: QToolBar) -> QWidget:
        holder = QWidget()
        v = QVBoxLayout(holder); v.setContentsMargins(0,0,0,0); v.addWidget(tb)
        holder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        return holder

    # Formatting targeting active rich text
    def current_text_widget(self):
        w = QApplication.focusWidget()
        return w if isinstance(w, QTextEdit) else self.val_in

    def on_bold(self):
        w = self.current_text_widget()
        if hasattr(w, "toggle_bold"): w.toggle_bold()

    def on_italic(self):
        w = self.current_text_widget()
        if hasattr(w, "toggle_italic"): w.toggle_italic()

    def on_color(self):
        w = self.current_text_widget()
        if hasattr(w, "pick_color"): w.pick_color()

    def on_bullets(self):
        w = self.current_text_widget()
        if hasattr(w, "toggle_bullets"): w.toggle_bullets()

    # Header edit toggle
    def _on_hdr_edit_toggled(self, checked: bool):
        self.hdr_left.setReadOnly(not checked)
        self.hdr_right.setReadOnly(not checked)

    def _clipboard_plain_trimmed(self) -> str:
        cb = QApplication.clipboard()
        t = cb.text() or ""
        # normalize line endings and trim only at the ends
        t = t.replace("\r\n", "\n").replace("\r", "\n")
        # strip BOM / zero-width / spaces / tabs / newlines only at the ends
        t = re.sub(r"^\ufeff", "", t)  # BOM at start if present
        t = re.sub(r"^[\u200B-\u200D\u2060 \t\n]+", "", t)  # leading
        t = re.sub(r"[\u200B-\u200D\u2060 \t\n]+$", "", t)  # trailing
        return _normalize_for_paste(t)

    # Paste helpers (plain text)
    def paste_key_plain(self):
        txt = self._clipboard_plain_trimmed()
        if not txt:
            return
        self.key_in.setFocus(Qt.OtherFocusReason)
        self.key_in.insert(txt)  # QLineEdit: plain text insert

    def paste_value_plain(self):
        txt = self._clipboard_plain_trimmed()
        if not txt:
            return
        self.val_in.setFocus(Qt.OtherFocusReason)
        c = self.val_in.textCursor()
        c.clearSelection()
        self.val_in.setTextCursor(c)
        self.val_in.insertPlainText(txt)  # QTextEdit: plain text insert

    def paste_section_plain(self):
        txt = self._clipboard_plain_trimmed()
        if not txt:
            return
        self.header_in.setFocus(Qt.OtherFocusReason)
        self.header_in.insert(txt)

    def _scroll_row_bottom_into_view(self, row: QWidget | None, extra_px: int = 24):
        """
        Scroll so the *bottom* of `row` is visible, with a small margin.
        Runs twice (0ms and ~40ms) to catch auto-grow after layout settles.
        """

        def snap():
            w = self.scroll.widget()
            if not w or not row or not row.isVisible():
                return
            y_top = row.mapTo(w, QPoint(0, 0)).y()
            y_bottom = y_top + row.height()
            vp_h = self.scroll.viewport().height()
            target = y_bottom - vp_h + max(0, extra_px)

            bar = self.scroll.verticalScrollBar()
            bar.setValue(max(0, min(target, bar.maximum())))

        QTimer.singleShot(0, snap)  # after this event loop turn
        QTimer.singleShot(40, snap)  # once more after auto-resize/auto-grow

    # Add a persistent row
    def confirm_current_input(self):
        if self.input_mode == "section":
            title = self.header_in.text().strip()
            if not title:
                QMessageBox.information(self, "Fehlender Abschnitt", "Bitte Abschnittstitel eingeben.")
                return

            row = HeaderRow(title, self.icons)
            row.requestDelete.connect(self._row_delete)
            row.requestMoveUp.connect(self._row_move_up)
            row.requestMoveDown.connect(self._row_move_down)
            row.requestFocusToKey.connect(lambda: self.key_in.setFocus(Qt.OtherFocusReason))

            self.rows_widgets.append(row)
            self.rows_v.addWidget(row)

            self._scroll_row_bottom_into_view(row)

            self.header_in.clear()
            self.btn_section.setChecked(False)
            self._set_input_mode("kv")
            self.key_in.setFocus()
            return

        key = self.key_in.text().strip()
        if not key:
            QMessageBox.information(self, "Fehlender Schlüssel", "Bitte Schlüssel eingeben.")
            return

        # Preserve lists by taking the ENTIRE document HTML
        val_html_full = self.val_in.document().toHtml()

        row = EntryRow(key, val_html_full, self.icons)
        row.requestDelete.connect(self._row_delete)
        row.requestMoveUp.connect(self._row_move_up)
        row.requestMoveDown.connect(self._row_move_down)

        self.rows_widgets.append(row)
        self.rows_v.addWidget(row)

        self._scroll_row_bottom_into_view(row)

        # Clear input and focus back to key
        self.key_in.clear()
        self.val_in.clear()
        self.key_in.setFocus()


    # Row actions
    def _row_delete(self, row: EntryRow):
        if row in self.rows_widgets:
            self.rows_widgets.remove(row)
            row.setParent(None); row.deleteLater()

    def _row_move_up(self, row: EntryRow):
        idx = self.rows_widgets.index(row)
        if idx > 0:
            self.rows_widgets[idx-1], self.rows_widgets[idx] = self.rows_widgets[idx], self.rows_widgets[idx-1]
            self._rebuild_rows_layout()

    def _row_move_down(self, row: EntryRow):
        idx = self.rows_widgets.index(row)
        if idx < len(self.rows_widgets) - 1:
            self.rows_widgets[idx+1], self.rows_widgets[idx] = self.rows_widgets[idx], self.rows_widgets[idx+1]
            self._rebuild_rows_layout()

    def _rebuild_rows_layout(self):
        # clear all items currently in the layout
        while self.rows_v.count():
            item = self.rows_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        # re-add rows
        for r in self.rows_widgets:
            self.rows_v.addWidget(r)

        # the bottom “stretch” is handled by the wrapper (rows_wrap.addStretch(1))
        self._scroll_row_bottom_into_view(self.rows_widgets[-1] if self.rows_widgets else None)

    # Export exact table
    def export_table_only(self):
        left_h = self.hdr_left.text().strip() or DEFAULT_HEADER_LEFT
        right_h = self.hdr_right.text().strip() or DEFAULT_HEADER_RIGHT

        # --- Save dialog ---
        base = self.title_in.text().strip() or DEFAULT_EXPORT_TITLE
        base = "".join(ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in base).strip()
        base = "_".join(base.split()) or DEFAULT_EXPORT_TITLE
        default_name = f"{base}.txt"
        desktop = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation) or ""
        default_path = os.path.join(desktop, default_name) if desktop else default_name
        path, _ = QFileDialog.getSaveFileName(
            self, "Speichern (einfügefertiges HTML)", default_path,
            "Text/HTML (*.txt *.html *.htm);;All Files (*.*)"
        )
        if not path:
            return
        if self.chk_only_de.isChecked():
            try:
                snapshot = []
                for rw in self.rows_widgets:
                    if hasattr(rw, "header_plain"):
                        snapshot.append(("section", rw.header_plain(), ""))
                    elif hasattr(rw, "title_plain") and not hasattr(rw, "key_plain"):
                        snapshot.append(("cat", rw.title_plain(), ""))
                    else:
                        snapshot.append(("kv", rw.key_plain(), rw.val_html()))
                out = _build_table_from_snapshot(snapshot, left_h, right_h, lambda s: s, lambda s: s)
                out = _normalize_for_paste(out)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(out)
                self.statusBar().showMessage(f"Gespeichert unter: {path}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Speicherfehler", str(e))
            return
        out_dir = os.path.dirname(path) or "."
        name = os.path.basename(path)
        stem, ext = os.path.splitext(name)
        if stem.endswith("_de") or stem.endswith("_fr"):
            stem = stem[:-3]
        if not ext:
            ext = ".txt"
        path_de = os.path.join(out_dir, f"{stem}_de{ext}")
        path_fr = os.path.join(out_dir, f"{stem}_fr{ext}")
        snapshot = []
        for rw in self.rows_widgets:
            if hasattr(rw, "header_plain"):
                snapshot.append(("section", rw.header_plain(), ""))
            elif hasattr(rw, "title_plain") and not hasattr(rw, "key_plain"):
                snapshot.append(("cat", rw.title_plain(), ""))
            else:
                snapshot.append(("kv", rw.key_plain(), rw.val_html()))

        self._show_translate_dialog()
        self._export_worker = ExportWorker(snapshot, left_h, right_h, path_de, path_fr, self)
        self._export_worker.finished.connect(
            lambda result: self._on_export_finished(result, path_de, path_fr)
        )
        self._export_worker.start()

    def _show_translate_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Übersetzen")
        dlg.setModal(False)
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        dlg.setAttribute(Qt.WA_TranslucentBackground, True)
        dlg.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        dlg.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        host = QWidget()
        host.setStyleSheet("background:#006b8d; border-radius:10px;")
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(12, 10, 12, 10)
        host_layout.setSpacing(0)
        host_layout.setSizeConstraint(QLayout.SetFixedSize)
        host_layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        layout.addWidget(host)

        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignHCenter)
        gif_path = resource_path("icons/robot_white.gif")
        movie = QMovie(gif_path)
        gif_label.setMovie(movie)
        movie.start()
        def _scale_movie():
            rect = movie.frameRect()
            if rect.isValid():
                movie.setScaledSize(QSize(max(1, rect.width() // 4), max(1, rect.height() // 4)))
        movie.jumpToFrame(0)
        _scale_movie()
        host_layout.addWidget(gif_label, 0, Qt.AlignHCenter)

        text_label = QLabel()
        text_label.setAlignment(Qt.AlignHCenter)
        text_label.setStyleSheet("color:#ffffff; font-weight:bold; font-size:18px; margin-top:-6px;")
        host_layout.addWidget(text_label, 0, Qt.AlignHCenter)

        target = "Übersetzen"
        gib = ["xqv!9kz", "k9v!xqz", "qz!9vkx", "9xq!kvz", "zq!9xkv"]
        frames = []
        base = gib[0].ljust(len(target))
        for i in range(len(target) + 1):
            head = target[:i]
            tail = base[i:]
            frames.append(head + tail)
        frames += [target]
        idx = {"i": 0, "phase": 0}

        def tick():
            if idx["phase"] < len(gib):
                text_label.setText(gib[idx["phase"]])
                idx["phase"] += 1
                return
            text_label.setText(frames[idx["i"] % len(frames)])
            idx["i"] += 1

        timer = QTimer(dlg)
        timer.timeout.connect(tick)
        timer.start(120)
        tick()

        self._translate_dialog = dlg
        host.setFixedSize(host.sizeHint())
        dlg.resize(host.sizeHint())
        dlg.setFixedSize(host.sizeHint())
        top_left = self.mapToGlobal(QPoint(0, 0))
        dlg.move(
            top_left.x() + (self.width() - dlg.width()) // 2,
            top_left.y() + (self.height() - dlg.height()) // 2
        )
        QTimer.singleShot(100, dlg.show)

    def _on_export_finished(self, result, path_de, path_fr):
        if getattr(self, "_translate_dialog", None):
            self._translate_dialog.close()
            self._translate_dialog = None
        if not result.get("ok"):
            QMessageBox.critical(self, "Speicherfehler", result.get("error") or "Unbekannter Fehler")
            return
        self.statusBar().showMessage(
            f"Gespeichert unter: {path_de} und {path_fr}", 5000
        )
        missing_fr = result.get("missing") or []
        if missing_fr:
            msg = "Nicht übersetzte Begriffe (bitte in translations_fr.json ergänzen):\n\n"
            if not result.get("argos"):
                msg = ("Offline-Übersetzer (Argos) nicht verfügbar. "
                       "Bitte Argos-Modell in argos_models ablegen.\n\n") + msg
            if not result.get("fasttext"):
                msg = ("Spracherkennung (fastText) nicht verfügbar. "
                       "Bitte lid.176.ftz in fasttext_models ablegen.\n\n") + msg
            msg += "\n".join(missing_fr)
            QMessageBox.information(self, "Fehlende Übersetzungen", msg)

    def _parse_specs_file(self, content: str):
        """
        Returns: (left_header, right_header, rows)
        rows is a list of tuples: (key_plain, value_html)
        1) Prefer embedded JSON snapshot (for old files).
        2) Otherwise reverse from the <table class="specs"> in order.
        """
        # 1) Embedded JSON? (kept for backward compatibility)
        m = re.search(r'<!--\s*SPECS_EDITOR_v(\d+)\s*(\{.*\})\s*-->', content, re.DOTALL)
        if m:
            try:
                ver = int(m.group(1))
                meta = json.loads(m.group(2))
                h_left = meta.get("headers", {}).get("left", DEFAULT_HEADER_LEFT)
                h_right = meta.get("headers", {}).get("right", DEFAULT_HEADER_RIGHT)
                rows_meta = meta.get("rows", []) or []

                rows = []
                if ver >= 2:
                    for r in rows_meta:
                        if r.get("type") == "section":
                            rows.append(("__SECTION__", r.get("title", "")))
                        elif r.get("type") == "cat":
                            rows.append(("__CAT__", r.get("title", "")))
                        else:
                            rows.append((r.get("key", ""), r.get("value_html", "")))
                else:
                    rows = [(r.get("key", ""), r.get("value_html", "")) for r in rows_meta]
                return h_left, h_right, rows
            except Exception:
                pass

        # 2) Fallback: parse the exported table in document order
        # headers
        mh = re.search(
            r'<thead>.*?<tr>\s*<th>(.*?)</th>\s*<th>(.*?)</th>\s*</tr>.*?</thead>',
            content, re.DOTALL | re.IGNORECASE
        )
        if mh:
            h_left = _html.unescape(mh.group(1).strip())
            h_right = _html.unescape(mh.group(2).strip())
        else:
            h_left, h_right = DEFAULT_HEADER_LEFT, DEFAULT_HEADER_RIGHT

        # tbody
        mt = re.search(r'<tbody>(.*?)</tbody>', content, re.DOTALL | re.IGNORECASE)
        rows = []
        if mt:
            tbody = mt.group(1)
            # iterate <tr> in order and decide per row
            for mtr in re.finditer(r'<tr[^>]*>(.*?)</tr>', tbody, re.DOTALL | re.IGNORECASE):
                tr_html = mtr.group(0)

                # section/header row?
                if re.search(r'class="[^"]*\bsection\b[^"]*"', tr_html, re.IGNORECASE):
                    mtitle = re.search(
                        r'<th[^>]*class="[^"]*\bsection\b[^"]*"[^>]*colspan="2"[^>]*>(.*?)</th>',
                        tr_html, re.DOTALL | re.IGNORECASE
                    )
                    title = _html.unescape(mtitle.group(1).strip()) if mtitle else ""
                    rows.append(("__SECTION__", title))
                    continue

                # category row?
                if re.search(r'class="[^"]*\bcat\b[^"]*"', tr_html, re.IGNORECASE):
                    mtitle = re.search(
                        r'<th[^>]*class="[^"]*\bcategory\b[^"]*"[^>]*colspan="2"[^>]*>(.*?)</th>',
                        tr_html, re.DOTALL | re.IGNORECASE
                    )
                    title = _html.unescape(mtitle.group(1).strip()) if mtitle else ""
                    rows.append(("__CAT__", title))
                    continue

                # kv row
                mk = re.search(r'<th>(.*?)</th>', tr_html, re.DOTALL | re.IGNORECASE)
                mv = re.search(r'<td>(.*?)</td>', tr_html, re.DOTALL | re.IGNORECASE)
                if mk and mv:
                    key_plain = _html.unescape(mk.group(1).strip())
                    value_html = (mv.group(1) or "").strip()
                    rows.append((key_plain, value_html))

        return h_left, h_right, rows

    def load_from_file(self):
        """
        File → headers + rows → repopulate UI.
        Preserves rich HTML in value cells; keys are plain text (bold in UI).
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "Öffnen", "", "Text/HTML (*.txt *.html *.htm);;Alle Dateien (*.*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Ladefehler", str(e))
            return

        left_h, right_h, rows = self._parse_specs_file(content)

        # Set headers
        self.hdr_left.setText(left_h or DEFAULT_HEADER_LEFT)
        self.hdr_right.setText(right_h or DEFAULT_HEADER_RIGHT)

        # Clear current rows
        self.rows_widgets.clear()
        # Remove all layout items
        while self.rows_v.count():
            item = self.rows_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        # Re-add rows + tail spacer so rows pin to top
        for key_plain, value_html in rows:
            if key_plain == "__SECTION__":
                row = HeaderRow(value_html, self.icons)
            elif key_plain == "__CAT__":
                row = CategoryRow(value_html, self.icons)  # value_html holds the title here
            else:
                row = EntryRow(key_plain, value_html, self.icons)
            row.requestDelete.connect(self._row_delete)
            row.requestMoveUp.connect(self._row_move_up)
            row.requestMoveDown.connect(self._row_move_down)
            if hasattr(row, "requestFocusToKey"):
                row.requestFocusToKey.connect(lambda: self.key_in.setFocus(Qt.OtherFocusReason))
            self.rows_widgets.append(row)
            self.rows_v.addWidget(row)

        # Focus the input row ready for edits
        self.key_in.setFocus()


def main():
    app = QApplication(sys.argv)
    try_set_modern_app_font()
    apply_brand_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
