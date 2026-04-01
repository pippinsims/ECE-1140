"""
launcher.py  –  Start CTC and Wayside Control System together
==============================================================

Run this file to open both windows simultaneously:

    python launcher.py

Architecture
------------
  Main thread  : PyQt6 event loop  (CTC window)
  Daemon thread: tkinter event loop (Wayside Dashboard window)

The two loops communicate exclusively through SharedState, which is
thread-safe and never blocks either event loop.

Data flows (every 100 ms)
--------------------------
  CTC (_poll_active_trains)
    └─► SharedState.push_ctc_data("Green" / "Red", {block: {occupied, cmd_speed, authority}})
          └─► Wayside (_poll_shared_state)
                └─► WaysideFrame.receive_live_data()   [feeds block inputs]
                └─► SharedState.push_wayside_outputs() [signals, switches, crossings]
                      └─► CTC (_poll_wayside_outputs)
                            └─► track diagram signal lights
                            └─► crossing up/down messages

Standalone use (for debugging individual windows):
    python ctc_ui.py             # CTC only
    python wayside_dashboard.py  # Wayside only
"""

import sys
import threading

from shared_state import SharedState


def _run_wayside(state: SharedState) -> None:
    """
    Entry point for the wayside tkinter thread.
    tkinter must be created and destroyed entirely within this thread.
    """
    # Import here so tkinter is only initialised inside this thread
    from wayside_dashboard import WaysideDashboard
    app = WaysideDashboard(shared_state=state)
    app.mainloop()


def main() -> None:
    # ── Shared state ─────────────────────────────────────────────────────────
    state = SharedState()

    # ── Wayside in daemon thread ──────────────────────────────────────────────
    wayside_thread = threading.Thread(
        target=_run_wayside,
        args=(state,),
        daemon=True,   # exits automatically when the main (CTC) thread exits
        name="WaysideThread",
    )
    wayside_thread.start()

    # ── CTC in main thread (PyQt6 requires main thread) ───────────────────────
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPalette, QColor
    from ctc_ui import MainWindow

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Train Control System")

    # Force light palette so dark-mode OS never flips text to white
    qt_app.setStyle("Fusion")
    light = QPalette()
    light.setColor(QPalette.ColorRole.Window,          QColor(255, 255, 255))
    light.setColor(QPalette.ColorRole.WindowText,      QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.Base,            QColor(240, 240, 240))
    light.setColor(QPalette.ColorRole.AlternateBase,   QColor(225, 225, 225))
    light.setColor(QPalette.ColorRole.Text,            QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.ButtonText,      QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.BrightText,      QColor(0,   0,   0))
    light.setColor(QPalette.ColorRole.Button,          QColor(225, 225, 225))
    light.setColor(QPalette.ColorRole.Highlight,       QColor(74,  111, 165))
    light.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    qt_app.setPalette(light)

    ctc_win = MainWindow(shared_state=state)
    ctc_win.show()

    # Block until the CTC window is closed; daemon thread exits with it
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
