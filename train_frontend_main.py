# ai was used for styling and layout creation of the ui

import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QGridLayout, QHBoxLayout, QVBoxLayout, QGroupBox, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPixmap

# colors used
BG_PAGE         = "#F7F8FA"
BG_CARD         = "#FFFFFF"
BG_HEADER       = "#FFFFFF"
BORDER_CARD     = "#E4E7ED"
TEXT_PRIMARY    = "#111827"
TEXT_SECONDARY  = "#6B7280"
TEXT_VALUE      = "#111827"
ACCENT_BLUE     = "#2563EB"
ACCENT_RED      = "#DC2626"
ACCENT_RED_BG   = "#FEF2F2"
ACCENT_AMBER    = "#D97706"
ACCENT_AMBER_BG = "#FFFBEB"
DIVIDER         = "#F3F4F6"
ADS_BG          = "#F0F4FF"
ADS_BORDER      = "#BFCFFF"
ADS_TEXT        = "#6B7280"


class TrainControlUI(QMainWindow):
    # Ad images to cycle through (optional). If files are missing, a text fallback is shown.
    AD_IMAGES = [
        "assets/ad_1_grimace_shake.svg",
        "assets/ad_2_duolingo.svg",
        "assets/ad_3_monster_energy.svg",
    ]

    def __init__(self, trainModel=None):
        super().__init__()

        self.trainModel       = trainModel
        self.emergencyBrakeOn = False
        self.engineFaultOn    = False
        self.brakeFaultOn     = False
        self.powerFaultOn     = False
        self.currentAdIndex   = 0

        self.setWindowTitle("Train Model")
        self.setBaseSize(1080, 800)
        self.setStyleSheet(f"background-color: {BG_PAGE};")

        central = QWidget()
        self.setCentralWidget(central)
        rootLayout = QVBoxLayout(central)
        rootLayout.setContentsMargins(0, 0, 0, 0)
        rootLayout.setSpacing(0)

        # header 
        headerFrame = QFrame()
        headerFrame.setFixedHeight(64)
        headerFrame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_HEADER};
                border-bottom: 1px solid {BORDER_CARD};}}""")
        headerLayout = QHBoxLayout(headerFrame)
        headerLayout.setContentsMargins(24, 0, 24, 0)

        titleLabel = QLabel("Train Model")
        titleLabel.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        titleLabel.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        headerLayout.addWidget(titleLabel)
        headerLayout.addStretch()

        rootLayout.addWidget(headerFrame)

        # page body 
        bodyWidget = QWidget()
        bodyWidget.setStyleSheet(f"background-color: {BG_PAGE};")
        bodyLayout = QVBoxLayout(bodyWidget)
        bodyLayout.setContentsMargins(18, 14, 18, 14)
        bodyLayout.setSpacing(14)
        rootLayout.addWidget(bodyWidget, stretch=1)

        # row 1: train info + cabin 
        topRow = QWidget()
        topRow.setStyleSheet("background: transparent;")
        topLayout = QHBoxLayout(topRow)
        topLayout.setContentsMargins(0, 0, 0, 0)
        topLayout.setSpacing(14)

        # train info card
        trainCard = self._makeCard()
        trainCardLayout = QVBoxLayout(trainCard)
        trainCardLayout.setContentsMargins(18, 14, 18, 14)
        trainCardLayout.setSpacing(0)
        trainCardLayout.addWidget(self._cardTitle("Train Info"))
        trainCardLayout.addSpacing(10)
        trainGrid = QGridLayout()
        trainGrid.setSpacing(0)
        trainGrid.setVerticalSpacing(6)
        trainGrid.setColumnStretch(0, 1)
        trainGrid.setColumnStretch(1, 1)
        trainCardLayout.addLayout(trainGrid)

        self.speedLabel      = self._addStatRow(trainGrid, 0, "Speed",        "0.00 mph")
        self.speedLimitLabel = self._addStatRow(trainGrid, 1, "Speed Limit",  "0.00 mph")
        self.stationLabel    = self._addStatRow(trainGrid, 2, "Station Info", "—")
        self.distanceLabel   = self._addStatRow(trainGrid, 3, "Distance",     "0.00 mi")
        self.authorityLabel  = self._addStatRow(trainGrid, 4, "Authority",    "0.00 mi")
        self.powerLabel      = self._addStatRow(trainGrid, 5, "Power",        "0.00 kW")
        self.accelLabel      = self._addStatRow(trainGrid, 6, "Acceleration", "0.0000 ft/s²")
        trainCardLayout.addStretch()
        topLayout.addWidget(trainCard, stretch=2)

        # cabin card 
        cabinCard = self._makeCard()
        cabinCardLayout = QVBoxLayout(cabinCard)
        cabinCardLayout.setContentsMargins(18, 14, 18, 14)
        cabinCardLayout.setSpacing(0)
        cabinCardLayout.addWidget(self._cardTitle("Cabin"))
        cabinCardLayout.addSpacing(10)
        cabinGrid = QGridLayout()
        cabinGrid.setSpacing(0)
        cabinGrid.setVerticalSpacing(6)
        cabinGrid.setColumnStretch(0, 1)
        cabinGrid.setColumnStretch(1, 1)
        cabinCardLayout.addLayout(cabinGrid)

        self.tempLabel           = self._addStatRow(cabinGrid, 0, "Temperature",        "68.0 °F")
        self.interiorLightsLabel = self._addStatRow(cabinGrid, 1, "Interior Lights",    "Off")
        self.exteriorLightsLabel = self._addStatRow(cabinGrid, 2, "Exterior Lights",    "Off")
        self.rightDoorLabel      = self._addStatRow(cabinGrid, 3, "Right Door",         "Closed")
        self.leftDoorLabel       = self._addStatRow(cabinGrid, 4, "Left Door",          "Closed")
        self.passengersLabel     = self._addStatRow(cabinGrid, 5, "Passengers On Board","0")
        cabinCardLayout.addStretch()
        topLayout.addWidget(cabinCard, stretch=2)

        bodyLayout.addWidget(topRow, stretch=3)

        # row 2: beacon data
        middleRow = QWidget()
        middleRow.setStyleSheet("background: transparent;")
        middleLayout = QHBoxLayout(middleRow)
        middleLayout.setContentsMargins(0, 0, 0, 0)
        middleLayout.setSpacing(14)

        beaconCard = self._makeCard()
        beaconCardLayout = QVBoxLayout(beaconCard)
        beaconCardLayout.setContentsMargins(18, 14, 18, 14)
        beaconCardLayout.setSpacing(0)
        beaconGrid = QGridLayout()
        beaconGrid.setSpacing(0)
        beaconGrid.setVerticalSpacing(2)
        beaconGrid.setColumnStretch(0, 1)
        beaconGrid.setColumnStretch(1, 1)
        beaconCardLayout.addLayout(beaconGrid)
        self.beaconDataLabel = self._addStatRow(beaconGrid, 0, "Beacon String", "—")
        beaconCardLayout.addStretch()
        beaconCard.setMaximumHeight(80)
        middleLayout.addWidget(beaconCard)
        bodyLayout.addWidget(middleRow, stretch=1)

        # row 3: passenger emergency brake + murphy faults
        bottomRow = QWidget()
        bottomRow.setStyleSheet("background: transparent;")
        bottomLayout = QHBoxLayout(bottomRow)
        bottomLayout.setContentsMargins(0, 0, 0, 0)
        bottomLayout.setSpacing(14)

        # passenger emergency brake card
        passengerCard = self._makeCard()
        passengerInner = QVBoxLayout(passengerCard)
        passengerInner.setContentsMargins(18, 14, 18, 14)
        passengerInner.setSpacing(10)
        passengerInner.addWidget(self._cardTitle("Passenger"))
        passengerInner.addSpacing(8)

        self.emergencyBtn = QPushButton("Emergency Brake")
        self.emergencyBtn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.emergencyBtn.setMinimumHeight(52)
        self.emergencyBtn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.emergencyBtn.setStyleSheet(self._emergencyStyle(False))
        self.emergencyBtn.clicked.connect(self.toggleEmergencyBrake)
        passengerInner.addWidget(self.emergencyBtn)
        bottomLayout.addWidget(passengerCard, stretch=2)

        # murphy faults card
        murphyCard = self._makeCard()
        murphyInner = QVBoxLayout(murphyCard)
        murphyInner.setContentsMargins(18, 14, 18, 14)
        murphyInner.setSpacing(10)
        murphyInner.addWidget(self._cardTitle("Faults (Murphy)"))
        murphyInner.addSpacing(8)

        self.engineFaultBtn = self._makeFaultBtn("Engine Fault", self.toggleEngineFault)
        self.brakeFaultBtn  = self._makeFaultBtn("Brake Fault",  self.toggleBrakeFault)
        self.powerFaultBtn  = self._makeFaultBtn("Power Fault",  self.togglePowerFault)
        murphyInner.addWidget(self.engineFaultBtn)
        murphyInner.addWidget(self.brakeFaultBtn)
        murphyInner.addWidget(self.powerFaultBtn)
        bottomLayout.addWidget(murphyCard, stretch=3)

        # ads card
        adsCard = QWidget()
        adsCard.setStyleSheet(f"""
            QWidget {{
                background-color: {ADS_BG};
                border: 2px dashed {ADS_BORDER};
                border-radius: 16px;
            }}
        """)
        adsCardLayout = QVBoxLayout(adsCard)
        adsCardLayout.setContentsMargins(18, 14, 18, 14)
        self.adsLabel = QLabel()
        self.adsLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.adsLabel.setStyleSheet("background: transparent; border: none;")
        self._updateAdImage()
        adsCardLayout.addWidget(self.adsLabel)
        bottomLayout.addWidget(adsCard, stretch=2)

        bodyLayout.addWidget(bottomRow, stretch=2)

        # timer refresh to keep ui updated
        self.refreshTimer = QTimer()
        self.refreshTimer.timeout.connect(self.refreshFromModel)
        self.refreshTimer.start(100)

        # ad cycling timer (15 second interval)
        self.adTimer = QTimer()
        self.adTimer.timeout.connect(self._cycleAd)
        self.adTimer.start(15000)

        # add doorlabel for test compatibility
        self.doorLabel = QLabel()

    # ui helpers 

    def _makeCard(self):
        # creates a white rounded card with a subtle border and shadow
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_CARD};
                border-radius: 16px;
            }}
        """)
        return card

    def _cardTitle(self, text):
        # section title label inside a card
        lbl = QLabel(text.upper())
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            letter-spacing: 1px;
            background: transparent;
            border: none;
            padding-bottom: 4px;
            border-bottom: 1px solid {DIVIDER};
        """)
        return lbl

    def _addStatRow(self, grid, row, labelText, valueText):
        # adds a greyed label + coloured value pair inside a grid layout
        lbl = QLabel(labelText)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setFixedHeight(32)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; border: none;")

        val = QLabel(valueText)
        val.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        val.setFixedHeight(32)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setStyleSheet(f"color: {TEXT_VALUE}; background: transparent; border: none;")

        grid.addWidget(lbl, row, 0)
        grid.addWidget(val, row, 1)
        return val

    def _makeFaultBtn(self, text, callback):
        # creates an inactive fault toggle button
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn.setMinimumHeight(44)
        btn.setStyleSheet(self._faultStyle(False))
        btn.clicked.connect(callback)
        return btn

    def _emergencyStyle(self, isActive):
        if isActive:
            return (f"QPushButton {{ background-color: {ACCENT_RED}; color: white; "
                    f"border: none; border-radius: 12px; font-size: 14px; }}"
                    f"QPushButton:hover {{ background-color: #B91C1C; }}")
        return (f"QPushButton {{ background-color: {ACCENT_RED_BG}; color: {ACCENT_RED}; "
                f"border: 1.5px solid #FECACA; border-radius: 12px; font-size: 14px; }}"
                f"QPushButton:hover {{ background-color: #FEE2E2; }}")

    def _faultStyle(self, isActive):
        if isActive:
            return (f"QPushButton {{ background-color: {ACCENT_AMBER_BG}; color: {ACCENT_AMBER}; "
                    f"border: 1.5px solid #FDE68A; border-radius: 12px; }}"
                    f"QPushButton:hover {{ background-color: #FEF3C7; }}")
        return (f"QPushButton {{ background-color: {BG_PAGE}; color: {TEXT_SECONDARY}; "
                f"border: 1px solid {BORDER_CARD}; border-radius: 12px; }}"
                f"QPushButton:hover {{ background-color: {DIVIDER}; color: {TEXT_PRIMARY}; }}")

    def _updateAdImage(self) -> None:
        """Load and display the current ad image (with text fallback)."""
        try:
            if 0 <= self.currentAdIndex < len(self.AD_IMAGES):
                rel = self.AD_IMAGES[self.currentAdIndex]
                ad_path = os.path.join(os.path.dirname(__file__), rel)
                if os.path.exists(ad_path):
                    pm = QPixmap(ad_path)
                    if not pm.isNull():
                        self.adsLabel.setPixmap(
                            pm.scaledToHeight(200, Qt.TransformationMode.SmoothTransformation)
                        )
                        return
        except Exception:
            pass
        self.adsLabel.setText("[ Ad Content ]")
        self.adsLabel.setFont(QFont("Segoe UI", 14))
        self.adsLabel.setStyleSheet(f"color: {ADS_BORDER}; background: transparent; border: none;")

    def _cycleAd(self) -> None:
        """Move to the next ad in the rotation."""
        if not self.AD_IMAGES:
            return
        self.currentAdIndex = (self.currentAdIndex + 1) % len(self.AD_IMAGES)
        self._updateAdImage()

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

    # refresh display from backend 

    def refreshFromModel(self):
        if not self.trainModel:
            return
        trainBackendModel = self.trainModel

        # train info — acceleration now in ft/s²
        self.speedLabel.setText("%.2f mph"    % trainBackendModel.displayCurrentSpeedMph())
        self.speedLimitLabel.setText("%.2f mph"    % trainBackendModel.displaySpeedLimitMph())
        self.distanceLabel.setText("%.2f mi"    % trainBackendModel.displayDistanceTraveledMiles())
        self.authorityLabel.setText("%.2f mi"  % trainBackendModel.displayRemainingAuthorityMiles())
        self.powerLabel.setText("%.2f kW"     % trainBackendModel.displayRequestedTractionPowerKw())
        self.accelLabel.setText("%.4f m/s²"  % trainBackendModel.displayCurrentAccelFps2())
        self.stationLabel.setText(trainBackendModel.approachingStation if trainBackendModel.approachingStation else "—")

        # cabin
        self.tempLabel.setText("%.1f °F"      % trainBackendModel.displayCabinTemperatureF())
        self.interiorLightsLabel.setText("On" if trainBackendModel.areInternalLightsOn else "Off")
        self.exteriorLightsLabel.setText("On" if trainBackendModel.areExternalLightsOn else "Off")
        self.rightDoorLabel.setText("Open" if trainBackendModel.isRightDoorOpen else "Closed")
        self.leftDoorLabel.setText("Open" if trainBackendModel.isLeftDoorOpen else "Closed")
        self.passengersLabel.setText(str(trainBackendModel.onboardPassengers))
        self.doorLabel.setText(f"Right {'Open' if trainBackendModel.isRightDoorOpen else 'Closed'}, Left {'Open' if trainBackendModel.isLeftDoorOpen else 'Closed'}")

        # beacon data — show dash when empty
        beacon = trainBackendModel.beaconData if trainBackendModel.beaconData else "—"
        self.beaconDataLabel.setText(beacon)

