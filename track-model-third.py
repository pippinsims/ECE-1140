import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import os

BOXSIZE = 70
TICKSPEED = 0.1
WHITPEN = QPen(QColor("white"),2)
PURPPEN = QPen(QColor("red"),2)
BLCKPEN = QPen(QColor("black"),2)
NONEPEN = QPen(Qt.PenStyle.NoPen) #QPen(QColor("black"),0)

def div(x, y):
    return int(x/y)

def to_int(b: bool) -> int:
    return 1 if b else 0

def first_int_in(s: str) -> int:
    import re
    return re.match(r'\d+', s).group(0)

def remall(x, l: list) -> list:
    import copy; c = copy.deepcopy(l)
    for i in c: 
        if i == x: c.remove(x)
    return c

def sign(b: bool)->int: return 1 if b else -1

def pixmap(name: str, color: str) -> QPixmap:
    p = QPixmap(f"{os.path.dirname(__file__)}\\{name}.png").scaled(32, 32)
    t = QPixmap(p.size())
    t.fill(Qt.GlobalColor.transparent)

    q = QPainter(t)
    q.drawPixmap(0, 0, p)
    q.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    q.fillRect(t.rect(), QColor(color))
    q.end()

    return t

class Block:
    def __init__(self, num, type:str, dir, leng, grade, spdlim):
        self.num = int(num)
        self.type = type
        self.directionality = dir
        self.grade = float(grade)
        self.is_occupied = False
        self.mylength = float(leng)
        self.speed_limit = int(spdlim)

        self.speed = 0
        self.authority = 0

        self.brknrail = False
        self.dsrptrck = False
        self.nopower = False

        self.isdownward = False
        self.next = []
        self.prev = []
        
        t = self.type

        #if 3 connections, if missing a neighbor, that is the unknown connection (i think 3way is always missing a neighbor)
        #if 2 connections, the unknown connection is the neighbor on that side (prev <, next >)
        if self.is_switch():
            self.switch_state = 0
            import re
            a = [int(i) for i in re.findall(r'\d+',t)] #array of all digit sequences in t
            n = self.num

            if len(a) == 2:
                if a[0] == n:
                    self.next = [a[1]]
                    self.prev = [n-1]
                else:
                    self.prev = [a[0]]
                    self.next = [n+1]
            if len(a) == 4:
                #  a[0]
                #   \ 
                #    [n]---x
                #   /
                #  a[2]
                # one known is a neighbor. x = the other neighbor
                other_neighbor = n+1 if n-1 in a else n-1

                if a[1] == n and a[3] == n:
                    self.prev = remall(n,a)
                    self.next = [other_neighbor]
                elif a[0] == n and a[3] == n:
                    self.next.append(a[1])
                    self.prev.append(a[2])
                    if abs(a[1] - n) == 1: 
                        self.prev.append(other_neighbor)
                    else:
                        self.next.append(other_neighbor)
                elif a[1] == n and a[2] == n:
                    self.next.append(a[3])
                    self.prev.append(a[0])
                    if abs(a[3] - n) == 1: 
                        self.prev.append(other_neighbor)
                    else:
                        self.next.append(other_neighbor)
                elif a[0] == n and a[2] == n:
                    self.next = remall(n,a)
                    self.prev = [other_neighbor]
                
                # if self.num in [15,10]: self.next = []
                # if self.num == 1: self.prev = []
                
                #
                #[5,6,5,11]
                #   |
                #  \ /
                #   V
                #p=[4] n=[6,11]
                #
                #[from, to ,from, to ]
                #  |    |    |    |
                #[self,othr,self,othr]
                #[self,othr,othr,self]
                #[othr,self,self,othr]
                #[othr,self,othr,self]
        else:
            if self.directionality in "+b":
                self.prev.append(self.num-1)
                self.next.append(self.num+1)
            else:
                self.prev.append(self.num+1)
                self.next.append(self.num-1)

        #     if self.num != 1: self.prev.append(self.num-1)
        #     if self.num not in [10, 15]: self.next.append(self.num+1)
        
        if self.has_light(): self.light_state = "green"
            
        if self.is_crossing(): self.crossing_state = False

        if self.is_station(): 
            self.tickets = 0
            self.num_boarding = 0
            self.num_standing = 0
            self.gentickets()

        print(f"Block {self.num} init!")
        print(f"next:{self.next}")
        print(f"prev:{self.prev}")
        print(f"type:{self.type}")
        print(f"tokens:{self.tokens()}")
    
    def tokens           (self) -> list[str]: return self.type.split(";")
    def is_switch        (self) -> bool: return len([x for x in self.tokens() if x[0] == "w"]) > 0
    def is_station       (self) -> bool: return len([x for x in self.tokens() if x[0] == "t"]) > 0
    def is_beacon        (self) -> bool: return len([x for x in self.tokens() if x[0] == "b"]) > 0
    def is_main_switch   (self) -> bool: return self.is_switch() and "l" not in self.tokens()
    def is_branch_switch (self) -> bool: return self.is_switch() and "l" in self.tokens()
    def has_light        (self) -> bool: return self.is_beacon() or self.is_branch_switch()
    def is_crossing      (self) -> bool: return "c" in self.tokens()
    def is_tunnel        (self) -> bool: return "u" in self.tokens()

    def station_name(self) -> str: return [x for x in self.tokens() if x[0] == "t"][0].split(",")[1]

    def first_switch_option(self) -> tuple[int,int]: #from,to
        tok = [x for x in self.tokens() if x[0] == "w"][0][1:]
        if "," in tok: return tok.split(",")[0].split("-")
        else: return tok.split("-")
    def second_switch_option(self) -> tuple[int,int]: #from,to
        tok = [x for x in self.tokens() if x[0] == "w"][0][1:]
        return tok.split(",")[1].split("-")

    def cur_switch_option(self):
        return [self.first_switch_option(),self.second_switch_option()][self.switch_state]
    
    def top_next(self):
        n = []+self.next
        ops = self.first_switch_option()+self.second_switch_option()
        ops = [int(x) for x in ops if x != str(self.num)]
        
        if set(ops) != set(n):
            for x in ops:
                if x in n:
                    n.remove(x)
                    return n[0]
        else:
            return ops[0]
    
    def bot_next(self):
        for x in self.next:
            if x != self.top_next(): return x

    def top_prev(self):
        p = []+self.prev
        ops = self.first_switch_option()+self.second_switch_option()
        ops = [int(x) for x in ops if x != str(self.num)]

        if set(ops) != set(p):
            for x in ops:
                if x in p:
                    p.remove(x)
                    return p[0]
        else:
            return ops[0]
    
    def bot_prev(self):
        for x in self.prev:
            if x != self.top_prev(): return x

    def chosen_next(self):
        if len(self.next) > 1:
            check = [int(x) for x in self.cur_switch_option() if x != str(self.num)][0]
            if check in self.next:
                return check
            else:
                unwanted = [int(x) for x in self.first_switch_option()+self.second_switch_option() if x != str(self.num) and x != str(check)][0]
                return [x for x in self.next if x != unwanted][0]
        else:
            return self.next[0]
    def chosen_prev(self):
        if len(self.prev) > 1:
            check = [int(x) for x in self.cur_switch_option() if x != str(self.num)][0]
            if check in self.prev: return check
            else:
                unwanted = [int(x) for x in self.first_switch_option()+self.second_switch_option() if x != str(self.num) and x != str(check)][0]
                return [x for x in self.prev if x != unwanted][0]
        else:
            return self.prev[0]
    
    def gentickets(self):
        import random
        self.num_boarding = random.randint(0,100)
        self.tickets = random.randint(self.num_boarding,100)
        self.num_standing += self.tickets
        print(f"there were {self.tickets} more sales!")
        print(f"{self.num_standing} are standing")
    
    def beacondata(self)->str:
        return self.type[2:] if self.is_beacon() else None
    
    # def setcard(self, c): self.card = c
    def setx(self, x): self.x = x
    def sety(self, y): self.y = y
    def occupy(self):
        self.is_occupied = True
    def deoccupy(self):
        self.is_occupied = False

