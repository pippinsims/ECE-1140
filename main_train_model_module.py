# ai was used to help with code development.

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from train_backend import TrainModel
from train_frontend_main import TrainControlUI
from train_frontend_test import TrainModelTestUI


def main():
    app = QApplication(sys.argv)  # to allow app to run

    # tie the model in with the backend that was made
    model = TrainModel()

    mainUI = TrainControlUI(trainModel=model)
    testUI = TrainModelTestUI(trainModel=model)

    mainUI.show()
    testUI.show()

    # artificial timer was made to simulate time so speed, accel, etc. could change as time passes
    simTimer = QTimer()
    simTimer.timeout.connect(model.tick)
    simTimer.start(100)  # 100 ms matches samplePeriodSec in the backend

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()