# ai was used for styling and layout creation of the ui

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QGridLayout, QHBoxLayout, QVBoxLayout, QDoubleSpinBox, QSpinBox,
    QScrollArea, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor


# colors
BG_PAGE      = "#F7F8FA"
BG_CARD      = "#FFFFFF"
BG_HEADER    = "#FFFFFF"
BORDER_CARD  = "#E4E7ED"
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#6B7280"
DIVIDER      = "#F3F4F6"
ACCENT_BLUE  = "#2563EB"
ACCENT_GREEN = "#16A34A"
ACCENT_GREEN_BG = "#F0FDF4"


def cardShadow(widget):
    # attaches a soft drop shadow to give cards depth
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(27)
    shadow.setOffset(0, 3)
    shadow.setColor(QColor(0, 0, 0, 22))
    widget.setGraphicsEffect(shadow)
    return shadow


class TrainModelTestUI(QMainWindow):
    def __init__(self, trainModel=None):
        super().__init__()

        self.trainModel      = trainModel
        self.brokenRailOn    = False
        self.trackCircuitOn  = False
        self.trackPowerOn    = False
        self.serviceBrakeOn  = False
        self.emergencyBrakeOn = False
        self.externalLightsOn = False
        self.internalLightsOn = False
        self.rightDoorOn     = False
        self.leftDoorOn      = False

        self.setWindowTitle("Train Model Test")
        self.setFixedSize(1920, 990)
        self.setStyleSheet(f"background-color: {BG_PAGE};")

        central = QWidget()
        self.setCentralWidget(central)
        rootLayout = QVBoxLayout(central)
        rootLayout.setContentsMargins(0, 0, 0, 0)
        rootLayout.setSpacing(0)

        # header
        headerFrame = QFrame()
        headerFrame.setFixedHeight(87)
        headerFrame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_HEADER};
                border-bottom: 1px solid {BORDER_CARD};
            }}
        """)
        headerLayout = QHBoxLayout(headerFrame)
        headerLayout.setContentsMargins(42, 0, 42, 0)

        titleLabel = QLabel("Train Model Test")
        titleLabel.setFont(QFont("Segoe UI", 22, QFont.Bold))
        titleLabel.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        headerLayout.addWidget(titleLabel)
        headerLayout.addStretch()

        rootLayout.addWidget(headerFrame)

        # body
        bodyWidget = QWidget()
        bodyWidget.setStyleSheet(f"background-color: {BG_PAGE};")
        bodyLayout = QHBoxLayout(bodyWidget)
        bodyLayout.setContentsMargins(36, 30, 36, 30)
        bodyLayout.setSpacing(24)
        rootLayout.addWidget(bodyWidget, stretch=1)

        # ── inputs card ──────────────────────────────────────────────────────
        inputsCard = QWidget()
        inputsCard.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_CARD};
                border-radius: 18px;
            }}
        """)
        cardShadow(inputsCard)
        inputsOuterLayout = QVBoxLayout(inputsCard)
        inputsOuterLayout.setContentsMargins(0, 0, 0, 0)
        inputsOuterLayout.setSpacing(0)

        cardTitleWidget = QWidget()
        cardTitleWidget.setStyleSheet("background: transparent; border: none;")
        cardTitleLayout = QVBoxLayout(cardTitleWidget)
        cardTitleLayout.setContentsMargins(30, 24, 30, 0)
        cardTitleLayout.setSpacing(12)
        cardTitleLayout.addWidget(self._cardTitle("Inputs"))
        inputsOuterLayout.addWidget(cardTitleWidget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 9px; background: #F3F4F6; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #D1D5DB; border-radius: 4px; }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        grid = QGridLayout(container)
        grid.setSpacing(0)
        grid.setVerticalSpacing(3)
        grid.setContentsMargins(30, 18, 30, 30)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)

        row = 0

        row = self._addSectionHeader(grid, row, "Track Model")
        self.commandedSpeedInput = self._addNumericRow(grid, row, "Commanded Speed", "km/hr", 0, 200, 1, 1)
        row += 1
        self.commandedAuthorityInput = self._addNumericRow(grid, row, "Commanded Authority", "km", 0, 9999, 0.1, 2)
        row += 1
        self.gradeInput = self._addNumericRow(grid, row, "Grade", "%", -20, 20, 0.1, 1)
        row += 1
        self.accelLimitInput = self._addNumericRow(grid, row, "Accel Limit", "km/hr\u00b2", 0, 25000, 100, 0)
        row += 1
        self.decelLimitInput = self._addNumericRow(grid, row, "Decel Limit", "km/hr\u00b2", 0, 40000, 100, 0)
        row += 1
        self.brokenRailToggle = self._addToggleRow(grid, row, "Broken Rail", self.onBrokenRailToggled)
        row += 1
        self.trackCircuitToggle = self._addToggleRow(grid, row, "Track Circuit Fail", self.onTrackCircuitToggled)
        row += 1
        self.trackPowerToggle = self._addToggleRow(grid, row, "Track Power Fail", self.onTrackPowerToggled)
        row += 1
        self.passengersInput = self._addIntRow(grid, row, "Passengers Boarded", 0, 300)
        row += 1

        row = self._addSectionHeader(grid, row, "Train Controller")
        self.temperatureInput = self._addNumericRow(grid, row, "Temperature", "\u00b0C", -40, 80, 0.5, 1)
        row += 1
        self.serviceBrakeToggle = self._addToggleRow(grid, row, "Service Brake", self.onServiceBrakeToggled)
        row += 1
        self.emergencyBrakeToggle = self._addToggleRow(grid, row, "Emergency Brake", self.onEmergencyBrakeToggled)
        row += 1
        self.externalLightsToggle = self._addToggleRow(grid, row, "External Lights", self.onExternalLightsToggled)
        row += 1
        self.internalLightsToggle = self._addToggleRow(grid, row, "Internal Lights", self.onInternalLightsToggled)
        row += 1
        self.rightDoorToggle = self._addToggleRow(grid, row, "Right Door", self.onRightDoorToggled)
        row += 1
        self.leftDoorToggle = self._addToggleRow(grid, row, "Left Door", self.onLeftDoorToggled)
        row += 1
        self.powerCommandInput = self._addNumericRow(grid, row, "Power Command", "W", 0, 120000, 500, 0)
        row += 1

        # seed defaults matching backend initial values
        self.commandedSpeedInput.setValue(70)
        self.commandedAuthorityInput.setValue(100)
        self.accelLimitInput.setValue(12960)
        self.decelLimitInput.setValue(15552)
        self.temperatureInput.setValue(20)

        # wire all spinboxes to live-push on every change
        self.commandedSpeedInput.valueChanged.connect(self.pushToModel)
        self.commandedAuthorityInput.valueChanged.connect(self.pushToModel)
        self.gradeInput.valueChanged.connect(self.pushToModel)
        self.accelLimitInput.valueChanged.connect(self.pushToModel)
        self.decelLimitInput.valueChanged.connect(self.pushToModel)
        self.passengersInput.valueChanged.connect(self.pushToModel)
        self.temperatureInput.valueChanged.connect(self.pushToModel)
        self.powerCommandInput.valueChanged.connect(self.pushToModel)

        scroll.setWidget(container)
        inputsOuterLayout.addWidget(scroll)
        bodyLayout.addWidget(inputsCard, stretch=3)

        # ── outputs card ─────────────────────────────────────────────────────
        outputsCard = QWidget()
        outputsCard.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_CARD};
                border-radius: 18px;
            }}
        """)
        cardShadow(outputsCard)
        outputsOuterLayout = QVBoxLayout(outputsCard)
        outputsOuterLayout.setContentsMargins(0, 0, 0, 0)
        outputsOuterLayout.setSpacing(0)

        outputsTitleWidget = QWidget()
        outputsTitleWidget.setStyleSheet("background: transparent; border: none;")
        outputsTitleLayout = QVBoxLayout(outputsTitleWidget)
        outputsTitleLayout.setContentsMargins(30, 24, 30, 0)
        outputsTitleLayout.setSpacing(12)
        outputsTitleLayout.addWidget(self._cardTitle("Outputs"))
        outputsOuterLayout.addWidget(outputsTitleWidget)

        outputsScroll = QScrollArea()
        outputsScroll.setWidgetResizable(True)
        outputsScroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 9px; background: #F3F4F6; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #D1D5DB; border-radius: 4px; }
        """)

        outputsContainer = QWidget()
        outputsContainer.setStyleSheet("background: transparent; border: none;")
        outputsGrid = QGridLayout(outputsContainer)
        outputsGrid.setSpacing(0)
        outputsGrid.setVerticalSpacing(3)
        outputsGrid.setContentsMargins(30, 18, 30, 30)
        outputsGrid.setColumnStretch(0, 3)
        outputsGrid.setColumnStretch(1, 2)
        outputsGrid.setColumnStretch(2, 1)

        orow = 0

        orow = self._addSectionHeader(outputsGrid, orow, "Track Model")
        self.outTrackSpeedLabel = self._addOutputRow(outputsGrid, orow, "Actual Speed", "km/hr")
        orow += 1

        orow = self._addSectionHeader(outputsGrid, orow, "Train Controller")
        self.outCtrlSpeedLabel      = self._addOutputRow(outputsGrid, orow, "Actual Speed", "km/hr")
        orow += 1
        self.outPassengersLabel     = self._addOutputRow(outputsGrid, orow, "Passengers On Board", "count")
        orow += 1
        self.outAuthorityLabel      = self._addOutputRow(outputsGrid, orow, "Authority", "km")
        orow += 1

        # push remaining space to bottom
        outputsGrid.setRowStretch(orow, 1)

        outputsScroll.setWidget(outputsContainer)
        outputsOuterLayout.addWidget(outputsScroll)
        bodyLayout.addWidget(outputsCard, stretch=2)

        if self.trainModel:
            self.pushToModel()

        # timer to keep output labels in sync with backend
        self.refreshTimer = QTimer()
        self.refreshTimer.timeout.connect(self.refreshFromModel)
        self.refreshTimer.start(100)

    # helpers

    def _cardTitle(self, text):
        # all-caps section label with a divider underline
        lbl = QLabel(text.upper())
        lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            letter-spacing: 2px;
            background: transparent;
            border: none;
            padding-bottom: 3px;
            border-bottom: 1px solid {DIVIDER};
        """)
        return lbl

    def _addSectionHeader(self, grid, row, text):
        # greyed subheading to separate input/output groups
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl.setFixedHeight(48)
        lbl.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            background: transparent;
            border: none;
            border-bottom: 1px solid {DIVIDER};
            padding-top: 12px;
        """)
        grid.addWidget(lbl, row, 0, 1, 3)
        return row + 1

    def _addNumericRow(self, grid, row, labelText, unitText, minVal, maxVal, step, decimals):
        # label + spinbox and unit in one grid row
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 15))
        lbl.setFixedHeight(51)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        spin = QDoubleSpinBox()
        spin.setRange(minVal, maxVal)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setFixedHeight(45)
        spin.setFont(QFont("Segoe UI", 15))
        spin.setAlignment(Qt.AlignRight)
        spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: {BG_PAGE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_CARD};
                border-radius: 7px;
                padding: 3px 9px;
            }}
            QDoubleSpinBox:focus {{ border: 1.5px solid {ACCENT_BLUE}; }}
            QDoubleSpinBox::up-button   {{ width: 0; border: none; }}
            QDoubleSpinBox::down-button {{ width: 0; border: none; }}
        """)

        unitLbl = QLabel(unitText)
        unitLbl.setFont(QFont("Segoe UI", 13))
        unitLbl.setFixedHeight(51)
        unitLbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unitLbl.setStyleSheet(f"color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl,     row, 0)
        grid.addWidget(spin,    row, 1)
        grid.addWidget(unitLbl, row, 2)
        return spin

    def _addIntRow(self, grid, row, labelText, minVal, maxVal):
        # label and integer spinbox + unit in one grid row
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 15))
        lbl.setFixedHeight(51)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        spin = QSpinBox()
        spin.setRange(minVal, maxVal)
        spin.setFixedHeight(45)
        spin.setFont(QFont("Segoe UI", 15))
        spin.setAlignment(Qt.AlignRight)
        spin.setStyleSheet(f"""
            QSpinBox {{
                background: {BG_PAGE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_CARD};
                border-radius: 7px;
                padding: 3px 9px;
            }}
            QSpinBox:focus {{ border: 1.5px solid {ACCENT_BLUE}; }}
            QSpinBox::up-button   {{ width: 0; border: none; }}
            QSpinBox::down-button {{ width: 0; border: none; }}
        """)

        unitLbl = QLabel("count")
        unitLbl.setFont(QFont("Segoe UI", 13))
        unitLbl.setFixedHeight(51)
        unitLbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unitLbl.setStyleSheet(f"color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl,     row, 0)
        grid.addWidget(spin,    row, 1)
        grid.addWidget(unitLbl, row, 2)
        return spin

    def _addToggleRow(self, grid, row, labelText, callback):
        # label and ON/OFF toggle button + unit in one grid row
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 15))
        lbl.setFixedHeight(51)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        btn = QPushButton("OFF")
        btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn.setFixedHeight(42)
        btn.setCheckable(True)
        btn.setStyleSheet(self._toggleStyle(False))
        btn.clicked.connect(callback)

        unitLbl = QLabel("bool")
        unitLbl.setFont(QFont("Segoe UI", 13))
        unitLbl.setFixedHeight(51)
        unitLbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unitLbl.setStyleSheet(f"color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl,     row, 0)
        grid.addWidget(btn,     row, 1)
        grid.addWidget(unitLbl, row, 2)
        return btn

    def _addOutputRow(self, grid, row, labelText, unitText):
        # read-only display row — same layout as inputs but greyed out and non-interactive
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 15))
        lbl.setFixedHeight(51)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        val = QLabel("—")
        val.setFont(QFont("Segoe UI", 15))
        val.setFixedHeight(45)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setStyleSheet(f"""
            color: #9CA3AF;
            background: {DIVIDER};
            border: 1px solid {BORDER_CARD};
            border-radius: 7px;
            padding: 3px 9px;
        """)

        unitLbl = QLabel(unitText)
        unitLbl.setFont(QFont("Segoe UI", 13))
        unitLbl.setFixedHeight(51)
        unitLbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unitLbl.setStyleSheet(f"color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl,     row, 0)
        grid.addWidget(val,     row, 1)
        grid.addWidget(unitLbl, row, 2)
        return val

    def _toggleStyle(self, isOn):
        # css for the ON/OFF toggle buttons
        if isOn:
            return (f"QPushButton {{ background-color: {ACCENT_GREEN_BG}; color: {ACCENT_GREEN}; "
                    f"border: 1.5px solid #BBF7D0; border-radius: 7px; }}"
                    f"QPushButton:hover {{ background-color: #DCFCE7; }}")
        return (f"QPushButton {{ background-color: {BG_PAGE}; color: {TEXT_SECONDARY}; "
                f"border: 1px solid {BORDER_CARD}; border-radius: 7px; }}"
                f"QPushButton:hover {{ background-color: {DIVIDER}; }}")

    def _setToggle(self, btn, isOn):
        # updates a toggle button's text and style to match its state
        btn.setText("ON" if isOn else "OFF")
        btn.setChecked(isOn)
        btn.setStyleSheet(self._toggleStyle(isOn))

    # read backend state and update output labels

    def refreshFromModel(self):
        if not self.trainModel:
            return
        m = self.trainModel
        self.outTrackSpeedLabel.setText("%.2f" % m.getCurrentSpeedKmh())
        self.outCtrlSpeedLabel.setText("%.2f"  % m.getCurrentSpeedKmh())
        self.outAuthorityLabel.setText("%.3f"  % m.getCommandedAuthorityKm())

    # give the values to backend

    def pushToModel(self):
        if not self.trainModel:
            return
        m = self.trainModel
        m.commandedSpeedKmh          = self.commandedSpeedInput.value()
        m.commandedAuthorityKm       = self.commandedAuthorityInput.value()
        m.trackGradePercent          = self.gradeInput.value()
        m.trackAccelerationLimitKmh2 = self.accelLimitInput.value()
        m.trackDecelerationLimitKmh2 = self.decelLimitInput.value()
        m.boardingPassengerCount     = self.passengersInput.value()
        m.cabinTemperatureC          = self.temperatureInput.value()
        m.requestedTractionPowerW    = self.powerCommandInput.value()

    # give the toggle values to backend

    def onBrokenRailToggled(self):
        self.brokenRailOn = not self.brokenRailOn
        self._setToggle(self.brokenRailToggle, self.brokenRailOn)
        if self.trainModel:
            self.trainModel.isRailBroken = self.brokenRailOn

    def onTrackCircuitToggled(self):
        self.trackCircuitOn = not self.trackCircuitOn
        self._setToggle(self.trackCircuitToggle, self.trackCircuitOn)
        if self.trainModel:
            self.trainModel.isTrackCircuitFailed = self.trackCircuitOn

    def onTrackPowerToggled(self):
        self.trackPowerOn = not self.trackPowerOn
        self._setToggle(self.trackPowerToggle, self.trackPowerOn)
        if self.trainModel:
            self.trainModel.isTrackPowerLost = self.trackPowerOn

    def onServiceBrakeToggled(self):
        self.serviceBrakeOn = not self.serviceBrakeOn
        self._setToggle(self.serviceBrakeToggle, self.serviceBrakeOn)
        if self.trainModel:
            self.trainModel.isServiceBrakeOn = self.serviceBrakeOn

    def onEmergencyBrakeToggled(self):
        self.emergencyBrakeOn = not self.emergencyBrakeOn
        self._setToggle(self.emergencyBrakeToggle, self.emergencyBrakeOn)
        if self.trainModel:
            self.trainModel.isEmergencyBrakeOn = self.emergencyBrakeOn

    def onExternalLightsToggled(self):
        self.externalLightsOn = not self.externalLightsOn
        self._setToggle(self.externalLightsToggle, self.externalLightsOn)
        if self.trainModel:
            self.trainModel.areExternalLightsOn = self.externalLightsOn

    def onInternalLightsToggled(self):
        self.internalLightsOn = not self.internalLightsOn
        self._setToggle(self.internalLightsToggle, self.internalLightsOn)
        if self.trainModel:
            self.trainModel.areInternalLightsOn = self.internalLightsOn

    def onRightDoorToggled(self):
        self.rightDoorOn = not self.rightDoorOn
        self._setToggle(self.rightDoorToggle, self.rightDoorOn)
        if self.trainModel:
            self.trainModel.isRightDoorOpen = self.rightDoorOn

    def onLeftDoorToggled(self):
        self.leftDoorOn = not self.leftDoorOn
        self._setToggle(self.leftDoorToggle, self.leftDoorOn)
        if self.trainModel:
            self.trainModel.isLeftDoorOpen = self.leftDoorOn

    def setTrainModel(self, trainModel):
        self.trainModel = trainModel
        self.pushToModel()


def main():
    app = QApplication(sys.argv)
    w = TrainModelTestUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()