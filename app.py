"""
Folder Organizer — modern PySide6 desktop app.
Portable: settings.json and move_log.jsonl live next to the script/exe.
"""
import os
import sys
import json
import shutil
import time
import uuid
import ctypes
import traceback
from pathlib import Path
from datetime import datetime

# --- High DPI BEFORE QApplication ---------------------------------------------
from PySide6.QtCore import Qt, QSize, QTimer, QPoint, QEvent, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, QAction, QPalette, QGuiApplication,
    QFontDatabase,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QSystemTrayIcon, QMenu, QDialog, QCheckBox, QListWidget, QListWidgetItem,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSpacerItem, QToolButton, QSpinBox, QLineEdit, QAbstractItemView,
    QGraphicsOpacityEffect, QStackedWidget,
)
try:
    from PySide6.QtCore import QScroller
    HAS_SCROLLER = True
except Exception:
    HAS_SCROLLER = False

QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)


# --- Constants ----------------------------------------------------
APP_NAME = "Folder Organizer"
APP_VERSION = "1.0.0"

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

SETTINGS_FILE = APP_DIR / "settings.json"
LOG_FILE = APP_DIR / "move_log.jsonl"

DEFAULT_EXT_MAP = {
    "jpg": "Images", "jpeg": "Images", "png": "Images", "gif": "Images",
    "webp": "Images", "bmp": "Images", "tiff": "Images", "tif": "Images",
    "svg": "Images", "heic": "Images", "ico": "Images",
    "pdf": "PDFs",
    "doc": "Words", "docx": "Words", "odt": "Words", "rtf": "Words", "txt": "Words",
    "html": "Files", "htm": "Files", "json": "Files", "js": "Files",
    "css": "Files", "xml": "Files", "yml": "Files", "yaml": "Files",
}

DEFAULT_CONFIG = {
    "version": APP_VERSION,
    "default_folder": "",
    "auto_organize_on_startup": False,
    "autostart_at_login": False,
    "age_window_hours": 24 * 7,     # 7 days
    "extension_map": dict(DEFAULT_EXT_MAP),
    "never_move": [],               # list of {"path": str, "name_match": bool}
    "conflict_policy": "rename",    # "rename" | "skip"
    "skip_hidden": True,
    "last_auto_run": None,
}

AGE_PRESETS = [
    ("Last 24 hours", 24),
    ("Last 7 days", 24 * 7),
    ("Last 30 days", 24 * 30),
    ("All files", -1),
]

CATEGORY_EMOJI = {
    "Images": "🖼", "PDFs": "📕", "Words": "📄", "Files": "🧩",
    "Folders": "📁", "Other": "📦",
}
REASON_TEXT = {
    "excluded": "excluded",
    "hidden": "hidden",
    "category_folder": "managed folder",
    "own_config": "app file",
    "too_old": "outside age window",
    "locked": "locked/in use",
    "conflict": "skipped (conflict)",
}


# --- Style -------------------------------------------------------------------
STYLE = """
QMainWindow, QDialog { background-color: #0b0d10; }
QWidget { color: #e6e8eb; font-size: 13px;
          font-family: "Segoe UI", "SF Pro Text", "Inter", -apple-system, Roboto, sans-serif; }
QFrame#card {
    background-color: #14171d;
    border: 1px solid #1f242d;
    border-radius: 12px;
}
QFrame#row {
    background-color: #14171d;
    border: 1px solid #1f242d;
    border-radius: 8px;
}
QFrame#row[excluded="true"] {
    background-color: #16181d;
    border-color: #232833;
}
QLabel#title { font-size: 22px; font-weight: 700; color: #f1f3f5; }
QLabel#subtitle { font-size: 12px; color: #8b93a1; }
QLabel#section { font-size: 11px; font-weight: 600; color: #8b93a1;
                 letter-spacing: 1px; }
QLabel#filename { font-size: 13px; color: #e6e8eb; font-weight: 500; }
QLabel#category { font-size: 11px; color: #8b93a1; }
QLabel#badge { font-size: 11px; color: #8b93a1; background: #1c2129;
               border: 1px solid #2a313d; border-radius: 10px; padding: 2px 8px; }
QLabel#empty { color: #5a6272; font-size: 13px; }
QPushButton {
    background-color: #1c2129; color: #e6e8eb;
    border: 1px solid #2a313d; border-radius: 8px;
    padding: 8px 16px; font-size: 13px; font-weight: 500;
}
QPushButton:hover { background-color: #232a34; border-color: #333c4a; }
QPushButton:pressed { background-color: #161b22; }
QPushButton:disabled { color: #4a5160; border-color: #1f242d; }
QPushButton#primary { background-color: #3b82f6; border: 1px solid #3b82f6;
                      color: #ffffff; font-weight: 600; }
QPushButton#primary:hover { background-color: #2563eb; border-color: #2563eb; }
QPushButton#ghost { background-color: transparent; border: 1px solid transparent;
                    color: #8b93a1; }
QPushButton#ghost:hover { background-color: #1c2129; color: #e6e8eb; }
QPushButton#danger { color: #f87171; }
QComboBox, QLineEdit, QSpinBox {
    background-color: #0f1319;
    border: 1px solid #2a313d; border-radius: 8px;
    padding: 7px 12px; color: #e6e8eb;
    selection-background-color: #3b82f6;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: #14171d; border: 1px solid #2a313d;
    border-radius: 8px; padding: 4px;
    selection-background-color: #232a34; outline: none;
}
QCheckBox { spacing: 8px; color: #e6e8eb; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid #2a313d; background-color: #0f1319;
}
QCheckBox::indicator:checked { background-color: #3b82f6; border-color: #3b82f6; }
QCheckBox::indicator:hover { border-color: #3b4250; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2a313d; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3b4250; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QTabWidget::pane {
    border: 1px solid #1f242d; border-radius: 12px;
    background-color: #14171d; top: -1px;
}
QTabBar::tab {
    background: transparent; color: #8b93a1;
    padding: 10px 18px; border: none; font-weight: 500;
}
QTabBar::tab:selected { color: #f1f3f5; border-bottom: 2px solid #3b82f6; }
QTabBar::tab:hover:!selected { color: #e6e8eb; }
QMenu { background-color: #14171d; border: 1px solid #2a313d;
        border-radius: 8px; padding: 6px; }
QMenu::item { padding: 8px 24px 8px 12px; border-radius: 6px; }
QMenu::item:selected { background-color: #232a34; }
QTableWidget {
    background-color: transparent; border: none; gridline-color: #1f242d;
    selection-background-color: #232a34;
}
QHeaderView::section {
    background-color: #0f1319; color: #8b93a1;
    padding: 8px; border: none;
    border-bottom: 1px solid #1f242d;
    font-weight: 600; font-size: 11px;
}
"""


