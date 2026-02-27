import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

BOXSIZE = 70
TICKSPEED = 0.5
WHITPEN = QPen(QColor("WHITE"),2)
PURPPEN = QPen(QColor("purple"),2)
GRENPEN = QPen(QColor("green"),2)
YELWPEN = QPen(QColor("yellow"),2)
REDDPEN = QPen(QColor("red"),2)
BLCKPEN = QPen(QColor("black"),2)
NONEPEN = QPen(Qt.PenStyle.NoPen) #QPen(QColor("black"),0)

def div(x, y):
    return int(x/y)

def toint(b: bool) -> int:
    return 1 if b else 0

class Block:
    def __init__(self, num, type:str, dir, leng, grade, spdlim):
        self.num = int(num)
        self.type = type
        self.dir = dir
        self.grade = int(grade)
        self.is_occupied = False
        self.leng = int(leng)
        self.spdlim = int(spdlim)

        self.spd = 0
        self.auth = 0

        self.brknrail = False
        self.dsrptrck = False
        self.nopower = False

        self.isdiagup = False
        self.next = []
        self.prev = []
        
        t = self.type
        if t.find("w")!=-1:
            while True: 
                i = t.find(str(self.num))
                if i == -1: break
                if t[i+1] == "-":
                    import re
                    s = re.match(r'\d+', t[i+2:]).group(0)
                    self.next.append(s)
                else:
                    import re
                    s = re.match(r'\d+', t[i-2:]).group(0)
                    self.prev.append(s)
                t = t[i+1:]
            self.swstat = 0
            if t.find("l")!=-1:
                self.listat = "green"
            if len(self.prev) == 0 and self.num != 1: self.prev = [self.num-1]
            if len(self.next) == 0 and self.num != 15: self.next = [self.num+1] #TODO that 15
        else:
            if self.num != 1:
                self.prev = [self.num-1]
            if self.num != 10:
                self.next = [self.num+1]

        if t[0] == "c": self.crstat = False

        if t[0] == "t": 
            import random
            self.psngrs = random.randint(0,100)

    def setcard(self, c): self.card = c
    def setx(self, x): self.x = x
    def sety(self, y): self.y = y
    def occupy(self):
        self.is_occupied = True
    def deoccupy(self):
        self.is_occupied = False

    def cur_switch_option(self):
        return [self.first_switch_option(),self.second_switch_option()][self.swstat]
    def first_switch_option(self) -> tuple[int,int]: #from, to
        txt = self.type[1:self.type.find(",")]
        if "l" in self.type: txt = self.type[1:self.type.find(";")]
        return (txt[:txt.find("-")],txt[txt.find("-")+1:])
    def second_switch_option(self):
        txt = self.type[self.type.find(",")+1:]
        return (txt[:txt.find("-")],txt[txt.find("-")+1:])

class Train:
    def __init__(self, num:int, tkm):
        self.num = num
        self.relpos = 0
        self.block:Block = tkm.blocks[0]
        self.spd = 0

