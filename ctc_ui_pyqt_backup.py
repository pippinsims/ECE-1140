import sys
import math
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QComboBox, QListWidget, QListWidgetItem,
    QSlider, QTableWidget, QTableWidgetItem, QPushButton,
    QLineEdit, QDialog, QCheckBox, QGridLayout, QSizePolicy
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Central Traffic Control Office")
        self.resize(1400, 1032)

        root = QWidget()
        root.setStyleSheet("background:white;")
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

        hbox.addWidget(logo)
        hbox.addSpacing(16)
        hbox.addWidget(title)
        hbox.addStretch(1)
        outer.addWidget(header)

        # ── Track Diagram panel ───────────────────────────────────────────────
        track_panel = QFrame()
        track_panel.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        track_layout = QVBoxLayout(track_panel)
        track_layout.setContentsMargins(8, 6, 8, 6)
        track_layout.setSpacing(4)

        self.track = TrackDiagramWidget(self.on_block_clicked)
        self.track.setFixedHeight(280)
        track_layout.addWidget(self.track)

        # Thin divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background:#c8c8c8;")
        track_layout.addWidget(divider)

        self.red_track = RedLineDiagramWidget(self.on_red_block_clicked)
        self.red_track.setFixedHeight(210)
        track_layout.addWidget(self.red_track)

        outer.addWidget(track_panel)   # fixed-height tracks → no stretch needed

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
        self.block_combo.currentIndexChanged.connect(self.on_left_block_changed)
        left_layout.addWidget(self.block_combo)

        self.block_list = QListWidget()
        self.block_list.itemSelectionChanged.connect(self.on_left_list_selected)
        left_layout.addWidget(self.block_list, stretch=1)

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

        # Existing/Manual card
        man_card = QFrame()
        man_card.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        man_grid = QGridLayout(man_card)
        man_grid.setContentsMargins(10, 10, 10, 10)

        btn_exist = QPushButton("Existing")
        btn_exist.setStyleSheet(
            "background:#e0e0e0; padding:6px 10px; border-radius:8px;")
        btn_manual = QPushButton("Manual")
        btn_manual.setStyleSheet(
            "background:#4a6fa5; padding:6px 10px; border-radius:8px;")
        man_grid.addWidget(btn_exist, 0, 0)
        man_grid.addWidget(btn_manual, 0, 1)

        man_grid.addWidget(QLabel("Destination:"), 1, 0)
        self.dest_combo = QComboBox()
        self.dest_combo.addItems(
            ["Castle Shannon", "Pioneer", "Downtown"])
        man_grid.addWidget(self.dest_combo, 1, 1)

        man_grid.addWidget(QLabel("Time:"), 2, 0)
        self.time_entry = QLineEdit("00:00")
        man_grid.addWidget(self.time_entry, 2, 1)

        btn_confirm = QPushButton("Confirm")
        btn_confirm.setStyleSheet(
            "background:#e0e0e0; padding:6px 10px; border-radius:8px;")
        man_grid.addWidget(btn_confirm, 3, 0, 1, 2)

        cards.addWidget(man_card)

        # Big gray info box
        big = QFrame()
        big.setStyleSheet(
            "background:#d9d9d9; border:2px solid #c8c8c8; border-radius:10px;")
        big_layout = QVBoxLayout(big)
        big_layout.addStretch(1)
        msg = QLabel(
            "(Schedule details / messages / upcoming trains would display here)")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color:#333333;")
        msg.setWordWrap(True)
        big_layout.addWidget(msg)
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

        # Table — columns: Train, Line, Section, Block
        self.schedule_table = QTableWidget(0, 4)
        self.schedule_table.setHorizontalHeaderLabels(
            ["Train", "Line", "Section", "Block"])
        self.schedule_table.verticalHeader().setVisible(False)
        self.schedule_table.setFixedHeight(140)

        # "No active trains" overlay — shown when table is empty
        self._no_trains_lbl = QLabel("No active trains")
        self._no_trains_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_trains_lbl.setStyleSheet("color:#888888; font-style:italic;")
        self._no_trains_lbl.setFixedHeight(140)

        # Use a stacked-style container so label and table occupy same space
        trains_stack = QWidget()
        trains_stack_layout = QVBoxLayout(trains_stack)
        trains_stack_layout.setContentsMargins(0, 0, 0, 0)
        trains_stack_layout.addWidget(self.schedule_table)
        trains_stack_layout.addWidget(self._no_trains_lbl)
        self._refresh_trains_view()
        right_layout.addWidget(trains_stack)

        thr_lbl = QLabel("Throughput (P/Hr/Ln)")
        thr_lbl.setStyleSheet("font-weight:800;")
        right_layout.addWidget(thr_lbl)

        self.thru_table = QTableWidget(2, 2)
        self.thru_table.setHorizontalHeaderLabels(
            ["Line", "Throughput (P/Hr/Ln)"])
        self.thru_table.verticalHeader().setVisible(False)
        self.thru_table.setItem(0, 0, QTableWidgetItem("Red Line"))
        self.thru_table.setItem(0, 1, QTableWidgetItem("100"))
        self.thru_table.setItem(1, 0, QTableWidgetItem("Green Line"))
        self.thru_table.setItem(1, 1, QTableWidgetItem("250"))
        self.thru_table.setFixedHeight(120)
        right_layout.addWidget(self.thru_table)

        right_layout.addStretch(1)
        bottom.addWidget(right, stretch=1)

        # ── 1-second refresh timer for Active Trains table ────────────────────
        self._train_timer = QTimer(self)
        self._train_timer.setInterval(1000)   # 1 000 ms = 1 s
        self._train_timer.timeout.connect(self._poll_active_trains)
        self._train_timer.start()

    # ── Interactions ──────────────────────────────────────────────────────────

    def _update_block_panel(self, label, line: str, track_widget):
        """Shared logic: update bottom-left panel for any line/section click."""
        if label is None:
            self.left_title.setText("Block Selection")
            self.block_combo.blockSignals(True)
            self.block_combo.clear()
            self.block_combo.addItem("— click a section on the track —")
            self.block_combo.setEnabled(False)
            self.block_combo.blockSignals(False)
            self.block_list.clear()
            return

        data_src = GREEN_LINE_BLOCKS if line == "Green Line" else RED_LINE_BLOCKS
        blocks = data_src.get(label, [])

        self.left_title.setText(f"Block Selection: Section {label}")

        self.block_combo.blockSignals(True)
        self.block_combo.clear()
        if blocks:
            for bn, length, grade, spd in blocks:
                self.block_combo.addItem(f"Block {bn}")
            self.block_combo.setEnabled(True)
        else:
            self.block_combo.addItem("No blocks defined")
            self.block_combo.setEnabled(False)
        self.block_combo.blockSignals(False)

        self.block_list.blockSignals(True)
        self.block_list.clear()
        for bn, length, grade, spd in blocks:
            self.block_list.addItem(QListWidgetItem(f"Block {bn}"))
        self.block_list.blockSignals(False)

        track_widget.update()

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
        """Called every second. Advances the simulation clock and refreshes the table."""
        if not getattr(self, "_sim_running", False):
            return

        # Advance simulation clock by speed_slider value each real second.
        # At slider=60: 1 sim-minute per real-second → 90-min run in ~90 s.
        self._sim_time_sec += self.speed_slider.value()

        trains = []
        if getattr(self, "_sim_schedule", None) == "Default Green":
            end_sec = DEFAULT_GREEN_WAYPOINTS[-1][0]
            for i in range(_GREEN_NUM_TRAINS):
                train_num   = i + 1
                train_start = i * _GREEN_TRAIN_GAP_SEC          # offset for this train
                train_t     = self._sim_time_sec - train_start   # time from this train's start

                if train_t < 0:
                    continue   # not dispatched yet
                if train_t > end_sec:
                    continue   # run completed

                # Find the most recent waypoint for this train
                current_wp = DEFAULT_GREEN_WAYPOINTS[0]
                for wp in DEFAULT_GREEN_WAYPOINTS:
                    if wp[0] <= train_t:
                        current_wp = wp
                    else:
                        break

                _, section, block, station = current_wp
                label = f"T-{train_num:02d}"
                detail = f"Blk {block}"
                if station:
                    detail += f" — {station}"
                trains.append({
                    "train":   label,
                    "line":    "Green",
                    "section": section,
                    "block":   detail,
                })

        self.schedule_table.setRowCount(len(trains))
        for row, t in enumerate(trains):
            self.schedule_table.setItem(row, 0, QTableWidgetItem(t["train"]))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(t["line"]))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(t["section"]))
            self.schedule_table.setItem(row, 3, QTableWidgetItem(t["block"]))

        self._refresh_trains_view()

        # Push occupied sections to the track widget so they render black
        occupied = {t["section"] for t in trains if t["line"] == "Green"}
        self.track.train_sections = occupied
        self.track.update()

        # Once all trains have finished, stop the simulation and reset button
        if self._sim_running and len(trains) == 0:
            last_train_end = DEFAULT_GREEN_WAYPOINTS[-1][0] + (_GREEN_NUM_TRAINS - 1) * _GREEN_TRAIN_GAP_SEC
            if self._sim_time_sec > last_train_end:
                self._sim_running = False
                self.btn_load.setText("Load")
                self.btn_load.setStyleSheet(
                    "background:#4a6fa5; color:white; font-weight:bold;"
                    "padding:6px 10px; border-radius:8px;")

    def on_left_list_selected(self):
        pass  # no detail panel — selection is visual only

    def on_left_block_changed(self, idx: int):
        pass  # no detail panel


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
