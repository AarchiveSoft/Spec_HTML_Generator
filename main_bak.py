# specs_editor.py
# Requirements: Python 3.9+  ->  pip install PySide6
# Focused, fully text-based GUI to build a paste-ready block:
#   <style>…</style> + <table class="specs">…</table>
# - No HTML editing in the UI.
# - Key/Value inputs: Value is multiline + rich text (bold, color, bullets).
# - Key inserted bold by default.
# - Paste buttons for quick clipboard workflows.
# - Headers disabled until "Change Headers" is checked.
# - Title input drives the default export filename.
# - Subtle brand theming using accent #006c8c.

import sys
import os

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import (
    QAction, QKeySequence, QTextCharFormat, QTextCursor, QTextListFormat,
    QTextTableFormat, QFont, QColor, QGuiApplication, QFontDatabase, QClipboard, QPalette, QIcon, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QColorDialog, QCheckBox, QFrame, QSizePolicy
)

APP_TITLE = "Claudias Spezifikationen Assistent"

DEFAULT_HEADER_LEFT = "Kategorie"
DEFAULT_HEADER_RIGHT = "Details"
DEFAULT_EXPORT_TITLE = "Technische_Daten"  # used to prefill the Title field and default filename

# Brand accent color (sparingly used)
ACCENT = "#006c8c"

