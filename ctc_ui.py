import sys
import re
import math
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QPalette, QColor

# SharedState bridge (optional – gracefully absent if run standalone)
try:
    from shared_state import SharedState
    _SHARED_STATE_AVAILABLE = True
except ImportError:
    _SHARED_STATE_AVAILABLE = False
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QComboBox, QListWidget, QListWidgetItem,
    QSlider, QTableWidget, QTableWidgetItem, QPushButton,
    QLineEdit, QDialog, QCheckBox, QGridLayout, QSizePolicy, QTabWidget
)


# -----------------------------
# Red Line block data
# (section → list of (block_num, length_m, grade_pct, speed_kmh))
# -----------------------------
# Default Green Line schedule — waypoints for Train 1
# Each entry: (time_sec, section, block, station_name)
# Trains 2-10 are dispatched 3 minutes (180 s) later per train.
_G_MIN = 60   # helper: convert minutes → seconds
DEFAULT_GREEN_WAYPOINTS = [
    ( 0*_G_MIN, "A",   1, "Pioneer"),
    ( 1*_G_MIN, "A",   2, "Pioneer"),
    ( 4*_G_MIN, "C",   9, "Edgebrook"),
    ( 8*_G_MIN, "D",  16, "D Station"),
    (12*_G_MIN, "F",  22, "Whited"),
    (16*_G_MIN, "G",  31, "South Bank"),
    (19*_G_MIN, "I",  39, "Central"),
    (21*_G_MIN, "I",  48, "Inglewood"),
    (24*_G_MIN, "I",  57, "Overbrook"),
    (27*_G_MIN, "K",  65, "Glenbury"),
    (31*_G_MIN, "L",  73, "Dormont"),
    (34*_G_MIN, "N",  77, "Mt Lebanon"),
    (41*_G_MIN, "O",  88, "Poplar"),
    (44*_G_MIN, "P",  96, "Castle Shannon"),
    (48*_G_MIN, "T", 105, "Dormont"),
    (51*_G_MIN, "U", 113, "Glenbury"),
    (54*_G_MIN, "W", 123, "Overbrook"),
    (57*_G_MIN, "W", 132, "Inglewood"),
    (60*_G_MIN, "W", 141, "Central"),
    (90*_G_MIN, "W", 141, "Central"),   # end of run
]
_GREEN_NUM_TRAINS    = 10
_GREEN_TRAIN_GAP_SEC = 3 * 60   # 3 minutes between each train dispatch

# Station name -> (section, block) for manual dispatch start positions.
# We derive this from the default schedule waypoints so the UI starts the train
# where it would first appear in the station sequence.
GREEN_STATION_TO_START = {}
for _t, _sec, _blk, _st in DEFAULT_GREEN_WAYPOINTS:
    if not _st:
        continue
    # Keep the first occurrence to avoid later duplicates (e.g., Dormont repeats).
    if _st not in GREEN_STATION_TO_START:
        GREEN_STATION_TO_START[_st] = (_sec, _blk)

# "Yard" is treated as the beginning of the Green line run.
GREEN_STATION_TO_START["Yard"] = ("J", 58)  # Yard entry at block 58 (Section J)

# Red Line station -> (section, block) start positions
RED_STATION_TO_START = {
    "Yard":                  ("C",  9),   # Red yard connects at block 9
    "Shadyside":             ("C",  7),
    "Herron Ave":            ("F", 16),
    "Swissville":            ("G", 21),
    "Penn Station":          ("H", 25),
    "Steel Plaza":           ("H", 35),
    "First Ave":             ("H", 45),
    "Station Square":        ("I", 48),
    "South Hills Junction":  ("L", 60),
}

GREEN_LINE_BLOCKS = {
    "A": [(1,  100,  0.5, 45), (2,  100, 1.0,  45), (3,  100, 1.5,  45)],
    "B": [(4,  100,  2.0, 45), (5,  100, 3.0,  45), (6,  100, 4.0,  45)],
    "C": [(7,  100,  5.0, 45), (8,  100, 0.0,  45), (9,  100, -5.0, 45),
          (10, 100, -4.5, 45), (11, 100, -4.0, 45), (12, 100, -3.0, 45)],
    "D": [(13, 150, 0.0, 70), (14, 150, 0.0, 70), (15, 150, 0.0, 70),
          (16, 150, 0.0, 70)],
    "E": [(17, 150, 0.0, 60), (18, 150, 0.0, 60), (19, 150, 0.0, 60),
          (20, 150, 0.0, 60)],
    "F": [(21, 300, 0.0, 70), (22, 300, 0.0, 70), (23, 300, 0.0, 70),
          (24, 300, 0.0, 70), (25, 200, 0.0, 70), (26, 100, 0.0, 70),
          (27,  50, 0.0, 30), (28,  50, 0.0, 30)],
    "G": [(29, 50, 0.0, 30), (30, 50, 0.0, 30), (31, 50, 0.0, 30),
          (32, 50, 0.0, 30)],
    "H": [(33, 50, 0.0, 30), (34, 50, 0.0, 30), (35, 50, 0.0, 30)],
    "I": [(36, 50, 0.0, 30), (37, 50, 0.0, 30), (38, 50, 0.0, 30),
          (39, 50, 0.0, 30), (40, 50, 0.0, 30), (41, 50, 0.0, 30),
          (42, 50, 0.0, 30), (43, 50, 0.0, 30), (44, 50, 0.0, 30),
          (45, 50, 0.0, 30), (46, 50, 0.0, 30), (47, 50, 0.0, 30),
          (48, 50, 0.0, 30), (49, 50, 0.0, 30), (50, 50, 0.0, 30),
          (51, 50, 0.0, 30), (52, 50, 0.0, 30), (53, 50, 0.0, 30),
          (54, 50, 0.0, 30), (55, 50, 0.0, 30), (56, 50, 0.0, 30),
          (57, 50, 0.0, 30)],
    "J": [(58, 50, 0.0, 30), (59, 50, 0.0, 30), (60, 50, 0.0, 30),
          (61, 50, 0.0, 30), (62, 50, 0.0, 30)],
    "K": [(63, 100, 0.0, 70), (64, 100, 0.0, 70), (65, 200, 0.0, 70),
          (66, 200, 0.0, 70), (67, 100, 0.0, 40), (68, 100, 0.0, 40)],
    "L": [(69, 100, 0.0, 40), (70, 100, 0.0, 40), (71, 100, 0.0, 40),
          (72, 100, 0.0, 40), (73, 100, 0.0, 40)],
    "M": [(74, 100, 0.0, 40), (75, 100, 0.0, 40), (76, 100, 0.0, 40)],
    "N": [(77, 300, 0.0, 70), (78, 300, 0.0, 70), (79, 300, 0.0, 70),
          (80, 300, 0.0, 70), (81, 300, 0.0, 70), (82, 300, 0.0, 70),
          (83, 300, 0.0, 70), (84, 300, 0.0, 70), (85, 300, 0.0, 70)],
    "O": [(86, 100, 0.0, 25), (87, 86.6, 0.0, 25), (88, 100, 0.0, 25)],
    "P": [(89,  75, -0.5, 25), (90,  75, -1.0, 25), (91,  75, -2.0, 25),
          (92,  75,  0.0, 25), (93,  75,  2.0, 25), (94,  75,  1.0, 25),
          (95,  75,  0.5, 25), (96,  75,  0.0, 25), (97,  75,  0.0, 25)],
    "Q": [(98, 75, 0.0, 25), (99, 75, 0.0, 25), (100, 75, 0.0, 25)],
    "R": [(101, 35, 0.0, 26)],
    "S": [(102, 100, 0.0, 28), (103, 100, 0.0, 28), (104, 80, 0.0, 28)],
    "T": [(105, 100, 0.0, 28), (106, 100, 0.0, 28), (107, 90, 0.0, 28),
          (108, 100, 0.0, 28), (109, 100, 0.0, 28)],
    "U": [(110, 100, 0.0, 30), (111, 100, 0.0, 30), (112, 100, 0.0, 30),
          (113, 100, 0.0, 30), (114, 162, 0.0, 30), (115, 100, 0.0, 30),
          (116, 100, 0.0, 30)],
    "V": [(117, 50, 0.0, 15), (118, 50, 0.0, 15), (119, 40, 0.0, 15),
          (120, 50, 0.0, 15), (121, 50, 0.0, 15)],
    "W": [(122, 50, 0.0, 20), (123, 50, 0.0, 20), (124, 50, 0.0, 20),
          (125, 50, 0.0, 20), (126, 50, 0.0, 20), (127, 50, 0.0, 20),
          (128, 50, 0.0, 20), (129, 50, 0.0, 20), (130, 50, 0.0, 20),
          (131, 50, 0.0, 20), (132, 50, 0.0, 20), (133, 50, 0.0, 20),
          (134, 50, 0.0, 20), (135, 50, 0.0, 20), (136, 50, 0.0, 20),
          (137, 50, 0.0, 20), (138, 50, 0.0, 20), (139, 50, 0.0, 20),
          (140, 50, 0.0, 20), (141, 50, 0.0, 20), (142, 50, 0.0, 20),
          (143, 50, 0.0, 20)],
    "X": [(144, 50, 0.0, 20), (145, 50, 0.0, 20), (146, 50, 0.0, 20)],
    "Y": [(147, 50, 0.0, 20), (148, 184, 0.0, 20), (149, 40, 0.0, 20)],
    "Z": [(150, 35, 0.0, 20)],
}

RED_LINE_BLOCKS = {
    "A": [(1,  50,  0.5,  40), (2,  50,  1.0,  40), (3,  50,  1.5,  40)],
    "B": [(4,  50,  2.0,  40), (5,  50,  1.5,  40), (6,  50,  1.0,  40)],
    "C": [(7,  75,  0.5,  40), (8,  75,  0.0,  40), (9,  75,  0.0,  40)],
    "D": [(10, 75,  0.0,  40), (11, 75, -0.5,  40), (12, 75, -1.0,  40)],
    "E": [(13, 70, -2.0,  40), (14, 60, -1.25, 40), (15, 60, -1.0,  40)],
    "F": [(16, 50, -0.5,  40), (17, 200, -0.5, 55), (18, 400, -0.06025, 70),
          (19, 400, 0.0,  70), (20, 200, 0.0,  70)],
    "G": [(21, 100, 0.0,  55), (22, 100, 0.0,  55), (23, 100, 0.0,  55)],
    "H": [(24, 50, 0.0, 70), (25, 50, 0.0, 70), (26, 50, 0.0, 70),
          (27, 50, 0.0, 70), (28, 50, 0.0, 70), (29, 60, 0.0, 70),
          (30, 60, 0.0, 70), (31, 50, 0.0, 70), (32, 50, 0.0, 70),
          (33, 50, 0.0, 70), (34, 50, 0.0, 70), (35, 50, 0.0, 70),
          (36, 50, 0.0, 70), (37, 50, 0.0, 70), (38, 50, 0.0, 70),
          (39, 50, 0.0, 70), (40, 60, 0.0, 70), (41, 60, 0.0, 70),
          (42, 50, 0.0, 70), (43, 50, 0.0, 70), (44, 50, 0.0, 70),
          (45, 50, 0.0, 70)],
    "I": [(46, 75, 0.0, 70), (47, 75, 0.0, 70), (48, 75, 0.0, 70)],
    "J": [(49, 50, 0.0, 60), (50, 50, 0.0, 60), (51, 50, 0.0, 55),
          (52, 43.2, 0.0, 55), (53, 50, 0.0, 55), (54, 50, 0.0, 55)],
    "K": [(55, 75, 0.5, 55), (56, 75, 0.5, 55), (57, 75, 0.5, 55)],
    "L": [(58, 75, 1.0, 55), (59, 75, 0.5, 55), (60, 75, 0.0, 55)],
    "M": [(61, 75, -0.5, 55), (62, 75, -1.0, 55), (63, 75, -1.0, 55)],
    "N": [(64, 75, -0.5, 55), (65, 75,  0.0, 55), (66, 75,  0.0, 55)],
    "O": [(67, 50,  0.0, 55)],
    "P": [(68, 50,  0.0, 55), (69, 50, 0.0, 55), (70, 50, 0.0, 55)],
    "Q": [(71, 50,  0.0, 55)],
    "R": [(72, 50,  0.0, 55)],
    "S": [(73, 50,  0.0, 55), (74, 50, 0.0, 55), (75, 50, 0.0, 55)],
    "T": [(76, 50,  0.0, 55)],
}

# ---------------------------------------------------------------------------
# Flat block lookup: block_num -> (section, length_m, speed_kmh)
# Built once at import time from the section dicts above.
# Used by the train advancement logic in _advance_external_trains.
# ---------------------------------------------------------------------------
_GREEN_BLOCK_INFO: dict[int, tuple[str, float, float]] = {}
for _sec, _blks in GREEN_LINE_BLOCKS.items():
    for _bn, _len, _grade, _spd in _blks:
        _GREEN_BLOCK_INFO[_bn] = (_sec, float(_len), float(_spd))

_RED_BLOCK_INFO: dict[int, tuple[str, float, float]] = {}
for _sec, _blks in RED_LINE_BLOCKS.items():
    for _bn, _len, _grade, _spd in _blks:
        _RED_BLOCK_INFO[_bn] = (_sec, float(_len), float(_spd))

# Maximum block numbers on each line (used to clamp advancement)
_GREEN_MAX_BLOCK = max(_GREEN_BLOCK_INFO.keys())  # 150
_RED_MAX_BLOCK   = max(_RED_BLOCK_INFO.keys())    # 76

