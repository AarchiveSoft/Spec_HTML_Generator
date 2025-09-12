# specs_editor.py
# Requirements: Python 3.9+  ->  pip install PySide6

import sys, os
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import (
    QAction, QKeySequence, QTextCharFormat, QTextCursor, QTextListFormat,
    QFont, QColor, QGuiApplication, QFontDatabase, QClipboard, QPalette, QIcon, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QColorDialog, QCheckBox, QFrame, QSizePolicy, QScrollArea, QGridLayout,
    QToolButton
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

    /* Accent separator lines */
    QFrame[frameShape="4"] {{
        color: {ACCENT};
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                                    stop:0 rgba(0,0,0,0),
                                    stop:0.5 {ACCENT},
                                    stop:1 rgba(0,0,0,0));
        min-height: 1px; max-height: 1px; border: none; margin: 10px 0;
    }}

    /* Formatting toolbar (vertical, accent buttons) */
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

    /* Table-like look */
    .KVTable QLineEdit, .KVTable QTextEdit {{
        border: 1px solid rgba(0,0,0,0.18);
        border-radius: 0; padding: 8px 10px; background: palette(base);
    }}
    .KVTable QLineEdit:focus, .KVTable QTextEdit:focus {{
        border: 2px solid {ACCENT}; outline: none;
    }}

    /* Header cells styled like your <th> */
    .HeaderCell {{
        font-weight: 700;
        background: #f5f5f5;
    }}

    /* Input row highlight */
    .InputRow QLineEdit, .InputRow QTextEdit {{
        background: rgba(0,108,140,0.06);
        border: 1px solid rgba(0,108,140,0.30);
    }}

    /* Primary buttons */
    QPushButton#primaryButton {{
        border: 1px solid {ACCENT}; background: rgba(0,108,140,0.10);
        color: palette(text); font-weight: 600; padding: 10px 16px; border-radius: 10px;
    }}
    QPushButton#primaryButton:hover  {{ background: rgba(0,108,140,0.18); }}
    QPushButton#primaryButton:pressed{{ background: rgba(0,108,140,0.24); }}

    /* Small action buttons on rows */
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
        # ensure wrapping width updates
        self.document().setTextWidth(self.viewport().width())
        super().resizeEvent(e)
        self._update_height()

    def _natural_height(self):
        fm = self.fontMetrics()
        line = fm.lineSpacing()
        margin = self.document().documentMargin()
        # natural doc height based on layout
        doc_h = self.document().size().height()
        # baseline for min/max
        min_h = int(line * self._min_lines + margin * 2 + 6)
        max_h = int(line * self._max_lines + margin * 2 + 6)
        nat = int(doc_h + margin * 2 + 6)
        return max(min_h, min(nat, max_h)), min_h, max_h

    def _update_height(self):
        h, _, _ = self._natural_height()
        if abs(self.height() - h) > 2:
            self.setFixedHeight(h)
            self.heightChanged.emit(h)