# --- Helpers -----------------------------------------------------------------
def is_hidden(path: Path) -> bool:
    name = path.name
    if name.startswith("."):
        return True
    if os.name == "nt":
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != -1 and (attrs & 0x2):  # FILE_ATTRIBUTE_HIDDEN
                return True
        except Exception:
            pass
    return False


def load_config() -> tuple[dict, bool]:
    """Return (config, was_reset)."""
    if not SETTINGS_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG), False
    try:
        cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        # ensure extension_map + never_move shape
        if not isinstance(merged.get("extension_map"), dict):
            merged["extension_map"] = dict(DEFAULT_EXT_MAP)
        if not isinstance(merged.get("never_move"), list):
            merged["never_move"] = []
        return merged, False
    except Exception:
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG), True


def save_config(cfg: dict):
    try:
        SETTINGS_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[warn] could not save settings: {e}", file=sys.stderr)


def append_log(entry: dict):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[warn] could not write log: {e}", file=sys.stderr)


def resolve_conflict(dest: Path) -> Path:
    """Append (1), (2)... until free."""
    stem, suffix = dest.stem, dest.suffix
    parent = dest.parent
    i = 1
    candidate = dest
    while candidate.exists():
        candidate = parent / f"{stem} ({i}){suffix}"
        i += 1
    return candidate


def make_icon(color="#3b82f6", size=64) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    r = size // 8
    p.drawRoundedRect(r, r * 2, size - 2 * r, size - r * 3, r, r)
    p.setBrush(QColor(color).lighter(115))
    p.drawRoundedRect(r, r * 2, size // 3, r, r, r)
    p.end()
    return QIcon(pm)


def set_autostart(enabled: bool):
    if os.name != "nt":
        return
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])
            winreg.SetValueEx(key, "FolderOrganizer", 0, winreg.REG_SZ, f'"{exe}" --minimized')
        else:
            try:
                winreg.DeleteValue(key, "FolderOrganizer")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[warn] autostart: {e}", file=sys.stderr)