# Blocks that have a switch: (section, block_num) -> list of "A → B" option strings
# From default Green Line block info (Infrastructure column)
GREEN_SWITCHES = {
    ("C", 12): ["12 → 13", "1 → 13"],           # SWITCH (12-13; 1-13)
    ("F", 28): ["28 → 29", "150 → 28"],         # SWITCH (28-29; 150-28)
    ("J", 58): ["57 → yard"],                    # SWITCH TO YARD (57-yard)
    ("J", 62): ["Yard → 63"],                   # SWITCH FROM YARD (Yard-63)
    ("M", 76): ["76 → 77", "77 → 101"],         # SWITCH (76-77;77-101)
    ("N", 85): ["85 → 86", "100 → 85"],         # SWITCH (85-86; 100-85)
}
# From default Red Line block info (Infrastructure column)
RED_SWITCHES = {
    ("C", 9): ["75 → yard", "yard → 75"],      # SWITCH TO/FROM YARD (75-yard)
    ("E", 15): ["15 → 16", "1 → 16"],          # SWITCH (15-16; 1-16)
    ("H", 27): ["27 → 28", "27 → 76"],         # SWITCH (27-28; 27-76)
    ("H", 32): ["32 → 33", "33 → 72"],         # SWITCH (32-33; 33-72)
    ("H", 38): ["38 → 39", "38 → 71"],         # SWITCH (38-39; 38-71)
    ("H", 43): ["43 → 44", "44 → 67"],         # SWITCH (43-44; 44-67)
    ("J", 52): ["52 → 53", "52 → 66"],         # SWITCH (52-53; 52-66)
}

# Railroad crossings from the provided block details (Infrastructure column).
# Key is the block that CONTAINS the crossing; messages are generated when a train is
# 1 block BEFORE (down) and 1 block AFTER (up).
GREEN_RAIL_CROSSINGS = {19, 108}  # E-19, T-108
RED_RAIL_CROSSINGS = {11, 47}     # D-11, I-47

# Stations from block details (Green + Red) for Schedule Info From/To dropdowns
SCHEDULE_STATIONS = [
    "Yard",
    # Green Line stations
    "Castle Shannon", "Central", "Dormont", "Edgebrook", "Glenbury",
    "Inglewood", "Mt Lebanon", "Overbrook", "Pioneer", "Poplar",
    "South Bank", "Whited",
    # Red Line stations
    "First Ave", "Herron Ave", "Penn Station", "Shadyside",
    "South Hills Junction", "Station Square", "Steel Plaza", "Swissville",
]
# Block number -> station name for each line (derived from track layout data)
# Used to populate the From/To dropdowns in the manual dispatch card.
GREEN_BLOCK_STATIONS = {
    2:   "Pioneer",
    9:   "Edgebrook",
    16:  "D Station",
    22:  "Whited",
    31:  "South Bank",
    39:  "Central",
    48:  "Inglewood",
    57:  "Overbrook",
    65:  "Glenbury",
    73:  "Dormont",
    77:  "Mt Lebanon",
    88:  "Poplar",
    96:  "Castle Shannon",
    105: "Dormont",
    114: "Glenbury",
    123: "Overbrook",
    132: "Inglewood",
    141: "Central",
}

RED_BLOCK_STATIONS = {
    7:  "Shadyside",
    16: "Herron Ave",
    21: "Swissville",
    25: "Penn Station",
    35: "Steel Plaza",
    45: "First Ave",
    48: "Station Square",
    60: "South Hills Junction",
}

def _dest_block_for_station(line_short: str, station_name: str) -> int | None:
    """Map a schedule station label to a representative block number (for arrival check)."""
    if not station_name:
        return None
    if station_name == "Yard":
        if line_short == "Green":
            return GREEN_STATION_TO_START["Yard"][1]
        return RED_STATION_TO_START["Yard"][1]
    if line_short == "Green":
        for bn, lbl in GREEN_BLOCK_STATIONS.items():
            if lbl == station_name:
                return bn
    else:
        for bn, lbl in RED_BLOCK_STATIONS.items():
            if lbl == station_name:
                return bn
    return None


def _yard_dispatch_start_block(line_short: str) -> int | None:
    """
    Block used when manually dispatching a train *from* Yard.

    Green line dispatches out of the yard onto block 63.
    Red line keeps its yard-connected start block.
    """
    if line_short == "Green":
        return 63
    return _dest_block_for_station(line_short, "Yard")


def _distance_between_blocks_m(
    block_info: dict[int, tuple[str, float, float]], start_block: int, end_block: int
) -> float:
    """
    Sum block lengths from start_block to end_block (inclusive), assuming
    increasing block-number traversal as used by manual train advancement.
    """
    if end_block < start_block:
        return 0.0
    total = 0.0
    for bn in range(start_block, end_block + 1):
        _sec, length_m, _spd = block_info.get(bn, ("", 50.0, 30.0))
        total += float(length_m)
    return total


def _block_items(line: str):
    """
    Return a list of (display_str, block_num) tuples for every block on the
    given line, formatted as '57 (Overbrook)' for station blocks or just '42'.
    """
    if line == "Green":
        total, stations = 150, GREEN_BLOCK_STATIONS
    else:
        total, stations = 76, RED_BLOCK_STATIONS
    items = []
    for b in range(1, total + 1):
        stn = stations.get(b)
        label = f"{b} ({stn})" if stn else str(b)
        items.append((label, b))
    return items



# Station → section anchor (approx) for drawing station lights on each line.
# These anchors correspond to section labels drawn on the diagrams.
GREEN_STATION_ANCHORS = {
    "Pioneer": "A",
    "Edgebrook": "C",
    "Whited": "F",
    "South Bank": "G",
    "Central": "I",
    "Inglewood": "I",
    "Overbrook": "W",
    "Glenbury": "K",
    "Dormont": "L",
    "Mt Lebanon": "N",
    "Poplar": "O",
    "Castle Shannon": "P",
    "D Station": "D",
}

RED_STATION_ANCHORS = {
    "Shadyside": "C",
    "Herron Ave": "F",
    "Swissville": "G",
    "Penn Station": "H",
    "Steel Plaza": "H",
    "First Ave": "H",
    "Station Square": "I",
    "South Hills Junction": "L",
}

# -----------------------------
# Data helpers
# -----------------------------
@dataclass
class ClickRegion:
    rect: QRect
    label: str
    line: str