class TrackRectItem(QGraphicsRectItem):
    def __init__(self, scene, b: Block):
        self.block = b
        self.myx = b.x
        self.myy = b.y
        self.is_selected = False
        self.arrow = []
        super().__init__(QRectF(b.x*BOXSIZE,b.y*BOXSIZE,BOXSIZE,BOXSIZE))
        
        txt = str(b.num)
        if b.type[0] == "c": txt+="C"
        if "l" in b.type: txt += "L"
        elif b.type[0] == "w": 
            txt += "SW"
            self.otherArrow = []
        if b.type[0] == "b": txt += "B"
        if b.type[0] == "t": txt += "ST"
        
        self.text = text = QGraphicsSimpleTextItem(txt, self)
        text.setFont(QFont("Segoe UI", 12))
        text.setPos((b.x+0.5)*BOXSIZE-div(text.boundingRect().width(),2), b.y*BOXSIZE)
        text.setPen(WHITPEN)
        
        if b.card: self.drawTrack(scene)
    
    def mousePressEvent(self, event):
        b = self.block
        print(f"{str(b.num)} clicked! ({str(self.myx)},{str(self.myy)})")
        global ui; ui.display_block(b)
        ui.selectedRect = self
        self.is_selected = True
        
        self.quietlySet(ui.chckbx,b.brknrail)
        self.quietlySet(ui.chckbx1,b.dsrptrck)
        self.quietlySet(ui.chckbx2,b.nopower)

    def quietlySet(self, c:QCheckBox, state):
        c.blockSignals(True)
        c.setChecked(state)
        c.blockSignals(False)
    
    #QtGui.QBrush(QtGui.QColor("red")) will fill the whole rect

    def hoverEnterEvent(self, event): 
        self.setPen(PURPPEN)
        self.setZValue(10)

    def hoverLeaveEvent(self, event):
        if not self.is_selected:
            self.setPen(NONEPEN)
            self.setZValue(0)

    def setTrackPen(self, p:QPen, other = False):
        for x in self.otherArrow if other else self.arrow:
            if type(x) is QGraphicsPolygonItem:
                x.setBrush(p.color())
            x.setPen(p)
        self.text.setPen(p)
        
    def drawTrack(self, scene: QGraphicsScene):
        def addHead(s,e,other = False):
            (sx,sy),(ex,ey) = s,e
            import math
            size = 5
            ang = math.atan2(ey - sy, ex - sx)
            xdif, ydif = size*math.cos(ang), size*math.sin(ang)
            left  = QPointF(ex-xdif + 0.6*ydif, ey-ydif - 0.6*xdif)
            right = QPointF(ex-xdif - 0.6*ydif, ey-ydif + 0.6*xdif)
            tip   = QPointF(ex, ey)
            head = QGraphicsPolygonItem(QPolygonF([tip, left, right]))

            head.setBrush(QBrush(QColor("blue")))
            head.setPen(WHITPEN)

            if other: self.otherArrow.append(head)
            else: self.arrow.append(head)
            scene.addItem(head)
            
        sx,ex,sy,ey = [0.5]*4
        
        if self.block.card == "left" : sx,ex = 1,0
        if self.block.card == "right": sx,ex = 0,1
        if self.block.card == "up"   : sy,ey = 1,0
        if self.block.card == "down" : sy,ey = 0,1

        def addArrow(stup, etup, other = False):
            x, y = self.myx*BOXSIZE, self.myy*BOXSIZE
            sx,ex,sy,ey = [d + int(BOXSIZE*i) for d,i in zip([x,x,y,y],[stup[0],etup[0],stup[1],etup[1]])]
            
            line = QGraphicsLineItem(sx,sy,ex,ey)
            line.setPen(WHITPEN)

            if other: self.otherArrow.append(line)
            else: self.arrow.append(line)
            scene.addItem(line)
            
            addHead((sx,sy),(ex,ey), other)
            if self.block.dir == "bid":
                addHead((ex,ey),(sx,sy), other)

        if self.block.type[0] == "w":
            if "l" not in self.block.type:
                if self.block.card in ["left","right"]:
                    addArrow((sx,sy),(ex, 0))
                    addArrow((sx,sy),(ex, 1),True)#down one is always 'other'
                    self.text.setX(self.text.x()-10)
                    self.text.setY(self.text.y()+20)
                else:
                    print("an 'up' switch?")
            else:
                if self.block.isdiagup:
                    addArrow((sx,1),(ex, ey))
                else:
                    self.text.setY(self.text.y()-10)
                    self.text.setX(self.text.x()-7)
                    addArrow((sx,0),(ex, ey))
        else:
            addArrow((sx,sy),(ex,ey))