# --- Organizer core ----------------------------------------------------------
class Organizer:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def managed_folders(self) -> set:
        s = set(self.cfg.get("extension_map", {}).values())
        s.update({"Folders", "Other"})
        return s

    def _never_moved(self, p: Path) -> bool:
        try:
            p_str = str(p.resolve())
        except Exception:
            p_str = str(p)
        name = p.name
        for entry in self.cfg.get("never_move", []):
            if entry.get("name_match"):
                if name == entry.get("path"):
                    return True
            else:
                if p_str == entry.get("path"):
                    return True
        return False

    def _in_age_window(self, p: Path) -> bool:
        hours = self.cfg.get("age_window_hours", 24 * 7)
        if hours is None or hours < 0:
            return True
        try:
            mtime = p.stat().st_mtime
        except Exception:
            return False
        return mtime >= time.time() - hours * 3600

    def category_for(self, p: Path) -> str:
        if p.is_dir():
            return "Folders"
        ext = p.suffix.lower().lstrip(".")
        return self.cfg.get("extension_map", {}).get(ext, "Other")

    def scan(self, folder: Path):
        """Return (candidates, skipped) where candidates are Path, skipped are (Path, reason)."""
        managed = self.managed_folders()
        own = {SETTINGS_FILE.name, LOG_FILE.name}
        candidates, skipped = [], []
        try:
            entries = list(folder.iterdir())
        except PermissionError:
            return [], []

        for p in entries:
            if p.name in own:
                skipped.append((p, "own_config")); continue
            if p.is_dir() and p.name in managed:
                skipped.append((p, "category_folder")); continue
            if self._never_moved(p):
                skipped.append((p, "excluded")); continue
            if self.cfg.get("skip_hidden", True) and is_hidden(p):
                skipped.append((p, "hidden")); continue
            if not self._in_age_window(p):
                skipped.append((p, "too_old")); continue
            candidates.append(p)
        return candidates, skipped

    def preview(self, folder: Path):
        candidates, skipped = self.scan(folder)
        items = []
        for p in candidates:
            items.append({
                "path": p,
                "name": p.name,
                "type": "folder" if p.is_dir() else "file",
                "category": self.category_for(p),
                "action": "would_move",
            })
        for p, reason in skipped:
            items.append({
                "path": p, "name": p.name,
                "type": "folder" if p.is_dir() else "file",
                "category": self.category_for(p),
                "action": "skipped", "reason": reason,
            })
        return items

    def organize(self, folder: Path, manual=True):
        batch_id = uuid.uuid4().hex[:10]
        start = {
            "event": "start", "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "folder": str(folder),
            "age_hours": self.cfg.get("age_window_hours"),
            "manual": manual,
            "app_version": APP_VERSION,
        }
        append_log(start)

        candidates, skipped = self.scan(folder)
        moved = skipped_n = failed = 0

        # skipped records
        for p, reason in skipped:
            append_log({
                "event": "item", "batch_id": batch_id,
                "action": "skipped", "reason": reason,
                "source": str(p), "name": p.name,
                "type": "folder" if p.is_dir() else "file",
            })
            skipped_n += 1

        for p in candidates:
            category = self.category_for(p)
            dest_dir = folder / category
            dest = dest_dir / p.name
            try:
                if not dest_dir.exists():
                    dest_dir.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    if self.cfg.get("conflict_policy") == "skip":
                        append_log({
                            "event": "item", "batch_id": batch_id,
                            "action": "skipped", "reason": "conflict",
                            "source": str(p), "name": p.name,
                            "type": "folder" if p.is_dir() else "file",
                            "category": category,
                        })
                        skipped_n += 1
                        continue
                    dest = resolve_conflict(dest)

                try:
                    stat = p.stat()
                    size, ctime, mtime = stat.st_size, stat.st_ctime, stat.st_mtime
                except Exception:
                    size, ctime, mtime = 0, 0, 0

                shutil.move(str(p), str(dest))
                moved += 1
                append_log({
                    "event": "item", "batch_id": batch_id,
                    "action": "moved",
                    "category": category,
                    "source": str(p), "destination": str(dest),
                    "name": p.name,
                    "type": "folder" if p.is_dir() else "file",
                    "size": size, "ctime": ctime, "mtime": mtime,
                    "status": "ok",
                })
            except Exception as e:
                failed += 1
                append_log({
                    "event": "item", "batch_id": batch_id,
                    "action": "failed",
                    "category": category,
                    "source": str(p), "destination": str(dest),
                    "name": p.name,
                    "type": "folder" if p.is_dir() else "file",
                    "error": str(e),
                })

        end = {
            "event": "end", "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "moved": moved, "skipped": skipped_n, "failed": failed,
        }
        append_log(end)
        return {"moved": moved, "skipped": skipped_n, "failed": failed,
                "batch_id": batch_id}


def undo_last_batch():
    if not LOG_FILE.exists():
        return None, "No log file yet."
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        return None, str(e)

    # find last finished batch id
    last_batch = None
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event") == "end":
            last_batch = e.get("batch_id")
            break
    if not last_batch:
        return None, "No completed batch to undo."

    moves = []
    for line in lines:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("batch_id") == last_batch and e.get("action") == "moved":
            moves.append(e)

    if not moves:
        return None, "Last batch had no moves."

    undone, failed = 0, 0
    for e in reversed(moves):
        src = Path(e["source"])
        dst = Path(e["destination"])
        try:
            if not dst.exists() or src.exists():
                failed += 1
                continue
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
            undone += 1
        except Exception:
            failed += 1
    return {"undone": undone, "failed": failed}, None