# -----------------------------
# Popup: Block Details
# -----------------------------
class BlockDetailsDialog(QDialog):
    """
    Popup shown when a track section is clicked.
    If `blocks` is provided (list of (block_num, length_m, grade_pct, speed_kmh)),
    a dropdown lets the user choose a specific block and see its details.
    """
    def __init__(self, parent, title: str, line_name: str, speed: str,
                 authority: str, show_switch: bool = False,
                 blocks=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        panel = QFrame()
        panel.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:8px;")

        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        header = QLabel(f"{title} — {line_name}")
        header.setStyleSheet("font-weight:700; font-size:13px;")
        layout.addWidget(header)

        self.maintenance = QCheckBox("Maintenance Mode")
        layout.addWidget(self.maintenance)

        if blocks:
            # ── block selector ────────────────────────────────────────────────
            layout.addWidget(QLabel("Select block:"))
            self.block_combo = QComboBox()
            for bn, length, grade, spd in blocks:
                self.block_combo.addItem(f"Block {bn}", (bn, length, grade, spd))
            layout.addWidget(self.block_combo)

            # ── per-block detail labels ───────────────────────────────────────
            detail_frame = QFrame()
            detail_frame.setStyleSheet(
                "background:white; border:1px solid #cccccc; border-radius:6px;")
            detail_grid = QGridLayout(detail_frame)
            detail_grid.setContentsMargins(10, 8, 10, 8)
            detail_grid.setSpacing(4)

            detail_grid.addWidget(QLabel("Block #:"),        0, 0)
            self._lbl_block  = QLabel()
            detail_grid.addWidget(self._lbl_block,           0, 1)

            detail_grid.addWidget(QLabel("Length (m):"),     1, 0)
            self._lbl_length = QLabel()
            detail_grid.addWidget(self._lbl_length,          1, 1)

            detail_grid.addWidget(QLabel("Grade (%):"),      2, 0)
            self._lbl_grade  = QLabel()
            detail_grid.addWidget(self._lbl_grade,           2, 1)

            detail_grid.addWidget(QLabel("Speed limit:"),    3, 0)
            self._lbl_speed  = QLabel()
            detail_grid.addWidget(self._lbl_speed,           3, 1)

            layout.addWidget(detail_frame)

            self.block_combo.currentIndexChanged.connect(self._refresh_block)
            self._refresh_block(0)

            self.setFixedSize(380, 310)
        else:
            # ── legacy plain display (Green Line / generic) ───────────────────
            layout.addWidget(QLabel(f"Speed: {speed}"))
            layout.addWidget(QLabel(f"Authority: {authority}"))

            if show_switch:
                layout.addWidget(QLabel("Switch:"))
                sw = QComboBox()
                sw.addItems(["Switch 43-44", "Position A", "Position B"])
                layout.addWidget(sw)

            self.setFixedSize(420, 260)

        layout.addStretch(1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(120)
        close_btn.setStyleSheet("padding:6px 10px;")
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        outer = QVBoxLayout(self)
        outer.addWidget(panel)
        self.setLayout(outer)

    def _refresh_block(self, idx: int):
        data = self.block_combo.itemData(idx)
        if data is None:
            return
        bn, length, grade, spd = data
        self._lbl_block.setText(str(bn))
        self._lbl_length.setText(str(length))
        self._lbl_grade.setText(str(grade))
        self._lbl_speed.setText(f"{spd} km/h")


# -----------------------------
# Track Diagram Widget
# -----------------------------
class TrackDiagramWidget(QWidget):
    def __init__(self, on_block_clicked):
        super().__init__()
        self.on_block_clicked = on_block_clicked
        self.setMinimumHeight(420)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            "background:white; border:2px solid #c8c8c8; border-radius:8px;")
        self.click_regions: list[ClickRegion] = []
        self.selected_section: str | None = None
        self.train_sections: set = set()   # sections currently occupied by a train
        # (station_name, position) -> "green" | "yellow" | "red"
        # position ∈ {"before","after"}
        self.station_light_overrides: dict[tuple[str, str], str] = {}

    def _station_light_color(self, station: str, position: str) -> str:
        color = self.station_light_overrides.get((station, position))
        return color if color in ("green", "yellow", "red") else "green"

    def _c(self, name: str) -> QColor:
        """Return the colour for a track section based on its state."""
        if name == self.selected_section:
            return QColor("#0088cc")   # blue   — selected (highest priority)
        if name in self.train_sections:
            return QColor("#111111")   # black  — train present
        return QColor("#1a7a2e")       # green  — normal

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _X(t: float, xL: int, xR: int) -> int:
        return int(xL + t * (xR - xL))

    def _draw_dir(self, p: QPainter, pts: list[QPoint],
                  color: QColor, width: int):
        """Draw a directed polyline (arrow at the last segment's tip)."""
        pen = QPen(color, width, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        for i in range(len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])

        a, b = pts[-2], pts[-1]
        angle = math.atan2(b.y() - a.y(), b.x() - a.x())
        alen, aang = 12, math.radians(28)
        for da in (-aang, +aang):
            tip_x = int(b.x() - alen * math.cos(angle - da))
            tip_y = int(b.y() - alen * math.sin(angle - da))
            p.drawLine(b, QPoint(tip_x, tip_y))

    def _draw_bidir(self, p: QPainter, pts: list[QPoint],
                    color: QColor, width: int):
        """Draw a bidirectional track segment (arrows at both ends)."""
        self._draw_dir(p, pts, color, width)
        self._draw_dir(p, list(reversed(pts)), color, width)

    def _label(self, p: QPainter, name: str, pt: QPoint,
               highlight: bool = False):
        """Draw a rounded box with the block letter centred at pt."""
        px, py = 18, 12
        rect = QRect(pt.x() - px, pt.y() - py, px * 2, py * 2)

        if name == self.selected_section:
            # selected always wins — shows blue even if a train is on it
            p.setPen(QPen(QColor("#0055aa"), 2))
            p.setBrush(QColor("#cceeff"))
            text_color = QColor("#003366")
        elif name in self.train_sections:
            # train present — show black
            p.setPen(QPen(QColor("#111111"), 2))
            p.setBrush(QColor("#333333"))
            text_color = QColor("#ffffff")
        else:
            p.setPen(QPen(QColor("#aaaaaa"), 1))
            p.setBrush(QColor("white"))
            text_color = QColor("#222222")

        p.drawRoundedRect(rect, 6, 6)
        p.setPen(text_color)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)
        self.click_regions.append(ClickRegion(rect=rect, label=name,
                                              line="Green Line"))

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _evt):
        self.click_regions.clear()

        w = self.width()
        h = self.height()
        M = 55
        xL, xR = M, w - M

        # ── Full S-curve layout ───────────────────────────────────────────────
        # Row 1 (→): X  Y  Z  ──────────────────────────────────── C (corner)
        # Row 2 (←): I  H  G  F↔  E↔  D  A  B  (full H-row, right→left)
        # J junction + Yard spur
        # Row 3 (→): K  L  M  N  O  P  (Q spur)
        # Row 4 (←): R  S  T  U
        # Left column (↑): U  V  W  X

        yTop = int(h * 0.10)   # top row near widget top
        yH   = int(h * 0.32)   # H-row — W/Z span = 0.22 h (≈62 px @ 280)
        yJ   = int(h * 0.52)   # J junction — J section = 0.20 h (≈56 px)
        yMid = int(h * 0.65)   # K-row
        yBot = int(h * 0.85)
        yQ   = yJ - int(h * 0.04)             # Q spur top sits above yJ — makes P taller

        P = {
            # Row 1 (yTop, →): X Y Z — Z drops straight down to G/F junction
            "X": QPoint(self._X(0.03, xL, xR), yTop),
            "Y": QPoint(self._X(0.22, xL, xR), yTop),
            "Z": QPoint(self._X(0.40, xL, xR), yTop),  # same x as G

            # H-row (yH): positions left→right; track flows RIGHT→LEFT
            # W is the left-column junction at the same height
            "W": QPoint(self._X(0.03, xL, xR), yH),
            "I": QPoint(self._X(0.14, xL, xR), yH),
            "H": QPoint(self._X(0.26, xL, xR), yH),
            "G": QPoint(self._X(0.40, xL, xR), yH),    # same x as Z
            "F": QPoint(self._X(0.52, xL, xR), yH),    # bidirectional
            "E": QPoint(self._X(0.63, xL, xR), yH),    # bidirectional
            "D": QPoint(self._X(0.74, xL, xR), yH),    # bidirectional
            "A": QPoint(self._X(0.85, xL, xR), yH),
            "B": QPoint(self._X(0.97, xL, xR), yH),

            # Left column
            "V": QPoint(self._X(0.03, xL, xR), yMid),
            "U": QPoint(self._X(0.03, xL, xR), yBot),

            # J junction
            "J": QPoint(self._X(0.14, xL, xR), yJ),

            # K-row (yMid, →)
            "K": QPoint(self._X(0.14, xL, xR), yMid),
            "L": QPoint(self._X(0.30, xL, xR), yMid),
            "M": QPoint(self._X(0.46, xL, xR), yMid),
            "N": QPoint(self._X(0.60, xL, xR), yMid),
            "O": QPoint(self._X(0.73, xL, xR), yMid),
            "P": QPoint(self._X(0.93, xL, xR), yMid),   # wider loop
            "Q": QPoint(self._X(0.93, xL, xR), yQ),     # same x as P → clean rectangle

            # Bottom row (yBot, ←)
            "R": QPoint(self._X(0.60, xL, xR), yBot),
            "S": QPoint(self._X(0.46, xL, xR), yBot),
            "T": QPoint(self._X(0.30, xL, xR), yBot),
        }

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        TW = 5  # track line width

        # ── Row 1: X → Y → Z  (rightward; Z drops straight down to G/F junc) ──
        self._draw_dir(p, [P["X"], P["Y"]], self._c("X"), TW)
        self._draw_dir(p, [P["Y"], P["Z"]], self._c("Y"), TW)
        self._draw_dir(p, [P["Z"], P["G"]], self._c("Z"), TW)   # vertical drop

        # ── C arch: branches UP from head of A (= D node) → top-right → B ───
        c_branch = QPoint(P["D"].x(), yH)    # head (tip) of section A on H-row
        c_top_l  = QPoint(P["D"].x(), yTop)  # top-left of arch
        c_top_r  = QPoint(P["B"].x(), yTop)  # top-right of arch
        self._draw_dir(p, [c_branch, c_top_l, c_top_r, P["B"]], self._c("C"), TW)

        # ── Full H-row: B → A → D ↔ E ↔ F ↔ G → H → I  (right to left) ─────
        self._draw_dir(p, [P["B"], P["A"]], self._c("B"), TW)
        self._draw_dir(p, [P["A"], P["D"]], self._c("A"), TW)
        self._draw_bidir(p, [P["D"], P["E"]], self._c("D"), TW)
        self._draw_bidir(p, [P["E"], P["F"]], self._c("E"), TW)
        self._draw_bidir(p, [P["F"], P["G"]], self._c("F"), TW)
        self._draw_dir(p, [P["G"], P["H"]], self._c("G"), TW)
        self._draw_dir(p, [P["H"], P["I"]], self._c("H"), TW)

        # ── Left column: U → V → W → X  (upward) ─────────────────────────────
        self._draw_dir(p, [P["U"], P["V"]], self._c("U"), TW)
        self._draw_dir(p, [P["V"], P["W"]], self._c("V"), TW)
        self._draw_dir(p, [P["W"], P["X"]], self._c("W"), TW)

        # ── I → J  ────────────────────────────────────────────────────────────
        self._draw_dir(p, [P["I"], P["J"]], self._c("I"), TW)

        # ── Yard spur ─────────────────────────────────────────────────────────
        yard_tip = QPoint(P["J"].x() + 130, P["J"].y())
        self._draw_dir(p, [P["J"], yard_tip], self._c("Yard"), TW)

        # ── J → K ─────────────────────────────────────────────────────────────
        self._draw_dir(p, [P["J"], P["K"]], self._c("J"), TW)

        # ── K-row: K → L → M → N → O → P ─────────────────────────────────────
        self._draw_dir(p, [P["K"], P["L"]], self._c("K"), TW)
        self._draw_dir(p, [P["L"], P["M"]], self._c("L"), TW)
        self._draw_dir(p, [P["M"], P["N"]], self._c("M"), TW)
        self._draw_dir(p, [P["N"], P["O"]], self._c("N"), TW)
        self._draw_dir(p, [P["O"], P["P"]], self._c("O"), TW)

        # ── Q spur: O → Q (up), Q → P (across) ───────────────────────────────
        self._draw_dir(
            p, [P["O"], QPoint(P["O"].x(), P["Q"].y()), P["Q"]], self._c("Q"), TW)
        self._draw_dir(p, [P["Q"], P["P"]], self._c("P"), TW)

        # ── Bottom row: R → S → T → U ─────────────────────────────────────────
        self._draw_dir(p, [P["R"], P["S"]], self._c("R"), TW)
        self._draw_dir(p, [P["S"], P["T"]], self._c("S"), TW)
        self._draw_dir(p, [P["T"], P["U"]], self._c("T"), TW)

        # ── R branches UP to merge at the N level ─────────────────────────────
        self._draw_dir(
            p, [P["R"], QPoint(P["R"].x(), P["N"].y())], self._c("R"), TW)

        # ── Labels at segment midpoints, offset away from the track line ───────
        font = QFont("Helvetica", 10)
        font.setBold(True)
        p.setFont(font)

        OFF = 22

        def mid(a, b): return QPoint((a.x() + b.x()) // 2,
                                     (a.y() + b.y()) // 2)

        label_pts = {
            # Row 1: horizontal → below; Z is vertical → left
            "X":    mid(P["X"], P["Y"])                           + QPoint(0,  OFF),
            "Y":    mid(P["Y"], P["Z"])                           + QPoint(0,  OFF),
            "Z":    mid(P["Z"], P["G"])                           + QPoint(-(OFF + 6), 0),

            # C arch top (horizontal) — label inside/below the arch top
            "C":    QPoint((P["D"].x() + P["B"].x()) // 2, yTop) + QPoint(0, OFF),

            # H-row: horizontal → below
            "B":    mid(P["B"], P["A"])           + QPoint(0,  OFF),
            "A":    mid(P["A"], P["D"])           + QPoint(0,  OFF),
            "D":    mid(P["D"], P["E"])           + QPoint(0,  OFF),
            "E":    mid(P["E"], P["F"])           + QPoint(0,  OFF),
            "F":    mid(P["F"], P["G"])           + QPoint(0,  OFF),
            "G":    mid(P["G"], P["H"])           + QPoint(0,  OFF),
            "H":    mid(P["H"], P["I"])           + QPoint(0,  OFF),

            # Left column: vertical → left
            "W":    mid(P["W"], P["X"])           + QPoint(-OFF - 10, 0),
            "V":    mid(P["V"], P["W"])           + QPoint(-OFF - 10, 0),
            "U":    mid(P["U"], P["V"])           + QPoint(-OFF - 10, 0),

            # I → J: vertical → left
            "I":    mid(P["I"], P["J"])           + QPoint(-(OFF + 4), 0),

            # Yard spur (→): label right at arrowhead tip
            "Yard": yard_tip                      + QPoint(22, 0),

            # J → K: vertical → left
            "J":    mid(P["J"], P["K"])           + QPoint(-(OFF + 4), 0),

            # K-row: horizontal → below
            "K":    mid(P["K"], P["L"])           + QPoint(0,  OFF),
            "L":    mid(P["L"], P["M"])           + QPoint(0,  OFF),
            "M":    mid(P["M"], P["N"])           + QPoint(0,  OFF),
            "N":    mid(P["N"], P["O"])           + QPoint(0,  OFF),
            "O":    mid(P["O"], P["P"])           + QPoint(0,  OFF),

            # Q spur vertical rise → left
            "Q":    mid(P["O"], QPoint(P["O"].x(), P["Q"].y()))
                                                  + QPoint(-(OFF + 4), 0),

            # P connector (now straight vertical) → left
            "P":    mid(P["Q"], P["P"])           + QPoint(-(OFF + 4), 0),

            # Bottom row: horizontal → below (already below)
            "R":    mid(P["R"], P["S"])           + QPoint(0, OFF),
            "S":    mid(P["S"], P["T"])           + QPoint(0, OFF),
            "T":    QPoint((P["T"].x() + P["U"].x()) // 2,
                           P["T"].y())            + QPoint(0, OFF),
        }

        # ── Station lights (before / at / after) ─────────────────────────────
        _LIGHT_COLORS = {
            "green":  (QColor("#22aa44"), QColor("#115522")),
            "yellow": (QColor("#ddaa00"), QColor("#886600")),
            "red":    (QColor("#cc2222"), QColor("#881111")),
        }

        def _draw_station_lights(station_name: str, anchor_section: str):
            anchor = label_pts.get(anchor_section)
            if anchor is None:
                return
            # Place two lights near the anchor point (slightly above track).
            base = anchor + QPoint(0, -34)
            pts = {
                "before": base + QPoint(-18, 0),
                "after":  base + QPoint(18, 0),
            }
            for pos, cpt in pts.items():
                col = self._station_light_color(station_name, pos)
                fill, ring = _LIGHT_COLORS[col]
                p.setPen(QPen(ring, 2))
                p.setBrush(fill)
                p.drawEllipse(cpt, 6, 6)

        for st, sec in GREEN_STATION_ANCHORS.items():
            _draw_station_lights(st, sec)

        for name, lpt in label_pts.items():
            self._label(p, name, lpt, highlight=False)

        # Line name badge — top-left corner
        badge_font = QFont("Helvetica", 9)
        badge_font.setBold(True)
        p.setFont(badge_font)
        p.setPen(QPen(QColor("#1a7a2e"), 1))
        p.setBrush(QColor("#e8f5e9"))
        p.drawRoundedRect(QRect(4, 3, 72, 16), 4, 4)
        p.drawText(QRect(4, 3, 72, 16), Qt.AlignmentFlag.AlignCenter, "Green Line")

        p.end()

    def mousePressEvent(self, evt):
        pos = evt.position().toPoint()
        for reg in self.click_regions:
            if reg.rect.contains(pos):
                if self.selected_section == reg.label:
                    self.selected_section = None
                    self.on_block_clicked(None, reg.line)  # signal deselect
                else:
                    self.selected_section = reg.label
                    self.on_block_clicked(reg.label, reg.line)
                self.update()
                return


# ──────────────────────────────────────────────────────────────────────────────
# Red Line Track Diagram
# ──────────────────────────────────────────────────────────────────────────────
class RedLineDiagramWidget(TrackDiagramWidget):
    """Red Line — full layout:
       Top arches:  O↕ P─ Q↕   and   R↕ S─ T↕   and   A↕ B─ C↕
       Main H row:  H ─ G ─ F ─ E ─ D  (all bidir)
       I column:    vertical drop from H-level to bottom
       J/K row:     J ─ K  with L dropping from K's right end
       Bottom row:  N (right from I) and M (left from L)
    """

    def _c(self, name: str) -> QColor:
        if name == self.selected_section:
            return QColor("#0088cc")   # blue — selected (highest priority)
        if name in self.train_sections:
            return QColor("#111111")   # black — train present
        return QColor("#b01010")       # red — normal

    def paintEvent(self, _evt):
        self.click_regions.clear()

        w = self.width()
        h = self.height()
        M = 55
        xL, xR = M, w - M

        # ── Y-levels ──────────────────────────────────────────────────────────
        yTop  = int(h * 0.12)   # top arches — moved up for taller O/Q/R/T/A/C
        yH    = int(h * 0.42)   # main H row — moved down for taller arches
        yYard = int(h * 0.60)   # Yard spur below D
        yJ    = int(h * 0.63)   # J/K row  AND  3-way junction for I
        yN    = int(h * 0.87)   # N/M bottom row

        # ── X junction coordinates ────────────────────────────────────────────
        xI  = self._X(0.03, xL, xR)   # far-left  (I, H left end)
        xO  = self._X(0.13, xL, xR)   # O on H  (left P-arch)
        xQ  = self._X(0.24, xL, xR)   # Q on H  (right P-arch)
        xR_ = self._X(0.33, xL, xR)   # R on H  (left S-arch) — moved left
        xT  = self._X(0.44, xL, xR)   # T on H  (right S-arch) — moved left
        xHG = self._X(0.56, xL, xR)   # H/G junction — moved left so G-F-E-D are wider
        xGF = self._X(0.67, xL, xR)   # G/F junction
        xFE = self._X(0.77, xL, xR)   # F/E junction  ← A arch
        xED = self._X(0.86, xL, xR)   # E/D junction
        xDR = self._X(0.96, xL, xR)   # D right end   ← C arch
        xYD = xED + int((xDR - xED) * 0.72)  # Yard branch point (72% along D, clear of D label)
        xJK = self._X(0.26, xL, xR)   # J/K junction
        xKR = self._X(0.46, xL, xR)   # K right end = L position
        xNM = xJK                      # N/M junction — aligned with J/K so rectangle is symmetric

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        TW = 5

        def pt(x, y): return QPoint(x, y)

        # ── Main H row (all bidir) ─────────────────────────────────────────────
        self._draw_bidir(p, [pt(xI,  yH), pt(xHG, yH)], self._c("H"), TW)
        self._draw_bidir(p, [pt(xHG, yH), pt(xGF, yH)], self._c("G"), TW)
        self._draw_bidir(p, [pt(xGF, yH), pt(xFE, yH)], self._c("F"), TW)
        self._draw_bidir(p, [pt(xFE, yH), pt(xED, yH)], self._c("E"), TW)
        self._draw_bidir(p, [pt(xED, yH), pt(xDR, yH)], self._c("D"), TW)

        # ── O / P / Q arch (left, above H) ────────────────────────────────────
        self._draw_bidir(p, [pt(xO,  yH),   pt(xO,  yTop)], self._c("O"), TW)
        self._draw_bidir(p, [pt(xO,  yTop), pt(xQ,  yTop)], self._c("P"), TW)
        self._draw_bidir(p, [pt(xQ,  yTop), pt(xQ,  yH)],   self._c("Q"), TW)

        # ── R / S / T arch (middle-right, above H) ────────────────────────────
        self._draw_bidir(p, [pt(xR_, yH),   pt(xR_, yTop)], self._c("R"), TW)
        self._draw_bidir(p, [pt(xR_, yTop), pt(xT,  yTop)], self._c("S"), TW)
        self._draw_bidir(p, [pt(xT,  yTop), pt(xT,  yH)],   self._c("T"), TW)

        # ── A / B / C arch (far right, above H) ───────────────────────────────
        self._draw_bidir(p, [pt(xFE, yH),   pt(xFE, yTop)], self._c("A"), TW)
        self._draw_bidir(p, [pt(xFE, yTop), pt(xDR, yTop)], self._c("B"), TW)
        self._draw_bidir(p, [pt(xDR, yTop), pt(xDR, yH)],   self._c("C"), TW)

        # ── I: vertical from H-row down to J junction ─────────────────────────
        self._draw_bidir(p, [pt(xI, yH), pt(xI, yJ)], self._c("I"), TW)

        # ── J / K row ─────────────────────────────────────────────────────────
        self._draw_bidir(p, [pt(xI,  yJ), pt(xJK, yJ)], self._c("J"), TW)
        self._draw_bidir(p, [pt(xJK, yJ), pt(xKR, yJ)], self._c("K"), TW)

        # ── L: vertical from K right end down to bottom row ───────────────────
        self._draw_bidir(p, [pt(xKR, yJ), pt(xKR, yN)], self._c("L"), TW)

        # ── N: L-shape — drops from J junction to yN then goes right ─────────
        # This fills the left vertical gap (yJ→yN) as part of N rather than I
        self._draw_bidir(p, [pt(xI, yJ), pt(xI, yN), pt(xNM, yN)], self._c("N"), TW)
        self._draw_bidir(p, [pt(xNM, yN), pt(xKR, yN)], self._c("M"), TW)

        # ── Yard spur: bidir down from midpoint of D ──────────────────────────
        self._draw_bidir(p, [pt(xYD, yH), pt(xYD, yYard)], self._c("Yard"), TW)

        # ── Labels ────────────────────────────────────────────────────────────
        font = QFont("Helvetica", 10)
        font.setBold(True)
        p.setFont(font)
        OFF = 20
        yard_lbl = pt(xYD + OFF + 4, (yH + yYard) // 2)   # right of Yard spur

        def mid(ax, ay, bx, by):
            return QPoint((ax + bx) // 2, (ay + by) // 2)

        label_pts = {
            # Main H row: horizontal → below
            "H": mid(xI,  yH, xHG, yH) + QPoint(0,  OFF),
            "G": mid(xHG, yH, xGF, yH) + QPoint(0,  OFF),
            "F": mid(xGF, yH, xFE, yH) + QPoint(0,  OFF),
            "E": mid(xFE, yH, xED, yH) + QPoint(0,  OFF),
            "D": mid(xED, yH, xDR, yH) + QPoint(0,  OFF),
            # O/P/Q arch: verticals → left, horizontal top → above (keep clear)
            "O": mid(xO, yH,   xO, yTop) + QPoint(-(OFF + 4), 0),
            "P": mid(xO, yTop, xQ, yTop) + QPoint(0,  OFF),
            "Q": mid(xQ, yTop, xQ, yH)   + QPoint(-(OFF + 4), 0),
            # R/S/T arch: verticals → left, horizontal top → below
            "R": mid(xR_, yH,   xR_, yTop) + QPoint(-(OFF + 4), 0),
            "S": mid(xR_, yTop, xT,  yTop) + QPoint(0,  OFF),
            "T": mid(xT,  yTop, xT,  yH)   + QPoint(-(OFF + 4), 0),
            # A/B/C arch: verticals → left, horizontal top → below
            "A": mid(xFE, yH,   xFE, yTop) + QPoint(-(OFF + 6), 0),
            "B": mid(xFE, yTop, xDR, yTop) + QPoint(0,  OFF),
            "C": mid(xDR, yTop, xDR, yH)   + QPoint( OFF + 6, 0),
            # I column: vertical → left (yH→yJ)
            "I": mid(xI, yH, xI, yJ)       + QPoint(-(OFF + 6), 0),
            # J/K row: horizontal → below
            "J": mid(xI,  yJ, xJK, yJ)     + QPoint(0,  OFF),
            "K": mid(xJK, yJ, xKR, yJ)     + QPoint(0,  OFF),
            # L: vertical → left
            "L": mid(xKR, yJ, xKR, yN)     + QPoint(-(OFF + 4), 0),
            # N: label on the horizontal leg, below
            "N": mid(xI, yN, xNM, yN)      + QPoint(0,  OFF),
            "M": mid(xNM, yN, xKR, yN)     + QPoint(0,  OFF),
            # Yard: bottom of spur, shifted right to clear D label
            "Yard": pt(xYD + 40, yYard),
        }

        # ── Station lights (before / at / after) ─────────────────────────────
        _LIGHT_COLORS = {
            "green":  (QColor("#22aa44"), QColor("#115522")),
            "yellow": (QColor("#ddaa00"), QColor("#886600")),
            "red":    (QColor("#cc2222"), QColor("#881111")),
        }

        def _draw_station_lights(station_name: str, anchor_section: str):
            anchor = label_pts.get(anchor_section)
            if anchor is None:
                return
            base = anchor + QPoint(0, -30)
            pts = {
                "before": base + QPoint(-18, 0),
                "after":  base + QPoint(18, 0),
            }
            for pos, cpt in pts.items():
                col = self._station_light_color(station_name, pos)
                fill, ring = _LIGHT_COLORS[col]
                p.setPen(QPen(ring, 2))
                p.setBrush(fill)
                p.drawEllipse(cpt, 6, 6)

        for st, sec in RED_STATION_ANCHORS.items():
            _draw_station_lights(st, sec)

        for name, lpt in label_pts.items():
            self._label(p, name, lpt)

        # Line name badge — top-left corner
        badge_font = QFont("Helvetica", 9)
        badge_font.setBold(True)
        p.setFont(badge_font)
        p.setPen(QPen(QColor("#b01010"), 1))
        p.setBrush(QColor("#fdecea"))
        p.drawRoundedRect(QRect(4, 3, 60, 16), 4, 4)
        p.drawText(QRect(4, 3, 60, 16), Qt.AlignmentFlag.AlignCenter, "Red Line")

        p.end()

    def mousePressEvent(self, evt):
        pos = evt.position().toPoint()
        for reg in self.click_regions:
            if reg.rect.contains(pos):
                if self.selected_section == reg.label:
                    self.selected_section = None
                    self.on_block_clicked(None, "Red Line")  # signal deselect
                else:
                    self.selected_section = reg.label
                    self.on_block_clicked(reg.label, "Red Line")
                self.update()
                return


# -----------------------------
# Main Window
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self, shared_state=None):
        super().__init__()
        # SharedState bridge (None when running standalone)
        self._shared: "SharedState | None" = shared_state
        self.setWindowTitle("Central Traffic Control Office")
        self.resize(1400, 1032)

        root = QWidget()
        root.setStyleSheet("QWidget#root { background:white; }")
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        # ── Header ───────────────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(44)
        header.setStyleSheet("background:#2a3f5f; border-radius:8px;")
        hbox = QHBoxLayout(header)
        hbox.setContentsMargins(10, 6, 10, 6)

        logo = QLabel("Logo")
        logo.setStyleSheet(
            "background:#3d5a80; color:white; font-weight:700; "
            "padding:4px 10px; border-radius:6px; font-size:12px;")
        title = QLabel("Central Traffic Control Office")
        title.setStyleSheet(
            "color:white; font-weight:800; font-size:15px;")
        self.header_clock_label = QLabel("")
        self.header_clock_label.setStyleSheet(
            "color:white; font-weight:700; font-size:13px;")

        hbox.addWidget(logo)
        hbox.addSpacing(16)
        hbox.addWidget(title)
        hbox.addStretch(1)
        hbox.addWidget(self.header_clock_label)
        outer.addWidget(header)

        # ── Track Diagram panel ───────────────────────────────────────────────
        track_tabs = QTabWidget()
        track_tabs.setStyleSheet(
            "QTabWidget::pane { background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px; }"
            "QTabBar::tab { background:#e0e0e0; color:#333; padding:6px 20px; font-weight:600; }"
            "QTabBar::tab:selected { background:#f0f0f0; color:#000; border-bottom:2px solid #4a6fa5; }"
        )

        # Green Line tab
        green_tab = QWidget()
        green_tab.setStyleSheet("background:#f0f0f0;")
        green_layout = QVBoxLayout(green_tab)
        green_layout.setContentsMargins(8, 6, 8, 6)
        self.track = TrackDiagramWidget(self.on_block_clicked)
        self.track.setFixedHeight(310)
        green_layout.addWidget(self.track)
        track_tabs.addTab(green_tab, "  Green Line  ")

        # Red Line tab
        red_tab = QWidget()
        red_tab.setStyleSheet("background:#f0f0f0;")
        red_layout = QVBoxLayout(red_tab)
        red_layout.setContentsMargins(8, 6, 8, 6)
        self.red_track = RedLineDiagramWidget(self.on_red_block_clicked)
        self.red_track.setFixedHeight(310)
        red_layout.addWidget(self.red_track)
        track_tabs.addTab(red_tab, "  Red Line  ")

        track_tabs.setFixedHeight(370)
        outer.addWidget(track_tabs)


        # ── Bottom row ────────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        outer.addLayout(bottom, stretch=1)

        # Left: Block selection
        left = QFrame()
        left.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        self.left_title = QLabel("Block Selection")
        self.left_title.setStyleSheet("font-weight:800;")
        left_layout.addWidget(self.left_title)

        self.block_combo = QComboBox()
        self.block_combo.setEnabled(False)
        self.block_combo.addItem("— click a section on the track —")
        self.block_combo.currentIndexChanged.connect(self._on_block_combo_changed)
        left_layout.addWidget(self.block_combo)

        # Block information area (replaces block list): Suggested Speed, Suggested Authority, Switch, Maintenance
        self.detail_card = QFrame()
        self.detail_card.setStyleSheet(
            "background:#e8ecf4; border:1px solid #b0b8cc; border-radius:8px;")
        # Reserve enough height for all content (including switch row) so layout doesn't shift when toggling maintenance
        self.detail_card.setMinimumHeight(200)
        detail_lay = QVBoxLayout(self.detail_card)
        detail_lay.setContentsMargins(10, 8, 10, 8)
        detail_lay.setSpacing(8)
        self.maint_check = QCheckBox("Maintenance")
        self.maint_check.setStyleSheet("font-weight:600;")
        self.maint_check.toggled.connect(self._on_maint_toggled)
        detail_lay.addWidget(self.maint_check)
        self.detail_title_lbl = QLabel("")
        self.detail_title_lbl.setStyleSheet(
            "border:1px solid #999; border-radius:4px; padding:3px 6px; background:white;")
        detail_lay.addWidget(self.detail_title_lbl)
        self.detail_placeholder = QLabel("Select a block from the dropdown above.")
        self.detail_placeholder.setStyleSheet("color:#666; font-style:italic;")
        self.detail_placeholder.setWordWrap(True)
        detail_lay.addWidget(self.detail_placeholder)
        self.speed_auth_frame = QFrame()
        self.speed_auth_frame.setStyleSheet(
            "border:1px solid #999; border-radius:4px; background:white;")
        sa_lay = QVBoxLayout(self.speed_auth_frame)
        sa_lay.setContentsMargins(6, 4, 6, 4)
        self.speed_label = QLabel("Suggested Speed:")
        self.speed_edit = QLineEdit()
        self.speed_edit.setPlaceholderText("—")
        self.speed_edit.setReadOnly(True)
        self.speed_edit.setMinimumWidth(80)  # stable width so "0 mph" / "28.0 mph" don't shift layout
        sa_lay.addWidget(self.speed_label)
        sa_lay.addWidget(self.speed_edit)
        self.auth_label = QLabel("Suggested Authority:")
        self.auth_edit = QLineEdit()
        self.auth_edit.setPlaceholderText("—")
        self.auth_edit.setReadOnly(True)
        self.auth_edit.setMinimumWidth(80)  # stable width so "N/A" / "328.1 ft" don't shift layout
        sa_lay.addWidget(self.auth_label)
        sa_lay.addWidget(self.auth_edit)
        detail_lay.addWidget(self.speed_auth_frame)
        self.speed_auth_frame.hide()
        self.switch_row = QHBoxLayout()
        self.switch_lbl = QLabel("Switch:")
        self.switch_combo_detail = QComboBox()
        self.switch_combo_detail.setMinimumWidth(120)
        self.switch_combo_detail.currentTextChanged.connect(self._on_switch_changed)
        self.switch_row.addWidget(self.switch_lbl)
        self.switch_row.addWidget(self.switch_combo_detail, stretch=1)
        self.switch_widget = QWidget()
        self.switch_widget.setLayout(self.switch_row)
        self.switch_widget.setStyleSheet("background:transparent; border:none;")
        detail_lay.addWidget(self.switch_widget)
        self.switch_widget.hide()
        detail_lay.addStretch(1)
        left_layout.addWidget(self.detail_card, stretch=1)

        # Keep left panel height stable so toggling maintenance doesn't shift the whole layout
        left.setMinimumHeight(260)
        bottom.addWidget(left, stretch=1)

        # Center: Schedule Info
        center = QFrame()
        center.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(10)

        center_title = QLabel("Schedule Info")
        center_title.setStyleSheet("font-weight:800;")
        center_layout.addWidget(center_title)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        center_layout.addLayout(cards)

        # Automatic/New card
        auto_card = QFrame()
        auto_card.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        auto_grid = QGridLayout(auto_card)
        auto_grid.setContentsMargins(10, 10, 10, 10)

        btn_auto = QPushButton("Automatic")
        btn_auto.setStyleSheet(
            "background:#4a6fa5; padding:6px 10px; border-radius:8px;")
        btn_new = QPushButton("New")
        btn_new.setStyleSheet(
            "background:#e0e0e0; padding:6px 10px; border-radius:8px;")
        auto_grid.addWidget(btn_auto, 0, 0)
        auto_grid.addWidget(btn_new, 0, 1)

        load_lbl = QLabel("Schedules to load")
        auto_grid.addWidget(load_lbl, 1, 0, 1, 2)

        self.load_combo = QComboBox()
        self.load_combo.addItems(["Default Green"])
        auto_grid.addWidget(self.load_combo, 2, 0, 1, 2)

        self.btn_load = QPushButton("Load")
        self.btn_load.setStyleSheet(
            "background:#4a6fa5; color:white; font-weight:bold;"
            "padding:6px 10px; border-radius:8px;")
        self.btn_load.clicked.connect(self._on_load_schedule)
        auto_grid.addWidget(self.btn_load, 3, 0, 1, 2)

        cards.addWidget(auto_card)

        # Manual schedule card
        man_card = QFrame()
        man_card.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        man_grid = QGridLayout(man_card)
        man_grid.setContentsMargins(10, 10, 10, 10)

        # Line selector
        man_grid.addWidget(QLabel("Line:"), 0, 0)
        self.dispatch_line_combo = QComboBox()
        self.dispatch_line_combo.addItems(["Green", "Red"])
        self.dispatch_line_combo.currentTextChanged.connect(self._on_dispatch_line_changed)
        man_grid.addWidget(self.dispatch_line_combo, 0, 1)

        man_grid.addWidget(QLabel("From:"), 1, 0)
        self.origin_combo = QComboBox()
        self.origin_combo.setMaxVisibleItems(20)
        man_grid.addWidget(self.origin_combo, 1, 1)

        man_grid.addWidget(QLabel("To:"), 2, 0)
        self.dest_combo = QComboBox()
        self.dest_combo.setMaxVisibleItems(20)
        man_grid.addWidget(self.dest_combo, 2, 1)

        man_grid.addWidget(QLabel("Arrival Time (HH:MM):"), 3, 0)
        self.time_entry = QLineEdit("00:00")
        man_grid.addWidget(self.time_entry, 3, 1)

        self.btn_man_load = QPushButton("Load")
        self.btn_man_load.setStyleSheet(
            "background:#4a6fa5; color:white; font-weight:bold; padding:6px 10px; border-radius:8px;")
        self.btn_man_load.clicked.connect(self._on_manual_load)
        man_grid.addWidget(self.btn_man_load, 4, 0, 1, 2)

        # Populate From/To with Green Line blocks on startup
        self._on_dispatch_line_changed("Green")

        cards.addWidget(man_card)

        # Existing train: change destination
        exist_card = QFrame()
        exist_card.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        exist_grid = QGridLayout(exist_card)
        exist_grid.setContentsMargins(10, 10, 10, 10)
        exist_grid.setHorizontalSpacing(8)
        exist_grid.setVerticalSpacing(6)

        exist_grid.addWidget(QLabel("Train:"), 0, 0)
        self.exist_train_combo = QComboBox()
        self.exist_train_combo.setEnabled(False)
        self.exist_train_combo.addItem("No editable trains")
        exist_grid.addWidget(self.exist_train_combo, 0, 1)

        exist_grid.addWidget(QLabel("New Destination:"), 1, 0)
        self.exist_dest_combo = QComboBox()
        self.exist_dest_combo.addItems(SCHEDULE_STATIONS)
        exist_grid.addWidget(self.exist_dest_combo, 1, 1)

        exist_grid.addWidget(QLabel("New Arrival (HH:MM):"), 2, 0)
        self.exist_arrival_entry = QLineEdit("00:00")
        exist_grid.addWidget(self.exist_arrival_entry, 2, 1)

        self.btn_change_dest = QPushButton("Apply")
        self.btn_change_dest.setStyleSheet(
            "background:#4a6fa5; color:white; font-weight:bold; padding:6px 10px; border-radius:8px;")
        self.btn_change_dest.clicked.connect(self._on_change_destination)
        exist_grid.addWidget(self.btn_change_dest, 3, 0, 1, 2)

        cards.addWidget(exist_card)

        # Big gray info box
        big = QFrame()
        big.setStyleSheet(
            "background:#d9d9d9; border:2px solid #c8c8c8; border-radius:10px;")
        big_layout = QVBoxLayout(big)
        big_layout.addStretch(1)
        self.info_msg = QLabel(
            "(Schedule details / messages / upcoming trains would display here)")
        self.info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_msg.setStyleSheet("color:#333333;")
        self.info_msg.setWordWrap(True)
        big_layout.addWidget(self.info_msg)
        big_layout.addStretch(1)

        center_layout.addWidget(big, stretch=1)
        bottom.addWidget(center, stretch=2)

        # Right: Sidebar
        right = QFrame()
        right.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Simulation Speed"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(10)
        self.speed_lbl = QLabel("10%")
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_lbl.setText(f"{v}%"))
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_lbl)
        right_layout.addLayout(speed_row)

        sch_lbl = QLabel("Active Trains")
        sch_lbl.setStyleSheet("font-weight:800;")
        right_layout.addWidget(sch_lbl)

        # Table — Train id matches controller/model; destination shows goal vs ✓ arrived
        self.schedule_table = QTableWidget(0, 5)
        self.schedule_table.setHorizontalHeaderLabels(
            ["Train", "Line", "Section", "Now (block)", "Destination"])
        self.schedule_table.verticalHeader().setVisible(False)
        self.schedule_table.setFixedHeight(155)

        # "No active trains" overlay — shown when table is empty
        self._no_trains_lbl = QLabel("No active trains")
        self._no_trains_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_trains_lbl.setStyleSheet("color:#888888; font-style:italic;")
        self._no_trains_lbl.setFixedHeight(155)

        # Use a stacked-style container so label and table occupy same space
        trains_stack = QWidget()
        trains_stack.setFixedHeight(155)  # prevent layout shift when toggling table/label visibility
        trains_stack_layout = QVBoxLayout(trains_stack)
        trains_stack_layout.setContentsMargins(0, 0, 0, 0)
        trains_stack_layout.addWidget(self.schedule_table)
        trains_stack_layout.addWidget(self._no_trains_lbl)
        self._refresh_trains_view()
        right_layout.addWidget(trains_stack)

        thr_lbl = QLabel("Ticket Sales")
        thr_lbl.setStyleSheet("font-weight:800;")
        right_layout.addWidget(thr_lbl)

        self.thru_table = QTableWidget(2, 2)
        self.thru_table.setHorizontalHeaderLabels(
            ["Line", "Ticket Sales"])
        self.thru_table.verticalHeader().setVisible(False)
        self.thru_table.setItem(0, 0, QTableWidgetItem("Red Line"))
        self.thru_table.setItem(0, 1, QTableWidgetItem("100"))
        self.thru_table.setItem(1, 0, QTableWidgetItem("Green Line"))
        self.thru_table.setItem(1, 1, QTableWidgetItem("250"))
        self.thru_table.setFixedHeight(120)
        right_layout.addWidget(self.thru_table)

        right_layout.addStretch(1)
        bottom.addWidget(right, stretch=1)

        # ── Refresh timer for Active Trains table ────────────────────────────
        self._train_timer = QTimer(self)
        self._train_timer.setInterval(100)   # 100 ms = 0.1 s
        self._train_timer.timeout.connect(self._poll_active_trains)
        self._train_timer.start()

        # ── Wayside-output poll timer (reads SharedState every 100 ms) ───────
        self._wayside_poll_timer = QTimer(self)
        self._wayside_poll_timer.setInterval(100)
        self._wayside_poll_timer.timeout.connect(self._poll_wayside_outputs)
        if self._shared is not None:
            self._wayside_poll_timer.start()

        # ── Header clock timer (simulation-scaled local time) ────────────────
        self._sim_clock_dt = datetime.now()
        self._sim_clock_last_wall = time.monotonic()
        self._header_clock_timer = QTimer(self)
        self._header_clock_timer.setInterval(100)
        self._header_clock_timer.timeout.connect(self._update_header_clock)
        self._update_header_clock()
        self._header_clock_timer.start()

        self._current_line = None
        self._current_section = None
        self._external_trains = {}
        self._maint_occupancy_id = None
        self._manual_train_counter = 0
        self._pending_timers = []
        self._rail_cross_state = {}  # (line_short, crossing_block) -> "down" | "up" | None

    # ── Interactions ──────────────────────────────────────────────────────────

    def _update_header_clock(self) -> None:
        """
        Update header clock and scale it with simulation speed.

        At slider=10, clock runs at 1x wall-clock.
        Higher slider values speed it up proportionally.
        """
        now_wall = time.monotonic()
        elapsed_wall_s = max(0.0, now_wall - getattr(self, "_sim_clock_last_wall", now_wall))
        self._sim_clock_last_wall = now_wall

        try:
            speed_factor = max(1.0, float(self.speed_slider.value())) / 10.0
        except Exception:
            speed_factor = 1.0

        self._sim_clock_dt = self._sim_clock_dt + timedelta(seconds=elapsed_wall_s * speed_factor)
        self.header_clock_label.setText(self._sim_clock_dt.strftime("%I:%M:%S %p"))

    def _suggested_speed_text_for_block(self, line_full: str, section: str, block_num: int) -> str | None:
        """
        Return a live suggested speed for the selected block.
        Recomputes speed from that block to destination using remaining wall-clock
        time to the train's target arrival.
        """
        for info in getattr(self, "_external_trains", {}).values():
            if info.get("line") != line_full:
                continue
            try:
                cur_block = int(info.get("block"))
                dest_block = int(info.get("dest_block"))
                target_block = int(block_num)
            except (TypeError, ValueError):
                continue

            # Current external-train movement logic traverses increasing block
            # numbers toward destination; only show route-ahead blocks.
            if not (cur_block <= target_block <= dest_block):
                continue

            arrival_str = (info.get("arrival") or "").strip()
            if not (arrival_str and re.match(r"^\d{1,2}:\d{2}$", arrival_str)):
                continue

            try:
                hh, mm = arrival_str.split(":")
                h, m = int(hh), int(mm)
                now_dt = datetime.now()
                target_dt = now_dt.replace(hour=h, minute=m, second=0, microsecond=0)
                if target_dt <= now_dt:
                    target_dt += timedelta(days=1)
                wall_remaining_s = (target_dt - now_dt).total_seconds()
                if wall_remaining_s <= 0:
                    continue

                block_info = _GREEN_BLOCK_INFO if "Green" in line_full else _RED_BLOCK_INFO

                # Remaining metres from the selected block to destination.
                if target_block == cur_block:
                    _s, cur_len_m, _v = block_info.get(cur_block, ("", 50.0, 30.0))
                    dist_in_cur = float(info.get("dist_in_block_m", 0.0))
                    dist_in_cur = max(0.0, min(dist_in_cur, float(cur_len_m)))
                    remaining_m = max(0.0, float(cur_len_m) - dist_in_cur)
                    if dest_block > cur_block:
                        remaining_m += _distance_between_blocks_m(
                            block_info, cur_block + 1, dest_block
                        )
                else:
                    remaining_m = _distance_between_blocks_m(
                        block_info, target_block, dest_block
                    )

                if remaining_m <= 0:
                    continue

                sk_val = (remaining_m / max(1e-6, wall_remaining_s)) * 3.6
            except Exception:
                continue

            return f"{round(sk_val * 0.621371, 1)} mph"
        return None

    def _update_block_panel(self, label, line: str, track_widget):
        """Shared logic: update bottom-left panel for any line/section click."""
        if label is None:
            self.left_title.setText("Block Selection")
            self.block_combo.blockSignals(True)
            self.block_combo.clear()
            self.block_combo.addItem("— click a section on the track —")
            self.block_combo.setEnabled(False)
            self.block_combo.blockSignals(False)
            if self._maint_occupancy_id is not None:
                self.remove_train(self._maint_occupancy_id)
                self._maint_occupancy_id = None
            self.detail_card.hide()
            self._current_line = None
            self._current_section = None
            return

        self._current_line = line
        self._current_section = label
        data_src = GREEN_LINE_BLOCKS if line == "Green Line" else RED_LINE_BLOCKS
        blocks = data_src.get(label, [])

        self.left_title.setText(f"Block Selection: Section {label}")

        self.block_combo.blockSignals(True)
        self.block_combo.clear()
        if blocks:
            self.block_combo.addItem("Select a block")
            for bn, length, grade, spd in blocks:
                self.block_combo.addItem(f"Block {bn}")
            self.block_combo.setEnabled(True)
        else:
            self.block_combo.addItem("No blocks defined")
            self.block_combo.setEnabled(False)
        self.block_combo.blockSignals(False)

        self.detail_card.show()
        self.detail_placeholder.show()
        self.speed_auth_frame.hide()
        self.switch_widget.hide()

        track_widget.update()

    def _on_block_combo_changed(self, idx: int):
        """Show block info: Suggested Speed, Suggested Authority, and Switch when applicable."""
        text = self.block_combo.itemText(idx)
        parts = text.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            self.detail_placeholder.show()
            self.detail_title_lbl.hide()
            self.speed_auth_frame.hide()
            self.switch_widget.hide()
            return
        bn = int(parts[-1])
        if self._current_section is None or self._current_line is None:
            self.detail_placeholder.show()
            self.speed_auth_frame.hide()
            self.switch_widget.hide()
            return
        data_src = GREEN_LINE_BLOCKS if self._current_line == "Green Line" else RED_LINE_BLOCKS
        blocks = data_src.get(self._current_section, [])
        info = next((b for b in blocks if b[0] == bn), None)
        if info is None:
            self.detail_placeholder.show()
            self.speed_auth_frame.hide()
            self.switch_widget.hide()
            return
        _, length_m, grade, speed_kmh = info
        speed_mph = round(speed_kmh * 0.621371, 1)
        length_ft = round(length_m * 3.28084, 1)
        if self._maint_occupancy_id is not None:
            self.remove_train(self._maint_occupancy_id)
            self._maint_occupancy_id = None
        self.detail_placeholder.hide()
        self.detail_title_lbl.show()
        self.maint_check.blockSignals(True)
        self.maint_check.setChecked(False)
        self.maint_check.blockSignals(False)
        self.detail_title_lbl.setText(f"Block Details (Block {bn}, {self._current_line})")
        suggested_txt = self._suggested_speed_text_for_block(self._current_line, self._current_section, bn)
        self.speed_edit.setText(suggested_txt if suggested_txt is not None else f"{speed_mph} mph")
        self.auth_edit.setText(f"{length_ft} ft")
        self.speed_edit.setReadOnly(True)
        self.auth_edit.setReadOnly(True)
        self.speed_auth_frame.show()
        sw_src = GREEN_SWITCHES if self._current_line == "Green Line" else RED_SWITCHES
        sw_opts = sw_src.get((self._current_section, bn), [])
        self.switch_combo_detail.clear()
        if sw_opts:
            self.switch_combo_detail.addItems(sw_opts)
            self.switch_widget.show()
            self.switch_combo_detail.setEnabled(False)
        else:
            self.switch_widget.hide()

    def _on_maint_toggled(self, checked: bool):
        """In maintenance mode: allow editing Suggested Speed, Authority, and Switch; mark block occupied."""
        # Freeze layout so toggling maintenance doesn't cause a visible shift
        central = self.centralWidget()
        if central:
            central.setUpdatesEnabled(False)
        _defer_central_unfreeze = False
        try:
            # Keep block dropdown always enabled so it never gets stuck when toggling maintenance
            if self._current_section is not None and self.block_combo.isEnabled() is False:
                self.block_combo.setEnabled(True)
            text = self.block_combo.currentText()
            parts = text.split()
            bn = None
            if len(parts) >= 2 and parts[-1].isdigit():
                bn = int(parts[-1])
            sw_src = GREEN_SWITCHES if self._current_line == "Green Line" else RED_SWITCHES
            has_switch = bool(sw_src.get((self._current_section, bn), [])) if bn is not None else False
            if checked:
                self.speed_edit.setReadOnly(False)
                self.auth_edit.setReadOnly(False)
                self.speed_edit.setText("0 mph")
                self.auth_edit.setText("N/A")
                if has_switch:
                    self.switch_widget.show()
                    self.switch_combo_detail.setEnabled(True)
                    self.switch_combo_detail.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                else:
                    self.switch_widget.hide()
                if bn is not None and self._current_section is not None and self._current_line is not None:
                    self._maint_occupancy_id = f"Maint-{bn}"
                    def _deferred_inject():
                        self.inject_train(self._maint_occupancy_id, self._current_line, self._current_section, bn)
                        if central:
                            central.setUpdatesEnabled(True)
                    _defer_central_unfreeze = True
                    QTimer.singleShot(0, _deferred_inject)
                    return  # unfreeze happens in deferred callback
            else:
                if self._maint_occupancy_id is not None:
                    self.remove_train(self._maint_occupancy_id)
                    self._maint_occupancy_id = None
                self.speed_edit.setReadOnly(True)
                self.auth_edit.setReadOnly(True)
                if has_switch:
                    self.switch_combo_detail.setEnabled(False)
                if bn is not None:
                    data_src = GREEN_LINE_BLOCKS if self._current_line == "Green Line" else RED_LINE_BLOCKS
                    blocks = data_src.get(self._current_section, [])
                    info = next((b for b in blocks if b[0] == bn), None)
                    if info:
                        _, length_m, _, speed_kmh = info
                        suggested_txt = self._suggested_speed_text_for_block(self._current_line, self._current_section, bn)
                        self.speed_edit.setText(
                            suggested_txt if suggested_txt is not None else f"{round(speed_kmh * 0.621371, 1)} mph"
                        )
                        self.auth_edit.setText(f"{round(length_m * 3.28084, 1)} ft")
                if not has_switch:
                    self.switch_widget.hide()
        finally:
            # Re-enable always unless maintenance ON with a valid block (deferred inject re-enables).
            # Otherwise toggling maintenance with no block selected left the whole CTC non-interactive.
            if central and not _defer_central_unfreeze:
                central.setUpdatesEnabled(True)

    def _on_switch_changed(self, text: str):
        if not text:
            return
        if not self.maint_check.isChecked():
            return
        block_text = self.block_combo.currentText()
        if block_text in ("Select a block", "— click a section on the track —", "No blocks defined"):
            return
        parts = block_text.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            return
        bn = int(parts[-1])
        sw_src = GREEN_SWITCHES if self._current_line == "Green Line" else RED_SWITCHES
        if (self._current_section, bn) not in sw_src:
            return
        line_short = "Green" if self._current_line == "Green Line" else "Red"
        self.info_msg.setText(f"Switch at Block {bn} ({line_short} Line, Section {self._current_section}) has been set to {text}.")
        self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")

    def inject_train(self, train_id: str, line: str, section: str, block: int):
        """Add a train (manual or maintenance) to the active list."""
        prev = self._external_trains.get(train_id, {})
        self._external_trains[train_id] = {
            **prev,
            "line": line,
            "section": section,
            "block": block,
        }
        self._poll_active_trains()

    def remove_train(self, train_id: str):
        """Remove a train from the active list."""
        self._external_trains.pop(train_id, None)
        self._poll_active_trains()

    def _refresh_existing_train_combo(self):
        """Refresh the train dropdown used to change destinations (manual/external trains only)."""
        self.exist_train_combo.blockSignals(True)
        current_id = self.exist_train_combo.currentData()
        self.exist_train_combo.clear()

        # Only allow editing of non-simulation trains (manual/external/maintenance)
        items = []
        for tid, info in getattr(self, "_external_trains", {}).items():
            line = info.get("line", "")
            section = info.get("section", "")
            block = info.get("block", "")
            label = f"{line} — Sec {section} — Blk {block}"
            items.append((label, tid))

        if not items:
            self.exist_train_combo.addItem("No editable trains", None)
            self.exist_train_combo.setEnabled(False)
            self.btn_change_dest.setEnabled(False)
        else:
            for label, tid in items:
                self.exist_train_combo.addItem(label, tid)
            self.exist_train_combo.setEnabled(True)
            self.btn_change_dest.setEnabled(True)

            # keep previous selection if possible
            if current_id is not None:
                for i in range(self.exist_train_combo.count()):
                    if self.exist_train_combo.itemData(i) == current_id:
                        self.exist_train_combo.setCurrentIndex(i)
                        break

        self.exist_train_combo.blockSignals(False)

    def _on_change_destination(self):
        """Change destination and/or arrival time for an existing (manual/external) train."""
        tid = self.exist_train_combo.currentData()
        if not tid:
            return
        new_dest = self.exist_dest_combo.currentText()
        new_arrival = self.exist_arrival_entry.text().strip()
        if not re.match(r"^\d{1,2}:\d{2}$", new_arrival):
            self.info_msg.setText("Error: Arrival time must be in HH:MM format (e.g. 14:30).")
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return
        hh, mm = new_arrival.split(":")
        h, m = int(hh), int(mm)
        if h < 0 or h > 23 or m < 0 or m > 59:
            self.info_msg.setText("Error: Invalid time (hours 00–23, minutes 00–59).")
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return
        info = self._external_trains.get(tid)
        if not info:
            return
        info["dest"] = new_dest
        info["arrival"] = new_arrival
        ls = "Green" if "Green" in info.get("line", "") else "Red"
        db = _dest_block_for_station(ls, new_dest)
        if db is not None:
            info["dest_block"] = db
        line = info.get("line", "")
        section = info.get("section", "")
        block = info.get("block", "")
        self.info_msg.setText(
            f"Train updated ({line}, Sec {section}, Blk {block}) → Dest: {new_dest}, Arrival: {new_arrival}.")
        self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")

    def set_station_light(self, line: str, station: str, position: str, color: str):
        """
        Record a change to a station signal light and show a message.

        This is intended to be called by another module that already decided the
        new aspect for a given signal; this UI does NOT compute signalling logic.

        Parameters
        ----------
        line: "Green" or "Red"
        station: station name as shown in your schedules (e.g. "Central")
        position: one of "before", "after"
        color: "green", "yellow", or "red"  (traffic-light colours)
        """
        line_short = line.strip().title()
        if line_short not in ("Green", "Red"):
            return

        pos_norm = position.strip().lower()
        if pos_norm not in ("before", "after"):
            return

        color_norm = color.strip().lower()
        if color_norm not in ("green", "yellow", "red"):
            return

        station_name = station.strip()
        if not station_name:
            return

        widget = self.track if line_short == "Green" else self.red_track
        prev = widget._station_light_color(station_name, pos_norm)
        if prev == color_norm:
            return

        widget.station_light_overrides[(station_name, pos_norm)] = color_norm
        widget.update()

        pretty_pos = {"before": "Before", "after": "After"}[pos_norm]

        self.info_msg.setText(
            f"{line_short} Line — {station_name} ({pretty_pos}) light → {color_norm.upper()}")
        self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")

    def _on_dispatch_line_changed(self, line: str) -> None:
        """Repopulate From/To block dropdowns whenever the Line selector changes."""
        items = _block_items(line)

        # From-block is always Yard for manual dispatch.
        yard_block = _yard_dispatch_start_block(line)
        yard_label = next((lbl for lbl, bn in items if bn == yard_block), str(yard_block))

        self.origin_combo.blockSignals(True)
        self.origin_combo.clear()
        if yard_block is not None:
            self.origin_combo.addItem(yard_label)
        self.origin_combo.blockSignals(False)
        self.origin_combo.setCurrentIndex(0)

        self.dest_combo.blockSignals(True)
        self.dest_combo.clear()
        for label, _ in items:
            self.dest_combo.addItem(label)
        self.dest_combo.blockSignals(False)
        self.dest_combo.setCurrentIndex(len(items) - 1)

    def _on_manual_load(self):
        """Dispatch a manual train from the selected line/block to the destination block."""
        time_str = self.time_entry.text().strip()
        if not re.match(r"^\d{1,2}:\d{2}$", time_str):
            self.info_msg.setText("Error: Arrival time must be in HH:MM format (e.g. 14:30).")
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return
        parts = time_str.split(":")
        h, m = int(parts[0]), int(parts[1])
        if h < 0 or h > 23 or m < 0 or m > 59:
            self.info_msg.setText("Error: Invalid time (hours 00–23, minutes 00–59).")
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return

        line_short = self.dispatch_line_combo.currentText()   # "Green" or "Red"
        line       = f"{line_short} Line"

        # Block number is the part before " (" (or the whole string if no station name)
        origin_text = self.origin_combo.currentText().split(" (")[0].strip()
        dest_text   = self.dest_combo.currentText().split(" (")[0].strip()
        if not origin_text.isdigit() or not dest_text.isdigit():
            self.info_msg.setText("Error: Could not parse block selection.")
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return
        origin_block = int(origin_text)
        dest_block   = int(dest_text)

        # Manual dispatch is yard-origin only.
        yard_block = _yard_dispatch_start_block(line_short)
        if yard_block is None:
            self.info_msg.setText(f"Error: Could not resolve Yard block for {line_short} Line.")
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return
        if origin_block != yard_block:
            self.info_msg.setText(
                f"Error: Manual dispatch must start from Yard (block {yard_block})."
            )
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return

        if origin_block == dest_block:
            self.info_msg.setText("Error: Origin and destination cannot be the same block.")
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return

        now = datetime.now()
        arrival_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if arrival_time <= now:
            self.info_msg.setText("Error: Arrival time must be in the future.")
            self.info_msg.setStyleSheet("color:#c00; font-weight:bold;")
            return

        # Find section for the origin block
        data_src = GREEN_LINE_BLOCKS if line_short == "Green" else RED_LINE_BLOCKS
        section  = next(
            (sec for sec, blks in data_src.items()
             if any(b[0] == origin_block for b in blks)),
            "A"
        )

        # Station name labels for the confirmation message
        stn_map    = GREEN_BLOCK_STATIONS if line_short == "Green" else RED_BLOCK_STATIONS
        origin_lbl = "Yard" if origin_block == yard_block else stn_map.get(origin_block, f"Block {origin_block}")
        dest_lbl   = stn_map.get(dest_block,   f"Block {dest_block}")

        self._manual_train_counter += 1
        train_id = f"Manual-{line_short}-{self._manual_train_counter}"
        self._external_trains[train_id] = {
            "line":       line,
            "section":    section,
            "block":      origin_block,
            "origin":     origin_lbl,
            "dest":       dest_lbl,
            "dest_block": dest_block,
            "arrival":    time_str,
        }

        # Initial suggested speed from total trip distance and requested arrival.
        block_info = _GREEN_BLOCK_INFO if line_short == "Green" else _RED_BLOCK_INFO
        trip_distance_m = _distance_between_blocks_m(block_info, origin_block, dest_block)
        wall_remaining_s = max(1.0, (arrival_time - now).total_seconds())
        # Suggested speed is based on real wall-clock remaining time to the
        # requested arrival target.
        suggested_speed_kmh = (trip_distance_m / max(1.0, wall_remaining_s)) * 3.6
        self._external_trains[train_id]["suggested_speed_kmh"] = round(suggested_speed_kmh, 2)
        suggested_speed_mph = suggested_speed_kmh * 0.621371

        self._poll_active_trains()
        self.info_msg.setText(
            f"{line_short} Line train dispatched: {origin_lbl} → {dest_lbl}. "
            f"Sec {section}, Blk {origin_block}. Arrival at {time_str}. "
            f"Suggested speed: {suggested_speed_mph:.1f} mph."
        )
        self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")


    def on_block_clicked(self, label, line: str):
        self._update_block_panel(label, line, self.track)

    def on_red_block_clicked(self, label, line: str):
        self._update_block_panel(label, line, self.red_track)

    def _refresh_trains_view(self):
        """Show the table when trains exist, otherwise show 'No active trains'."""
        has_trains = self.schedule_table.rowCount() > 0
        self.schedule_table.setVisible(has_trains)
        self._no_trains_lbl.setVisible(not has_trains)

    def _on_load_schedule(self):
        """Start (or restart) the selected schedule simulation."""
        schedule = self.load_combo.currentText()
        if schedule == "Default Green":
            self._sim_schedule = "Default Green"
            self._sim_time_sec = 0
            self._sim_running  = True

            # Visual feedback
            self.btn_load.setText("Running ▶")
            self.btn_load.setStyleSheet(
                "background:#2e7d32; color:white; font-weight:bold;"
                "padding:6px 10px; border-radius:8px;")

            # Populate the table immediately — don't wait for the first timer tick
            self._poll_active_trains()

    def _poll_active_trains(self):
        """Called every 100 ms. Advances the simulation clock and refreshes the table."""
        # launch_system.py advances the clock in its own timer; avoid double-counting.
        if getattr(self, "_sim_running", False) and not getattr(
            self, "_integrated_sim_clock_from_launcher", False
        ):
            self._sim_time_sec += self.speed_slider.value()

        # Advance manually-dispatched train positions along the track.
        # This is a no-op when launch_system is driving positions via the track model.
        self._advance_external_trains()
        self._auto_route_arrived_trains_to_yard()

        trains = []
        # Integrated launcher uses 3 physical trains only; skip T-01…T-10 so the
        # CTC diagram / wayside occupancy match train controller & models.
        _hide_sched = getattr(self, "_integrated_hide_schedule_trains", False)
        if (
            getattr(self, "_sim_schedule", None) == "Default Green"
            and not _hide_sched
        ):
            end_sec = DEFAULT_GREEN_WAYPOINTS[-1][0]
            for i in range(_GREEN_NUM_TRAINS):
                train_num   = i + 1
                train_start = i * _GREEN_TRAIN_GAP_SEC
                train_t     = self._sim_time_sec - train_start

                if train_t < 0 or train_t > end_sec:
                    continue
                current_wp = DEFAULT_GREEN_WAYPOINTS[0]
                for wp in DEFAULT_GREEN_WAYPOINTS:
                    if wp[0] <= train_t:
                        current_wp = wp
                    else:
                        break
                _, section, block, station = current_wp
                detail = f"Blk {block}"
                if station:
                    detail += f" — {station}"
                trains.append({
                    "train":        f"T-{train_num:02d}",
                    "train_label":  f"T-{train_num:02d}",
                    "line":         "Green",
                    "section":      section,
                    "block":        detail,
                    "dest_display": "—",
                })

        for tid, info in getattr(self, "_external_trains", {}).items():
            line = info["line"].replace(" Line", "") if " Line" in info["line"] else info["line"]
            cur = int(info["block"]) if isinstance(info.get("block"), (int, float)) else 0
            dest_blk = info.get("dest_block")
            dest_nm = (info.get("dest") or "").strip()
            if dest_blk is not None and cur == int(dest_blk):
                dest_disp = f"✓ At {dest_nm}" if dest_nm else "✓ At destination block"
            elif dest_nm:
                dest_disp = f"→ {dest_nm}"
            elif dest_blk is not None:
                dest_disp = f"→ block {dest_blk}"
            else:
                dest_disp = "—"
            trains.append({
                "train":        tid,
                "train_label":  str(tid),
                "line":         line,
                "section":      info["section"],
                "block":        f"Blk {info['block']}",
                "dest_display": dest_disp,
            })

        self.schedule_table.setRowCount(len(trains))
        for row, t in enumerate(trains):
            self.schedule_table.setItem(row, 0, QTableWidgetItem(t.get("train_label", t.get("train", ""))))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(t["line"]))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(t["section"]))
            self.schedule_table.setItem(row, 3, QTableWidgetItem(t["block"]))
            self.schedule_table.setItem(row, 4, QTableWidgetItem(t.get("dest_display", "—")))

        self._refresh_trains_view()
        self._refresh_existing_train_combo()

        # ── Railroad crossing messages (no occupancy changes) ─────────────────
        def _blk_num(block_str: str) -> int | None:
            m = re.search(r"\bBlk\s+(\d+)\b", block_str)
            return int(m.group(1)) if m else None

        occupied_blocks = {"Green": set(), "Red": set()}
        for t in trains:
            bn = _blk_num(t.get("block", ""))
            if bn is None:
                continue
            if t.get("line") in occupied_blocks:
                occupied_blocks[t["line"]].add(bn)

        # Crossing state messages are driven by wayside outputs
        # via _poll_wayside_outputs — no duplicate detection here.

        occupied_green = {t["section"] for t in trains if t["line"] == "Green"}
        occupied_red   = {t["section"] for t in trains if t["line"] == "Red"}
        self.track.train_sections = occupied_green
        self.red_track.train_sections = occupied_red
        self.track.update()
        self.red_track.update()

        if not getattr(self, "_integrated_hide_schedule_trains", False):
            sim_trains = [
                t for t in trains
                if t["line"] == "Green"
                and isinstance(t.get("train"), str)
                and t["train"].startswith("T-")
            ]
            if getattr(self, "_sim_running", False) and len(sim_trains) == 0:
                last_train_end = (
                    DEFAULT_GREEN_WAYPOINTS[-1][0]
                    + (_GREEN_NUM_TRAINS - 1) * _GREEN_TRAIN_GAP_SEC
                )
                if self._sim_time_sec > last_train_end:
                    self._sim_running = False
                    self.btn_load.setText("Load")
                    self.btn_load.setStyleSheet(
                        "background:#4a6fa5; color:white; font-weight:bold;"
                        "padding:6px 10px; border-radius:8px;")

        # Push occupied block data to SharedState for Wayside to consume
        if self._shared is not None:
            self._build_ctc_block_state(trains)

    def _auto_route_arrived_trains_to_yard(self):
        """
        When an external train reaches a non-yard destination, automatically
        retarget it to Yard so the route can be sent back.
        """
        for tid, info in getattr(self, "_external_trains", {}).items():
            dest_block = info.get("dest_block")
            if dest_block is None:
                continue
            try:
                cur_block = int(info.get("block"))
                dest_block_int = int(dest_block)
            except (TypeError, ValueError):
                continue

            # We only retarget exactly when the train reaches its destination.
            if cur_block != dest_block_int:
                continue

            dest_name = (info.get("dest") or "").strip()
            if dest_name.lower() == "yard":
                continue

            # Prevent repeating the same auto-reroute every poll tick.
            if info.get("_auto_return_from_dest_block") == dest_block_int:
                continue

            line_full = info.get("line", "")
            line_short = "Green" if "Green" in line_full else "Red"
            yard_block = _dest_block_for_station(line_short, "Yard")
            if yard_block is None:
                continue

            info["_auto_return_from_dest_block"] = dest_block_int
            info["origin"] = dest_name or f"Block {dest_block_int}"
            info["dest"] = "Yard"
            info["dest_block"] = yard_block

            self.info_msg.setText(
                f"{line_short} Line {tid} reached {info['origin']}. "
                f"Destination auto-set to Yard."
            )
            self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")

    def on_left_list_selected(self):
        pass  # no detail panel — selection is visual only

    def on_left_block_changed(self, idx: int):
        pass  # no detail panel


