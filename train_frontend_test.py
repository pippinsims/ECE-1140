# AI was used for styling and layout creation of this UI.
#
# Standalone Train Model test UI that can also be embedded into the integrated system.
# - If constructed with a TrainModel instance, it will only push/pull to that model.
# - If run as __main__ with no model provided, it will create a TrainSystem and tick it.

from __future__ import annotations

import sys
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from train_backend import TrainModel, TrainSystem, samplePeriodSec
from train_frontend_main import TrainControlUI


# colors
BG_PAGE = "#F7F8FA"
BG_CARD = "#FFFFFF"
BG_HEADER = "#FFFFFF"
BORDER_CARD = "#E4E7ED"
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#6B7280"
DIVIDER = "#F3F4F6"
ACCENT_BLUE = "#2563EB"
ACCENT_GREEN = "#16A34A"
ACCENT_GREEN_BG = "#F0FDF4"
ACCENT_RED = "#DC2626"
ACCENT_RED_BG = "#FEF2F2"


def cardShadow(widget: QWidget) -> None:
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(27)
    shadow.setOffset(0, 3)
    shadow.setColor(QColor(0, 0, 0, 22))
    widget.setGraphicsEffect(shadow)


class TrainModelTestUI(QMainWindow):
    """
    A "test harness" UI for TrainModel.

    - In integrated usage: pass `trainModel=<TrainModel>` and do NOT enable standalone ticking.
      The integrated launcher already ticks the model (and may overwrite some controller-driven fields).
    - In standalone usage: pass neither; it will create a TrainModel and tick it so outputs update.
    """

    def __init__(
        self,
        trainModel: Optional[TrainModel] = None,
        trainSystem: Optional[TrainSystem] = None,
        *,
        standalone_tick: bool = False,
    ):
        super().__init__()

        if trainModel is None and trainSystem is None:
            # Standalone: drive the TrainModel directly so UI inputs persist and
            # are visible in both this test UI and the main TrainControlUI.
            trainModel = TrainModel()
            standalone_tick = True

        self._system = trainSystem
        self.trainModel = trainModel
        self._standalone_tick = bool(standalone_tick)

        self.setWindowTitle("Train Model Test")
        self.setBaseSize(1080, 800)
        self.setStyleSheet(f"background-color: {BG_PAGE};")

        central = QWidget()
        self.setCentralWidget(central)
        rootLayout = QVBoxLayout(central)
        rootLayout.setContentsMargins(0, 0, 0, 0)
        rootLayout.setSpacing(0)

        # header
        headerFrame = QFrame()
        headerFrame.setFixedHeight(60)
        headerFrame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {BG_HEADER};
                border-bottom: 1px solid {BORDER_CARD};
            }}
            """
        )
        headerLayout = QHBoxLayout(headerFrame)
        headerLayout.setContentsMargins(24, 0, 24, 0)

        titleLabel = QLabel("Train Model Test")
        titleLabel.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        titleLabel.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        headerLayout.addWidget(titleLabel)
        headerLayout.addStretch()
        rootLayout.addWidget(headerFrame)

        # body
        bodyWidget = QWidget()
        bodyWidget.setStyleSheet(f"background-color: {BG_PAGE};")
        bodyLayout = QHBoxLayout(bodyWidget)
        bodyLayout.setContentsMargins(18, 14, 18, 14)
        bodyLayout.setSpacing(14)
        rootLayout.addWidget(bodyWidget, stretch=1)

        # inputs card
        inputsCard = QWidget()
        inputsCard.setStyleSheet(
            f"""
            QWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_CARD};
                border-radius: 12px;
            }}
            """
        )
        cardShadow(inputsCard)
        inputsOuterLayout = QVBoxLayout(inputsCard)
        inputsOuterLayout.setContentsMargins(0, 0, 0, 0)
        inputsOuterLayout.setSpacing(0)

        cardTitleWidget = QWidget()
        cardTitleWidget.setStyleSheet("background: transparent; border: none;")
        cardTitleLayout = QVBoxLayout(cardTitleWidget)
        cardTitleLayout.setContentsMargins(20, 16, 20, 0)
        cardTitleLayout.setSpacing(8)
        cardTitleLayout.addWidget(self._cardTitle("Inputs"))
        inputsOuterLayout.addWidget(cardTitleWidget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 9px; background: #F3F4F6; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #D1D5DB; border-radius: 4px; }
            """
        )

        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        grid = QGridLayout(container)
        grid.setSpacing(0)
        grid.setVerticalSpacing(4)
        grid.setContentsMargins(18, 12, 18, 18)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)

        row = 0

        # Track Model inputs (into TrainModel)
        row = self._addSectionHeader(grid, row, "Track Model → Train Model")
        self.commandedSpeedInput = self._addNumericRow(grid, row, "Commanded Speed", "km/hr", 0, 200, 1, 1)
        row += 1
        self.speedLimitInput = self._addNumericRow(grid, row, "Speed Limit", "km/hr", 0, 200, 1, 1)
        row += 1
        self.commandedAuthorityInput = self._addNumericRow(grid, row, "Commanded Authority", "km", 0, 9999, 0.1, 3)
        row += 1
        self.gradeInput = self._addNumericRow(grid, row, "Grade", "%", -20, 20, 0.1, 1)
        row += 1
        self.accelLimitInput = self._addNumericRow(grid, row, "Accel Limit", "km/hr²", 0, 25000, 100, 0)
        row += 1
        self.decelLimitInput = self._addNumericRow(grid, row, "Decel Limit", "km/hr²", 0, 40000, 100, 0)
        row += 1
        self.brokenRailToggle = self._addToggleRow(grid, row, "Broken Rail", self.onBrokenRailToggled)
        row += 1
        self.trackCircuitToggle = self._addToggleRow(grid, row, "Track Circuit Fail", self.onTrackCircuitToggled)
        row += 1
        self.trackPowerToggle = self._addToggleRow(grid, row, "Track Power Fail", self.onTrackPowerToggled)
        row += 1
        self.passengersInput = self._addIntRow(grid, row, "Passengers Boarded", 0, 300)
        row += 1
        self.beaconDataInput = self._addStringRow(grid, row, "Beacon Data", "string")
        row += 1

        # Train Controller → Train Model inputs (directly into TrainModel)
        row = self._addSectionHeader(grid, row, "Train Controller → Train Model")
        self.temperatureInput = self._addNumericRow(grid, row, "Cabin Temp", "°C", -40, 80, 0.5, 1)
        row += 1
        self.serviceBrakeToggle = self._addToggleRow(grid, row, "Service Brake", self.onServiceBrakeToggled)
        row += 1
        self.emergencyBrakeToggle = self._addToggleRow(grid, row, "Emergency Brake", self.onEmergencyBrakeToggled)
        row += 1
        self.passengerEBrakeToggle = self._addToggleRow(grid, row, "Passenger E-Brake", self.onPassengerEBrakeToggled)
        row += 1
        self.externalLightsToggle = self._addToggleRow(grid, row, "External Lights", self.onExternalLightsToggled)
        row += 1
        self.internalLightsToggle = self._addToggleRow(grid, row, "Internal Lights", self.onInternalLightsToggled)
        row += 1
        self.rightDoorToggle = self._addToggleRow(grid, row, "Right Door", self.onRightDoorToggled)
        row += 1
        self.leftDoorToggle = self._addToggleRow(grid, row, "Left Door", self.onLeftDoorToggled)
        row += 1
        self.powerCommandInput = self._addNumericRow(grid, row, "Requested Traction Power", "W", 0, 120000, 500, 0)
        row += 1

        # seed defaults matching backend initial values
        self.commandedSpeedInput.setValue(70)
        self.speedLimitInput.setValue(70)
        self.commandedAuthorityInput.setValue(0.0)
        self.accelLimitInput.setValue(12960)
        self.decelLimitInput.setValue(15552)
        self.temperatureInput.setValue(20)

        # wire spinboxes to live-push on every change
        for sb in [
            self.commandedSpeedInput,
            self.speedLimitInput,
            self.commandedAuthorityInput,
            self.gradeInput,
            self.accelLimitInput,
            self.decelLimitInput,
            self.passengersInput,
            self.temperatureInput,
            self.powerCommandInput,
        ]:
            sb.valueChanged.connect(self.pushToModel)
        self.beaconDataInput.textChanged.connect(self.pushToModel)

        scroll.setWidget(container)
        inputsOuterLayout.addWidget(scroll)
        bodyLayout.addWidget(inputsCard, stretch=3)

        # outputs card
        outputsCard = QWidget()
        outputsCard.setStyleSheet(
            f"""
            QWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_CARD};
                border-radius: 12px;
            }}
            """
        )
        cardShadow(outputsCard)
        outputsOuterLayout = QVBoxLayout(outputsCard)
        outputsOuterLayout.setContentsMargins(0, 0, 0, 0)
        outputsOuterLayout.setSpacing(0)

        outputsTitleWidget = QWidget()
        outputsTitleWidget.setStyleSheet("background: transparent; border: none;")
        outputsTitleLayout = QVBoxLayout(outputsTitleWidget)
        outputsTitleLayout.setContentsMargins(20, 16, 20, 0)
        outputsTitleLayout.setSpacing(8)
        outputsTitleLayout.addWidget(self._cardTitle("Outputs"))
        outputsOuterLayout.addWidget(outputsTitleWidget)

        outputsScroll = QScrollArea()
        outputsScroll.setWidgetResizable(True)
        outputsScroll.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 9px; background: #F3F4F6; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #D1D5DB; border-radius: 4px; }
            """
        )

        outputsContainer = QWidget()
        outputsContainer.setStyleSheet("background: transparent; border: none;")
        outputsGrid = QGridLayout(outputsContainer)
        outputsGrid.setSpacing(0)
        outputsGrid.setVerticalSpacing(4)
        outputsGrid.setContentsMargins(18, 12, 18, 18)
        outputsGrid.setColumnStretch(0, 3)
        outputsGrid.setColumnStretch(1, 2)
        outputsGrid.setColumnStretch(2, 1)

        orow = 0
        orow = self._addSectionHeader(outputsGrid, orow, "Train Model Outputs")
        self.outSpeedKmh = self._addOutputRow(outputsGrid, orow, "Current Speed", "km/hr")
        orow += 1
        self.outAccel = self._addOutputRow(outputsGrid, orow, "Acceleration", "m/s²")
        orow += 1
        self.outDistance = self._addOutputRow(outputsGrid, orow, "Distance Traveled", "km")
        orow += 1
        self.outAuthority = self._addOutputRow(outputsGrid, orow, "Remaining Authority", "km")
        orow += 1
        self.outPassengers = self._addOutputRow(outputsGrid, orow, "Passengers On Board", "count")
        orow += 1
        self.outStation = self._addOutputRow(outputsGrid, orow, "Approaching Station", "string")
        orow += 1
        self.outEBrake = self._addOutputRow(outputsGrid, orow, "Emergency Brake Active", "bool")
        orow += 1

        outputsGrid.setRowStretch(orow, 1)
        outputsScroll.setWidget(outputsContainer)
        outputsOuterLayout.addWidget(outputsScroll)
        bodyLayout.addWidget(outputsCard, stretch=2)

        # initial push
        if self.trainModel is not None:
            self.pushToModel()
            self._sync_toggles_from_model()

        # timers
        self.refreshTimer = QTimer()
        self.refreshTimer.timeout.connect(self.refreshFromModel)
        self.refreshTimer.start(100)

        if self._system is not None or self._standalone_tick:
            self.tickTimer = QTimer()
            self.tickTimer.timeout.connect(self._tickStandaloneSystem)
            self.tickTimer.start(int(samplePeriodSec * 1000))

    # ── helpers ──────────────────────────────────────────────────────────────

    def _cardTitle(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(
            f"""
            color: {TEXT_SECONDARY};
            letter-spacing: 1px;
            background: transparent;
            border: none;
            padding-bottom: 3px;
            border-bottom: 1px solid {DIVIDER};
            """
        )
        return lbl

    def _addSectionHeader(self, grid: QGridLayout, row: int, text: str) -> int:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setFixedHeight(32)
        lbl.setStyleSheet(
            f"""
            color: {TEXT_SECONDARY};
            background: transparent;
            border: none;
            border-bottom: 1px solid {DIVIDER};
            padding-top: 12px;
            """
        )
        grid.addWidget(lbl, row, 0, 1, 3)
        return row + 1

    def _addNumericRow(
        self,
        grid: QGridLayout,
        row: int,
        labelText: str,
        unitText: str,
        minVal: float,
        maxVal: float,
        step: float,
        decimals: int,
    ) -> QDoubleSpinBox:
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setFixedHeight(32)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        spin = QDoubleSpinBox()
        spin.setRange(minVal, maxVal)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setFixedHeight(30)
        spin.setFont(QFont("Segoe UI", 11))
        spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        spin.setStyleSheet(
            f"""
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
            """
        )

        unitLbl = QLabel(unitText)
        unitLbl.setFont(QFont("Segoe UI", 10))
        unitLbl.setFixedHeight(32)
        unitLbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        unitLbl.setStyleSheet("color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl, row, 0)
        grid.addWidget(spin, row, 1)
        grid.addWidget(unitLbl, row, 2)
        return spin

    def _addIntRow(self, grid: QGridLayout, row: int, labelText: str, minVal: int, maxVal: int) -> QSpinBox:
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setFixedHeight(32)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        spin = QSpinBox()
        spin.setRange(minVal, maxVal)
        spin.setFixedHeight(30)
        spin.setFont(QFont("Segoe UI", 11))
        spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        spin.setStyleSheet(
            f"""
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
            """
        )

        unitLbl = QLabel("count")
        unitLbl.setFont(QFont("Segoe UI", 10))
        unitLbl.setFixedHeight(32)
        unitLbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        unitLbl.setStyleSheet("color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl, row, 0)
        grid.addWidget(spin, row, 1)
        grid.addWidget(unitLbl, row, 2)
        return spin

    def _addStringRow(self, grid: QGridLayout, row: int, labelText: str, unitText: str) -> QLineEdit:
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setFixedHeight(32)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        edit = QLineEdit()
        edit.setFixedHeight(30)
        edit.setFont(QFont("Segoe UI", 11))
        edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        edit.setPlaceholderText("—")
        edit.setStyleSheet(
            f"""
            QLineEdit {{
                background: {BG_PAGE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_CARD};
                border-radius: 7px;
                padding: 3px 9px;
            }}
            QLineEdit:focus {{ border: 1.5px solid {ACCENT_BLUE}; }}
            """
        )

        unitLbl = QLabel(unitText)
        unitLbl.setFont(QFont("Segoe UI", 10))
        unitLbl.setFixedHeight(32)
        unitLbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        unitLbl.setStyleSheet("color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl, row, 0)
        grid.addWidget(edit, row, 1)
        grid.addWidget(unitLbl, row, 2)
        return edit

    def _toggleStyle(self, isOn: bool, isDanger: bool = False) -> str:
        if isOn:
            if isDanger:
                return (
                    f"QPushButton {{ background-color: {ACCENT_RED_BG}; color: {ACCENT_RED}; "
                    f"border: 1.5px solid #FECACA; border-radius: 7px; }}"
                    f"QPushButton:hover {{ background-color: #FEE2E2; }}"
                )
            return (
                f"QPushButton {{ background-color: {ACCENT_GREEN_BG}; color: {ACCENT_GREEN}; "
                f"border: 1.5px solid #BBF7D0; border-radius: 7px; }}"
                f"QPushButton:hover {{ background-color: #DCFCE7; }}"
            )
        return (
            f"QPushButton {{ background-color: {BG_PAGE}; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {BORDER_CARD}; border-radius: 7px; }}"
            f"QPushButton:hover {{ background-color: {DIVIDER}; }}"
        )

    def _addToggleRow(self, grid: QGridLayout, row: int, labelText: str, callback) -> QPushButton:
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setFixedHeight(32)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        btn = QPushButton("OFF")
        btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn.setFixedHeight(28)
        btn.setCheckable(True)
        btn.setStyleSheet(self._toggleStyle(False))
        btn.clicked.connect(callback)

        unitLbl = QLabel("bool")
        unitLbl.setFont(QFont("Segoe UI", 10))
        unitLbl.setFixedHeight(32)
        unitLbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        unitLbl.setStyleSheet("color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl, row, 0)
        grid.addWidget(btn, row, 1)
        grid.addWidget(unitLbl, row, 2)
        return btn

    def _setToggle(self, btn: QPushButton, isOn: bool, isDanger: bool = False) -> None:
        btn.setText("ON" if isOn else "OFF")
        btn.setChecked(isOn)
        btn.setStyleSheet(self._toggleStyle(isOn, isDanger=isDanger))

    def _addOutputRow(self, grid: QGridLayout, row: int, labelText: str, unitText: str) -> QLabel:
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setFixedHeight(32)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        val = QLabel("—")
        val.setFont(QFont("Segoe UI", 11))
        val.setFixedHeight(30)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setStyleSheet(
            f"""
            color: #9CA3AF;
            background: {DIVIDER};
            border: 1px solid {BORDER_CARD};
            border-radius: 7px;
            padding: 3px 9px;
            """
        )

        unitLbl = QLabel(unitText)
        unitLbl.setFont(QFont("Segoe UI", 10))
        unitLbl.setFixedHeight(32)
        unitLbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        unitLbl.setStyleSheet("color: #9CA3AF; background: transparent; border: none; padding-left: 6px;")

        grid.addWidget(lbl, row, 0)
        grid.addWidget(val, row, 1)
        grid.addWidget(unitLbl, row, 2)
        return val

    # ── model sync ───────────────────────────────────────────────────────────

    def _sync_toggles_from_model(self) -> None:
        m = self.trainModel
        if m is None:
            return
        self._setToggle(self.brokenRailToggle, bool(m.isRailBroken))
        self._setToggle(self.trackCircuitToggle, bool(m.isTrackCircuitFailed))
        self._setToggle(self.trackPowerToggle, bool(m.isTrackPowerLost), isDanger=True)
        self._setToggle(self.serviceBrakeToggle, bool(m.isServiceBrakeOn))
        self._setToggle(self.emergencyBrakeToggle, bool(m.isEmergencyBrakeOn), isDanger=True)
        self._setToggle(self.passengerEBrakeToggle, bool(m.isPassengerEmergencyBrakeOn), isDanger=True)
        self._setToggle(self.externalLightsToggle, bool(m.areExternalLightsOn))
        self._setToggle(self.internalLightsToggle, bool(m.areInternalLightsOn))
        self._setToggle(self.rightDoorToggle, bool(m.isRightDoorOpen))
        self._setToggle(self.leftDoorToggle, bool(m.isLeftDoorOpen))

    def refreshFromModel(self) -> None:
        m = self.trainModel
        if m is None:
            return
        self.outSpeedKmh.setText(f"{m.currentSpeedKmh:.2f}")
        self.outAccel.setText(f"{m.currentAccelMps2:.3f}")
        self.outDistance.setText(f"{m.distanceTraveledKm:.3f}")
        self.outAuthority.setText(f"{m.commandedAuthorityKm:.3f}")
        self.outPassengers.setText(str(int(m.onboardPassengers)))
        self.outStation.setText(m.approachingStation or (m.beaconData or "—"))
        self.outEBrake.setText("True" if bool(m.getEmergencyBrakeStatus()) else "False")

    def pushToModel(self) -> None:
        m = self.trainModel
        if m is None:
            return
        m.commandedSpeedKmh = float(self.commandedSpeedInput.value())
        m.speedLimitKmh = float(self.speedLimitInput.value())
        m.commandedAuthorityKm = float(self.commandedAuthorityInput.value())
        m.trackGradePercent = float(self.gradeInput.value())
        m.trackAccelerationLimitKmh2 = float(self.accelLimitInput.value())
        m.trackDecelerationLimitKmh2 = float(self.decelLimitInput.value())
        m.boardingPassengerCount = int(self.passengersInput.value())
        m.cabinTemperatureC = float(self.temperatureInput.value())
        m.requestedTractionPowerW = float(self.powerCommandInput.value())
        m.beaconData = str(self.beaconDataInput.text() or "")

    def setTrainModel(self, trainModel: TrainModel) -> None:
        self.trainModel = trainModel
        self._system = None  # integrated mode should tick elsewhere
        self.pushToModel()
        self._sync_toggles_from_model()

    def _tickStandaloneSystem(self) -> None:
        # Always respect live UI values each tick.
        self.pushToModel()
        if self._system is not None:
            # Integrated-like standalone (full TrainSystem): note that TrainSystem will
            # overwrite some controller-driven fields after reading the model.
            self._system.tick(samplePeriodSec)
            return
        if self._standalone_tick and self.trainModel is not None:
            self.trainModel.tick(samplePeriodSec)

    # ── toggle handlers ──────────────────────────────────────────────────────

    def onBrokenRailToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.isRailBroken = not bool(self.trainModel.isRailBroken)
        self._setToggle(self.brokenRailToggle, bool(self.trainModel.isRailBroken))

    def onTrackCircuitToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.isTrackCircuitFailed = not bool(self.trainModel.isTrackCircuitFailed)
        self._setToggle(self.trackCircuitToggle, bool(self.trainModel.isTrackCircuitFailed))

    def onTrackPowerToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.isTrackPowerLost = not bool(self.trainModel.isTrackPowerLost)
        self._setToggle(self.trackPowerToggle, bool(self.trainModel.isTrackPowerLost), isDanger=True)

    def onServiceBrakeToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.isServiceBrakeOn = not bool(self.trainModel.isServiceBrakeOn)
        self._setToggle(self.serviceBrakeToggle, bool(self.trainModel.isServiceBrakeOn))

    def onEmergencyBrakeToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.isEmergencyBrakeOn = not bool(self.trainModel.isEmergencyBrakeOn)
        self._setToggle(self.emergencyBrakeToggle, bool(self.trainModel.isEmergencyBrakeOn), isDanger=True)

    def onPassengerEBrakeToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.isPassengerEmergencyBrakeOn = not bool(self.trainModel.isPassengerEmergencyBrakeOn)
        self._setToggle(self.passengerEBrakeToggle, bool(self.trainModel.isPassengerEmergencyBrakeOn), isDanger=True)

    def onExternalLightsToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.areExternalLightsOn = not bool(self.trainModel.areExternalLightsOn)
        self._setToggle(self.externalLightsToggle, bool(self.trainModel.areExternalLightsOn))

    def onInternalLightsToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.areInternalLightsOn = not bool(self.trainModel.areInternalLightsOn)
        self._setToggle(self.internalLightsToggle, bool(self.trainModel.areInternalLightsOn))

    def onRightDoorToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.isRightDoorOpen = not bool(self.trainModel.isRightDoorOpen)
        self._setToggle(self.rightDoorToggle, bool(self.trainModel.isRightDoorOpen))

    def onLeftDoorToggled(self) -> None:
        if self.trainModel is None:
            return
        self.trainModel.isLeftDoorOpen = not bool(self.trainModel.isLeftDoorOpen)
        self._setToggle(self.leftDoorToggle, bool(self.trainModel.isLeftDoorOpen))


def main() -> None:
    created = False
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        created = True

    # Standalone = launch BOTH:
    # - the normal Train Model UI (frontend main)
    # - this Test UI
    # Both share the same TrainModel so they stay cohesive.
    model = TrainModel()

    main_ui = TrainControlUI(trainModel=model)
    test_ui = TrainModelTestUI(trainModel=model, standalone_tick=True)

    main_ui.show()
    test_ui.show()

    # Bring the main UI to front by default.
    try:
        main_ui.raise_()
        main_ui.activateWindow()
    except Exception:
        pass

    # Only start the event loop if we created the app here.
    if created:
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