# Your site CSS, embedded verbatim in the export:
SPEC_TABLE_CSS = """
<style type="text/css">
table.specs {width:100%; border-collapse:collapse; font-family:Arial, Helvetica, sans-serif; font-size:14px;}
      .specs th, .specs td {border:1px solid #ddd; padding:8px; vertical-align:top;}
      .specs th {background:#f5f5f5; text-align:left; width:30%;}
      .specs tr:nth-child(even){background:#fafafa;}
      ul {margin:6px 0 6px 18px; padding:0;}</style>
""".strip()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller .exe """
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def try_set_modern_app_font():
    """Prefer Aptos if installed; otherwise fall back to a clean system UI font (Qt 6-safe static API)."""
    families = set(QFontDatabase.families())
    for name in ("Aptos", "Segoe UI Variable", "Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue"):
        if name in families:
            QGuiApplication.setFont(QFont(name, 10))
            return
    # Fall back to platform default silently


def apply_brand_theme(app: QApplication):
    """
    Subtle, classy theming using the brand accent.
    - Palette: selection, link, highlight.
    - Stylesheet: focus rings, primary buttons, toolbar, headings, checkboxes, scrollbars.
    """
    accent = QColor(ACCENT)

    # Palette nudges (keeps system theme; just make selections/links on-brand)
    pal = app.palette()
    pal.setColor(QPalette.Highlight, accent)
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.Link, accent)
    pal.setColor(QPalette.LinkVisited, accent.darker(110))
    app.setPalette(pal)

    # Global stylesheet
    app.setStyleSheet(f"""
    /* Section headers (use: setProperty("class","section") + setAlignment(Qt.AlignHCenter)) */
    QLabel[class="section"] {{
        color: {ACCENT};
        font-weight: 700;
        font-size: 20px;
        padding: 6px 0 6px 0;
    }}

    /* Subtle separators with accent tint (any HLine) */
    QFrame[frameShape="4"] {{ /* HLine */
        color: {ACCENT};
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                                    stop:0 rgba(0,0,0,0),
                                    stop:0.5 {ACCENT},
                                    stop:1 rgba(0,0,0,0));
        min-height: 1px;
        max-height: 1px;
        border: none;
        margin: 10px 0;
    }}

    /* Formatting toolbar (only this one gets solid accent buttons) */
    QToolBar#formatToolbar {{
        border: none;
        padding: 8px 10px;
        border-bottom: 1px solid rgba(0,0,0,0.08);
    }}
    QToolBar#formatToolbar QToolButton {{
        padding: 6px 12px;
        border-radius: 8px;
        border: 1px solid {ACCENT};
        background: {ACCENT};
        color: #ffffff;
        margin: 0 6px 0 0;
        font-weight: 600;
    }}
    QToolBar#formatToolbar QToolButton:hover {{
        background: rgba(0,108,140,0.90);
    }}
    QToolBar#formatToolbar QToolButton:pressed {{
        background: rgba(0,108,140,0.80);
    }}

    /* Other toolbars keep a clean look */
    QToolBar {{
        border: none;
        padding: 6px;
        border-bottom: 1px solid rgba(0,0,0,0.06);
    }}

    /* Inputs: calm borders; accent focus ring */
    QLineEdit, QTextEdit {{
        border: 1px solid rgba(0,0,0,0.16);
        border-radius: 8px;
        padding: 8px 10px;
        background: palette(base);
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border: 2px solid {ACCENT};
        outline: none;
    }}

    /* Read-only headers look subtly locked */
    QLineEdit[readOnly="true"], QLineEdit[readOnly="1"] {{
        color: palette(text);
        background: palette(alternate-base);
        border: 1px dashed rgba(0,0,0,0.28);
    }}
    QLineEdit[readOnly="true"]:focus, QLineEdit[readOnly="1"]:focus {{
        border: 1px dashed rgba(0,0,0,0.28);
    }}

    /* Truly disabled */
    QLineEdit:disabled, QTextEdit:disabled {{
        color: palette(text);
        background: palette(alternate-base);
    }}

    /* Buttons */
    QPushButton {{
        border: 1px solid rgba(0,0,0,0.2);
        border-radius: 10px;
        padding: 10px 16px;
        background: palette(button);
    }}
    QPushButton:hover {{
        background: rgba(0,0,0,0.04);
    }}
    QPushButton:pressed {{
        background: rgba(0,0,0,0.08);
    }}

    /* Primary buttons (by objectName) use a light accent fill */
    QPushButton#primaryButton {{
        border: 1px solid {ACCENT};
        background: rgba(0,108,140,0.10);
        color: palette(text);
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background: rgba(0,108,140,0.18);
    }}
    QPushButton#primaryButton:pressed {{
        background: rgba(0,108,140,0.24);
    }}

    /* Checkbox accent */
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border-radius: 4px;
        border: 1px solid rgba(0,0,0,0.25);
        background: palette(base);
    }}
    QCheckBox::indicator:checked {{
        border: 1px solid {ACCENT};
        background: {ACCENT};
        image: none;
    }}

    /* Subtle scrollbar accent */
    QScrollBar:vertical {{
        width: 12px; background: transparent; margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        min-height: 24px; border-radius: 6px; background: rgba(0,0,0,0.18);
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(0,0,0,0.28);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px; background: none;
    }}

    /* Status bar line */
    QStatusBar {{
        border-top: 1px solid rgba(0,0,0,0.08);
    }}
    """)


def print_widget_sizes(window, widgets):
    """
    Print width/height of each widget after the UI has been shown.
    :param window: the QMainWindow or QWidget
    :param widgets: dict of {name: widget}
    """
    def _report():
        print("=== Widget sizes ===")
        for name, w in widgets.items():
            if w is not None:
                print(f"{name}: {w.width()} x {w.height()}")
        print("====================")

    # Defer until event loop has settled
    QTimer.singleShot(0, _report)


class RichTextArea(QTextEdit):
    """Rich text control (no raw HTML shown)."""
    def toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if self.fontWeight() != QFont.Bold else QFont.Normal)
        self.mergeCurrentCharFormat(fmt)

    def toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.fontItalic())
        self.mergeCurrentCharFormat(fmt)

    def pick_color(self):
        c = QColorDialog.getColor(self.textColor(), self, "Choose text color")
        if c.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(c)
            self.mergeCurrentCharFormat(fmt)

    def toggle_bullets(self):
        cur = self.textCursor()
        if cur.currentList():
            lst = cur.currentList()
            if lst:
                block_fmt = cur.blockFormat()
                block_fmt.setIndent(0)
                cur.mergeBlockFormat(block_fmt)
                lst.remove(cur.block())
        else:
            lst_fmt = QTextListFormat()
            lst_fmt.setStyle(QTextListFormat.ListDisc)
            cur.createList(lst_fmt)


class SpecsTableEditor(RichTextArea):
    """Editable 2-column table in a rich-text area; export to clean HTML matching your sample."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._table = None
        self.setPlaceholderText(
            "Specs table will appear here. Use the inputs below to add rows,\n"
            "or edit cells directly. Bold/Color/Bullets are available without HTML."
        )

    def ensure_table(self, left_header=DEFAULT_HEADER_LEFT, right_header=DEFAULT_HEADER_RIGHT):
        if self._table is not None:
            return
        cur = self.textCursor()
        cur.movePosition(QTextCursor.End)
        tf = QTextTableFormat()
        tf.setAlignment(Qt.AlignLeft)
        tf.setHeaderRowCount(1)
        tf.setCellPadding(6)
        tf.setCellSpacing(0)
        tf.setBorder(0.8)
        self._table = cur.insertTable(1, 2, tf)
        self._write_cell(0, 0, left_header, header=True)
        self._write_cell(0, 1, right_header, header=True)

    def _write_cell(self, row, col, text, header=False, bold=False):
        cell = self._table.cellAt(row, col)
        cur = cell.firstCursorPosition()
        cur.select(QTextCursor.BlockUnderCursor)
        cur.removeSelectedText()
        if header or bold:
            fmt = QTextCharFormat()
            fmt.setFontWeight(QFont.Bold)
            cur.mergeCharFormat(fmt)
        cur.insertText(text)

    def add_row(self, key_text, value_fragment_html):
        self.ensure_table()
        row_idx = self._table.rows()
        self._table.insertRows(row_idx, 1)

        # Key: plain text, but visually bold by default in the editor
        self._write_cell(row_idx, 0, key_text, header=False, bold=True)

        # Value: rich fragment (preserve bullets/bold/color/newlines)
        start = self._table.cellAt(row_idx, 1).firstCursorPosition()
        cur = self.textCursor()
        cur.setPosition(start.position())
        if not value_fragment_html.strip():
            cur.insertText("")
        else:
            cur.insertHtml(value_fragment_html)

    def delete_selected_row(self):
        if not self._table:
            return
        cur = self.textCursor()
        cell = self._table.cellAt(cur)
        if not cell.isValid():
            return
        row = cell.row()
        if row == 0:
            return
        self._table.removeRows(row, 1)

    def move_selected_row(self, direction):
        if not self._table:
            return
        cur = self.textCursor()
        cell = self._table.cellAt(cur)
        if not cell.isValid():
            return
        row = cell.row()
        if row == 0:
            return
        target = row + direction
        if target < 1 or target >= self._table.rows():
            return

        def get_plain(r, c):
            return self._table.cellAt(r, c).firstCursorPosition().block().text()

        def set_plain(r, c, text, make_bold=False):
            self._write_cell(r, c, text, header=False, bold=make_bold)

        a_left = get_plain(row, 0)
        a_right = get_plain(row, 1)
        b_left = get_plain(target, 0)
        b_right = get_plain(target, 1)

        set_plain(row, 0, b_left, make_bold=True)
        set_plain(row, 1, b_right)
        set_plain(target, 0, a_left, make_bold=True)
        set_plain(target, 1, a_right)

        self.setTextCursor(self._table.cellAt(target, 0).firstCursorPosition())

    def extract_headers_and_rows_as_html(self):
        """Returns (left_header, right_header, rows_as_html) preserving value formatting."""
        if not self._table or self._table.rows() < 1:
            return DEFAULT_HEADER_LEFT, DEFAULT_HEADER_RIGHT, []
        h_left = self._table.cellAt(0, 0).firstCursorPosition().block().text()
        h_right = self._table.cellAt(0, 1).firstCursorPosition().block().text()
        rows = []
        for r in range(1, self._table.rows()):
            key_plain = self._table.cellAt(r, 0).firstCursorPosition().block().text()
            val_html = _cell_inner_html(self._table, r, 1)
            rows.append((key_plain, val_html))
        return h_left, h_right, rows