# ---------- Entry row with actions ----------
class EntryRow(QWidget):
    requestDelete = Signal(object)
    requestMoveUp = Signal(object)
    requestMoveDown = Signal(object)

    def __init__(self, key_text: str, value_html: str, icons: dict[str, QIcon], parent=None):
        super().__init__(parent)
        self.setProperty("class", "KVTable")  # for cell styles

        self.row_layout = QHBoxLayout(self)
        self.row_layout.setContentsMargins(0,0,0,0)
        self.row_layout.setSpacing(0)

        self.key = QLineEdit(key_text)
        self.key.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.val = AutoGrowTextEdit(min_lines=3, max_lines=12)
        self.val.setAcceptRichText(True)
        if value_html:
            self.val.setHtml(f"<div>{value_html}</div>")

        # Keep key cell height tracking the value height
        self.val.heightChanged.connect(self._sync_key_height)
        self._sync_key_height(self.val.height())

        # Actions on the right
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

        # Assemble row (key | value | actions)
        self.row_layout.addWidget(self.key, 1)
        self.row_layout.addSpacing(1)   # thin grid line
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
            "up"    : QIcon(resource_path("icons/arrow-up.svg")),
            "down"  : QIcon(resource_path("icons/arrow-down.svg")),
            "delete": QIcon(resource_path("icons/trash.svg")),
        }

        # --- Vertical formatting toolbar (left) ---
        tb = QToolBar("Formatierung")
        tb.setObjectName("formatToolbar")
        tb.setOrientation(Qt.Vertical)
        tb.setIconSize(QSize(18, 18))
        tb.setMovable(False); tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        tb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        act_bold   = QAction(self.icons["bold"],  "", self);  act_bold.setToolTip("Fett (Ctrl+B)")
        act_italic = QAction(self.icons["italic"],"", self);  act_italic.setToolTip("Kursiv (Ctrl+I)")
        act_color  = QAction(self.icons["color"], "", self);  act_color.setToolTip("Textfarbe wählen")
        act_list   = QAction(self.icons["list"],  "", self);  act_list.setToolTip("Liste (Ctrl+Shift+8)")
        act_bold.setShortcut(QKeySequence.Bold); act_bold.triggered.connect(self.on_bold)
        act_italic.setShortcut(QKeySequence.Italic); act_italic.triggered.connect(self.on_italic)
        act_list.setShortcut("Ctrl+Shift+8"); act_list.triggered.connect(self.on_bullets)
        act_color.triggered.connect(self.on_color)

        def _vstretch():
            w = QWidget(); w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding); w.setMinimumWidth(1); return w
        for act in (act_bold, act_italic, act_color, act_list):
            tb.addWidget(_vstretch()); tb.addAction(act)
        tb.addWidget(_vstretch())

        # --- Main content ---
        central = QWidget(); self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 20, 18, 20); outer.setSpacing(18)

        # Title
        title_row = QHBoxLayout(); title_row.setSpacing(12)
        title_label = QLabel("Titel:"); self.title_in = QLineEdit(DEFAULT_EXPORT_TITLE)
        title_row.addWidget(title_label); title_row.addWidget(self.title_in)
        outer.addLayout(title_row)
        outer.addWidget(make_separator())

        # --- Unified table block ---
        block = QHBoxLayout(); block.setSpacing(12)

        # Right side table shell
        shell = QVBoxLayout(); shell.setSpacing(8)

        # Header row (in table)
        hdr_container = QWidget(); hdr_container.setProperty("class", "KVTable")
        hdr_l = QHBoxLayout(hdr_container); hdr_l.setContentsMargins(0,0,0,0); hdr_l.setSpacing(0)
        self.hdr_left  = QLineEdit(DEFAULT_HEADER_LEFT);  self.hdr_left.setReadOnly(True)
        self.hdr_right = QLineEdit(DEFAULT_HEADER_RIGHT); self.hdr_right.setReadOnly(True)
        for e in (self.hdr_left, self.hdr_right):
            e.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            e.setProperty("class", "HeaderCell")
        # header edit toggle
        self.chk_hdr_edit = QCheckBox("Bearbeiten")
        self.chk_hdr_edit.setToolTip("Überschriften bearbeiten")
        self.chk_hdr_edit.toggled.connect(self._on_hdr_edit_toggled)

        hdr_l.addWidget(self.hdr_left, 1)
        hdr_l.addSpacing(1)
        hdr_l.addWidget(self.hdr_right, 2)
        hdr_l.addSpacing(1)
        hdr_actions = QWidget()
        ha = QHBoxLayout(hdr_actions); ha.setContentsMargins(6,0,0,0)
        ha.addWidget(self.chk_hdr_edit)
        hdr_l.addWidget(hdr_actions, 0)

        shell.addWidget(hdr_container)

        # Input row (highlighted) — fixed baseline of ~3 lines, grows as needed
        input_container = QWidget(); input_container.setProperty("class", "KVTable")
        input_container.setObjectName("InputRow")
        input_l = QHBoxLayout(input_container); input_l.setContentsMargins(0,0,0,0); input_l.setSpacing(0)
        self.key_in = QLineEdit(); self.key_in.setPlaceholderText("Key input")
        self.key_in.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.val_in = AutoGrowTextEdit(min_lines=3, max_lines=12)
        self.val_in.setAcceptRichText(True)
        self.val_in.setPlaceholderText("Value input (Ctrl+Enter bestätigt)")
        self.confirm_btn = QPushButton("Bestätigen"); self.confirm_btn.setObjectName("primaryButton")
        self.confirm_btn.clicked.connect(self.confirm_current_input)
        self.key_in.returnPressed.connect(self.confirm_current_input)
        self.val_in.confirm.connect(self.confirm_current_input)

        # keep key cell height in sync with value
        self.val_in.heightChanged.connect(lambda h: self.key_in.setFixedHeight(h))
        self.key_in.setFixedHeight(self.val_in.height())

        input_l.addWidget(self.key_in, 1)
        input_l.addSpacing(1)
        input_l.addWidget(self.val_in, 2)
        input_l.addSpacing(1)
        input_l.addWidget(self.confirm_btn, 0)

        shell.addWidget(input_container)

        # Scroll area for created rows ONLY
        rows_frame = QWidget(); rows_frame.setProperty("class", "KVTable")
        self.rows_v = QVBoxLayout(rows_frame); self.rows_v.setContentsMargins(0,0,0,0); self.rows_v.setSpacing(0)
        self.rows_widgets: list[EntryRow] = []

        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(rows_frame)
        self.scroll.setMaximumHeight(520)
        shell.addWidget(self.scroll)

        # Export + robot footer
        footer = QHBoxLayout(); footer.setSpacing(12)
        self.btn_export = QPushButton("Exportieren"); self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_table_only)
        footer.addStretch(1); footer.addWidget(self.btn_export)

        # robot
        robo_wrap = QHBoxLayout()
        robo_label = QLabel()
        rp = resource_path("icons/robot_gra_100px.png")
        if os.path.exists(rp):
            robo_label.setPixmap(QPixmap(rp))
        robo_wrap.addWidget(robo_label)
        footer.addLayout(robo_wrap)
        shell.addLayout(footer)

        # Compose (toolbar left + table right)
        block.addWidget(self._build_toolbar_widget(tb), 0)
        block.addLayout(shell, 1)
        outer.addLayout(block)

        self.statusBar().showMessage("Bereit")

    # Place a QToolBar inside a QWidget so layouts can size it vertically
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

    # Add a persistent row
    def confirm_current_input(self):
        key = self.key_in.text().strip()
        if not key:
            QMessageBox.information(self, "Fehlender Schlüssel", "Bitte Schlüssel eingeben.")
            return
        # extract inner HTML of value
        cur = self.val_in.textCursor(); cur.select(QTextCursor.Document)
        frag = cur.selection().toHtml()
        start = frag.find("<body"); val_html = ""
        if start == -1:
            val_html = _escape_html(self.val_in.toPlainText()).replace("\n", "<br />")
        else:
            s2 = frag.find(">", start); e2 = frag.rfind("</body>")
            val_html = frag[s2+1:e2].strip() if s2 != -1 and e2 != -1 else _escape_html(self.val_in.toPlainText()).replace("\n","<br />")

        row = EntryRow(key, val_html, self.icons)
        row.requestDelete.connect(self._row_delete)
        row.requestMoveUp.connect(self._row_move_up)
        row.requestMoveDown.connect(self._row_move_down)

        self.rows_widgets.append(row)
        self.rows_v.addWidget(row)

        # clear input row
        self.key_in.clear(); self.val_in.clear(); self.key_in.setFocus()

        # scroll to bottom
        bar = self.scroll.verticalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

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
        # remove all, re-add in order
        while self.rows_v.count():
            item = self.rows_v.takeAt(0)
            w = item.widget()
            if w: w.setParent(None)
        for r in self.rows_widgets:
            self.rows_v.addWidget(r)

    # Export exact table
    def export_table_only(self):
        left_h  = self.hdr_left.text().strip()  or DEFAULT_HEADER_LEFT
        right_h = self.hdr_right.text().strip() or DEFAULT_HEADER_RIGHT
        rows = []
        for rw in self.rows_widgets:
            k = rw.key_plain(); v = rw.val_html()
            if k or v: rows.append((k, v))

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

        base = self.title_in.text().strip() or DEFAULT_EXPORT_TITLE
        base = "".join(ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in base).strip()
        base = "_".join(base.split()) or DEFAULT_EXPORT_TITLE
        default_name = f"{base}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save (paste-ready HTML)", default_name,
            "Text/HTML (*.txt *.html *.htm);;All Files (*.*)"
        )
        if not path: return
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