# --- Never-move picker dialog ------------------------------------------------
class NeverMovePicker(QDialog):
    def __init__(self, folder: Path, cfg: dict, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.cfg = cfg
        self.setWindowTitle("Add items to never move")
        self.resize(560, 560)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        head = QLabel("Choose items to protect")
        head.setObjectName("title")
        root.addWidget(head)

        sub = QLabel(f"From: {folder}")
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        root.addWidget(sub)

        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget {
                background: #0f1319; border: 1px solid #2a313d;
                border-radius: 10px; padding: 6px;
            }
            QListWidget::item { padding: 6px; border-radius: 6px; }
            QListWidget::item:selected { background: #232a34; }
        """)
        self.list.setSelectionMode(QAbstractItemView.NoSelection)
        root.addWidget(self.list, 1)

        self._populate()

        # match by name checkbox
        self.name_match_cb = QCheckBox("Match by name (anywhere it appears)")
        root.addWidget(self.name_match_cb)

        btn_row = QHBoxLayout()
        btn_all = QPushButton("Select all"); btn_all.setObjectName("ghost")
        btn_all.clicked.connect(self._select_all)
        btn_none = QPushButton("Clear"); btn_none.setObjectName("ghost")
        btn_none.clicked.connect(self._clear_all)
        btn_row.addWidget(btn_all); btn_row.addWidget(btn_none)
        btn_row.addStretch(1)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        ok = QPushButton("Add"); ok.setObjectName("primary"); ok.clicked.connect(self.accept)
        btn_row.addWidget(cancel); btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _populate(self):
        org = Organizer(self.cfg)
        managed = org.managed_folders()
        own = {SETTINGS_FILE.name, LOG_FILE.name}
        excluded_paths = {e.get("path") for e in self.cfg.get("never_move", []) if not e.get("name_match")}
        excluded_names = {e.get("path") for e in self.cfg.get("never_move", []) if e.get("name_match")}

        try:
            entries = sorted(self.folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception:
            entries = []

        if not entries:
            item = QListWidgetItem("(folder is empty)")
            item.setFlags(Qt.NoItemFlags)
            self.list.addItem(item)
            return

        for p in entries:
            disabled = False
            note = ""
            if p.name in own:
                disabled, note = True, " (app file)"
            elif p.is_dir() and p.name in managed:
                disabled, note = True, " (managed folder)"

            is_excluded = (str(p.resolve()) in excluded_paths) or (p.name in excluded_names)
            item = QListWidgetItem(f"{'📁' if p.is_dir() else '📄'}  {p.name}{note}")
            item.setData(Qt.UserRole, (p, disabled))
            flags = Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
            if disabled:
                flags = Qt.NoItemFlags
            item.setFlags(flags)
            item.setCheckState(Qt.Checked if is_excluded else Qt.Unchecked)
            self.list.addItem(item)

    def _select_all(self):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(Qt.Checked)

    def _clear_all(self):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(Qt.Unchecked)

    def selected(self):
        name_match = self.name_match_cb.isChecked()
        result = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.checkState() == Qt.Checked and it.flags() & Qt.ItemIsUserCheckable:
                p, _ = it.data(Qt.UserRole)
                result.append({"path": str(p.resolve()) if not name_match else p.name,
                               "name_match": name_match})
        return result


# --- Settings dialog ---------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, current_folder: str, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.current_folder = current_folder
        self.setWindowTitle("Settings")
        self.resize(720, 620)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header
        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(24, 24, 24, 12)
        t = QLabel("Settings"); t.setObjectName("title")
        s = QLabel("Configure how files are organized"); s.setObjectName("subtitle")
        hl.addWidget(t); hl.addWidget(s)
        root.addWidget(head)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1)

        self._build_general()
        self._build_categories()
        self._build_never_move()

        # footer
        footer = QWidget()
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 12, 24, 24)
        fl.addStretch(1)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        save = QPushButton("Save"); save.setObjectName("primary"); save.clicked.connect(self.accept)
        fl.addWidget(cancel); fl.addWidget(save)
        root.addWidget(footer)

    # --- General tab ---
    def _build_general(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        # default folder
        lbl = QLabel("DEFAULT FOLDER"); lbl.setObjectName("section")
        v.addWidget(lbl)
        row = QHBoxLayout()
        self.folder_edit = QLineEdit(self.cfg.get("default_folder", ""))
        self.folder_edit.setReadOnly(True)
        browse = QPushButton("Browse…"); browse.clicked.connect(self._browse_folder)
        row.addWidget(self.folder_edit, 1); row.addWidget(browse)
        v.addLayout(row)

        # toggles
        lbl2 = QLabel("BEHAVIOR"); lbl2.setObjectName("section")
        v.addWidget(lbl2)
        self.auto_cb = QCheckBox("Auto-organize on startup")
        self.auto_cb.setChecked(self.cfg.get("auto_organize_on_startup", False))
        v.addWidget(self.auto_cb)
        self.login_cb = QCheckBox("Start with Windows (autostart at login)")
        self.login_cb.setChecked(self.cfg.get("autostart_at_login", False))
        v.addWidget(self.login_cb)
        self.skip_hidden_cb = QCheckBox("Skip hidden / system files")
        self.skip_hidden_cb.setChecked(self.cfg.get("skip_hidden", True))
        v.addWidget(self.skip_hidden_cb)

        # age
        lbl3 = QLabel("AGE WINDOW"); lbl3.setObjectName("section")
        v.addWidget(lbl3)
        self.age_combo = QComboBox()
        current = self.cfg.get("age_window_hours", 24 * 7)
        idx = 0
        for i, (name, val) in enumerate(AGE_PRESETS):
            self.age_combo.addItem(name, val)
            if val == current:
                idx = i
        self.age_combo.setCurrentIndex(idx)
        v.addWidget(self.age_combo)

        # conflict policy
        lbl4 = QLabel("CONFLICT POLICY"); lbl4.setObjectName("section")
        v.addWidget(lbl4)
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem("Rename (add counter)", "rename")
        self.conflict_combo.addItem("Skip", "skip")
        self.conflict_combo.setCurrentIndex(
            0 if self.cfg.get("conflict_policy", "rename") == "rename" else 1
        )
        v.addWidget(self.conflict_combo)

        v.addStretch(1)
        self.tabs.addTab(page, "General")

    def _browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Choose default folder",
                                             self.folder_edit.text() or str(Path.home()))
        if d:
            self.folder_edit.setText(d)

    # --- Categories tab ---
    def _build_categories(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(12)

        head = QLabel("Map file extensions to category folders")
        head.setObjectName("section")
        v.addWidget(head)

        hint = QLabel("Adding a new extension creates the target folder immediately.")
        hint.setObjectName("subtitle")
        v.addWidget(hint)

        self.ext_table = QTableWidget(0, 2)
        self.ext_table.setHorizontalHeaderLabels(["EXTENSION", "FOLDER"])
        self.ext_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ext_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ext_table.verticalHeader().setVisible(False)
        self.ext_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        v.addWidget(self.ext_table, 1)

        for ext, folder in sorted(self.cfg.get("extension_map", {}).items()):
            self._add_ext_row(ext, folder)

        row = QHBoxLayout()
        self.new_ext = QLineEdit(); self.new_ext.setPlaceholderText("extension (e.g. pptx)")
        self.new_folder = QLineEdit(); self.new_folder.setPlaceholderText("folder (e.g. PPT)")
        add = QPushButton("Add mapping"); add.setObjectName("primary")
        add.clicked.connect(self._add_mapping)
        rem = QPushButton("Remove selected"); rem.setObjectName("ghost")
        rem.clicked.connect(self._remove_mapping)
        row.addWidget(self.new_ext); row.addWidget(self.new_folder); row.addWidget(add)
        v.addLayout(row)
        v.addWidget(rem)

        self.tabs.addTab(page, "Categories")

    def _add_ext_row(self, ext, folder):
        r = self.ext_table.rowCount()
        self.ext_table.insertRow(r)
        self.ext_table.setItem(r, 0, QTableWidgetItem(ext))
        self.ext_table.setItem(r, 1, QTableWidgetItem(folder))

    def _add_mapping(self):
        ext = self.new_ext.text().strip().lower().lstrip(".")
        folder = self.new_folder.text().strip()
        if not ext or not folder:
            return
        # Update cfg + create folder immediately if default folder exists
        self.cfg.setdefault("extension_map", {})[ext] = folder
        if self.cfg.get("default_folder"):
            try:
                (Path(self.cfg["default_folder"]) / folder).mkdir(exist_ok=True)
            except Exception:
                pass
        self._add_ext_row(ext, folder)
        self.new_ext.clear(); self.new_folder.clear()

    def _remove_mapping(self):
        rows = sorted({i.row() for i in self.ext_table.selectedIndexes()}, reverse=True)
        for r in rows:
            ext = self.ext_table.item(r, 0).text()
            self.cfg.get("extension_map", {}).pop(ext, None)
            self.ext_table.removeRow(r)

    # --- Never-move tab ---
    def _build_never_move(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(12)

        head = QLabel("NEVER MOVE THESE"); head.setObjectName("section")
        v.addWidget(head)
        hint = QLabel("Strict path or name match. No wildcards.")
        hint.setObjectName("subtitle")
        v.addWidget(hint)

        self.nm_table = QTableWidget(0, 3)
        self.nm_table.setHorizontalHeaderLabels(["NAME / PATH", "MATCH", ""])
        self.nm_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.nm_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.nm_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.nm_table.verticalHeader().setVisible(False)
        self.nm_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        v.addWidget(self.nm_table, 1)

        for entry in self.cfg.get("never_move", []):
            self._add_nm_row(entry)

        row = QHBoxLayout()
        add_cur = QPushButton("Add from current folder"); add_cur.setObjectName("primary")
        add_cur.clicked.connect(self._add_from_current)
        add_br = QPushButton("Browse…"); add_br.clicked.connect(self._add_from_browse)
        rem = QPushButton("Remove selected"); rem.setObjectName("ghost")
        rem.clicked.connect(self._remove_nm)
        row.addWidget(add_cur); row.addWidget(add_br); row.addStretch(1); row.addWidget(rem)
        v.addLayout(row)

        self.tabs.addTab(page, "Never move")

    def _add_nm_row(self, entry):
        r = self.nm_table.rowCount()
        self.nm_table.insertRow(r)
        display = entry.get("path", "")
        self.nm_table.setItem(r, 0, QTableWidgetItem(display))
        match_txt = "by name" if entry.get("name_match") else "full path"
        self.nm_table.setItem(r, 1, QTableWidgetItem(match_txt))
        btn = QPushButton("×"); btn.setObjectName("danger"); btn.setFixedWidth(32)
        btn.clicked.connect(lambda _=False, b=btn: self._remove_row_by_btn(b))
        self.nm_table.setCellWidget(r, 2, btn)
        self.nm_table.item(r, 0).setData(Qt.UserRole, dict(entry))

    def _remove_row_by_btn(self, btn):
        for r in range(self.nm_table.rowCount()):
            if self.nm_table.cellWidget(r, 2) is btn:
                self.nm_table.removeRow(r)
                return

    def _add_from_current(self):
        folder = self.folder_edit.text()
        if not folder or not Path(folder).is_dir():
            QMessageBox.information(self, "No folder", "Select a default folder first.")
            return
        dlg = NeverMovePicker(Path(folder), self.cfg, self)
        if dlg.exec():
            for entry in dlg.selected():
                self._append_nm(entry)

    def _add_from_browse(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose files to never move")
        # also allow choosing folders
        if not paths:
            d = QFileDialog.getExistingDirectory(self, "Choose folder to never move")
            if d:
                paths = [d]
        for p in paths:
            self._append_nm({"path": str(Path(p).resolve()), "name_match": False})

    def _append_nm(self, entry):
        # dedupe
        for r in range(self.nm_table.rowCount()):
            existing = self.nm_table.item(r, 0).data(Qt.UserRole)
            if existing.get("path") == entry["path"] and existing.get("name_match") == entry["name_match"]:
                return
        self._add_nm_row(entry)

    def _remove_nm(self):
        rows = sorted({i.row() for i in self.nm_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.nm_table.removeRow(r)

    # --- Save ---
    def apply(self):
        self.cfg["default_folder"] = self.folder_edit.text()
        self.cfg["auto_organize_on_startup"] = self.auto_cb.isChecked()
        prev_login = self.cfg.get("autostart_at_login", False)
        self.cfg["autostart_at_login"] = self.login_cb.isChecked()
        if self.cfg["autostart_at_login"] != prev_login:
            set_autostart(self.cfg["autostart_at_login"])
        self.cfg["skip_hidden"] = self.skip_hidden_cb.isChecked()
        self.cfg["age_window_hours"] = self.age_combo.currentData()
        self.cfg["conflict_policy"] = self.conflict_combo.currentData()

        # rebuild extension_map from table
        ext_map = {}
        for r in range(self.ext_table.rowCount()):
            ext = self.ext_table.item(r, 0).text().strip().lower()
            folder = self.ext_table.item(r, 1).text().strip()
            if ext and folder:
                ext_map[ext] = folder
        self.cfg["extension_map"] = ext_map

        # rebuild never_move from table
        nm = []
        for r in range(self.nm_table.rowCount()):
            data = self.nm_table.item(r, 0).data(Qt.UserRole)
            if data:
                nm.append(data)
        self.cfg["never_move"] = nm


# --- Preview row widget ------------------------------------------------------
class PreviewRow(QFrame):
    def __init__(self, item: dict, on_never_move, parent=None):
        super().__init__(parent)
        self.setObjectName("row")
        self.setProperty("excluded", item["action"] == "skipped")
        self.setFixedHeight(52)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 0, 14, 0)
        h.setSpacing(10)

        emoji = CATEGORY_EMOJI.get(item["category"], "📦")
        icon = QLabel(emoji)
        icon.setStyleSheet("font-size: 18px;")
        icon.setFixedWidth(26)
        h.addWidget(icon)

        name_lbl = QLabel(item["name"])
        name_lbl.setObjectName("filename")
        h.addWidget(name_lbl)
        h.addStretch(1)

        if item["action"] == "skipped":
            badge = QLabel(REASON_TEXT.get(item.get("reason", ""), "skipped"))
            badge.setObjectName("badge")
            h.addWidget(badge)
        else:
            cat = QLabel(f"→ {item['category']}")
            cat.setObjectName("category")
            h.addWidget(cat)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item = item
        self.on_never_move = on_never_move
        self.customContextMenuRequested.connect(self._ctx)

    def _ctx(self, pos):
        m = QMenu(self)
        a1 = m.addAction("Never move this")
        a2 = m.addAction("Never move this (by name)")
        chosen = m.exec(self.mapToGlobal(pos))
        if chosen == a1 and self.on_never_move:
            self.on_never_move(self.item, False)
        elif chosen == a2 and self.on_never_move:
            self.on_never_move(self.item, True)


# --- Main window -------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self, cfg: dict, tray=None):
        super().__init__()
        self.cfg = cfg
        self.tray = tray
        self.folder: Path | None = None
        self.setWindowTitle(APP_NAME)
        self.resize(760, 720)
        self.setStyleSheet(STYLE)

        if self.cfg.get("default_folder"):
            p = Path(self.cfg["default_folder"])
            if p.is_dir():
                self.folder = p

        self._build_ui()
        self._refresh_folder_label()
        self._render_empty("Press Preview or Organize Now to begin.")

    # --- UI ---
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # header
        title = QLabel(APP_NAME); title.setObjectName("title")
        subtitle = QLabel("Tidy a folder in one click. Top level only.")
        subtitle.setObjectName("subtitle")
        root.addWidget(title); root.addWidget(subtitle)

        # folder card
        folder_card = QFrame(); folder_card.setObjectName("card")
        fc = QHBoxLayout(folder_card)
        fc.setContentsMargins(16, 14, 16, 14); fc.setSpacing(12)

        folder_icon = QLabel("📁"); folder_icon.setStyleSheet("font-size: 22px;")
        fc.addWidget(folder_icon)

        col = QVBoxLayout(); col.setSpacing(2)
        small = QLabel("CURRENT FOLDER"); small.setObjectName("section")
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setObjectName("filename")
        self.folder_label.setWordWrap(True)
        col.addWidget(small); col.addWidget(self.folder_label)
        fc.addLayout(col, 1)

        self.default_cb = QCheckBox("Set as default")
        self.default_cb.setChecked(
            self.folder is not None and
            str(self.folder) == self.cfg.get("default_folder")
        )
        fc.addWidget(self.default_cb)

        btn_pick = QPushButton("Choose folder")
        btn_pick.clicked.connect(self._pick_folder)
        fc.addWidget(btn_pick)

        root.addWidget(folder_card)

        # age row
        age_card = QFrame(); age_card.setObjectName("card")
        ac = QHBoxLayout(age_card)
        ac.setContentsMargins(16, 12, 16, 12)
        al = QLabel("Only touch files modified in")
        al.setObjectName("subtitle")
        ac.addWidget(al)
        self.age_combo = QComboBox()
        for name, val in AGE_PRESETS:
            self.age_combo.addItem(name, val)
        # select current
        cur = self.cfg.get("age_window_hours", 24 * 7)
        for i in range(self.age_combo.count()):
            if self.age_combo.itemData(i) == cur:
                self.age_combo.setCurrentIndex(i); break
        ac.addWidget(self.age_combo)
        ac.addStretch(1)
        root.addWidget(age_card)

        # actions
        actions = QHBoxLayout(); actions.setSpacing(10)
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_organize = QPushButton("Organize Now")
        self.btn_organize.setObjectName("primary")
        self.btn_organize.clicked.connect(self._on_organize)
        self.btn_undo = QPushButton("Undo last batch")
        self.btn_undo.setObjectName("ghost")
        self.btn_undo.clicked.connect(self._on_undo)
        self.btn_settings = QPushButton("⚙  Settings")
        self.btn_settings.setObjectName("ghost")
        self.btn_settings.clicked.connect(self._on_settings)
        self.btn_hide = QPushButton("Hide")
        self.btn_hide.setObjectName("ghost")
        self.btn_hide.clicked.connect(self._hide_to_tray)

        actions.addWidget(self.btn_preview)
        actions.addWidget(self.btn_organize)
        actions.addStretch(1)
        actions.addWidget(self.btn_undo)
        actions.addWidget(self.btn_settings)
        actions.addWidget(self.btn_hide)
        root.addLayout(actions)

        # preview panel
        panel = QFrame(); panel.setObjectName("card")
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(6, 6, 6, 6)
        pv.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        if HAS_SCROLLER:
            try:
                QScroller.grabGesture(self.scroll.viewport(),
                                      QScroller.ScrollerGestureType.LeftMouseButtonGesture)
                QScroller.grabGesture(self.scroll.viewport(),
                                      QScroller.ScrollerGestureType.TouchGesture)
            except Exception:
                pass

        self.list_holder = QWidget()
        self.list_layout = QVBoxLayout(self.list_holder)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_holder)
        pv.addWidget(self.scroll)

        root.addWidget(panel, 1)

        # status bar
        self.status = QLabel("Ready")
        self.status.setObjectName("subtitle")
        root.addWidget(self.status)

    # --- UI helpers ---
    def _refresh_folder_label(self):
        if self.folder:
            self.folder_label.setText(str(self.folder))
        else:
            self.folder_label.setText("No folder selected")
        self.default_cb.setChecked(
            self.folder is not None and
            str(self.folder) == self.cfg.get("default_folder")
        )

    def _clear_list(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _render_empty(self, msg):
        self._clear_list()
        lbl = QLabel(msg); lbl.setObjectName("empty")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setMinimumHeight(160)
        self.list_layout.insertWidget(0, lbl)

    def _render_items(self, items):
        self._clear_list()
        for it in items:
            row = PreviewRow(it, self._on_never_move)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)

    # --- Actions ---
    def _pick_folder(self):
        start = str(self.folder) if self.folder else str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "Choose a folder to organize", start)
        if d:
            self.folder = Path(d)
            self._refresh_folder_label()
            self._render_empty("Ready — press Preview or Organize Now.")

    def _persist_default(self):
        if self.default_cb.isChecked() and self.folder:
            self.cfg["default_folder"] = str(self.folder)
        elif not self.default_cb.isChecked() and self.folder and \
                self.cfg.get("default_folder") == str(self.folder):
            self.cfg["default_folder"] = ""
        save_config(self.cfg)

    def _current_age_hours(self):
        return self.age_combo.currentData()

    def _sync_age(self):
        h = self._current_age_hours()
        if h is not None and h != self.cfg.get("age_window_hours"):
            self.cfg["age_window_hours"] = h
            save_config(self.cfg)

    def _on_preview(self):
        if not self.folder or not self.folder.is_dir():
            QMessageBox.warning(self, "No folder", "Choose a folder first.")
            return
        self._persist_default()
        self._sync_age()
        org = Organizer(self.cfg)
        items = org.preview(self.folder)
        if not items:
            self._render_empty("Nothing to do — folder is already tidy.")
            self.status.setText("Preview: 0 items")
            return
        self._render_items(items)
        would = sum(1 for i in items if i["action"] == "would_move")
        skipped = sum(1 for i in items if i["action"] == "skipped")
        self.status.setText(f"Preview — would move {would} · skipped {skipped}")

    def _on_organize(self):
        if not self.folder or not self.folder.is_dir():
            QMessageBox.warning(self, "No folder", "Choose a folder first.")
            return
        self._persist_default()
        self._sync_age()
        org = Organizer(self.cfg)
        try:
            result = org.organize(self.folder, manual=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Organize failed:\n{e}")
            return
        self.status.setText(
            f"Moved {result['moved']} · skipped {result['skipped']} · failed {result['failed']}"
        )
        if self.tray:
            self.tray.showMessage(
                APP_NAME,
                f"Moved {result['moved']} · skipped {result['skipped']} · failed {result['failed']}",
                QSystemTrayIcon.Information, 4000,
            )
        self._on_preview()  # refresh view (now empty or with leftovers)

    def _on_undo(self):
        if QMessageBox.question(
            self, "Undo last batch",
            "Undo the last organize batch?\nOnly the most recent batch can be undone."
        ) != QMessageBox.Yes:
            return
        result, err = undo_last_batch()
        if err:
            QMessageBox.information(self, "Nothing to undo", err)
            return
        self.status.setText(f"Undo — reversed {result['undone']} · failed {result['failed']}")
        self._on_preview()

    def _on_settings(self):
        dlg = SettingsDialog(self.cfg, str(self.folder) if self.folder else "", self)
        if dlg.exec():
            dlg.apply()
            save_config(self.cfg)
            if self.cfg.get("default_folder"):
                p = Path(self.cfg["default_folder"])
                if p.is_dir():
                    self.folder = p
            self._refresh_folder_label()
            # refresh age combo to reflect new default
            cur = self.cfg.get("age_window_hours", 24 * 7)
            for i in range(self.age_combo.count()):
                if self.age_combo.itemData(i) == cur:
                    self.age_combo.setCurrentIndex(i); break
            self._render_empty("Settings saved. Press Preview to continue.")

    def _on_never_move(self, item, by_name):
        entry = {
            "path": item["name"] if by_name else str(item["path"].resolve()),
            "name_match": by_name,
        }
        for existing in self.cfg.get("never_move", []):
            if existing.get("path") == entry["path"] and \
                    existing.get("name_match") == entry["name_match"]:
                return
        self.cfg.setdefault("never_move", []).append(entry)
        save_config(self.cfg)
        self._on_preview()  # re-run preview to show exclusion applied

    def _hide_to_tray(self):
        self.hide()
        if self.tray:
            self.tray.showMessage(APP_NAME, "Running in the background.",
                                  QSystemTrayIcon.Information, 2000)

    def closeEvent(self, event):
        # X = quit
        QApplication.quit()
        event.accept()


# --- Tray --------------------------------------------------------------------
class Tray(QSystemTrayIcon):
    def __init__(self, window: MainWindow):
        super().__init__(make_icon())
        self.window = window
        self.setToolTip(APP_NAME)

        menu = QMenu()
        a_open = QAction("Open", self); a_open.triggered.connect(self._open)
        a_org = QAction("Organize now", self); a_org.triggered.connect(self._quick_organize)
        a_set = QAction("Settings", self)
        a_set.triggered.connect(lambda: (self._open(), window._on_settings()))
        a_quit = QAction("Quit", self); a_quit.triggered.connect(QApplication.quit)

        menu.addAction(a_open)
        menu.addAction(a_org)
        menu.addSeparator()
        menu.addAction(a_set)
        menu.addSeparator()
        menu.addAction(a_quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activate)

    def _open(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._open()

    def _quick_organize(self):
        if not self.window.folder or not self.window.folder.is_dir():
            self.showMessage(APP_NAME, "No folder selected.",
                             QSystemTrayIcon.Warning, 3000)
            return
        org = Organizer(self.window.cfg)
        res = org.organize(self.window.folder, manual=True)
        self.showMessage(
            APP_NAME,
            f"Moved {res['moved']} · skipped {res['skipped']} · failed {res['failed']}",
            QSystemTrayIcon.Information, 4000,
        )


# --- main --------------------------------------------------------------------
def run_startup_auto(cfg: dict, tray: QSystemTrayIcon):
    if not cfg.get("auto_organize_on_startup"):
        return
    folder = cfg.get("default_folder", "")
    if not folder or not Path(folder).is_dir():
        return
    # throttle: at most once per 12 hours
    last = cfg.get("last_auto_run")
    if last:
        try:
            if time.time() - float(last) < 12 * 3600:
                return
        except Exception:
            pass
    org = Organizer(cfg)
    res = org.organize(Path(folder), manual=False)
    cfg["last_auto_run"] = str(time.time())
    save_config(cfg)
    tray.showMessage(
        APP_NAME,
        f"Auto-organize: moved {res['moved']} · skipped {res['skipped']} · failed {res['failed']}",
        QSystemTrayIcon.Information, 4000,
    )


def main():
    minimized = "--minimized" in sys.argv
    QApplication.setQuitOnLastWindowClosed(False)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(make_icon())

    cfg, was_reset = load_config()

    window = MainWindow(cfg)
    tray = Tray(window)
    window.tray = tray
    tray.show()

    if was_reset:
        tray.showMessage(
            APP_NAME,
            "settings.json was corrupt or missing — reset to defaults.",
            QSystemTrayIcon.Warning, 5000,
        )

    # auto-organize on startup (throttled)
    QTimer.singleShot(600, lambda: run_startup_auto(cfg, tray))

    if not minimized:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()