def main(shared_state=None, app=None):
    """
    Launch the CTC window.

    Parameters
    ----------
    shared_state : SharedState | None
        Pass the SharedState instance when running alongside the Wayside.
        Pass None (default) to run the CTC standalone.
    app : QApplication | None
        Pass an existing QApplication if one is already running (launcher use).
        Pass None to create a new one (standalone use).

    Returns
    -------
    (QApplication, MainWindow)  so the launcher can manage lifetime.
    """
    own_app = app is None
    if own_app:
        app = QApplication(sys.argv)

    # Force Fusion style + light palette so dark-mode OS never overrides
    # text colors to white. All explicit stylesheets in the app assume
    # black text on light backgrounds.
    app.setStyle("Fusion")
    light = QPalette()
    light.setColor(QPalette.ColorRole.Window,          QColor(255, 255, 255))
    light.setColor(QPalette.ColorRole.WindowText,      QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.Base,            QColor(240, 240, 240))
    light.setColor(QPalette.ColorRole.AlternateBase,   QColor(225, 225, 225))
    light.setColor(QPalette.ColorRole.Text,            QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.ButtonText,      QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.BrightText,      QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.ToolTipBase,     QColor(255, 255, 220))
    light.setColor(QPalette.ColorRole.ToolTipText,     QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.Button,          QColor(225, 225, 225))
    light.setColor(QPalette.ColorRole.Highlight,       QColor(74,  111, 165))
    light.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(light)

    win = MainWindow(shared_state=shared_state)
    win.show()
    if own_app:
        sys.exit(app.exec())
    return app, win