class TrackMap:
    def __init__(self, filename):
        self.height, self.width = 10, 20
        import csv
        csv_table = []
        with open(filename, newline="") as f:
            for row in csv.reader(f):
                csv_table.append(tuple(row[:6]))
        self.blocks = [Block(*b) for b in csv_table]
        self.trains = [Train(1, self), Train(2, self)]

    def analyze(self):
        blocks = self.blocks
        todo = [blocks[0]]
        while len(todo) > 0:
            b = todo.pop(0)
            if b.num == 1:
                b.setx(int(self.width*0.75))
                b.sety(int(self.height*0.5))
                b.setcard("left")
            else:
                b0 = self.find(b.prev[0])
                if b0.type[0] == "w" and b.type.find("l") != -1:
                    if b0.num == b.num - 1: 
                        b.sety(b0.y-1)
                        b.isdiagup = True
                    else: 
                        b.sety(b0.y+1)
                else: b.sety(b0.y)
                b.setx(b0.x-1) #TODO follow direction of prev
                b.setcard(b0.card)
            for n in b.next: 
                todo.insert(0, self.find(n))
                print(str(b.num)+"->"+str(n))
            print(str(b.num) +":"+str(b.x) + "," + str(b.y) + "|" + b.card)
    
    def find(self, n):
        for b in self.blocks:
            if b.num == int(n):
                return b
        return None
    
    def view(self) -> QGraphicsScene:
        self.analyze()
        
        scene = QGraphicsScene()
        
        self.items: dict[TrackRectItem,Block] = {}
        for b in self.blocks:
            it = TrackRectItem(scene, b)
            self.items[it] = b

            it.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
            it.setAcceptHoverEvents(True)
            it.setPen(NONEPEN)
            
            scene.addItem(it)

        view = QGraphicsView(scene)
        view.setGeometry(0,0,(self.width*BOXSIZE)+100,(self.height*BOXSIZE)+100)
        view.setMaximumSize(view.width(),view.height())
        return view
    
    def blockOf(self, t: Train) -> Block:
        sum = 0
        for b in self.blocks:
            sum += b.leng
            if t.relpos > sum: continue
            else: return b
    
    def update(self):
        for t in self.trains:
            #km/hr * 1hr/3600s * 1000m/1km = 10/36 m/s, and each tick is 0.5s
            if t.spd != 0: 
                t.relpos += t.spd * (10/36) * TICKSPEED

            if t.spd > 0:
                while t.relpos > t.block.leng:
                    if len(t.block.next) > 0:
                        t.block.deoccupy()
                        nex = self.blocks[int(t.block.next[t.block.swstat if t.block.type[0] == "w" and "l" not in t.block.type else 0])-1]
                        if nex.is_occupied:
                            t.relpos = t.block.leng
                            print(f"train {t.num} CRASH (occupied block)")
                            break
                        if nex.type[0] == "c" and nex.crstat:
                            t.relpos = t.block.leng
                            print(f"train {t.num} CRASH (crossing)")
                            break
                        else:
                            t.relpos -= t.block.leng
                            t.block = nex
                    else: 
                        #at the end
                        t.relpos = t.block.leng
                        break
            else:
                while t.relpos < 0:
                    if len(t.block.prev) > 0:
                        t.block.deoccupy()
                        pre = self.blocks[int(t.block.prev[0])-1]
                        if pre.is_occupied:
                            t.relpos = 0
                            print(f"train {t.num} CRASH (occupied block)")
                            break
                        if pre.type[0] == "w" and "l" not in pre.type:
                            if int(pre.cur_switch_option()[-1]) == t.block.num:
                                t.block = pre
                                t.relpos += t.block.leng
                            else: 
                                t.relpos = 0
                                print(f"train {t.num} CRASH (switch)")
                                break
                        elif pre.type[0] == "c" and pre.crstat:
                            t.relpos = 0
                            print(f"train {t.num} CRASH (crossing)")
                            break
                        else:
                            t.block = pre
                            t.relpos += t.block.leng
                    else:
                        #at the beginning
                        t.relpos = 0
                        break
            t.block.occupy()

            print(f"train {t.num} dist along block {t.block.num}: {t.relpos}")

        for b in self.blocks:
            if b.brknrail or b.dsrptrck or b.nopower:
                b.occupy()

        for it, b in self.items.items():
            it.setTrackPen(WHITPEN)

            if b.type[0] == "w": #switch
                if "l" not in b.type: #main
                    it.setTrackPen(BLCKPEN, b.swstat != 1)
                    it.setTrackPen(PURPPEN if b.is_occupied else WHITPEN, b.swstat == 1)

                else: #branch (light)
                    if b.is_occupied: it.setTrackPen(PURPPEN)
                    elif b.listat == "green": it.setTrackPen(GRENPEN)
                    elif b.listat == "yellow": it.setTrackPen(YELWPEN)
                    else: it.setTrackPen(REDDPEN)
            
            elif b.is_occupied:
                it.setTrackPen(PURPPEN)
                
            elif b.type[0] == "c": #crossing
                if b.crstat: it.setTrackPen(BLCKPEN)


