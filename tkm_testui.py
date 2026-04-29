from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import track_model as tkm

class TestUI(QWidget):
    def __init__(self, m: tkm.MainWindow):
        super().__init__()
        
        self.myscroll = QScrollArea()
        self.myscroll.setWindowTitle("Test UI")

        self.myscroll.setWidget(self)
        self.myscroll.setWidgetResizable(True)
        
        self.uilayout = QHBoxLayout(self)

        self.inputlayout = QVBoxLayout()

        self.curtrains:dict[tkm.Train,QHBoxLayout] = {}
        self.m = m

        def label(words, layout):
            lbl = QLabel(words)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 18pt;")
            layout.addWidget(lbl)

        label("---From Track Controller---", self.inputlayout)
        for b in m.tkm.blocks: self.addBlockIn(b)

        label("---From Train Model---", self.inputlayout)
        # for t in m.tkm.trains: self.addTrainIn(t)

        self.uilayout.addLayout(self.inputlayout)

        self.outputlayout = QVBoxLayout()

        label("---To Track Controller---", self.outputlayout)
        self.blocksout = []
        self.trainsout = []
        for b in m.tkm.blocks: self.addBlockOut(b)

        label("---To Train Model---", self.outputlayout)
        for t in m.tkm.trains: self.addTrainOut(t)

        self.uilayout.addLayout(self.outputlayout)

    def blockOut(self, b:tkm.Block)->str: return f"\t\t\tBlock {b.num}   \toccupancy:{b.is_occupied}\tswitch state:{b.switch_state if b.is_main_switch() else 'N/A'}\tsignal state:{b.light_state if b.is_branch_switch() else 'N/A'}"
    
    def trainOut(self, t:tkm.Train)->str: return f"cmd spd:{t.block.speed}   cmd auth:{t.block.authority}   cur grade:{t.block.grade}   cur spd lim:{t.block.speed_limit}   isbrokenrail:{t.block.brknrail}   isbrokentrackcircuit:{t.block.dsrptrck}   hasnopower:{t.block.nopower}   num passengers:{t.block.tickets if t.block.is_station() else 'N/A'}"

    def addTrainOut(self, t):
        pertrn = QHBoxLayout()
        lbl = QLabel(self.trainOut(t))
        lbl.setFont(QFont("Segoe UI", 12))
        self.trainsout += [(t, lbl)]

        pertrn.addWidget(lbl)

        self.outputlayout.addLayout(pertrn)
        #TODO decel lim
        #TODO accel lim

    def addBlockOut(self, b):
        perblk = QHBoxLayout()
        lbl = QLabel(self.blockOut(b))
        lbl.setFont(QFont("Segoe UI", 12))
        self.blocksout += [(b, lbl)]

        perblk.addWidget(lbl)

        self.outputlayout.addLayout(perblk)

    def remTrainIn(self, t: tkm.Train):
        l = self.curtrains.pop(t)
        if l:            
            while l.count():
                it = l.takeAt(0)
                if it.widget(): it.widget().deleteLater()
            l.deleteLater()


    def addTrainIn(self, t: tkm.Train):
        lbl = QLabel("Train "+str(t.num)+" Speed (km/hr):\t")
        inp = QLineEdit()
        btn = QPushButton("Confirm")
        
        lbl.setMinimumHeight(30)
        inp.setMinimumHeight(20)
        btn.setMinimumHeight(20)

        def confirm():
            print(f"Train "+str(t.num)+" speed set to:"+inp.text())
            t.speed = float(inp.text())

        btn.clicked.connect(confirm)

        pertrn = QHBoxLayout()
        pertrn.addWidget(lbl)
        pertrn.addWidget(inp)
        pertrn.addWidget(btn)

        self.inputlayout.addLayout(pertrn)

        self.curtrains[t] = pertrn

    def addBlockIn(self, b: tkm.Block):
        swbox:QCheckBox = None
        switches = []
        if b.is_main_switch():
            switches = [b.first_switch_option(),b.second_switch_option()]
            swbox = QCheckBox(f"Switch {switches[0][0]}-{switches[0][1]}/{switches[1][0]}-{switches[1][1]}")
            swbox.setMinimumHeight(20)
        
        sig: QFormLayout = None
        sig_ed: QLineEdit
        if b.has_light():
            sig_ed = QLineEdit()
            sig = QFormLayout()
            sig.addRow("Signal Color:", sig_ed)
            sig_ed.setMinimumHeight(20)

        crbox:QCheckBox = None
        if b.is_crossing():
            crbox = QCheckBox("Crossing Active")
            crbox.setMinimumHeight(20)

        authlbl = QLabel("Block "+str(b.num) + " Authority, Speed (km, km/hr):\t")
        inp0 = QLineEdit()
        inp = QLineEdit()
        btn = QPushButton("Confirm")
        
        authlbl.setMinimumHeight(30)
        inp0.setMinimumHeight(20)
        inp.setMinimumHeight(20)
        btn.setMinimumHeight(20)

        def confirm():
            print(f"Block {b.num} auth set to:", inp0.text())
            print(f"Block {b.num} spd set to:", inp.text())
            b.authority = inp0.text()
            b.speed = inp.text()
            if swbox:
                print(f"Block {b.num} switch set to:", switches[tkm.to_int(swbox.isChecked())])
                b.switch_state = tkm.to_int(swbox.isChecked())
                print(f"{b.num} switched to {[b.chosen_prev(),b.chosen_next()]}")
            if crbox:
                print(f"Block {b.num} crossing set to: ", "Active" if crbox.isChecked() else "Non-active")
                b.crossing_state = crbox.isChecked() 
            if sig:
                print(f"Block {b.num} signal set to: ", sig_ed.text())
                b.light_state = sig_ed.text()

        btn.clicked.connect(confirm)

        perblk = QHBoxLayout()
        perblk.addWidget(authlbl)
        perblk.addWidget(inp0)
        perblk.addWidget(inp)
        if swbox: perblk.addWidget(swbox)
        if crbox: perblk.addWidget(crbox)
        if sig: perblk.addLayout(sig)
        perblk.addWidget(btn)

        # this causes perblk to have the same spacing rule as inputlayout, also adds it to inputlayout like a widget
        self.inputlayout.addLayout(perblk)

    def show(self):
        self.myscroll.show()
        return super().show()

    def hide(self):
        self.myscroll.hide()
        return super().hide()
    
    def update(self):
        if len(self.m.tkm.trains) != len(self.curtrains):
            for x in [x for x in self.curtrains.keys() if x not in self.m.tkm.trains]: self.remTrainIn(x)
            for x in [x for x in self.m.tkm.trains if x not in self.curtrains.keys()]: self.addTrainIn(x)
        for x in self.blocksout: x[1].setText(self.blockOut(x[0]))
        for x in self.trainsout: x[1].setText(self.trainOut(x[0]))