if __name__ == "__main__":
    main()

# =============================================================================
# SharedState integration methods – appended by merger
# These are mixed into MainWindow at import time via monkey-patch below
# so that the original class definition above stays unmodified.
# =============================================================================

def _mw_advance_external_trains(self) -> None:
    """
    Advance manually-dispatched trains (entries in _external_trains whose key
    starts with 'Manual-' or 'Train-' but are NOT being driven by launch_system's
    track model) one simulation step forward along the track.

    Called at the top of _poll_active_trains every 100 ms tick.

    Skipped entirely when launch_system is managing positions, because that path
    overwrites _external_trains[Train-*].block directly from the track model.

    Physics
    -------
    Each train stores `dist_in_block_m` (metres travelled inside the current
    block) in its _external_trains entry.  Each tick we add:

        Δd = speed_kmh * (slider / 10.0) * TICK_WALL_SEC * (1000 / 3600)
             = speed_kmh * (slider / 10.0) * (100 / 3600)   # m per 100 ms tick

    When Δd pushes the train past the end of the current block it steps to
    block+1 (simple sequential routing, no switch awareness) and carries the
    remainder forward.  Stops at dest_block.
    """
    # When launch_system drives train positions, skip this entirely.
    if getattr(self, "_integrated_sim_clock_from_launcher", False):
        return

    try:
        slider = float(self.speed_slider.value())
    except Exception:
        slider = 10.0
    slider = max(1.0, min(100.0, slider))

    # Wall-clock seconds per tick × speed multiplier factor.
    # Slider value 10 = real time (100 ms tick = 0.1 s wall = 0.1 sim-sec at 1× speed).
    # The schedule increments _sim_time_sec by `slider` per tick, meaning at slider=10
    # one tick represents 10 sim-seconds (100× real time). We match that.
    TICK_WALL_SEC = 0.1          # timer interval in seconds
    sim_seconds_per_tick = slider   # same rate the schedule uses

    for tid, info in list(getattr(self, "_external_trains", {}).items()):
        # Only advance entries that were created by manual dispatch or that are
        # Train-* entries without a live track-model object driving them.
        # We detect "live" Train-* entries by checking if launch_system populated
        # them this tick (handled by the guard above).

        dest_block = info.get("dest_block")
        if dest_block is None:
            continue  # no destination set, nothing to move toward

        line_full = info.get("line", "")
        if "Green" in line_full:
            block_info = _GREEN_BLOCK_INFO
            max_block  = _GREEN_MAX_BLOCK
        elif "Red" in line_full:
            block_info = _RED_BLOCK_INFO
            max_block  = _RED_MAX_BLOCK
        else:
            continue

        try:
            cur_block = int(info["block"])
        except (KeyError, ValueError, TypeError):
            continue

        dest_block = int(dest_block)

        # Already at or past destination — don't move further.
        if cur_block >= dest_block:
            info["block"] = dest_block
            sec, _, _ = block_info.get(dest_block, (info.get("section", "A"), 50, 0))
            info["section"] = sec
            continue

        # Get current block properties.
        sec, length_m, speed_kmh = block_info.get(
            cur_block, (info.get("section", "A"), 50.0, 30.0))

        if speed_kmh <= 0:
            speed_kmh = 30.0

        # Compute a suggested speed to target the configured arrival time using:
        # remaining distance / effective simulation time remaining.
        suggested_speed_kmh = None
        arrival_str = (info.get("arrival") or "").strip()
        if arrival_str and re.match(r"^\d{1,2}:\d{2}$", arrival_str):
            try:
                hh, mm = arrival_str.split(":")
                h, m = int(hh), int(mm)
                now_dt = datetime.now()
                target_dt = now_dt.replace(hour=h, minute=m, second=0, microsecond=0)
                if target_dt <= now_dt:
                    target_dt += timedelta(days=1)
                wall_remaining_s = (target_dt - now_dt).total_seconds()

                # Remaining metres to destination (including current block remainder).
                _sec_cur, cur_len_m, _spd_cur = block_info.get(
                    cur_block, (sec, 50.0, 30.0)
                )
                dist_in_cur = float(info.get("dist_in_block_m", 0.0))
                dist_in_cur = max(0.0, min(dist_in_cur, float(cur_len_m)))
                remaining_m = max(0.0, float(cur_len_m) - dist_in_cur)
                if dest_block > cur_block:
                    remaining_m += _distance_between_blocks_m(
                        block_info, cur_block + 1, dest_block
                    )

                if wall_remaining_s > 0 and remaining_m > 0:
                    # Use wall-clock remaining time so the arrival target is
                    # interpreted as actual clock time (HH:MM), not sim-time.
                    suggested_speed_kmh = (remaining_m / max(1e-6, wall_remaining_s)) * 3.6
            except Exception:
                suggested_speed_kmh = None

        if suggested_speed_kmh is not None:
            info["suggested_speed_kmh"] = round(suggested_speed_kmh, 2)
            # Drive movement from the arrival-targeted suggested speed.
            speed_kmh = max(0.0, float(suggested_speed_kmh))

        # Distance to advance this tick (metres).
        # speed in km/h -> m/s = speed * 1000/3600; x sim_seconds_per_tick
        delta_m = speed_kmh * (1000.0 / 3600.0) * sim_seconds_per_tick

        dist = info.get("dist_in_block_m", 0.0) + delta_m

        # Step through blocks until distance budget is consumed or dest reached.
        while dist >= length_m and cur_block < dest_block:
            dist -= length_m
            cur_block = min(cur_block + 1, max_block)
            sec, length_m, speed_kmh = block_info.get(
                cur_block, (sec, 50.0, 30.0))
            if speed_kmh <= 0:
                speed_kmh = 30.0

        # Clamp to destination.
        if cur_block >= dest_block:
            cur_block = dest_block
            dist = 0.0
            sec, _, _ = block_info.get(dest_block, (sec, 50.0, 30.0))

        info["block"]           = cur_block
        info["section"]         = sec
        info["dist_in_block_m"] = dist


