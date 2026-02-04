"""
Auto-Update System for Claudias Spezifikationen Assistent
Silent check on startup, German UI with "du" form
"""

import os
import sys
import json
import tempfile
import subprocess
import threading
from packaging import version
from datetime import datetime

# Try requests import - graceful fallback if not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
CURRENT_VERSION = "2.1.0"
UPDATE_SERVER = "https://downloads.graphicart.ch/ListenWichtel"
VERSION_JSON_URL = f"{UPDATE_SERVER}/version.json"

# HTTP Basic Auth credentials
AUTH_USER = "autoupdate"
AUTH_PASS = "GA_au70upd473_2025_secure"

def _log(msg: str):
    try:
        base = os.path.abspath(".")
        out_dir = os.path.join(base, "output")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(out_dir, "update.log"), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def get_auth():
    """Return requests auth tuple."""
    return (AUTH_USER, AUTH_PASS)


def fetch_version_info():
    """
    Fetch version.json from update server.
    Returns dict with version info or None on failure.
    """
    if not REQUESTS_AVAILABLE:
        _log("requests not available; update check skipped")
        return None

    try:
        response = requests.get(
            VERSION_JSON_URL,
            auth=get_auth(),
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        _log(f"version.json fetched OK; version={data.get('version')}")
        return data
    except Exception as e:
        # Silent failure - don't interrupt user
        _log(f"fetch_version_info failed: {e}")
        return None


def is_update_available(server_version: str) -> bool:
    """Check if server version is newer than current."""
    try:
        return version.parse(server_version) > version.parse(CURRENT_VERSION)
    except Exception:
        return False


def download_update(download_url: str, progress_callback=None) -> str:
    """
    Download update installer to temp directory.
    Returns path to downloaded file or None on failure.
    """
    if not REQUESTS_AVAILABLE:
        return None

    try:
        response = requests.get(
            download_url,
            auth=get_auth(),
            stream=True,
            timeout=300
        )
        response.raise_for_status()

        # Get total size for progress
        total_size = int(response.headers.get('content-length', 0))

        # Create temp file
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"{APP_NAME}_setup.exe")

        downloaded = 0
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)

        return temp_path
    except Exception:
        return None


