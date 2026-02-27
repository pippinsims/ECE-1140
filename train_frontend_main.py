# ai was used for styling and layout creation of the ui

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QGridLayout, QHBoxLayout, QVBoxLayout, QGroupBox, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

import train_frontend_test

#colors used.
BG_PAGE        = "#F7F8FA"
BG_CARD        = "#FFFFFF"
BG_HEADER      = "#FFFFFF"
BORDER_CARD    = "#E4E7ED"
TEXT_PRIMARY   = "#111827"
TEXT_SECONDARY = "#6B7280"
TEXT_VALUE     = "#111827"
ACCENT_BLUE    = "#2563EB"
ACCENT_RED     = "#DC2626"
ACCENT_RED_BG  = "#FEF2F2"
ACCENT_AMBER   = "#D97706"
ACCENT_AMBER_BG = "#FFFBEB"
DIVIDER        = "#F3F4F6"


def cardShadow(widget):
    # attaches a soft drop shadow to give cards depth
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(36)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(0, 0, 0, 22))
    widget.setGraphicsEffect(shadow)
    return shadow


class TrainControlUI(QMainWindow):
    def __init__(self, trainModel=None):
        super().__init__()

        self.trainModel        = trainModel
        self.emergencyBrakeOn  = False
        self.engineFaultOn     = False
        self.brakeFaultOn      = False
        self.powerFaultOn      = False

        self.setWindowTitle("Train Model")
        self.setFixedSize(1920, 1360)
        self.setStyleSheet(f"background-color: {BG_PAGE};")

        central = QWidget()
        self.setCentralWidget(central)
        rootLayout = QVBoxLayout(central)
        rootLayout.setContentsMargins(0, 0, 0, 0)
        rootLayout.setSpacing(0)

        #header
        headerFrame = QFrame()
        headerFrame.setFixedHeight(116)
        headerFrame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_HEADER};
                border-bottom: 1px solid {BORDER_CARD};
            }}
        """)
        headerLayout = QHBoxLayout(headerFrame)
        headerLayout.setContentsMargins(56, 0, 56, 0)

        titleLabel = QLabel("Train Model")
        titleLabel.setFont(QFont("Segoe UI", 30, QFont.Bold))
        titleLabel.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        headerLayout.addWidget(titleLabel)
        headerLayout.addStretch()

        rootLayout.addWidget(headerFrame)

        #page body
        bodyWidget = QWidget()
        bodyWidget.setStyleSheet(f"background-color: {BG_PAGE};")
        bodyLayout = QVBoxLayout(bodyWidget)
        bodyLayout.setContentsMargins(48, 40, 48, 40)
        bodyLayout.setSpacing(32)
        rootLayout.addWidget(bodyWidget, stretch=1)

        # train and cabin info
        topRow = QWidget()
        topRow.setStyleSheet("background: transparent;")
        topLayout = QHBoxLayout(topRow)
        topLayout.setContentsMargins(0, 0, 0, 0)
        topLayout.setSpacing(32)

        # full train info box
        trainCard = self._makeCard()
        trainCardLayout = QVBoxLayout(trainCard)
        trainCardLayout.setContentsMargins(40, 32, 40, 32)
        trainCardLayout.setSpacing(0)
        trainCardLayout.addWidget(self._cardTitle("Train Info"))
        trainCardLayout.addSpacing(24)
        trainGrid = QGridLayout()
        trainGrid.setSpacing(0)
        trainGrid.setVerticalSpacing(4)
        trainCardLayout.addLayout(trainGrid)

        self.speedLabel      = self._addStatRow(trainGrid, 0, "Speed",        "0.00 mph")
        self.speedLimitLabel = self._addStatRow(trainGrid, 1, "Speed Limit",  "0.00 mph")
        self.stationLabel    = self._addStatRow(trainGrid, 2, "Next Station", "—")
        self.distanceLabel   = self._addStatRow(trainGrid, 3, "Distance",     "0.00 mi")
        self.powerLabel      = self._addStatRow(trainGrid, 4, "Power",        "0.00 kW")
        self.accelLabel      = self._addStatRow(trainGrid, 5, "Acceleration", "0.00 ft/s²")
        topLayout.addWidget(trainCard, stretch=3)

        # cabin info box
        cabinCard = self._makeCard()
        cabinCardLayout = QVBoxLayout(cabinCard)
        cabinCardLayout.setContentsMargins(40, 32, 40, 32)
        cabinCardLayout.setSpacing(0)
        cabinCardLayout.addWidget(self._cardTitle("Cabin"))
        cabinCardLayout.addSpacing(24)
        cabinGrid = QGridLayout()
        cabinGrid.setSpacing(0)
        cabinGrid.setVerticalSpacing(4)
        cabinCardLayout.addLayout(cabinGrid)

        self.tempLabel           = self._addStatRow(cabinGrid, 0, "Temperature",     "68.0 °F")
        self.interiorLightsLabel = self._addStatRow(cabinGrid, 1, "Interior Lights", "Off")
        self.exteriorLightsLabel = self._addStatRow(cabinGrid, 2, "Exterior Lights", "Off")
        self.doorLabel           = self._addStatRow(cabinGrid, 3, "Doors",           "Closed")
        cabinCardLayout.addStretch()
        topLayout.addWidget(cabinCard, stretch=2)

        bodyLayout.addWidget(topRow, stretch=3)

        #murphy and emergency brake input boxes
        bottomRow = QWidget()
        bottomRow.setStyleSheet("background: transparent;")
        bottomLayout = QHBoxLayout(bottomRow)
        bottomLayout.setContentsMargins(0, 0, 0, 0)
        bottomLayout.setSpacing(32)

        # passenger box
        passengerCard = self._makeCard()
        passengerInner = QVBoxLayout(passengerCard)
        passengerInner.setContentsMargins(40, 32, 40, 32)
        passengerInner.setSpacing(20)
        passengerInner.addWidget(self._cardTitle("Passenger"))
        passengerInner.addSpacing(8)

        self.emergencyBtn = QPushButton("Emergency Brake")
        self.emergencyBtn.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.emergencyBtn.setMinimumHeight(96)
        self.emergencyBtn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.emergencyBtn.setStyleSheet(self._emergencyStyle(False))
        self.emergencyBtn.clicked.connect(self.toggleEmergencyBrake)
        passengerInner.addWidget(self.emergencyBtn)
        bottomLayout.addWidget(passengerCard, stretch=2)

        # murphy faults box
        murphyCard = self._makeCard()
        murphyInner = QVBoxLayout(murphyCard)
        murphyInner.setContentsMargins(40, 32, 40, 32)
        murphyInner.setSpacing(20)
        murphyInner.addWidget(self._cardTitle("Faults (Murphy)"))
        murphyInner.addSpacing(8)

        self.engineFaultBtn = self._makeFaultBtn("Engine Fault",  self.toggleEngineFault)
        self.brakeFaultBtn  = self._makeFaultBtn("Brake Fault",   self.toggleBrakeFault)
        self.powerFaultBtn  = self._makeFaultBtn("Power Fault",   self.togglePowerFault)
        murphyInner.addWidget(self.engineFaultBtn)
        murphyInner.addWidget(self.brakeFaultBtn)
        murphyInner.addWidget(self.powerFaultBtn)
        bottomLayout.addWidget(murphyCard, stretch=3)

        bodyLayout.addWidget(bottomRow, stretch=2)

        # timer refresh to keep ui updated
        self.refreshTimer = QTimer()
        self.refreshTimer.timeout.connect(self.refreshFromModel)
        self.refreshTimer.start(100)

    # ui helpers

    def _makeCard(self):
        # creates a white rounded card with a subtle border and shadow
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_CARD};
                border-radius: 24px;
            }}
        """)
        cardShadow(card)
        return card

    def _cardTitle(self, text):
        # section title label inside a card
        lbl = QLabel(text.upper())
        lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            letter-spacing: 2px;
            background: transparent;
            border: none;
            padding-bottom: 4px;
            border-bottom: 1px solid {DIVIDER};
        """)
        return lbl

    def _addStatRow(self, grid, row, labelText, valueText):
        # adds a greyed label + coloured value pair inside a grid layout
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 20))
        lbl.setFixedHeight(72)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        val = QLabel(valueText)
        val.setFont(QFont("Segoe UI", 20, QFont.Bold))
        val.setFixedHeight(72)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setStyleSheet(f"color: {TEXT_VALUE}; background: transparent; border: none;")

        grid.addWidget(lbl, row, 0)
        grid.addWidget(val, row, 1)
        return val

    def _makeFaultBtn(self, text, callback):
        # creates an inactive fault toggle button
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 20, QFont.Bold))
        btn.setMinimumHeight(76)
        btn.setStyleSheet(self._faultStyle(False))
        btn.clicked.connect(callback)
        return btn

    def _emergencyStyle(self, isActive):
        # css for the emergency brake button
        if isActive:
            return (f"QPushButton {{ background-color: {ACCENT_RED}; color: white; "
                    f"border: none; border-radius: 16px; font-size: 22px; }}"
                    f"QPushButton:hover {{ background-color: #B91C1C; }}")
        return (f"QPushButton {{ background-color: {ACCENT_RED_BG}; color: {ACCENT_RED}; "
                f"border: 1.5px solid #FECACA; border-radius: 16px; font-size: 22px; }}"
                f"QPushButton:hover {{ background-color: #FEE2E2; }}")

    def _faultStyle(self, isActive):
        # css for fault toggle buttons
        if isActive:
            return (f"QPushButton {{ background-color: {ACCENT_AMBER_BG}; color: {ACCENT_AMBER}; "
                    f"border: 1.5px solid #FDE68A; border-radius: 12px; }}"
                    f"QPushButton:hover {{ background-color: #FEF3C7; }}")
        return (f"QPushButton {{ background-color: {BG_PAGE}; color: {TEXT_SECONDARY}; "
                f"border: 1px solid {BORDER_CARD}; border-radius: 12px; }}"
                f"QPushButton:hover {{ background-color: {DIVIDER}; color: {TEXT_PRIMARY}; }}")

    # toggles

    def toggleEmergencyBrake(self):
        self.emergencyBrakeOn = not self.emergencyBrakeOn
        self.emergencyBtn.setStyleSheet(self._emergencyStyle(self.emergencyBrakeOn))
        if self.trainModel:
            self.trainModel.isPassengerEmergencyBrakeOn = self.emergencyBrakeOn

    def toggleEngineFault(self):
        self.engineFaultOn = not self.engineFaultOn
        self.engineFaultBtn.setStyleSheet(self._faultStyle(self.engineFaultOn))
        if self.trainModel:
            self.trainModel.hasEngineFault = self.engineFaultOn

    def toggleBrakeFault(self):
        self.brakeFaultOn = not self.brakeFaultOn
        self.brakeFaultBtn.setStyleSheet(self._faultStyle(self.brakeFaultOn))
        if self.trainModel:
            self.trainModel.hasBrakeFault = self.brakeFaultOn

    def togglePowerFault(self):
        self.powerFaultOn = not self.powerFaultOn
        self.powerFaultBtn.setStyleSheet(self._faultStyle(self.powerFaultOn))
        if self.trainModel:
            self.trainModel.hasPowerFault = self.powerFaultOn

    # refreshes ui to match backend caluclations

    def refreshFromModel(self):
        if not self.trainModel:
            return
        m = self.trainModel
        self.speedLabel.setText("%.2f mph"   % m.displayCurrentSpeedMph())
        self.speedLimitLabel.setText("%.2f mph"   % m.displaySpeedLimitMph())
        self.distanceLabel.setText("%.2f mi"   % m.displayDistanceTraveledMiles())
        self.powerLabel.setText("%.2f kW"    % m.displayRequestedTractionPowerKw())
        self.accelLabel.setText("%.4f m/s²" % m.displayCurrentAccelMps2())
        self.tempLabel.setText("%.1f °F"    % m.displayCabinTemperatureF())
        self.interiorLightsLabel.setText("On" if m.areInternalLightsOn else "Off")
        self.exteriorLightsLabel.setText("On" if m.areExternalLightsOn else "Off")
        self.stationLabel.setText(m.approachingStation if m.approachingStation else "—")

        # door status from individual door states
        if m.isLeftDoorOpen and m.isRightDoorOpen:
            self.doorLabel.setText("Both Open")
        elif m.isLeftDoorOpen:
            self.doorLabel.setText("Left Open")
        elif m.isRightDoorOpen:
            self.doorLabel.setText("Right Open")
        else:
            self.doorLabel.setText("Closed")

    def setTrainModel(self, trainModel):
        self.trainModel = trainModel


def main():
    app = QApplication(sys.argv)
    w = TrainControlUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()