def _mw_push_block_data_to_wayside(self, line: str, block_data: dict) -> None:
    """Push CTC block data into SharedState for the Wayside to consume."""
    if self._shared is not None:
        self._shared.push_ctc_data(line, block_data)

def _mw_poll_wayside_outputs(self) -> None:
    """
    Called every 100 ms. Reads new wayside outputs from SharedState.
    Updates crossing messages and station signal lights on the track diagram.
    """
    if self._shared is None:
        return
    result = self._shared.poll_wayside_outputs()
    if result is None:
        return

    for line_name, outputs in result.items():
        if not outputs:
            continue
        line_short = line_name  # "Green" or "Red"

        # Crossing states
        for blk, state in outputs.get("crossings", {}).items():
            key = (line_short, blk)
            desired = "down" if state == "active" else "up"
            if self._rail_cross_state.get(key) != desired:
                self._rail_cross_state[key] = desired
                msg = (f"Railroad crossing active — {line_short} Line block {blk}."
                       if desired == "down"
                       else f"Railroad crossing clear — {line_short} Line block {blk}.")
                self.info_msg.setText(msg)
                self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")

        # Signal states → station light overrides
        widget = self.track if line_short == "Green" else self.red_track
        for blk, sig_color in outputs.get("signals", {}).items():
            if sig_color is None:
                continue
            stn, pos = _block_to_station_pos(line_short, blk)
            if stn and pos:
                widget.station_light_overrides[(stn, pos)] = sig_color
        widget.update()