def _extract_inner_html_from_selection(sel_cursor: QTextCursor) -> str:
    """Extract inner <body>… content from a QTextDocumentFragment's HTML, or fallback to escaped text with <br>."""
    frag = sel_cursor.selection().toHtml()
    start_tag = "<body"
    start = frag.find(start_tag)
    if start == -1:
        return _escape_html(sel_cursor.selection().toPlainText()).replace("\n", "<br />")
    start = frag.find(">", start)
    end = frag.rfind("</body>")
    if start == -1 or end == -1:
        return _escape_html(sel_cursor.selection().toPlainText()).replace("\n", "<br />")
    inner = frag[start + 1:end].strip()
    return inner


def _cell_inner_html(table, r, c) -> str:
    start = table.cellAt(r, c).firstCursorPosition()
    end = table.cellAt(r, c).lastCursorPosition()
    cur = QTextCursor(start.document())
    cur.setPosition(start.position())
    cur.setPosition(end.position(), QTextCursor.KeepAnchor)
    return _extract_inner_html_from_selection(cur)


def _escape_html(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def _sanitize_filename(name: str) -> str:
    valid = "".join(ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in name).strip()
    return "_".join(valid.split()) or DEFAULT_EXPORT_TITLE


def make_separator() -> QFrame:
    """Accent-tinted HLine separator (picks up stylesheet for HLine)."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line

# 2) Helper to add an icon-only action with tooltip + shortcut
def add_icon_action(toolbar, icon: QIcon, tooltip: str, shortcut: QKeySequence | str, slot):
    act = QAction(icon, "", toolbar)   # empty text → icon-only
    act.setToolTip(tooltip)            # tooltip on hover
    act.setStatusTip(tooltip)          # shows in status bar (nice!)
    if shortcut:
        act.setShortcut(shortcut)
    act.triggered.connect(slot)
    toolbar.addAction(act)
    return act


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(resource_path("icons\\icon_gra.ico")))
        self.resize(1040, 820)  # a bit larger by default for breathing room
        try_set_modern_app_font()
        apply_brand_theme(QApplication.instance())

        # --- Formatting toolbar (accent buttons) — vertical, embedded left of inputs ---
        from PySide6.QtWidgets import QSizePolicy  # ensure imported
        tb = QToolBar("Formatierung")
        tb.setObjectName("formatToolbar")
        tb.setOrientation(Qt.Vertical)
        tb.setIconSize(QSize(18, 18))
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        tb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)  # fill vertical space

        # Load icons
        bold_icon = QIcon(resource_path("icons/bold.svg"))
        italic_icon = QIcon(resource_path("icons/italic.svg"))
        color_icon = QIcon(resource_path("icons/color.svg"))
        list_icon = QIcon(resource_path("icons/list.svg"))

        # Helper: a vertical stretch widget for the toolbar
        def _vstretch():
            w = QWidget()
            w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
            w.setMinimumWidth(1)  # keeps toolbar narrow
            return w

        # Icon-only actions with tooltips + shortcuts
        act_bold = QAction(bold_icon, "", self)
        act_bold.setToolTip("Fett (Ctrl+B)")
        act_bold.setStatusTip("Fett (Ctrl+B)")
        act_bold.setShortcut(QKeySequence.Bold)
        act_bold.triggered.connect(self.on_bold)

        act_italic = QAction(italic_icon, "", self)
        act_italic.setToolTip("Kursiv (Ctrl+I)")
        act_italic.setStatusTip("Kursiv (Ctrl+I)")
        act_italic.setShortcut(QKeySequence.Italic)
        act_italic.triggered.connect(self.on_italic)

        act_color = QAction(color_icon, "", self)
        act_color.setToolTip("Textfarbe wählen")
        act_color.setStatusTip("Textfarbe wählen")
        act_color.triggered.connect(self.on_color)

        act_bullets = QAction(list_icon, "", self)
        act_bullets.setToolTip("Liste (Ctrl+Shift+8)")
        act_bullets.setStatusTip("Liste (Ctrl+Shift+8)")
        act_bullets.setShortcut("Ctrl+Shift+8")
        act_bullets.triggered.connect(self.on_bullets)

        # Add N+1 stretches around N actions -> equal vertical spacing
        tb.addWidget(_vstretch())
        tb.addAction(act_bold)
        tb.addWidget(_vstretch())
        tb.addAction(act_italic)
        tb.addWidget(_vstretch())
        tb.addAction(act_color)
        tb.addWidget(_vstretch())
        tb.addAction(act_bullets)
        tb.addWidget(_vstretch())

        # --- Main content ---
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 20, 18, 20)  # breathing room
        outer.setSpacing(18)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_label = QLabel("Titel:")
        self.title_in = QLineEdit(DEFAULT_EXPORT_TITLE)
        title_row.addWidget(title_label)
        title_row.addWidget(self.title_in)
        outer.addLayout(title_row)

        # Separator
        outer.addWidget(make_separator())

        # Headers controls (disabled by default, gated by checkbox)
        hdr_row1 = QHBoxLayout()
        hdr_row1.setSpacing(12)
        self.chk_headers = QCheckBox("Überschriften ändern?")
        self.chk_headers.toggled.connect(self.on_headers_toggled)
        hdr_row1.addWidget(self.chk_headers)
        hdr_row1.addStretch(1)
        outer.addLayout(hdr_row1)

        hdr_row2 = QHBoxLayout()
        hdr_row2.setSpacing(12)
        self.h_left = QLineEdit(DEFAULT_HEADER_LEFT);
        self.h_left.setReadOnly(True)
        self.h_right = QLineEdit(DEFAULT_HEADER_RIGHT);
        self.h_right.setReadOnly(True)
        apply_headers = QPushButton("Überschriften anwenden");
        apply_headers.setEnabled(False)
        apply_headers.setObjectName("primaryButton")
        self.apply_headers_btn = apply_headers
        apply_headers.clicked.connect(self.apply_headers)
        hdr_row2.addWidget(self.h_left);
        hdr_row2.addWidget(self.h_right);
        hdr_row2.addWidget(apply_headers)
        outer.addLayout(hdr_row2)

        # Separator before “Eintrag hinzufügen”
        outer.addWidget(make_separator())

        # Section heading: Eintrag hinzufügen
        add_label = QLabel("Eintrag hinzufügen")
        add_label.setProperty("class", "section")
        add_label.setAlignment(Qt.AlignHCenter)
        outer.addWidget(add_label)

        # --- Key/Value block with vertical toolbar on the left ---

        # Key row
        kv_row1 = QHBoxLayout()
        kv_row1.setSpacing(12)
        self.key_in = QLineEdit()
        self.key_in.setPlaceholderText("Schlüssel (Kategorie / Titel)")
        paste_key = QPushButton("Schlüssel einfügen (Zwischenablage)")
        paste_key.clicked.connect(self.paste_key_from_clipboard)
        kv_row1.addWidget(self.key_in, 1)
        kv_row1.addWidget(paste_key, 0)

        # Value row
        kv_row2 = QHBoxLayout()
        kv_row2.setSpacing(12)
        self.val_in = RichTextArea()
        self.val_in.setPlaceholderText("Wert (Liste, Fett, Kursiv, Farbe). \nEnter = Neue Zeile")
        self.val_in.setAcceptRichText(True)
        self.val_in.setMinimumHeight(200)
        self.val_in.setMinimumWidth(636)

        right_buttons = QVBoxLayout()
        right_buttons.setSpacing(10)
        paste_val = QPushButton("Wert einfügen (Zwischenablage)")
        add_btn = QPushButton("Eintrag hinzufügen")
        add_btn.setObjectName("primaryButton")
        export_btn_sidecar = QPushButton("Exportieren")
        export_btn_sidecar.setObjectName("primaryButton")
        paste_val.clicked.connect(self.paste_value_from_clipboard)
        add_btn.clicked.connect(self.add_kv)
        export_btn_sidecar.clicked.connect(self.export_table_only)
        right_buttons.addWidget(paste_val)
        right_buttons.addStretch(1)
        right_buttons.addWidget(add_btn)
        right_buttons.addWidget(export_btn_sidecar)

        kv_row2.addWidget(self.val_in, 2)
        kv_row2.addLayout(right_buttons, 1)

        # Right side panel that contains key+value rows (so toolbar can match its height)
        right_panel = QWidget()
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        kv_right = QVBoxLayout(right_panel)
        kv_right.setSpacing(12)
        kv_right.addLayout(kv_row1)
        kv_right.addLayout(kv_row2)

        # Wrap with a horizontal layout: toolbar (left) + right_panel (right)
        kv_block = QHBoxLayout()
        kv_block.setSpacing(12)
        kv_block.addWidget(tb, 0)  # IMPORTANT: no AlignTop, let it expand vertically
        kv_block.addWidget(right_panel, 1)
        outer.addLayout(kv_block)

        self.statusBar().showMessage("Bereit")

        # Separator before “Vorschau”
        outer.addWidget(make_separator())

        # Section heading: Vorschau
        specs_label = QLabel("Vorschau")
        specs_label.setProperty("class", "section")
        specs_label.setAlignment(Qt.AlignHCenter)
        outer.addWidget(specs_label)

        self.specs = SpecsTableEditor()
        spec_layout = QHBoxLayout()
        spec_layout.setSpacing(12)

        image_layout = QVBoxLayout()
        image_layout.setSpacing(6)
        robot_label = QLabel(self)
        robot_image = QPixmap('icons\\robot_gra_100px.png')
        robot_label.setPixmap(robot_image)
        robot_label.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)

        bubble_label = QLabel(self)
        bubble_image = QPixmap('icons\\speech_bubble.png')
        bubble_label.setPixmap(bubble_image)
        bubble_label.setAlignment(Qt.AlignHCenter)

        image_layout.addStretch()
        image_layout.addWidget(bubble_label)
        image_layout.addWidget(robot_label)
        spec_layout.addWidget(self.specs, 3)
        spec_layout.addLayout(image_layout, 1)

        outer.addLayout(spec_layout)

        # Separator before row management
        outer.addWidget(make_separator())

        # Row management
        ops = QHBoxLayout()
        ops.setSpacing(12)
        up = QPushButton("Nach Oben")
        down = QPushButton("Nach Unten")
        delete = QPushButton("Eintrag löschen")
        up.clicked.connect(lambda: self.specs.move_selected_row(-1))
        down.clicked.connect(lambda: self.specs.move_selected_row(+1))
        delete.clicked.connect(self.specs.delete_selected_row)
        ops.addWidget(up)
        ops.addWidget(down)
        ops.addStretch(1)
        ops.addWidget(delete)
        outer.addLayout(ops)

        # Ensure table exists
        self.specs.ensure_table(DEFAULT_HEADER_LEFT, DEFAULT_HEADER_RIGHT)

        # Debug sizes (optional)
        print_widget_sizes(self, {
            "Key Input"         : self.key_in,
            "Value input"       : self.val_in,
            "paste key"         : paste_key,
            "paste val"         : paste_val,
            "hinz button"       : add_btn,
            "exportieren button": export_btn_sidecar,
            "Vorschau"          : self.specs
        })

    # Formatting targeting whichever rich text widget has focus (Value editor or table)
    def current_text_widget(self):
        w = QApplication.focusWidget()
        return w if isinstance(w, QTextEdit) else self.specs

    def on_bold(self):
        w = self.current_text_widget()
        if hasattr(w, "toggle_bold"):
            w.toggle_bold()

    def on_italic(self):
        w = self.current_text_widget()
        if hasattr(w, "toggle_italic"):
            w.toggle_italic()

    def on_color(self):
        w = self.current_text_widget()
        if hasattr(w, "pick_color"):
            w.pick_color()

    def on_bullets(self):
        w = self.current_text_widget()
        if hasattr(w, "toggle_bullets"):
            w.toggle_bullets()

    # Headers
    def on_headers_toggled(self, checked: bool):
        # checked = “Change Headers” ON → editable
        self.h_left.setReadOnly(not checked)
        self.h_right.setReadOnly(not checked)
        self.apply_headers_btn.setEnabled(checked)

    def apply_headers(self):
        left = self.h_left.text().strip() or DEFAULT_HEADER_LEFT
        right = self.h_right.text().strip() or DEFAULT_HEADER_RIGHT
        self.specs.ensure_table(left, right)
        self.specs._write_cell(0, 0, left, header=True)
        self.specs._write_cell(0, 1, right, header=True)

    # Paste helpers
    def paste_key_from_clipboard(self):
        cb: QClipboard = QApplication.clipboard()
        text = cb.text() or ""
        self.key_in.insert(text)

    def paste_value_from_clipboard(self):
        self.val_in.setFocus()
        self.val_in.paste()  # preserves rich formatting

    # Add KV
    def add_kv(self):
        key = self.key_in.text().strip()
        if not key:
            QMessageBox.information(self, "Fehlender Schlüssel", "Bitte Schlüssel eingeben.")
            return

        # Grab rich fragment HTML from the Value input (inner body only)
        cur = self.val_in.textCursor()
        cur.select(QTextCursor.Document)
        frag_html = _extract_inner_html_from_selection(cur)
        if not frag_html.strip():
            QMessageBox.information(self, "Fehlender Wert", "Bitte Wert eingeben.")
            return

        self.specs.add_row(key, frag_html)
        self.key_in.clear()
        self.val_in.clear()
        self.key_in.setFocus()

    # Export exactly: <style> … </style> + <table class="specs">…</table>
    def export_table_only(self):
        left_h, right_h, rows = self.specs.extract_headers_and_rows_as_html()
        if not rows:
            if QMessageBox.question(self, "No rows", "The specs table is empty. Export anyway?") != QMessageBox.Yes:
                return

        lines = []
        lines.append(SPEC_TABLE_CSS)
        lines.append(f'<table border="1" class="specs">')
        lines.append("\t<thead>")
        lines.append("\t\t<tr>")
        lines.append(f"\t\t\t<th>{_escape_html(left_h)}</th>")
        lines.append(f"\t\t\t<th>{_escape_html(right_h)}</th>")
        lines.append("\t\t</tr>")
        lines.append("\t</thead>")
        lines.append("\t<tbody>")
        for key_plain, val_html in rows:
            lines.append("\t\t<tr>")
            lines.append(f"\t\t\t<th>{_escape_html(key_plain)}</th>")
            lines.append(f"\t\t\t<td>{val_html}</td>")
            lines.append("\t\t</tr>")
        lines.append("\t</tbody>")
        lines.append("</table>")
        out = "\n".join(lines)

        # Filename based on Title
        base = _sanitize_filename(self.title_in.text().strip() or DEFAULT_EXPORT_TITLE)
        default_name = f"{base}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save (paste-ready HTML)", default_name,
            "Text/HTML (*.txt *.html *.htm);;All Files (*.*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(out)
            self.statusBar().showMessage(f"Saved to {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))


def main():
    app = QApplication(sys.argv)
    try_set_modern_app_font()
    apply_brand_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