class Train:
    def __init__(self, num:int, tkm):
        self.dir = "+"
        self.num = num
        self.pos_on_b = 0
        self.block:Block = tkm.blocks[0]
        self.speed = 0
        self.num_riding = 0
        self.beacon = ''

    def update(self):
        if self.block.nopower: print("NO POWER TO TRAIN!")
        if self.block.is_station(): self.board()
        if self.block.is_beacon():
            print(f"block {self.block.num} beacondata:'{self.block.beacondata()}'")
            self.beacon = self.block.beacondata()
    
    def board(self):
        import random
        r = random.randint(0, self.num_riding)
        self.num_riding -= r
        self.block.num_standing += r
        print(f"{r} got off of the train")
        print(f"{self.block.num_standing} are standing")

        self.block.num_standing -= self.block.num_boarding
        self.num_riding += self.block.num_boarding
        print(f"{self.block.num_boarding} got on the train")
        print(f"{self.block.num_standing} are standing")

        self.block.gentickets()

        if ui.selectedRect and ui.selectedRect.block == self.block: ui.display_block(self.block)

#TODO test ui should receive the actual output type of the tkc not strings/ints.
#make TrackMap.build() work for the Green and Red lines
#CORRECT THE UNITS

class TrackRectItem(QGraphicsRectItem):
    def __init__(self, scene: QGraphicsScene, b: Block):
        self.block = b
        self.myx = b.x
        self.myy = b.y
        self.is_selected = False
        self.upArrow = []
        super().__init__(QRectF(b.x*BOXSIZE,b.y*BOXSIZE,BOXSIZE,BOXSIZE))
        
        self.ic1 = scene.addPixmap(QPixmap())
        self.ic2 = scene.addPixmap(QPixmap())
        self.ic3 = scene.addPixmap(QPixmap())

        txt = str(b.num)
        if b.is_crossing(): self.ic2 = scene.addPixmap(pixmap('railroad-crossing','white'))
        if b.has_light  (): self.ic2 = scene.addPixmap(pixmap('traffic-light','white'))
        elif b.is_switch(): self.downArrow = []
        if b.is_station (): self.ic2 = scene.addPixmap(pixmap('building','white'))
        if b.is_beacon  (): self.ic3 = scene.addPixmap(pixmap('beacon','white'))
        
        self.ic1.setPos((b.x      )*BOXSIZE, b.y     *BOXSIZE)
        self.ic2.setPos((b.x + 0.5)*BOXSIZE, b.y     *BOXSIZE)
        self.ic3.setPos((b.x + 0.5)*BOXSIZE,(b.y+0.5)*BOXSIZE)
        
        self.text = text = QGraphicsSimpleTextItem(txt, self)
        text.setFont(QFont("Segoe UI", 12))
        if b.is_main_switch(): text.setPos((b.x+0.5 )*BOXSIZE-div(text.boundingRect().width(),2),  b.y     *BOXSIZE)
        else:                  text.setPos((b.x+0.25)*BOXSIZE-div(text.boundingRect().width(),2), (b.y+0.5)*BOXSIZE)
        text.setPen(WHITPEN)

        # if b.card: 
        self.drawTrack(scene)
    
    def mousePressEvent(self, event):
        b = self.block
        print(f"{str(b.num)} clicked! ({str(self.myx)},{str(self.myy)})")
        global ui 
        ui.display_block(b)
        ui.selectedRect = self
        self.is_selected = True
        
        self.quietlySet(ui.chkbrk  ,b.brknrail)
        self.quietlySet(ui.chkcirc ,b.dsrptrck)
        self.quietlySet(ui.chkpower,b.nopower)

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

    def update(self):
        self.train_icon(None)
        b = self.block

        if b.is_main_switch():
            self.setTrack(WHITPEN, b.switch_state == 1)
            self.setTrack(BLCKPEN, b.switch_state != 1)
        else:
            self.setTrack(WHITPEN)
                            
        if b.has_light(): self.light_icon(b.light_state)
        if b.is_occupied: self.train_icon("white")
        if b.is_crossing() and b.crossing_state: self.setTrack(BLCKPEN)

    def train_icon   (self, color): self.ic1.setPixmap(pixmap('train',            color) if color else QPixmap())
    def crossing_icon(self, color): self.ic2.setPixmap(pixmap('railroad-crossing',color) if color else QPixmap())
    def station_icon (self, color): self.ic2.setPixmap(pixmap('building',         color) if color else QPixmap())
    def light_icon   (self, color): self.ic2.setPixmap(pixmap('traffic-light',    color) if color else QPixmap())
    def beacon_icon  (self, color): self.ic3.setPixmap(pixmap('beacon',           color) if color else QPixmap())

    def setTrack(self, p:QPen, downward = False):
        for x in self.downArrow if downward else self.upArrow:
            if type(x) is QGraphicsPolygonItem:
                x.setBrush(p.color())
            x.setPen(p)
        if self.block.is_crossing():
            self.crossing_icon('black' if p == BLCKPEN else 'white')
            self.text.setPen(p)
        
    def drawTrack(self, scene: QGraphicsScene):
        def addHead(s,e,downward = False):
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

            if downward: self.downArrow.append(head)
            else: self.upArrow.append(head)
            scene.addItem(head)
            
        sx,ex,sy,ey = [0.5]*4
        
        # if self.block.card == "left" : 
        sx,ex = 1,0
        # if self.block.card == "right": sx,ex = 0,1
        # if self.block.card == "up"   : sy,ey = 1,0
        # if self.block.card == "down" : sy,ey = 0,1

        def addArrow(stup, etup, downward = False):
            x, y = self.myx*BOXSIZE, self.myy*BOXSIZE
            sx,ex,sy,ey = [d + int(BOXSIZE*i) for d,i in zip([x,x,y,y],[stup[0],etup[0],stup[1],etup[1]])]
            
            line = QGraphicsLineItem(sx,sy,ex,ey)
            line.setPen(WHITPEN)

            if downward: self.downArrow.append(line)
            else: self.upArrow.append(line)
            scene.addItem(line)
            
            addHead((sx,sy),(ex,ey), downward)
            if self.block.directionality == "b":
                addHead((ex,ey),(sx,sy), downward)

        #TODO factor in directionality

        # if self.block.is_switch():
        if self.block.is_main_switch():
            #next 
            # \ __ from
            # /
            #next
            #    or
            #      from
            #next __ / 
            #        \
            #      from
            self.text.setX(self.text.x()-10)
            self.text.setY(self.text.y()+20)

            b = self.block
            
            if len(self.block.next) > 1:
                addArrow((sx,sy),(ex, 0))
                addArrow((sx,sy),(ex, 1),True)
                u,d = self.block.top_next(),self.block.bot_next()
                plus = -0.25
            else:
                addArrow((0,0.5),(1,0))
                addArrow((0,0.5),(1,1),True)
                u,d = self.block.top_prev(),self.block.bot_prev()
                plus = 0.25

            self.upbranchtext = ut = QGraphicsSimpleTextItem(str(u) if u > 0 else "Y", self)
            ut.setFont(QFont("Segoe UI", 12))
            ut.setPos((b.x+0.5+plus)*BOXSIZE-div(ut.boundingRect().width(),2),b.y*BOXSIZE-10)
            ut.setPen(WHITPEN)
            
            self.dnbranchtext = dt = QGraphicsSimpleTextItem(str(d) if d > 0 else "Y", self)
            dt.setFont(QFont("Segoe UI", 12))
            dt.setPos((b.x+0.5+plus)*BOXSIZE-div(dt.boundingRect().width(),2),b.y*BOXSIZE+50)
            dt.setPen(WHITPEN)
        # else:
        #     if self.block.isdownward:
        #         self.text.setY(self.text.y()-10)
        #         self.text.setX(self.text.x()-7)
        #         addArrow((sx,0),(ex, ey))
        #     else:
        #         addArrow((sx,1),(ex, ey))
        else:
            
            if self.block.directionality in "+bs":
                addArrow((sx,sy),(ex,ey))
            else:
                addArrow((ex,ey),(sx,sy))

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

    def build(self):
        for b in self.blocks:
            if b.num == 0: 
                b.setx(10)
                b.sety(10)
            elif b.num == 1:
                b.setx(int(self.width*0.75))
                b.sety(int(self.height*0.5))
            elif b.num == 2:
                b.setx(int(self.width*0.75))
                b.sety(int(self.height*0.5)+2)
            else:
                print(b.directionality)
                if b.directionality in "+bs": b0 = self.block(min(b.prev))
                else:                         b0 = self.block(min(b.next))
                if b0.num == 0:               b0 = self.block([x for x in b.prev if x != 0][0])
                
                print(f"from:{b0.num}")
                print(f"to{b.num}")
                
                if b0.is_main_switch() and len(b0.next) > 1:
                    if b.num == b0.top_next():
                        b.sety(b0.y-1)
                    else:
                        b.sety(b0.y+1)
                        b.isdownward = True
                else: 
                    b.sety(b0.y)
                
                #
                #18 17 16 15 <14>< 
                #                13 <1 <2 <3 <4 <5 <6 <7> <8> <9> <10> <11> <12>
                #             12>   
                # 
                b.setx(b0.x-1) #TODO follow direction of prev

                # if b.directionality in "+bs":
                #     b.setcard(b0.card)
                # else:
                #     b.setcard("right")

            for n in b.next: print(str(b.num)+"->"+str(n))
            # print(str(b.num) +":"+str(b.x) + "," + str(b.y) + "|" + b.card)
    
    def block(self, n):
        for b in self.blocks:
            if b.num == int(n):
                return b
        return None
    
    def view(self) -> QGraphicsScene:
        self.build()
        
        scene = QGraphicsScene()
        
        self.items: list[TrackRectItem] = []
        for b in self.blocks:
            if b.num != 0:
                it = TrackRectItem(scene, b)
                self.items.append(it)

                it.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
                it.setAcceptHoverEvents(True)
                it.setPen(NONEPEN)
                
                scene.addItem(it)

        view = QGraphicsView(scene)
        view.setGeometry(0,0,(self.width*BOXSIZE)+100,(self.height*BOXSIZE)+100)
        view.setMaximumSize(view.width(),view.height())
        return view
    
    def update(self):
        for t in self.trains:
            #km/hr * 1hr/3600s * 1000m/1km = 10/36 m/s, and each tick is 0.1s
            if t.speed != 0:
                old = t.pos_on_b
                t.pos_on_b += t.speed * (10/36) * TICKSPEED
                
                while t.pos_on_b > t.block.mylength or t.pos_on_b < 0:
                    b = t.block
                    if b.is_switch():
                        if t.dir == "+": c = b.chosen_next()
                        elif t.dir == "-": c = b.chosen_prev()
                        if c == 0:
                            self.trains.remove(t)
                            b.deoccupy()
                            break
                        else:
                            to_b = self.blocks[c-1]

                    elif b.directionality in "+b":
                        if b.next[0] > b.num:to_b = self.blocks[b.next[0]-1]
                        else:                to_b = self.blocks[b.prev[0]-1]

                    elif b.directionality == "-":
                        if b.prev[0] < b.num:to_b = self.blocks[b.prev[0]-1]
                        else:                to_b = self.blocks[b.next[0]-1]
                        
                    if b in to_b.next:
                        t.dir = "-"
                    elif b in to_b.prev:
                        t.dir = "+"

                    print(f"from{b.num}")
                    print(f"to{to_b.num}")

                    #going forward is defined as getting closer to next
                    if b.directionality in "+b" or b.is_switch(): going_forward = to_b.num in b.next
                    elif b.directionality == "-":                going_forward = to_b.num in b.prev
                    
                    if to_b.is_occupied:
                        t.pos_on_b = old
                        print(f"train {t.num} CRASH (occupied block)")
                        break
                    if to_b.is_main_switch():
                        if not (b.num == to_b.chosen_next() or b.num == to_b.chosen_prev()): #switch is not aligned with this block
                            t.pos_on_b = old
                            print(f"train {t.num} CRASH (switch)")
                            break
                    if to_b.is_crossing() and to_b.crossing_state:
                        t.pos_on_b = old
                        print(f"train {t.num} CRASH (crossing)")
                        break

                    t.block.deoccupy()
                    t.pos_on_b += t.block.mylength * sign(not going_forward)
                    t.block = to_b
                    t.update()
            if t in self.trains:
                t.block.occupy()
        
        for it in self.items: it.update()

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
        binfo.setGeometry(0,0,500,120)
        binfo.setMaximumSize(binfo.width(),binfo.height())
        binfo.setMinimumSize(binfo.width(),binfo.height())

        self.chkbrk = brk = QCheckBox("Break Block Rail")
        self.chkcirc = circ = QCheckBox("Disrupt Block Track Circuit")
        self.chkpower = pwr = QCheckBox("Cut Overhead Power")

        def occ():
            if self.selectedRect:
                if brk.isChecked() or circ.isChecked():
                    self.selectedRect.block.occupy()
                else:
                    self.selectedRect.block.deoccupy()
                self.selectedRect.block.brknrail = brk.isChecked()
                self.selectedRect.block.dsrptrck = circ.isChecked()
                self.selectedRect.block.nopower = pwr.isChecked()

        lay = QVBoxLayout(controls)

        for c in [brk,circ,pwr]:
            c.setTristate(False)
            c.setChecked(False)
            c.stateChanged.connect(occ)
            lay.addWidget(c)

        tui_btn = QPushButton("Test UI", controls); 
        tui_btn.clicked.connect(m.testui.show)

        hl.addWidget(binfo)
        hl.addLayout(lay)
        hl.addWidget(tui_btn)

    def display_block(self, b:Block):
        if b.directionality == "b": dir = "Bidirectional"
        if b.directionality == "+": dir = "Increasing Block Number"
        if b.directionality == "-": dir = "Decreasing Block Number"
        if b.directionality == "s": 
            if b.is_main_switch():
                ops = b.cur_switch_option()
                dir = f"{ops[0]}→{ops[1]}"
            else:
                ops = b.first_switch_option()
                dir = f"{ops[0]}→{ops[1]}"
        type = "Track"
        if b.is_station() and b.is_main_switch():
            c = b.cur_switch_option()
            type = f"{b.station_name()} Station, Ticket Sales: {str(b.tickets)}, {str(b.num_boarding)} boarding, {str(b.num_standing)} standing\nSwitch (Currently {c[0]}→{c[1]})"
        else:
            if b.is_main_switch(): 
                b0 = self.m.tkm.blocks[int(b.first_switch_option()[0])-1] if b.has_light() else b    
                chosen = b0.cur_switch_option()
                type = f"Switch (Currently {chosen[0]}→{chosen[1]})"
            if b.is_station(): type = f"{b.station_name()} Station, Ticket Sales: {str(b.tickets)}, {str(b.num_boarding)} boarding, {str(b.num_standing)} standing"
        if b.is_crossing(): type = "Track Crossing"
        
        self.binfo.setText(f"Directionality: {dir}"
                           f"\nCommanded Authority: {round(b.authority*0.621371192,1) if b.authority else "0"} mi"
                           f"\nCommanded Speed: {round(b.speed*0.621371192,1) if b.speed else "0"} mi/hr"
                           f"\nGrade: {b.grade}%"
                           f"\nSpeed Limit: {round(b.speed_limit*0.621371192,1) if b.speed_limit else "0"} mi/hr"
                           f"\nInfrastructure: {type}"
                           f"\nOccupied: {b.is_occupied}")
    
    def update(self):
        if self.selectedRect: 
            self.display_block(self.selectedRect.block)
            for it in self.m.tkm.items:
                it.is_selected = False
                if not it.isUnderMouse(): it.setPen(NONEPEN)
            self.selectedRect.setPen(PURPPEN)
            self.selectedRect.is_selected = True
        for c in [self.chkbrk,self.chkcirc,self.chkpower]: c.setEnabled(self.selectedRect != None)
    
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
        return f"\t\t\tBlock {b.num}   \toccupancy:{b.is_occupied}\tswitch state:{b.switch_state if b.is_main_switch() else 'N/A'}\tsignal state:{b.light_state if b.is_branch_switch() else 'N/A'}"
    
    def trainOut(self, t:Train)->str:
        return f"cmd spd:{t.block.speed}   cmd auth:{t.block.authority}   cur grade:{t.block.grade}   cur spd lim:{t.block.speed_limit}   isbrokenrail:{t.block.brknrail}   isbrokentrackcircuit:{t.block.dsrptrck}   hasnopower:{t.block.nopower}   num passengers:{t.block.tickets if t.block.is_station() else 'N/A'}"

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

    def addTrainIn(self, t: Train):
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

    def addBlockIn(self, b: Block):
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
                print(f"Block {b.num} switch set to:", switches[to_int(swbox.isChecked())])
                b.switch_state = to_int(swbox.isChecked())
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
        for x in self.blocksout:
            x[1].setText(self.blockOut(x[0]))
        for x in self.trainsout:
            t = x[0]
            x[1].setText(self.trainOut(x[0]))

def main():
    app = QApplication(sys.argv)

    tkm = TrackMap("greenline.csv")
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