def _mw_build_ctc_block_state(self, trains: list) -> None:
    """Derive occupied block data from current train list and push to SharedState."""
    if self._shared is None:
        return
    green_data: dict = {}
    red_data:   dict = {}

    # Build reverse lookups from external trains so we can compute destination-
    # based authority and override static cmd_speed with live suggested speed.
    ext = getattr(self, "_external_trains", {}) or {}
    # Key: (line_short, block_num) -> dest_block  (best-effort, may be None)
    _dest_lookup: dict = {}
    # Key: (line_short, block_num) -> suggested_speed_kmh (occupied block)
    _cmd_speed_lookup: dict = {}
    # Key: (line_short, block_num) -> (suggested_speed_kmh, dest_block)
    # Used to push live suggested speed across the active route segment.
    _route_speed_lookup: dict = {}
    for tid, tinfo in ext.items():
        db = tinfo.get("dest_block")
        line_full = tinfo.get("line", "")
        ls = "Green" if "Green" in line_full else ("Red" if "Red" in line_full else None)
        if not ls:
            continue
        try:
            cur_bn = int(tinfo.get("block", -1))
        except (TypeError, ValueError):
            continue
        if db is not None:
            try:
                _dest_lookup[(ls, int(tinfo.get("block", -1)))] = int(db)
            except (TypeError, ValueError):
                pass
        sk = tinfo.get("suggested_speed_kmh")
        try:
            if sk is not None:
                sk_val = max(0.0, float(sk))
                _cmd_speed_lookup[(ls, cur_bn)] = sk_val
                if db is not None:
                    dest_bn = int(db)
                    if cur_bn <= dest_bn:
                        for rb in range(cur_bn, dest_bn + 1):
                            _route_speed_lookup[(ls, rb)] = (sk_val, dest_bn)
        except (TypeError, ValueError):
            pass

    def _authority_km(line_short: str, cur_bn: int) -> float:
        """
        Sum block lengths from cur_bn up to dest_block (inclusive of cur_bn).
        Returns 0.0 when the train is already at its destination.
        Falls back to a single block's length if no destination is known.
        """
        block_info = _GREEN_BLOCK_INFO if line_short == "Green" else _RED_BLOCK_INFO
        dest = _dest_lookup.get((line_short, cur_bn))
        if dest is None:
            # No destination known: authority = just current block
            _, length_m, _ = block_info.get(cur_bn, ("", 50.0, 0.0))
            return length_m / 1000.0
        if dest <= cur_bn:
            # Already at or past destination: no further authority
            return 0.0
        # Accumulate lengths from cur_bn to dest (inclusive)
        total_m = 0.0
        max_b = max(block_info.keys()) if block_info else cur_bn
        for b in range(cur_bn, min(dest, max_b) + 1):
            _, blen, _ = block_info.get(b, ("", 50.0, 0.0))
            total_m += blen
        return total_m / 1000.0

    def _authority_to_dest_km(line_short: str, cur_bn: int, dest_bn: int) -> float:
        """Authority from cur_bn to dest_bn (inclusive), in km."""
        block_info = _GREEN_BLOCK_INFO if line_short == "Green" else _RED_BLOCK_INFO
        if dest_bn <= cur_bn:
            return 0.0
        total_m = 0.0
        max_b = max(block_info.keys()) if block_info else cur_bn
        for b in range(cur_bn, min(dest_bn, max_b) + 1):
            _, blen, _ = block_info.get(b, ("", 50.0, 0.0))
            total_m += blen
        return total_m / 1000.0

    for t in trains:
        line_short = t.get("line", "")
        blk_str    = t.get("block", "")
        import re as _re
        m = _re.search(r"\bBlk\s+(\d+)\b", blk_str)
        if not m:
            continue
        bn = int(m.group(1))

        if line_short == "Green":
            block_info, target = _GREEN_BLOCK_INFO, green_data
        elif line_short == "Red":
            block_info, target = _RED_BLOCK_INFO, red_data
        else:
            continue

        _, length_m, speed_kmh = block_info.get(bn, ("", 50.0, 30.0))
        cmd_speed_kmh = _cmd_speed_lookup.get((line_short, bn), speed_kmh)
        authority_km = _authority_km(line_short, bn)

        target[bn] = {
            "occupied":  True,
            "cmd_speed": cmd_speed_kmh,
            "authority": authority_km,
        }

    # Ensure wayside receives live suggested speed across the active route
    # segment (not just the currently occupied block).
    for (line_short, bn), (sk_val, dest_bn) in _route_speed_lookup.items():
        target = green_data if line_short == "Green" else red_data
        auth_km = _authority_to_dest_km(line_short, bn, dest_bn)
        existing = target.get(bn)
        if existing is not None:
            existing["cmd_speed"] = sk_val
            # Keep occupied state from existing snapshot; update authority so
            # route blocks have a destination-based value.
            existing["authority"] = auth_km
        else:
            target[bn] = {
                "occupied": False,
                "cmd_speed": sk_val,
                "authority": auth_km,
            }

    # Always push both lines (possibly empty). Otherwise wayside keeps stale
    # occupancy for blocks that are no longer in this snapshot, and an empty
    # train list would never clear the last push.
    self._shared.push_ctc_data("Green", green_data)
    self._shared.push_ctc_data("Red", red_data)