def run_installer(installer_path: str):
    """Run the downloaded installer and exit current application."""
    try:
        # Start installer detached from current process
        if sys.platform == 'win32':
            subprocess.Popen(
                [installer_path],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            subprocess.Popen([installer_path])

        # Exit current application
        sys.exit(0)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Qt UI Components (German with "du" form, using "ss" instead of "ss")
# -----------------------------------------------------------------------------
def show_update_dialog(version_info: dict, parent=None):
    """
    Show update available dialog with release notes.
    German UI with "du" form.
    """
    try:
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel,
            QPushButton, QTextEdit, QProgressBar, QMessageBox
        )
        from PySide6.QtCore import Qt, QThread, Signal
    except ImportError:
        return False

    class DownloadThread(QThread):
        progress = Signal(int, int)
        finished = Signal(str)
        error = Signal(str)

        def __init__(self, url):
            super().__init__()
            self.url = url

        def run(self):
            try:
                path = download_update(
                    self.url,
                    lambda downloaded, total: self.progress.emit(downloaded, total)
                )
                if path:
                    self.finished.emit(path)
                else:
                    self.error.emit("Download fehlgeschlagen")
            except Exception as e:
                self.error.emit(str(e))

    class UpdateDialog(QDialog):
        def __init__(self, version_info, parent=None):
            super().__init__(parent)
            self.version_info = version_info
            self.download_thread = None
            self.installer_path = None

            self.setWindowTitle("Update verfuegbar")
            self.setMinimumWidth(450)
            self.setMinimumHeight(350)

            layout = QVBoxLayout(self)
            layout.setSpacing(12)

            # Header
            new_ver = version_info.get('version', 'unbekannt')
            header = QLabel(
                f"<b>Eine neue Version ist verfuegbar!</b><br>"
                f"Deine Version: {CURRENT_VERSION}<br>"
                f"Neue Version: {new_ver}"
            )
            header.setTextFormat(Qt.RichText)
            layout.addWidget(header)

            # Release notes
            notes_label = QLabel("<b>Neuerungen:</b>")
            layout.addWidget(notes_label)

            self.notes_text = QTextEdit()
            self.notes_text.setReadOnly(True)
            release_notes = version_info.get('release_notes', 'Keine Versionshinweise verfuegbar.')
            self.notes_text.setPlainText(release_notes)
            self.notes_text.setMaximumHeight(150)
            layout.addWidget(self.notes_text)

            # Progress bar (hidden initially)
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setTextVisible(True)
            layout.addWidget(self.progress_bar)

            # Status label
            self.status_label = QLabel("")
            self.status_label.setVisible(False)
            layout.addWidget(self.status_label)

            # Buttons
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()

            self.btn_later = QPushButton("Spaeter")
            self.btn_later.clicked.connect(self.reject)
            btn_layout.addWidget(self.btn_later)

            self.btn_update = QPushButton("Jetzt aktualisieren")
            self.btn_update.setDefault(True)
            self.btn_update.clicked.connect(self.start_download)
            btn_layout.addWidget(self.btn_update)

            layout.addLayout(btn_layout)

        def start_download(self):
            """Start the download process."""
            download_url = self.version_info.get('download_url')
            if not download_url:
                QMessageBox.warning(
                    self,
                    "Fehler",
                    "Keine Download-URL verfuegbar."
                )
                return

            # Update UI
            self.btn_update.setEnabled(False)
            self.btn_later.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setVisible(True)
            self.status_label.setText("Lade herunter...")

            # Start download thread
            self.download_thread = DownloadThread(download_url)
            self.download_thread.progress.connect(self.on_progress)
            self.download_thread.finished.connect(self.on_download_finished)
            self.download_thread.error.connect(self.on_download_error)
            self.download_thread.start()

        def on_progress(self, downloaded, total):
            """Update progress bar."""
            if total > 0:
                percent = int((downloaded / total) * 100)
                self.progress_bar.setValue(percent)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                self.status_label.setText(
                    f"Lade herunter... {mb_downloaded:.1f} / {mb_total:.1f} MB"
                )

        def on_download_finished(self, path):
            """Handle successful download."""
            self.installer_path = path
            self.progress_bar.setValue(100)
            self.status_label.setText("Download abgeschlossen!")

            # Ask to install
            reply = QMessageBox.question(
                self,
                "Installation starten",
                "Der Download ist abgeschlossen.\n"
                "Moechtest du das Update jetzt installieren?\n\n"
                "Die Anwendung wird geschlossen.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                run_installer(self.installer_path)
            else:
                self.btn_later.setEnabled(True)
                self.btn_update.setEnabled(True)
                self.btn_update.setText("Installieren")
                self.btn_update.clicked.disconnect()
                self.btn_update.clicked.connect(
                    lambda: run_installer(self.installer_path)
                )

        def on_download_error(self, error_msg):
            """Handle download error."""
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"Fehler: {error_msg}")
            self.btn_later.setEnabled(True)
            self.btn_update.setEnabled(True)

            QMessageBox.warning(
                self,
                "Download fehlgeschlagen",
                f"Das Update konnte nicht heruntergeladen werden:\n{error_msg}\n\n"
                "Bitte versuche es spaeter erneut oder lade das Update manuell herunter."
            )

    dialog = UpdateDialog(version_info, parent)
    return dialog.exec() == QDialog.Accepted


def check_for_updates_silent(parent=None, callback=None):
    """
    Check for updates in background thread.
    If update available, shows dialog.

    Args:
        parent: Parent widget for dialog
        callback: Optional callback(has_update: bool) when check complete
    """
    def check_thread():
        _log("silent update check started")
        version_info = fetch_version_info()

        if version_info and is_update_available(version_info.get('version', '')):
            _log(f"update available: {version_info.get('version')}")
            # Update available - show dialog on main thread
            if parent:
                try:
                    from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                    # Use invokeMethod to show dialog on main thread
                    QMetaObject.invokeMethod(
                        parent,
                        "_show_update_dialog_slot",
                        Qt.QueuedConnection,
                        Q_ARG(object, version_info)
                    )
                except Exception:
                    pass
            if callback:
                callback(True)
        else:
            _log("no update available")
            if callback:
                callback(False)

    thread = threading.Thread(target=check_thread, daemon=True)
    thread.start()


def check_for_updates_blocking():
    """
    Check for updates (blocking).
    Returns (has_update, version_info) tuple.
    """
    version_info = fetch_version_info()

    if version_info and is_update_available(version_info.get('version', '')):
        return True, version_info

    return False, version_info


# -----------------------------------------------------------------------------
# Main entry point for testing
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Auto-Update System v{CURRENT_VERSION}")
    print(f"App: {APP_NAME}")
    print(f"Server: {UPDATE_SERVER}")
    print()

    print("Pruefe auf Updates...")
    has_update, info = check_for_updates_blocking()

    if has_update:
        print(f"Update verfuegbar: {info.get('version')}")
        print(f"Release Notes: {info.get('release_notes', 'Keine')}")
    else:
        print("Du verwendest bereits die neueste Version.")