class MainWindow(QWidget):
    def __init__(self, tkm:TrackMap):
        super().__init__()
        self.setWindowTitle("Train Track Model")
        self.setMinimumSize(400,400)
        self.tkm = tkm
        self.testui = TestUI(self)

    def closeEvent(self, a0):
        self.testui.hide()
        return super().closeEvent(a0)

class UIControls:
    def __init__(self, m: MainWindow):
        self.controls = QWidget()
        self.selectedRect:TrackRectItem = None
        self.m = m
        controls = self.controls
        hl = QHBoxLayout(controls)

        self.binfo = QLabel("Block info", controls)
        binfo = self.binfo
        binfo.setStyleSheet("""
            background-color: #555555;
            border: 1px solid black;
            padding: 4px;
        """)
        binfo.setGeometry(0,0,300,120)
        binfo.setMaximumSize(binfo.width(),binfo.height())
        binfo.setMinimumSize(binfo.width(),binfo.height())

        self.chckbx = c = QCheckBox("Break Block Rail")
        self.chckbx1 = c1 = QCheckBox("Disrupt Block Track Circuit")
        self.chckbx2 = c2 = QCheckBox("Cut Block Power")

        def occ():
            if self.selectedRect:
                if c.isChecked() or c1.isChecked() or c2.isChecked():
                    self.selectedRect.block.occupy()
                else:
                    self.selectedRect.block.deoccupy()
                self.selectedRect.block.brknrail = c.isChecked()
                self.selectedRect.block.dsrptrck = c1.isChecked()
                self.selectedRect.block.nopower = c2.isChecked()

        lay = QVBoxLayout(controls)

        for c0 in [c,c1,c2]:
            c0.setTristate(False)
            c0.setChecked(False)
            c0.stateChanged.connect(occ)
            lay.addWidget(c0)

        tui_btn = QPushButton("Test UI", controls); 
        tui_btn.clicked.connect(m.testui.show)

        hl.addWidget(binfo)
        hl.addLayout(lay)
        hl.addWidget(tui_btn)

    def display_block(self, b:Block):
        dir = "Bidirectional" if b.dir == "bid" else b.dir
        type:str
        if b.type[0] in "nb": type = "Track"
        if b.type[0] == "w": 
            b0 = self.m.tkm.blocks[int(b.first_switch_option()[0])-1] if "l" in b.type else b    
            chosen = b0.cur_switch_option()
            type = f"Switch (Currently {chosen[0]}→{chosen[1]})"
        if b.type[0] == "t": type = b.type[2:] + " Station"
        if b.type[0] == "c": type = "Track Crossing"
        
        self.binfo.setText(f"Directionality: {dir}"+
                           f"\nCommanded Authority: {b.auth} km"+
                           f"\nCommanded Speed: {b.spd} km/hr"+
                           f"\nGrade: {b.grade}%"+
                           f"\nSpeed Limit: {b.spdlim} km/hr"+
                           f"\nInfrastructure: {type}"+
                           f"\nOccupied: {b.is_occupied}")
    
    def update(self):
        if self.selectedRect: 
            self.display_block(self.selectedRect.block)
            for it in self.m.tkm.items.keys():
                it.is_selected = False
                if not it.isUnderMouse(): it.setPen(NONEPEN)
            self.selectedRect.setPen(PURPPEN)
            self.selectedRect.is_selected = True
        for c in [self.chckbx,self.chckbx1,self.chckbx2]: c.setEnabled(self.selectedRect != None)
    
