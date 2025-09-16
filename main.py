# specs_editor.py
# Requirements: Python 3.9+  ->  pip install PySide6

import sys, os
import re
import json
import html as _html
from PySide6.QtCore import Qt, QSize, QTimer, Signal, QPoint
from PySide6.QtGui import (
    QAction, QKeySequence, QTextCharFormat, QTextCursor, QTextListFormat,
    QFont, QColor, QGuiApplication, QFontDatabase, QClipboard, QPalette, QIcon, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QColorDialog, QCheckBox, QFrame, QSizePolicy, QScrollArea, QGridLayout,
    QToolButton, QSpacerItem
)

APP_TITLE = "Claudias Spezifikationen Assistent"

DEFAULT_HEADER_LEFT  = "Kategorie"
DEFAULT_HEADER_RIGHT = "Details"
DEFAULT_EXPORT_TITLE = "Technische_Daten"
ACCENT = "#006c8c"

SPEC_TABLE_CSS = """
<style type="text/css">
table.specs {width:100%; border-collapse:collapse; font-family:Arial, Helvetica, sans-serif; font-size:14px;}
      .specs th, .specs td {border:1px solid #ddd; padding:8px; vertical-align:top;}
      .specs th {background:#f5f5f5; text-align:left; width:30%;}
      .specs tr:nth-child(even){background:#fafafa;}
      ul {margin:6px 0 6px 18px; padding:0;}</style>
""".strip()

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
            self.insertPlainText(text)
        else:
            super().insertFromMimeData(source)

    def paste(self):
        cb = QApplication.clipboard()
        self.insertPlainText(cb.text() or "")

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
        t = t.strip("\n")  # keep inner newlines
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
        self.key.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

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
        cur = self.val.textCursor(); cur.select(QTextCursor.Document)
        frag = cur.selection().toHtml()
        start = frag.find("<body")
        if start == -1:
            return _escape_html(self.val.toPlainText()).replace("\n", "<br />")
        start = frag.find(">", start)
        end = frag.rfind("</body>")
        if start == -1 or end == -1:
            return _escape_html(self.val.toPlainText()).replace("\n", "<br />")
        return frag[start+1:end].strip()

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


