import track_model as tkm
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

app = QApplication(sys.argv)

widget = tkm.make_widget()
widget.show()

class Counter():
    def __init__(self):
        self.count = 0
    def tick(self):
        self.count += 1

c = Counter()

def tick(c:Counter):
    widget.tkm.update()
    widget.ui.update()
    widget.testui.update()

    trains = widget.tkm.trains
    block = widget.tkm.block

    if c.count == 0:
        trains.append(tkm.Train(1, widget.tkm))
        b = block(1) 
        b.switch_state = 0
        trains[0].block = b #Block 1 is set up to crash into block 13
        trains[0].speed = 1000.0

    if c.count == 4:
        trains[0].block = block(18)
        trains[0].pos_on_b = 0
        block(1).deoccupy()
        block(19).crossing_state = 1 #deactivate crossing

    if c.count == 10:
        trains[0].block = block(14)
        trains[0].pos_on_b = 0
        block(18).deoccupy()
        block(15).occupy()

    if c.count == 16: sys.exit()

    c.tick()

timer = QTimer()
timer.timeout.connect(lambda:tick(c))
timer.start(int(tkm.TICKSPEED*1000))

sys.exit(app.exec())