class TestUI(QWidget):
    def __init__(self, m: MainWindow):
        super().__init__()
        
        self.myscroll = QScrollArea()
        self.myscroll.setWindowTitle("Test UI")

        self.myscroll.setWidget(self)
        self.myscroll.setWidgetResizable(True)
        
        self.uilayout = QHBoxLayout(self)

        self.inputlayout = QVBoxLayout()

        def label(words, layout):
            lbl = QLabel(words)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 18pt;")
            layout.addWidget(lbl)

        label("---From Track Controller---", self.inputlayout)
        for b in m.tkm.blocks: self.addBlockIn(b)

        label("---From Train Model---", self.inputlayout)
        for t in m.tkm.trains: self.addTrainIn(t)

        self.uilayout.addLayout(self.inputlayout)

        self.outputlayout = QVBoxLayout()

        label("---To Track Controller---", self.outputlayout)
        self.blocksout = []
        self.trainsout = []
        for b in m.tkm.blocks: self.addBlockOut(b)

        label("---To Train Model---", self.outputlayout)
        for t in m.tkm.trains: self.addTrainOut(t)

        self.uilayout.addLayout(self.outputlayout)

    def blockOut(self, b:Block)->str:
        return f"\t\t\tBlock {b.num}   \toccupancy:{b.is_occupied}\tswitch state:{b.swstat if b.type[0] == 'w' and 'l' not in b.type else 'N/A'}\tsignal state:{b.listat if b.type[0] == 'w' and 'l' in b.type else 'N/A'}"
    
    def trainOut(self, t:Train)->str:
        return f"cmd spd:{t.block.spd}   cmd auth:{t.block.auth}   cur grade:{t.block.grade}   cur spd lim:{t.block.spdlim}   isbrokenrail:{t.block.brknrail}   isbrokentrackcircuit:{t.block.dsrptrck}   hasnopower:{t.block.nopower}   num passengers:{t.block.psngrs if t.block.type[0] == 't' else 'N/A'}"

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

    def addTrainIn(self, t):
        lbl = QLabel("Train "+str(t.num)+" Speed (km/hr):\t")
        inp = QLineEdit()
        btn = QPushButton("Confirm")
        
        lbl.setMinimumHeight(30)
        inp.setMinimumHeight(20)
        btn.setMinimumHeight(20)

        def confirm():
            print(f"Train "+str(t.num)+" speed set to:"+inp.text())
            t.spd = float(inp.text())

        btn.clicked.connect(confirm)

        pertrn = QHBoxLayout()
        pertrn.addWidget(lbl)
        pertrn.addWidget(inp)
        pertrn.addWidget(btn)

        self.inputlayout.addLayout(pertrn)

    def addBlockIn(self, b: Block):
        swbox:QCheckBox = None
        swches = []
        if b.type[0] == "w" and not "l" in b.type:
            swches = [b.first_switch_option(),b.second_switch_option()]
            swbox = QCheckBox(f"Switch {swches[0][0]}-{swches[0][1]}/{swches[1][0]}-{swches[1][1]}")
            swbox.setMinimumHeight(20)
        
        sig: QFormLayout = None
        sig_ed: QLineEdit
        if "l" in b.type:
            sig_ed = QLineEdit()
            sig = QFormLayout()
            sig.addRow("Signal Color:", sig_ed)
            sig_ed.setMinimumHeight(20)

        crbox:QCheckBox = None
        if b.type[0] == "c":
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
            b.auth = inp0.text()
            b.spd = inp.text()
            if swbox:
                print(f"Block {b.num} switch set to:", swches[toint(swbox.isChecked())])
                b.swstat = toint(swbox.isChecked())
            if crbox:
                print(f"Block {b.num} crossing set to: ", "Active" if crbox.isChecked() else "Non-active")
                b.crstat = crbox.isChecked() 
            if sig:
                print(f"Block {b.num} signal set to: ", sig_ed.text())
                b.listat = sig_ed.text()

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
        for x in self.blocksout:
            x[1].setText(self.blockOut(x[0]))
        for x in self.trainsout:
            t = x[0]
            x[1].setText(self.trainOut(x[0]))

def main():
    app = QApplication(sys.argv)

    tkm = TrackMap("Book1.csv")
    window = MainWindow(tkm)

    global ui; ui = UIControls(window)

    layout = QVBoxLayout(window)
    layout.addWidget(tkm.view())
    layout.addWidget(ui.controls)

    window.show()

    def tick():
        tkm.update()
        ui.update()
        window.testui.update()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(int(TICKSPEED*1000))

    sys.exit(app.exec())

if __name__ == "__main__":
    main()