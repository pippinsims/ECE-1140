"""
test_ui.py — Block occupancy test interface for ctc_blueTrack.py

Select a section and block, press "Occupy Block" to mark it occupied.
The CTC diagram turns that section black and the block appears in Active Trains.
Press "Clear Block" to free it, or "Clear All" to reset everything.
"""

import sys
from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QFrame, QPushButton, QComboBox, QSpinBox,
)

from ctc_blueTrack import MainWindow as BlueTrackWindow, BLUE_LINE_BLOCKS

SIGNAL_SECTIONS = ["B", "C"]
SIGNAL_COLORS   = ["Green", "Red", "Yellow", "Auto"]

SECTION_BLOCKS = {
    sec: [bn for bn, *_ in blocks]
    for sec, blocks in BLUE_LINE_BLOCKS.items()
}


class TestUI(QMainWindow):
    def __init__(self, ctc_window: BlueTrackWindow):
        super().__init__()
        self.ctc = ctc_window
        self.setWindowTitle("Test UI — Block Occupancy")
        self.resize(420, 420)

        root = QWidget()
        root.setStyleSheet(
            "QWidget { background:white; }"
            "QComboBox { background:white; color:black; }"
            "QComboBox QAbstractItemView { background:white; color:black; "
            "selection-background-color:#4a6fa5; selection-color:white; }")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QLabel("Blue Track — Block Occupancy Panel")
        hdr.setStyleSheet(
            "background:#2a3f5f; color:white; font-size:15px; font-weight:700;"
            "padding:10px 14px; border-radius:8px;")
        outer.addWidget(hdr)

        # ── Block selection ───────────────────────────────────────────────────
        sel_box = self._section_frame("Set Block Occupancy")

        combo_style = ("QComboBox { background:white; color:black; min-width:200px; "
                       "padding:4px 8px; }"
                       "QComboBox QAbstractItemView { background:white; color:black; "
                       "selection-background-color:#4a6fa5; selection-color:white; }")

        sel_box.layout().addWidget(QLabel("Section:"))
        self.section_combo = QComboBox()
        self.section_combo.addItems(sorted(SECTION_BLOCKS.keys()))
        self.section_combo.setStyleSheet(combo_style)
        self.section_combo.currentTextChanged.connect(self._on_section_changed)
        sel_box.layout().addWidget(self.section_combo)

        sel_box.layout().addWidget(QLabel("Block:"))
        self.block_combo = QComboBox()
        self.block_combo.setStyleSheet(combo_style)
        sel_box.layout().addWidget(self.block_combo)
        self._on_section_changed(self.section_combo.currentText())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_occupy = QPushButton("Occupy Block")
        btn_occupy.setStyleSheet(
            "background:#1a5fa8; color:white; font-weight:bold;"
            "padding:8px 16px; border-radius:8px;")
        btn_occupy.clicked.connect(self._occupy)

        btn_clear = QPushButton("Clear Block")
        btn_clear.setStyleSheet(
            "background:#b03030; color:white; font-weight:bold;"
            "padding:8px 16px; border-radius:8px;")
        btn_clear.clicked.connect(self._clear_block)

        btn_row.addWidget(btn_occupy)
        btn_row.addWidget(btn_clear)
        sel_box.layout().addLayout(btn_row)

        btn_clear_all = QPushButton("Clear All Blocks")
        btn_clear_all.setStyleSheet(
            "background:#888888; color:white; font-weight:bold;"
            "padding:7px 14px; border-radius:8px;")
        btn_clear_all.clicked.connect(self._clear_all)
        sel_box.layout().addWidget(btn_clear_all)

        outer.addWidget(sel_box)

        # ── Signal control ────────────────────────────────────────────────────
        sig_box = self._section_frame("Signal Control")

        sig_box.layout().addWidget(QLabel("Section:"))
        self.sig_section_combo = QComboBox()
        self.sig_section_combo.addItems(SIGNAL_SECTIONS)
        self.sig_section_combo.setStyleSheet(combo_style)
        sig_box.layout().addWidget(self.sig_section_combo)

        sig_box.layout().addWidget(QLabel("Color:"))
        self.sig_color_combo = QComboBox()
        self.sig_color_combo.addItems(SIGNAL_COLORS)
        self.sig_color_combo.setStyleSheet(combo_style)
        sig_box.layout().addWidget(self.sig_color_combo)

        btn_set_sig = QPushButton("Set Signal")
        btn_set_sig.setStyleSheet(
            "background:#2a3f5f; color:white; font-weight:bold;"
            "padding:8px 16px; border-radius:8px;")
        btn_set_sig.clicked.connect(self._set_signal)
        sig_box.layout().addWidget(btn_set_sig)

        outer.addWidget(sig_box)

        # ── Ticket sales ───────────────────────────────────────────────────────
        sales_box = self._section_frame("Ticket Sales")
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Blue Line:"))
        self.sales_spin = QSpinBox()
        self.sales_spin.setRange(0, 1_000_000)
        self.sales_spin.setSingleStep(10)
        self.sales_spin.setValue(0)
        row.addWidget(self.sales_spin, stretch=1)
        btn_sales = QPushButton("Apply")
        btn_sales.setStyleSheet(
            "background:#4a6fa5; color:white; font-weight:bold;"
            "padding:4px 10px; border-radius:6px;")
        btn_sales.clicked.connect(self._apply_ticket_sales)
        row.addWidget(btn_sales)
        sales_box.layout().addLayout(row)

        outer.addWidget(sales_box)
        outer.addStretch(1)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _section_frame(title: str) -> QFrame:
        box = QFrame()
        box.setStyleSheet(
            "background:#f5f5f5; border:2px solid #c8c8c8; border-radius:10px;")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight:800; font-size:13px;")
        lay.addWidget(lbl)
        return box

    def _on_section_changed(self, sec: str):
        self.block_combo.clear()
        for bn in SECTION_BLOCKS.get(sec, []):
            self.block_combo.addItem(str(bn))

    def _train_id(self) -> str:
        """Unique key for the selected block."""
        return f"Block {self.block_combo.currentText()}"

    def _occupy(self):
        sec = self.section_combo.currentText()
        blk = int(self.block_combo.currentText())
        self.ctc.inject_train(f"Block {blk}", sec, blk)

    def _clear_block(self):
        self.ctc.remove_train(self._train_id())

    def _set_signal(self):
        sec   = self.sig_section_combo.currentText()
        color = self.sig_color_combo.currentText().lower()
        self.ctc.set_signal(sec, color)

    def _apply_ticket_sales(self):
        self.ctc.set_ticket_sales(self.sales_spin.value())

    def _clear_all(self):
        self.ctc.clear_trains()


def main():
    app = QApplication(sys.argv)

    ctc_win  = BlueTrackWindow()
    test_win = TestUI(ctc_win)

    ctc_win.setWindowTitle("CTC — Blue Track")
    ctc_win.move(100, 80)
    test_win.move(ctc_win.x() + ctc_win.width() + 20, 80)

    ctc_win.show()
    test_win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