# ---------- Main window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(resource_path("icons\\icon_gra.ico")))
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

        # --- Bottom row: add-category button (spans both columns) ---
        self.btn_add_cat = QPushButton("Kategoriezeile\neinfügen")
        self.btn_add_cat.setObjectName("accentSmall")
        self.btn_add_cat.setToolTip("Abschnitts-Überschrift in die Liste einfügen")
        self.btn_add_cat.clicked.connect(self.add_category_row)  # expects you implemented add_category_row()

        # open button
        open_button = QPushButton("Öffnen...")
        open_button.setObjectName("primaryButton")
        open_button.setShortcut(QKeySequence.Open)
        open_button.clicked.connect(self.load_from_file)

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
        lh_layout.addWidget(format_panel, 0)
        lh_layout.addWidget(self.btn_add_cat)
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

        # Row 1: inputs
        self.key_in = PlainPasteLineEdit()
        self.key_in.setPlaceholderText("Schlüssel Eingabe")
        _f = self.key_in.font()
        _f.setBold(True)
        self.key_in.setFont(_f)
        self.key_in.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.val_in = PlainPasteTextEdit(min_lines=3, max_lines=12)
        self.val_in.setPlaceholderText("Wert Eingabe (Ctrl+Enter bestätigt)")
        self.confirm_btn = QPushButton("Bestätigen");
        self.confirm_btn.setObjectName("primaryButton")
        self.confirm_btn.clicked.connect(self.confirm_current_input)
        self.key_in.returnPressed.connect(self.confirm_current_input)
        self.val_in.confirm.connect(self.confirm_current_input)
        self.val_in.heightChanged.connect(lambda h: self.key_in.setFixedHeight(h))
        self.key_in.setFixedHeight(self.val_in.height())

        table_grid.addWidget(self.key_in, 1, 0)
        table_grid.addWidget(vline(), 1, 1)
        table_grid.addWidget(self.val_in, 1, 2)
        table_grid.addWidget(vline(), 1, 3)
        table_grid.addWidget(self.confirm_btn, 1, 4, Qt.AlignVCenter)

        # Row 2: paste buttons
        self.btn_paste_key = QPushButton("Schlüssel einfügen (Zwischenablage)")
        self.btn_paste_val = QPushButton("Wert einfügen (Zwischenablage)")
        for b in (self.btn_paste_key, self.btn_paste_val):
            b.setObjectName("accentSmall")
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_paste_key.clicked.connect(self.paste_key_plain)
        self.btn_paste_val.clicked.connect(self.paste_value_plain)

        confirm_width = self.confirm_btn.sizeHint().width()
        confirm_spacer = QSpacerItem(confirm_width, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)

        table_grid.addWidget(self.btn_paste_key, 2, 0, Qt.AlignTop)
        table_grid.addWidget(vline(), 2, 1)
        table_grid.addWidget(self.btn_paste_val, 2, 2, Qt.AlignTop)
        table_grid.addWidget(vline(), 2, 3)
        table_grid.addItem(confirm_spacer, 2, 4, Qt.AlignTop)

        paste_h = max(self.btn_paste_key.sizeHint().height(), self.btn_paste_val.sizeHint().height())
        table_grid.setRowMinimumHeight(2, paste_h)
        table_grid.setRowStretch(2, 0)
        shell.addWidget(table)

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
        self.btn_export = QPushButton("Exportieren");
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_table_only)
        footer.addStretch(1);
        footer.addWidget(self.btn_export, alignment=Qt.AlignBottom)
        shell.addLayout(footer)

        # Compose
        block.addLayout(shell, 1)
        outer.addLayout(block)

        self.statusBar().showMessage("Bereit")

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
        return t

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
        # clear all items (widgets + spacers)
        while self.rows_v.count():
            item = self.rows_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        # re-add rows
        for r in self.rows_widgets:
            self.rows_v.addWidget(r)

        # ensure the tail spacer is the final item
        self.rows_v.addItem(self._tail_spacer)
        self._scroll_row_bottom_into_view(self.rows_widgets[-1] if self.rows_widgets else None)

    # Export exact table
    def export_table_only(self):
        left_h = self.hdr_left.text().strip() or DEFAULT_HEADER_LEFT
        right_h = self.hdr_right.text().strip() or DEFAULT_HEADER_RIGHT

        # --- Build HTML table (category rows render full-width) ---
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

        rows_meta = []  # for JSON snapshot v2

        for rw in self.rows_widgets:
            # Category row?
            try:
                from types import SimpleNamespace
                is_category = hasattr(rw, "title_plain") and not hasattr(rw, "key_plain")
            except Exception:
                is_category = False

            if is_category:
                title = _escape_html(rw.title_plain())
                lines.append('\t\t<tr class="cat">')
                lines.append(f'\t\t\t<th class="category" colspan="2">{title}</th>')
                lines.append('\t\t</tr>')
                rows_meta.append({"type": "cat", "title": rw.title_plain()})
            else:
                # Key/Value row
                k = _escape_html(rw.key_plain())
                v = rw.val_html()
                # Skip completely empty rows
                if not (k or v):
                    continue
                lines.append("\t\t<tr>")
                lines.append(f"\t\t\t<th>{k}</th>")
                lines.append(f"\t\t\t<td>{v}</td>")
                lines.append("\t\t</tr>")
                rows_meta.append({"type": "kv", "key": rw.key_plain(), "value_html": v})

        lines.append("\t</tbody>")
        lines.append("</table>")

        # --- Embed a JSON snapshot for perfect round-trip (version 2 supports categories) ---
        snapshot = {
            "headers": {"left": left_h, "right": right_h},
            "rows"   : rows_meta,
            "version": 2,
        }
        lines.append(f"\n<!-- SPECS_EDITOR_v2 {json.dumps(snapshot, ensure_ascii=False)} -->\n")

        out = "\n".join(lines)

        # --- Save dialog ---
        base = self.title_in.text().strip() or DEFAULT_EXPORT_TITLE
        base = "".join(ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in base).strip()
        base = "_".join(base.split()) or DEFAULT_EXPORT_TITLE
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

    def _parse_specs_file(self, content: str):
        """
        Returns: (left_header, right_header, rows)
        rows is a list of tuples: (key_plain, value_html)
        1) Prefer embedded JSON snapshot.
        2) Fallback to simple regex table parse for legacy files.
        """
        # 1) Embedded JSON?
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
                        if r.get("type") == "cat":
                            rows.append(("__CAT__", r.get("title", "")))  # sentinel form
                        else:
                            rows.append((r.get("key", ""), r.get("value_html", "")))
                else:
                    # v1 = only KV rows
                    rows = [(r.get("key", ""), r.get("value_html", "")) for r in rows_meta]

                return h_left, h_right, rows
            except Exception:
                pass

        # 2) Fallback: parse the table we export (predictable structure)
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

        # body rows
        mt = re.search(r'<tbody>(.*?)</tbody>', content, re.DOTALL | re.IGNORECASE)
        rows = []
        if mt:
            tbody = mt.group(1)
            # additionally detect category rows like: <tr class="cat"><th class="category" colspan="2">Title</th></tr>
            for mcat in re.finditer(
                    r'<tr[^>]*class="[^"]*\bcat\b[^"]*"[^>]*>\s*<th[^>]*class="[^"]*\bcategory\b[^"]*"[^>]*colspan="2"[^>]*>(.*?)</th>\s*</tr>',
                    content, re.DOTALL | re.IGNORECASE
            ):
                title = _html.unescape(mcat.group(1).strip())
                rows.append(("__CAT__", title))
            for mrow in re.finditer(
                    r'<tr>\s*<th>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>',
                    tbody, re.DOTALL | re.IGNORECASE
            ):
                key_plain = _html.unescape(mrow.group(1).strip())
                value_html = mrow.group(2).strip()  # keep inner HTML intact
                rows.append((key_plain, value_html))

        return h_left, h_right, rows

    def load_from_file(self):
        """
        File → headers + rows → repopulate UI.
        Preserves rich HTML in value cells; keys are plain text (bold in UI).
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "Öffnen", "", "Text/HTML (*.txt *.html *.htm);;All Files (*.*)"
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
            if key_plain == "__CAT__":
                row = CategoryRow(value_html, self.icons)  # value_html holds the title here
            else:
                row = EntryRow(key_plain, value_html, self.icons)
            row.requestDelete.connect(self._row_delete)
            row.requestMoveUp.connect(self._row_move_up)
            row.requestMoveDown.connect(self._row_move_down)
            self.rows_widgets.append(row)
            self.rows_v.addWidget(row)

        # tail spacer
        self.tail_spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.rows_v.addItem(self.tail_spacer)

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