def _block_to_station_pos(line: str, block: int):
    """
    Map a wayside signal block to (station_name, position) where position
    is "before" or "after" relative to the station block.
    Returns (None, None) for switch-only blocks with no nearby station.

    Derived from the wayside signal_blocks sets and track layout data.
    """
    GREEN_MAP = {
        # Pioneer (station 2)
        1: ("Pioneer",         "before"),
        3: ("Pioneer",         "after"),
        # Edgebrook (station 9)
        8: ("Edgebrook",       "before"),
        10:("Edgebrook",       "after"),
        # D Station (station 16)
        15:("D Station",       "before"),
        17:("D Station",       "after"),
        # Whited (station 22)
        21:("Whited",          "before"),
        23:("Whited",          "after"),
        # South Bank (station 31)
        29:("South Bank",      "before"),
        30:("South Bank",      "before"),
        32:("South Bank",      "after"),
        # Central (station 39)
        38:("Central",         "before"),
        40:("Central",         "after"),
        # Inglewood (station 48)
        47:("Inglewood",       "before"),
        49:("Inglewood",       "after"),
        # Overbrook (station 57)
        56:("Overbrook",       "before"),
        57:("Overbrook",       "before"),   # station block itself has a signal
        58:("Overbrook",       "after"),
        # Glenbury (station 65)
        63:("Glenbury",        "before"),
        64:("Glenbury",        "before"),
        66:("Glenbury",        "after"),
        # Dormont (station 73)
        72:("Dormont",         "before"),
        74:("Dormont",         "after"),
        # Mt Lebanon (station 77)
        76:("Mt Lebanon",      "before"),
        77:("Mt Lebanon",      "before"),   # station block itself has a signal
        78:("Mt Lebanon",      "after"),
        # Poplar (station 88)
        86:("Poplar",          "before"),
        87:("Poplar",          "before"),
        89:("Poplar",          "after"),
        # Castle Shannon (station 96)
        95:("Castle Shannon",  "before"),
        97:("Castle Shannon",  "after"),
    }
    RED_MAP = {
        # Shadyside (station 7)
        6: ("Shadyside",             "before"),
        8: ("Shadyside",             "after"),
        9: ("Shadyside",             "after"),
        # Herron Ave (station 16)
        15:("Herron Ave",            "before"),
        16:("Herron Ave",            "before"),  # station block has a signal
        17:("Herron Ave",            "after"),
        # Swissville (station 21)
        20:("Swissville",            "before"),
        22:("Swissville",            "after"),
        # Penn Station (station 25)
        24:("Penn Station",          "before"),
        26:("Penn Station",          "after"),
        27:("Penn Station",          "after"),
        # Steel Plaza (station 35)
        33:("Steel Plaza",           "before"),
        34:("Steel Plaza",           "before"),
        36:("Steel Plaza",           "after"),
        # First Ave (station 45)
        43:("First Ave",             "before"),
        44:("First Ave",             "before"),
        46:("First Ave",             "after"),
        # Station Square (station 48)
        47:("Station Square",        "before"),
        49:("Station Square",        "after"),
        # South Hills Junction (station 60)
        59:("South Hills Junction",  "before"),
        61:("South Hills Junction",  "after"),
    }
    result = (GREEN_MAP if line == "Green" else RED_MAP).get(block)
    if result is None:
        return None, None
    return result


# Keep old name as alias so any other callers don't break
def _block_to_station(line: str, block: int) -> str:
    stn, _ = _block_to_station_pos(line, block)
    return stn or ""


# Monkey-patch the new methods onto MainWindow
MainWindow.push_block_data_to_wayside  = _mw_push_block_data_to_wayside
MainWindow._poll_wayside_outputs        = _mw_poll_wayside_outputs
MainWindow._build_ctc_block_state       = _mw_build_ctc_block_state
MainWindow._advance_external_trains     = _mw_advance_external_trains

# =============================================================================
# Override + switch-event wiring – appended by merger (round 2)
# =============================================================================

# -- Replacement for _poll_wayside_outputs that also handles switch events ----

def _mw_poll_wayside_outputs_v2(self) -> None:
    """
    Called every 100 ms by _wayside_poll_timer.
    Reads wayside outputs AND drains the switch-event queue from SharedState.
    """
    if self._shared is None:
        return

    # ── Wayside computed outputs (crossings + signals) ───────────────────────
    result = self._shared.poll_wayside_outputs()
    if result:
        for line_name, outputs in result.items():
            if not outputs:
                continue
            line_short = line_name

            # Crossing states
            for blk, state in outputs.get("crossings", {}).items():
                key = (line_short, blk)
                desired = "down" if state == "active" else "up"
                if self._rail_cross_state.get(key) != desired:
                    self._rail_cross_state[key] = desired
                    msg = (f"Railroad crossing active — {line_short} Line block {blk}."
                           if desired == "down"
                           else f"Railroad crossing clear — {line_short} Line block {blk}.")
                    self.info_msg.setText(msg)
                    self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")

            # Signal states -> station light overrides on track diagram
            widget = self.track if line_short == "Green" else self.red_track
            for blk, sig_color in outputs.get("signals", {}).items():
                if sig_color is None:
                    continue
                stn, pos = _block_to_station_pos(line_short, blk)
                if stn and pos:
                    widget.station_light_overrides[(stn, pos)] = sig_color
            widget.update()

    # ── Switch-change events ──────────────────────────────────────────────────
    events = self._shared.poll_switch_events()
    if events:
        # Show the most recent event in the info box; each earlier one is still
        # logged to the list so nothing is silently dropped.
        for ev in events:
            line  = ev["line"]
            sw_id = ev["sw_id"]
            old   = ev["old"].upper()
            new   = ev["new"].upper()
            msg   = f"Wayside: {sw_id} ({line} Line) changed {old} \u2192 {new}."
            self.info_msg.setText(msg)
            self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")


def _mw_on_switch_changed_v2(self, text: str) -> None:
    """
    Called when the CTC maintenance switch dropdown changes.
    Displays a message AND pushes the override into SharedState so the
    Wayside reflects the manually selected position.
    """
    if not text:
        return
    if not self.maint_check.isChecked():
        return
    block_text = self.block_combo.currentText()
    if block_text in ("Select a block", "— click a section on the track —", "No blocks defined"):
        return
    parts = block_text.split()
    if len(parts) < 2 or not parts[-1].isdigit():
        return
    bn = int(parts[-1])
    sw_src = GREEN_SWITCHES if self._current_line == "Green Line" else RED_SWITCHES
    if (self._current_section, bn) not in sw_src:
        return

    line_short = "Green" if self._current_line == "Green Line" else "Red"

    # Map the CTC dropdown text to a wayside sw_id.
    # CTC uses display strings like "12 → 13"; wayside uses "SW12".
    # We find the matching switch by host block number.
    sw_id = _ctc_find_sw_id(line_short, bn)

    # Determine position from the dropdown text
    sw_opts = sw_src.get((self._current_section, bn), [])
    position = "normal" if (not sw_opts or text == sw_opts[0]) else "reverse"

    # Push override to SharedState
    if self._shared is not None and sw_id:
        self._shared.push_ctc_switch_override(line_short, sw_id, position)

    self.info_msg.setText(
        f"CTC: Switch {sw_id or f'at Block {bn}'} ({line_short} Line) "
        f"set to {position.upper()} via maintenance."
    )
    self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")


def _mw_on_maint_toggled_v2(self, checked: bool) -> None:
    """
    Augmented maintenance-toggle handler.
    Calls the original logic, then syncs maintenance state and overrides
    to SharedState so the Wayside reflects the CTC's maintenance decision.
    """
    # Run the original handler first
    _original_on_maint_toggled(self, checked)

    if self._shared is None or self._current_line is None:
        return

    line_short = "Green" if self._current_line == "Green Line" else "Red"

    # Push maintenance state to SharedState so Wayside can toggle its own mode
    # Track how many blocks are currently in maintenance per line
    if not hasattr(self, "_maint_lines"):
        self._maint_lines: set = set()

    if checked:
        self._maint_lines.add(line_short)
    else:
        self._maint_lines.discard(line_short)
        # Also clear any CTC switch/signal overrides for this line
        self._shared.clear_ctc_override(line_short)

    self._shared.push_ctc_maintenance(line_short, line_short in self._maint_lines)


def _ctc_find_sw_id(line_short: str, block_num: int) -> str:
    """
    Return the wayside sw_id (e.g. 'SW12') for a given line + host block number.
    Returns empty string if not found.
    """
    from wayside_controller import GREEN_SWITCHES as GS, RED_SWITCHES as RS
    sw_defs = GS if line_short == "Green" else RS
    for sw_id, sw in sw_defs.items():
        if sw["host"] == block_num:
            return sw_id
    return ""


# Keep a reference to the original _on_maint_toggled before overwriting
_original_on_maint_toggled = MainWindow._on_maint_toggled

# Re-patch with updated versions
MainWindow._poll_wayside_outputs = _mw_poll_wayside_outputs_v2
MainWindow._on_switch_changed    = _mw_on_switch_changed_v2
MainWindow._on_maint_toggled     = _mw_on_maint_toggled_v2
