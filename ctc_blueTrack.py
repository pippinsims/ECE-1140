"""
ctc_blueTrack.py  —  Blue track CTC prototype

Track topology (sections A / B / C):
    Yard ── A(1-5) ──┬── B(6-10) ── Station B
                     └── C(11-15) ── Station C
"""

import sys
import os
import re
import math
from datetime import datetime
from dataclasses import dataclass

from PyQt6.QtCore    import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui     import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QSizePolicy, QComboBox,
    QPushButton, QHeaderView,
    QLineEdit, QSlider, QTableWidget, QTableWidgetItem,
    QCheckBox,
)


# ── Load block data from Excel (falls back to defaults if file not found) ─────
def _load_blue_blocks():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "blue_track_schedule.xlsx")
    result = {"A": [], "B": [], "C": []}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb["Blue Line"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            sec = row[1]
            if sec not in result:
                continue
            bn   = int(row[2]) if row[2] is not None else None
            llen = float(row[3]) if row[3] is not None else 50.0
            grade= float(row[4]) if row[4] is not None else 0.0
            speed= float(row[5]) if row[5] is not None else 50.0
            infra= str(row[6]) if row[6] is not None else ""
            if bn is not None:
                result[sec].append((bn, llen, grade, speed, infra))
    except Exception:
        # Default fallback
        result = {
            "A": [(i, 50, 0.0, 50, "") for i in range(1, 6)],
            "B": [(i, 50, 0.0, 50, "") for i in range(6, 11)],
            "C": [(i, 50, 0.0, 50, "") for i in range(11, 16)],
        }
    return result


BLUE_LINE_BLOCKS = _load_blue_blocks()

# Full route sequences (section, block, speed_kmh, length_m)
# Route A→B: yard → A(1-5) → B(6-10, Station B)
# Route A→C: yard → A(1-5) → C(11-15, Station C)
def _build_route(branch: str):
    route = []
    for sec in ("A", branch):
        for entry in BLUE_LINE_BLOCKS.get(sec, []):
            bn, llen, grade, speed = entry[0], entry[1], entry[2], entry[3]
            route.append({"section": sec, "block": bn,
                          "speed_kmh": speed, "length_m": llen})
    return route

BLUE_ROUTE_B = _build_route("B")   # A then B (→ Station B)
BLUE_ROUTE_C = _build_route("C")   # A then C (→ Station C)

# ── Flat block lookup: block_num → (section, length_m, speed_kmh, infra) ─────
BLUE_BLOCK_INFO = {}
for _sec, _blocks in BLUE_LINE_BLOCKS.items():
    for _entry in _blocks:
        BLUE_BLOCK_INFO[_entry[0]] = (
            _sec,
            _entry[1],                          # length_m
            _entry[3],                          # speed_kmh
            _entry[4] if len(_entry) > 4 else "",  # infrastructure
        )

def _parse_switch_options(infra: str):
    """Return list of switch options parsed from an infrastructure string."""
    if "Switch" not in infra:
        return []
    pairs = re.findall(r'(\d+)\s+to\s+(\d+)', infra)
    return [f"{a} → {b}" for a, b in pairs]

# block_num → [switch option strings]  (empty list if no switch)
BLUE_SWITCHES = {
    bn: _parse_switch_options(info[3])
    for bn, info in BLUE_BLOCK_INFO.items()
}

# ── colours ───────────────────────────────────────────────────────────────────
C_NORMAL   = QColor("#1a5fa8")
C_SELECTED = QColor("#cc2222")
C_BLACK    = QColor("#111111")
TW = 4


@dataclass
class ClickRegion:
    rect:  QRect
    label: str


# ─────────────────────────────────────────────────────────────────────────────
# Blue Track Widget
# ─────────────────────────────────────────────────────────────────────────────
class BlueTrackWidget(QWidget):
    def __init__(self, on_section_clicked=None):
        super().__init__()
        self.on_section_clicked = on_section_clicked or (lambda lbl: None)
        self.selected_section = None
        self.train_sections: set = set()
        self.signal_overrides: dict = {}   # section → "green" | "red" | "yellow"
        self.click_regions: list[ClickRegion] = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            "background:white; border:2px solid #c8c8c8; border-radius:8px;")

    def _c(self, name: str) -> QColor:
        if name == self.selected_section:
            return C_SELECTED
        if name in self.train_sections:
            return C_BLACK
        return C_NORMAL

    def _px(self, f): return int(self.width()  * f)
    def _py(self, f): return int(self.height() * f)

    def _seg(self, p: QPainter, name: str, *pts: QPoint):
        pen = QPen(self._c(name), TW, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        for i in range(len(pts) - 1):
            p.drawLine(pts[i], pts[i + 1])

    def _label(self, p: QPainter, name: str, pt: QPoint):
        px, py = 16, 11
        rect = QRect(pt.x() - px, pt.y() - py, px * 2, py * 2)
        if name == self.selected_section:
            p.setPen(QPen(QColor("#991111"), 2)); p.setBrush(QColor("#ffdddd"))
            txt = QColor("#770000")
        elif name in self.train_sections:
            p.setPen(QPen(QColor("#111111"), 2)); p.setBrush(QColor("#333333"))
            txt = QColor("#ffffff")
        else:
            p.setPen(QPen(QColor("#aaaaaa"), 1)); p.setBrush(QColor("white"))
            txt = QColor("#222222")
        p.drawRoundedRect(rect, 5, 5)
        p.setPen(txt)
        f = QFont("Helvetica", 9); f.setBold(True); p.setFont(f)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)
        self.click_regions.append(ClickRegion(rect=rect, label=name))

    def paintEvent(self, _):
        self.click_regions.clear()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── y levels ──────────────────────────────────────────────────────────
        yM  = self._py(0.50)           # main line
        yU1 = self._py(0.38)           # upper branch step 1
        yU2 = self._py(0.28)           # upper branch step 2
        yU3 = self._py(0.20)           # upper branch step 3
        yB  = self._py(0.14)           # Station B level
        yL1 = self._py(0.62)           # lower branch step 1
        yL2 = self._py(0.72)           # lower branch step 2
        yL3 = self._py(0.80)           # lower branch step 3
        yC  = self._py(0.87)           # Station C level

        # ── x positions ───────────────────────────────────────────────────────
        xYd  = self._px(0.04);  x0   = self._px(0.10)
        x1   = self._px(0.17);  x2   = self._px(0.24)
        x3   = self._px(0.31);  x4   = self._px(0.38)
        xF   = self._px(0.46)          # fork
        xB1  = self._px(0.53);  xB2  = self._px(0.60)
        xB3  = self._px(0.67);  xB4  = self._px(0.75)
        xB5  = self._px(0.83)          # Station B end
        xC1  = self._px(0.53);  xC2  = self._px(0.60)
        xC3  = self._px(0.67);  xC4  = self._px(0.75)
        xC5  = self._px(0.83)          # Station C end

        def pt(x, y): return QPoint(x, y)
        def mid(a, b): return QPoint((a.x()+b.x())//2, (a.y()+b.y())//2)

        # ── Yard oval ─────────────────────────────────────────────────────────
        p.setPen(QPen(C_NORMAL, TW)); p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        rw, rh = self._px(0.06), self._py(0.28)
        p.drawEllipse(pt(xYd, yM), rw, rh)
        p.setPen(QPen(self._c("A"), TW))
        p.drawLine(pt(xYd + rw, yM), pt(x0, yM))

        # ── Section A: main line (blocks 1-5) ─────────────────────────────────
        self._seg(p, "A", pt(x0,yM), pt(x1,yM), pt(x2,yM),
                           pt(x3,yM), pt(x4,yM), pt(xF,yM))

        # Switch X at block 3 midpoint
        sx, sy, sr = (x2+x3)//2, yM, 6
        p.setPen(QPen(self._c("A"), 2))
        p.drawLine(sx-sr, sy-sr, sx+sr, sy+sr)
        p.drawLine(sx+sr, sy-sr, sx-sr, sy+sr)

        # ── Section B: upper branch (blocks 6-10) → Station B ─────────────────
        # Smooth diagonal climb: 6=first diagonal, 7=second, 8=horizontal,
        # 9=slight climb, 10=final climb to Station B
        self._seg(p, "B",
                  pt(xF, yM),
                  pt(xB1, yU1),
                  pt(xB2, yU2),
                  pt(xB3, yU2),
                  pt(xB4, yU3),
                  pt(xB5, yB))

        # ── Section C: lower branch (blocks 11-15) → Station C ────────────────
        self._seg(p, "C",
                  pt(xF, yM),
                  pt(xC1, yL1),
                  pt(xC2, yL2),
                  pt(xC3, yL2),
                  pt(xC4, yL3),
                  pt(xC5, yC))

        # ── Station badges ────────────────────────────────────────────────────
        def station_badge(name, cx, cy):
            p.setPen(QPen(QColor("#1a5fa8"), 1))
            p.setBrush(QColor("#ddeeff"))
            f = QFont("Helvetica", 8); f.setBold(True); p.setFont(f)
            r = QRect(cx - 38, cy - 10, 76, 20)
            p.drawRoundedRect(r, 4, 4)
            p.setPen(QColor("#003366"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, name)

        station_badge("Station B", xB5, yB - 18)
        station_badge("Station C", xC5, yC + 18)

        # ── Yard label ────────────────────────────────────────────────────────
        p.setPen(C_NORMAL)
        f = QFont("Helvetica", 9); f.setBold(True); p.setFont(f)
        p.drawText(QRect(xYd-22, yM-10, 44, 20), Qt.AlignmentFlag.AlignCenter, "Yard")

        # ── Section buttons (A, B, C) ─────────────────────────────────────────
        OFF = 14
        self._label(p, "A", mid(pt(x1,yM), pt(x4,yM)) + QPoint(0, -OFF))
        self._label(p, "B", mid(pt(xB1,yU1), pt(xB3,yU2)) + QPoint(-OFF, 0))
        self._label(p, "C", mid(pt(xC1,yL1), pt(xC3,yL2)) + QPoint(-OFF, 0))

        # ── Signal lights (one per section + Yard) ────────────────────────────
        _SIGNAL_COLORS = {
            "green":  (QColor("#22aa44"), QColor("#115522")),
            "red":    (QColor("#cc2222"), QColor("#881111")),
            "yellow": (QColor("#ddaa00"), QColor("#886600")),
        }

        def signal_light(sec: str, cx: int, cy: int):
            override = self.signal_overrides.get(sec)
            if override in _SIGNAL_COLORS:
                fill, ring = _SIGNAL_COLORS[override]
            else:
                # Auto: red if occupied, green if clear
                key = "red" if sec in self.train_sections else "green"
                fill, ring = _SIGNAL_COLORS[key]
            p.setPen(QPen(ring, 2))
            p.setBrush(QBrush(fill))
            p.drawEllipse(QPoint(cx, cy), 7, 7)

        # B: just above the fork into the upper branch
        signal_light("B", xF + 8, yU1 - 8)
        # C: just below the fork into the lower branch
        signal_light("C", xF + 8, yL1 + 8)

        p.end()

    def mousePressEvent(self, evt):
        pos = evt.position().toPoint()
        for reg in self.click_regions:
            if reg.rect.contains(pos):
                if self.selected_section == reg.label:
                    self.selected_section = None
                    self.on_section_clicked(None)
                else:
                    self.selected_section = reg.label
                    self.on_section_clicked(reg.label)
                self.update()
                return


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CTC — Blue Track")
        self.resize(1400, 820)

        root = QWidget()
        root.setStyleSheet("background:white;")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(44)
        header.setStyleSheet("background:#2a3f5f; border-radius:8px;")
        hbox = QHBoxLayout(header)
        hbox.setContentsMargins(14, 6, 14, 6)
        logo = QLabel("Logo")
        logo.setFixedWidth(60)
        logo.setStyleSheet(
            "color:white; font-weight:900; font-size:14px;"
            "background:#3d5a80; border-radius:6px; padding:4px 8px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Central Traffic Control Office")
        title.setStyleSheet("color:white; font-size:16px; font-weight:700;")
        hbox.addWidget(logo); hbox.addSpacing(16); hbox.addWidget(title)
        hbox.addStretch(1)
        outer.addWidget(header)

        # ── Track diagram ─────────────────────────────────────────────────────
        track_panel = QFrame()
        track_panel.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        tpl = QVBoxLayout(track_panel)
        tpl.setContentsMargins(8, 6, 8, 6)
        self.track = BlueTrackWidget(on_section_clicked=self._on_section_clicked)
        self.track.setFixedHeight(300)
        tpl.addWidget(self.track)
        outer.addWidget(track_panel)

        # ── Bottom row ────────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        outer.addLayout(bottom, stretch=1)

        # Left: Block selection ───────────────────────────────────────────────
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
        left_layout.addWidget(self.block_combo)

        # ── Block detail card (shown when a block is chosen from the dropdown) ─
        self.detail_card = QFrame()
        self.detail_card.setStyleSheet(
            "background:#e8ecf4; border:1px solid #b0b8cc; border-radius:8px;")
        detail_lay = QVBoxLayout(self.detail_card)
        detail_lay.setContentsMargins(10, 8, 10, 8)
        detail_lay.setSpacing(6)

        self.maint_check = QCheckBox("Maintenance")
        self.maint_check.setStyleSheet("font-weight:600;")
        self.maint_check.toggled.connect(self._on_maint_toggled)
        detail_lay.addWidget(self.maint_check)

        self.detail_title_lbl = QLabel("")
        self.detail_title_lbl.setStyleSheet(
            "border:1px solid #999; border-radius:4px;"
            "padding:3px 6px; background:white;")
        detail_lay.addWidget(self.detail_title_lbl)

        self.speed_auth_frame = QFrame()
        self.speed_auth_frame.setStyleSheet(
            "border:1px solid #999; border-radius:4px; background:white;")
        sa_lay = QVBoxLayout(self.speed_auth_frame)
        sa_lay.setContentsMargins(6, 4, 6, 4)
        sa_lay.setSpacing(2)
        self.speed_lbl_detail = QLabel("Speed: —")
        self.auth_lbl_detail  = QLabel("Authority: —")
        sa_lay.addWidget(self.speed_lbl_detail)
        sa_lay.addWidget(self.auth_lbl_detail)
        detail_lay.addWidget(self.speed_auth_frame)

        self.switch_row = QHBoxLayout()
        self.switch_lbl = QLabel("Switch:")
        self.switch_combo_detail = QComboBox()
        self.switch_combo_detail.currentTextChanged.connect(self._on_switch_changed)
        self.switch_row.addWidget(self.switch_lbl)
        self.switch_row.addWidget(self.switch_combo_detail, stretch=1)
        switch_widget = QWidget()
        switch_widget.setLayout(self.switch_row)
        switch_widget.setStyleSheet("background:transparent; border:none;")
        self.switch_widget = switch_widget
        detail_lay.addWidget(self.switch_widget)
        self.switch_widget.hide()

        self.detail_card.hide()
        self.block_combo.currentIndexChanged.connect(self._on_block_combo_changed)
        left_layout.addWidget(self.detail_card)

        bottom.addWidget(left, stretch=1)

        # Center: Schedule Info ───────────────────────────────────────────────
        center = QFrame()
        center.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(10)

        center_title = QLabel("Schedule Info")
        center_title.setStyleSheet("font-weight:800;")
        center_layout.addWidget(center_title)

        cards = QHBoxLayout(); cards.setSpacing(12)
        center_layout.addLayout(cards)

        # Automatic card
        auto_card = QFrame()
        auto_card.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        auto_lay = QVBoxLayout(auto_card)
        auto_lay.setContentsMargins(10, 10, 10, 10)
        auto_lay.setSpacing(8)

        btn_auto = QPushButton("Automatic")
        btn_auto.setStyleSheet(
            "background:#4a6fa5; color:white; font-weight:bold;"
            "padding:6px 10px; border-radius:8px;")
        btn_auto.setFixedHeight(34)
        auto_lay.addWidget(btn_auto, alignment=Qt.AlignmentFlag.AlignHCenter)

        auto_lay.addWidget(QLabel("Schedules to load"))

        self.load_combo = QComboBox()
        self.load_combo.addItems(["Default Blue"])
        auto_lay.addWidget(self.load_combo)

        self.btn_load = QPushButton("Load")
        self.btn_load.setStyleSheet(
            "background:#4a6fa5; color:white; font-weight:bold;"
            "padding:6px 10px; border-radius:8px;")
        self.btn_load.clicked.connect(self._on_load_schedule)
        auto_lay.addWidget(self.btn_load)
        cards.addWidget(auto_card)

        # Manual card
        man_card = QFrame()
        man_card.setStyleSheet(
            "background:#f0f0f0; border:2px solid #c8c8c8; border-radius:10px;")
        man_grid = QGridLayout(man_card)
        man_grid.setContentsMargins(10, 10, 10, 10)

        btn_manual = QPushButton("Manual")
        btn_manual.setStyleSheet(
            "background:#4a6fa5; color:white; font-weight:bold;"
            "padding:6px 10px; border-radius:8px;")
        btn_manual.setFixedHeight(34)
        man_grid.addWidget(btn_manual, 0, 0, 1, 2,
                           alignment=Qt.AlignmentFlag.AlignHCenter)

        _STOPS = ["Yard", "Station B", "Station C"]

        man_grid.addWidget(QLabel("From:"), 1, 0)
        self.origin_combo = QComboBox()
        self.origin_combo.addItems(_STOPS)
        man_grid.addWidget(self.origin_combo, 1, 1)

        man_grid.addWidget(QLabel("To:"), 2, 0)
        self.dest_combo = QComboBox()
        self.dest_combo.addItems(_STOPS)
        self.dest_combo.setCurrentIndex(1)   # default to Station B
        man_grid.addWidget(self.dest_combo, 2, 1)

        man_grid.addWidget(QLabel("Time:"), 3, 0)
        self.time_entry = QLineEdit("00:00")
        man_grid.addWidget(self.time_entry, 3, 1)

        self.btn_man_load = QPushButton("Load")
        self.btn_man_load.setStyleSheet(
            "background:#4a6fa5; color:white; font-weight:bold;"
            "padding:6px 10px; border-radius:8px;")
        self.btn_man_load.clicked.connect(self._on_manual_confirm)
        man_grid.addWidget(self.btn_man_load, 4, 0, 1, 2)
        cards.addWidget(man_card)

        # Big info box
        big = QFrame()
        big.setStyleSheet(
            "background:#d9d9d9; border:2px solid #c8c8c8; border-radius:10px;")
        big_layout = QVBoxLayout(big)
        big_layout.addStretch(1)
        self.info_msg = QLabel("(Signal changes and system messages will appear here)")
        self.info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_msg.setStyleSheet("color:#333333;")
        self.info_msg.setWordWrap(True)
        big_layout.addWidget(self.info_msg)
        big_layout.addStretch(1)
        center_layout.addWidget(big, stretch=1)
        bottom.addWidget(center, stretch=2)

        # Right: sidebar ──────────────────────────────────────────────────────
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
        self.speed_slider.valueChanged.connect(lambda v: self.speed_lbl.setText(f"{v}%"))
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_lbl)
        right_layout.addLayout(speed_row)

        act_lbl = QLabel("Active Trains")
        act_lbl.setStyleSheet("font-weight:800;")
        right_layout.addWidget(act_lbl)

        self.schedule_table = QTableWidget(0, 3)
        self.schedule_table.setHorizontalHeaderLabels(["Line", "Section", "Block"])
        self.schedule_table.verticalHeader().setVisible(False)
        self.schedule_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.schedule_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.schedule_table.setFixedHeight(140)

        self._no_trains_lbl = QLabel("No active trains")
        self._no_trains_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_trains_lbl.setStyleSheet("color:#888888; font-style:italic;")
        self._no_trains_lbl.setFixedHeight(140)

        trains_stack = QWidget()
        trains_stack_layout = QVBoxLayout(trains_stack)
        trains_stack_layout.setContentsMargins(0, 0, 0, 0)
        trains_stack_layout.addWidget(self.schedule_table)
        trains_stack_layout.addWidget(self._no_trains_lbl)
        self._refresh_trains_view()
        right_layout.addWidget(trains_stack)

        thr_lbl = QLabel("Ticket Sales")
        thr_lbl.setStyleSheet("font-weight:800;")
        right_layout.addWidget(thr_lbl)

        self.thru_table = QTableWidget(1, 2)
        self.thru_table.setHorizontalHeaderLabels(["Line", "Ticket Sales"])
        self.thru_table.verticalHeader().setVisible(False)
        self.thru_table.setItem(0, 0, QTableWidgetItem("Blue Line"))
        self.thru_table.setItem(0, 1, QTableWidgetItem("0"))
        self.thru_table.setFixedHeight(90)
        right_layout.addWidget(self.thru_table)

        right_layout.addStretch(1)
        bottom.addWidget(right, stretch=1)

        # External trains injected by test_ui (train_id → {section, block})
        self._external_trains = {}
        self._manual_train_counter = 0
        self._maint_occupancy_id = None   # e.g. "Maint-5" when block 5 is in maintenance
        self._pending_timers = []   # keep singleShot timers alive

        # 1-second timer
        self._train_timer = QTimer(self)
        self._train_timer.setInterval(1000)
        self._train_timer.timeout.connect(self._poll_active_trains)
        self._train_timer.start()

    # ── Interactions ──────────────────────────────────────────────────────────

    def _on_block_combo_changed(self, idx: int):
        """Show block detail card when a specific block is selected."""
        text = self.block_combo.itemText(idx)
        # Parse block number from "Block N"
        parts = text.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            self.detail_card.hide()
            return
        bn = int(parts[-1])
        info = BLUE_BLOCK_INFO.get(bn)
        if info is None:
            self.detail_card.hide()
            return

        _sec, length_m, speed_kmh, infra = info
        speed_mph = round(speed_kmh * 0.621371, 1)
        length_ft = round(length_m * 3.28084, 1)

        # Clear any maintenance occupancy from the previous block
        if self._maint_occupancy_id is not None:
            self.remove_train(self._maint_occupancy_id)
            self._maint_occupancy_id = None

        self.detail_card.show()
        self.maint_check.blockSignals(True)
        self.maint_check.setChecked(False)
        self.maint_check.blockSignals(False)

        self.detail_title_lbl.setText(f"Block Details (Block {bn}, Blue Line)")
        self.speed_lbl_detail.setText(f"Speed: {speed_mph} mph")
        self.auth_lbl_detail.setText(f"Authority: {length_ft} ft")

        # Switch dropdown — only shown when maintenance is checked + block has switch
        sw_opts = BLUE_SWITCHES.get(bn, [])
        self.switch_combo_detail.clear()
        if sw_opts:
            self.switch_combo_detail.addItems(sw_opts)
        # Hide switch row initially (maintenance not checked)
        self.switch_widget.hide()

    def _on_maint_toggled(self, checked: bool):
        """Update speed/authority display and mark block occupied when maintenance toggled."""
        text = self.block_combo.currentText()
        parts = text.split()
        has_switch = False
        bn = None
        sec = None
        if len(parts) >= 2 and parts[-1].isdigit():
            bn = int(parts[-1])
            has_switch = bool(BLUE_SWITCHES.get(bn, []))
            info = BLUE_BLOCK_INFO.get(bn)
            if info:
                sec = info[0]

        if checked:
            self.speed_lbl_detail.setText("Speed: 0 mph")
            self.auth_lbl_detail.setText("Authority: N/A")
            if has_switch:
                self.switch_widget.show()
            else:
                self.switch_widget.hide()
            # Mark block as occupied so section turns black and appears in Active Trains
            if bn is not None and sec is not None:
                self._maint_occupancy_id = f"Maint-{bn}"
                self.inject_train(self._maint_occupancy_id, sec, bn)
        else:
            if self._maint_occupancy_id is not None:
                self.remove_train(self._maint_occupancy_id)
                self._maint_occupancy_id = None
            if bn is not None:
                info = BLUE_BLOCK_INFO.get(bn)
                if info:
                    speed_mph = round(info[2] * 0.621371, 1)
                    length_ft = round(info[1] * 3.28084, 1)
                    self.speed_lbl_detail.setText(f"Speed: {speed_mph} mph")
                    self.auth_lbl_detail.setText(f"Authority: {length_ft} ft")
            self.switch_widget.hide()

    def _on_switch_changed(self, text: str):
        """Log a message when a maintenance switch position is changed."""
        if not text or not self.maint_check.isChecked():
            return
        # Current block number from dropdown
        cur = self.block_combo.currentText().split()
        if len(cur) < 2 or not cur[-1].isdigit():
            return
        bn = int(cur[-1])
        # Only react if this block actually has a switch definition
        if bn not in BLUE_SWITCHES or not BLUE_SWITCHES[bn]:
            return

        self.info_msg.setText(
            f"Switch at Block {bn} has been set to {text}")
        self.info_msg.setStyleSheet("color:#333333; font-weight:bold;")

    def _on_section_clicked(self, label):
        """Update block selection panel when a track section is clicked."""
        if label is None:
            self.left_title.setText("Block Selection")
            self.block_combo.blockSignals(True)
            self.block_combo.clear()
            self.block_combo.addItem("— click a section on the track —")
            self.block_combo.setEnabled(False)
            self.block_combo.blockSignals(False)
            self.detail_card.hide()
            return

        blocks = BLUE_LINE_BLOCKS.get(label, [])
        self.left_title.setText(f"Block Selection: Section {label}")

        self.block_combo.blockSignals(True)
        self.block_combo.clear()
        for bn, *_ in blocks:
            self.block_combo.addItem(f"Block {bn}")
        self.block_combo.setEnabled(bool(blocks))
        self.block_combo.blockSignals(False)

        self.track.update()

    def _on_manual_confirm(self):
        """Validate manual schedule, then dispatch the train at the given time."""
        origin = self.origin_combo.currentText()
        dest   = self.dest_combo.currentText()
        time   = self.time_entry.text().strip()

        # ── Validation ────────────────────────────────────────────────────────
        def show_error(msg):
            self.info_msg.setText(f"⚠ ERROR: {msg}")
            self.info_msg.setStyleSheet("color:#cc2222; font-weight:bold;")

        if not re.fullmatch(r'\d{2}:\d{2}', time):
            return show_error("Time must be in HH:MM format (e.g. 08:30).")

        hh, mm = int(time[:2]), int(time[3:])
        if hh > 23 or mm > 59:
            return show_error(
                f"Invalid time '{time}'. Hours must be 00-23, minutes 00-59.")

        if origin == dest:
            return show_error(
                f"Origin and destination cannot be the same ({origin}).")
        if origin in ("Station B", "Station C") and dest in ("Station B", "Station C"):
            return show_error(
                f"Cannot go from {origin} to {dest}. "
                f"Trains at a station must return to Yard first.")
        if origin == "Yard" and dest == "Yard":
            return show_error("Origin and destination cannot both be Yard.")

        # ── Check departure time is in the future ─────────────────────────────
        now    = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            return show_error(
                f"Departure time {time} has already passed. "
                f"Current time is {now.strftime('%H:%M')}.")

        delay_ms = int((target - now).total_seconds() * 1000)

        # ── Build route description ───────────────────────────────────────────
        routes = {
            ("Yard",      "Station B"): ("Yard → A → Station B", "A"),
            ("Yard",      "Station C"): ("Yard → A → Station C", "A"),
            ("Station B", "Yard"):      ("Station B → A → Yard",  "B"),
            ("Station C", "Yard"):      ("Station C → A → Yard",  "C"),
        }
        route_str, start_sec = routes.get((origin, dest), (f"{origin} → {dest}", "A"))

        # ── Assign unique train ID ────────────────────────────────────────────
        self._manual_train_counter += 1
        train_id = f"M-{self._manual_train_counter:02d}"

        self.info_msg.setText(
            f"⏱ {train_id} scheduled  |  {route_str}  |  Departs {time}")
        self.info_msg.setStyleSheet("color:#2255aa; font-weight:bold;")

        # ── Fire dispatch at departure time ───────────────────────────────────
        t = QTimer(self)
        t.setSingleShot(True)
        t.timeout.connect(lambda: self._dispatch_manual_train(
            train_id, start_sec, route_str))
        t.start(delay_ms)
        self._pending_timers.append(t)

    def _dispatch_manual_train(self, train_id: str, section: str, route_str: str):
        """Called at departure time — injects the train onto the track."""
        # First block of the starting section
        first_block = BLUE_LINE_BLOCKS[section][0][0]
        self.inject_train(train_id, section, first_block)
        self.info_msg.setText(
            f"🚃 {train_id} dispatched  |  {route_str}  "
            f"|  Now at Section {section}, Block {first_block}")
        self.info_msg.setStyleSheet("color:#115522; font-weight:bold;")

    def _on_load_schedule(self):
        self._sim_time_sec = 0
        self._sim_running  = True
        self.btn_load.setText("Running ▶")
        self.btn_load.setStyleSheet(
            "background:#2e7d32; color:white; font-weight:bold;"
            "padding:6px 10px; border-radius:8px;")
        self._poll_active_trains()

    # ── Public API for test_ui.py ─────────────────────────────────────────────

    def inject_train(self, train_id: str, section: str, block: int):
        """Place or move a train on the track (called from test_ui)."""
        self._external_trains[train_id] = {"section": section, "block": block}
        self._rebuild_train_table()

    def remove_train(self, train_id: str):
        """Remove a train from the track (called from test_ui)."""
        self._external_trains.pop(train_id, None)
        self._rebuild_train_table()

    def clear_trains(self):
        """Remove all externally injected trains."""
        self._external_trains.clear()
        self._rebuild_train_table()

    def set_signal(self, section: str, color: str):
        """Set a signal light override (called from test_ui).
        color: 'green' | 'red' | 'yellow' | 'auto'
        """
        if color == "auto":
            self.track.signal_overrides.pop(section, None)
            msg = f"Signal {section}: auto (occupancy-based)"
        else:
            self.track.signal_overrides[section] = color
            msg = f"Signal {section} → {color.upper()}"
        self.info_msg.setText(msg)
        self.track.update()

    def set_ticket_sales(self, value: int):
        """Update ticket sales value shown in the sidebar (called from test_ui)."""
        self.thru_table.setItem(0, 1, QTableWidgetItem(str(value)))

    def _rebuild_train_table(self):
        """Rebuild Active Trains table from external + sim trains."""
        all_trains = []

        # Externally injected trains
        for tid, info in self._external_trains.items():
            all_trains.append({
                "train": tid, "line": "Blue",
                "section": info["section"],
                "block": f"Blk {info['block']}",
            })

        # Simulation train (if running)
        if getattr(self, "_sim_running", False):
            section_order = [
                ("A", 1), ("A", 2), ("A", 3), ("A", 4), ("A", 5),
                ("B", 6), ("B", 7), ("B", 8), ("B", 9), ("B", 10),
                ("A", 5), ("A", 4), ("A", 3), ("A", 2), ("A", 1),
                ("C", 11), ("C", 12), ("C", 13), ("C", 14), ("C", 15),
            ]
            total = len(section_order) * 30
            t = getattr(self, "_sim_time_sec", 0) % total
            idx = min(int(t // 30), len(section_order) - 1)
            sec, blk = section_order[idx]
            all_trains.append({
                "train": "T-01", "line": "Blue",
                "section": sec, "block": f"Blk {blk}",
            })

        self.schedule_table.setRowCount(len(all_trains))
        for row, tr in enumerate(all_trains):
            self.schedule_table.setItem(row, 0, QTableWidgetItem(tr["line"]))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(tr["section"]))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(tr["block"]))

        self._refresh_trains_view()
        self.track.train_sections = {tr["section"] for tr in all_trains}
        self.track.update()

    def _poll_active_trains(self):
        if not getattr(self, "_sim_running", False):
            return
        self._sim_time_sec += self.speed_slider.value()
        self._rebuild_train_table()

    def _refresh_trains_view(self):
        has = self.schedule_table.rowCount() > 0
        self.schedule_table.setVisible(has)
        self._no_trains_lbl.setVisible(not has)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
