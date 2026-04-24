import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import os

BOXSIZE = 70
TICKSPEED = 0.1
WHITPEN = QPen(QColor("#e5e7eb"), 2)
PURPPEN = QPen(QColor("#a855f7"), 2)
BLCKPEN = QPen(QColor("#111827"), 2)
NONEPEN = QPen(Qt.PenStyle.NoPen) #QPen(QColor("black"),0)

# Track Model dark theme (local styling only)
TM_BG = QColor("#0b1020")          # window background
TM_PANEL = QColor("#111827")       # block tile background
TM_GRID = QColor("#1f2937")        # subtle borders
TM_TEXT = QColor("#e5e7eb")

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
        # Normalize directionality values from CSV so routing logic is consistent.
        _d = str(dir).strip().lower()
        if _d in ("bid", "bidir", "bidirectional"):
            _d = "b"
        self.directionality = _d
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
        # print(f"there were {self.tickets} more sales!")
        # print(f"{self.num_standing} are standing")
    
    def beacondata(self)->str:
        # return self.type[2:] if self.is_beacon() else None
        return [x for x in self.tokens() if x[0] == "b"][0][2:] if self.is_beacon() else None
    
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
        self.integrated_alighting_count: int = 0
        # Integrated launcher may override command/authority per-train even if
        # multiple trains share a block (do not rely solely on block fields).
        self.integrated_cmd_kmh: float | None = None
        self.integrated_auth_km: float | None = None

    def update(self):
        if self.block.nopower: print("NO POWER TO TRAIN!")
        if self.block.is_station(): self.board()
        if self.block.is_beacon():
            print(f"block {self.block.num} beacondata:'{self.block.beacondata()}'")
            self.beacon = self.block.beacondata()
    
    def board(self):
        # Offboarding count comes from the integrated Train Model backend.
        r = max(0, int(getattr(self, "integrated_alighting_count", 0)))
        r = min(r, self.num_riding)
        self.num_riding -= r
        self.block.num_standing += r
        # print(f"{r} got off of the train")
        # print(f"{self.block.num_standing} are standing")

        boarded = min(int(self.block.num_boarding), int(self.block.num_standing))
        self.block.num_standing -= boarded
        self.num_riding += boarded
        # print(f"{self.block.num_boarding} got on the train")
        # print(f"{self.block.num_standing} are standing")

        self.block.gentickets()

        try:
            if ui.selectedRect and ui.selectedRect.block == self.block:
                ui.display_block(self.block)
        except Exception:
            pass

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
        super().__init__(QRectF(b.x * BOXSIZE, b.y * BOXSIZE, BOXSIZE, BOXSIZE))
        # No tile fill; only show arrows/icons/text.
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        
        self.ic1 = scene.addPixmap(QPixmap())
        self.ic2 = scene.addPixmap(QPixmap())
        self.ic3 = scene.addPixmap(QPixmap())
        # Keep icons above arrows/lines for visibility.
        try:
            self.ic1.setZValue(3)
            self.ic2.setZValue(3)
            self.ic3.setZValue(3)
        except Exception:
            pass

        txt = str(b.num)
        if b.is_crossing(): self.ic2 = scene.addPixmap(pixmap('/assets/railroad-crossing','white'))
        if b.has_light  (): self.ic2 = scene.addPixmap(pixmap('/assets/traffic-light','white'))
        elif b.is_switch(): self.downArrow = []
        if b.is_station (): self.ic2 = scene.addPixmap(pixmap('/assets/building','white'))
        if b.is_beacon  (): self.ic3 = scene.addPixmap(pixmap('/assets/beacon','white'))
        
        self.ic1.setPos((b.x      )*BOXSIZE, b.y     *BOXSIZE)
        self.ic2.setPos((b.x + 0.5)*BOXSIZE, b.y     *BOXSIZE)
        self.ic3.setPos((b.x + 0.5)*BOXSIZE,(b.y+0.5)*BOXSIZE)
        
        self.text = text = QGraphicsSimpleTextItem(txt, self)
        text.setFont(QFont("Segoe UI", 12))
        if b.is_main_switch(): text.setPos((b.x+0.5 )*BOXSIZE-div(text.boundingRect().width(),2),  b.y     *BOXSIZE)
        else:                  text.setPos((b.x+0.25)*BOXSIZE-div(text.boundingRect().width(),2), (b.y+0.5)*BOXSIZE)
        text.setPen(QPen(TM_TEXT, 1))
        self.setZValue(0)

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
            self.setPen(QPen(Qt.PenStyle.NoPen))
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

    def train_icon   (self, color): self.ic1.setPixmap(pixmap('/assets/train',            color) if color else QPixmap())
    def crossing_icon(self, color): self.ic2.setPixmap(pixmap('/assets/railroad-crossing',color) if color else QPixmap())
    def station_icon (self, color): self.ic2.setPixmap(pixmap('/assets/building',         color) if color else QPixmap())
    def light_icon   (self, color): self.ic2.setPixmap(pixmap('/assets/traffic-light',    color) if color else QPixmap())
    def beacon_icon  (self, color): self.ic3.setPixmap(pixmap('/assets/beacon',           color) if color else QPixmap())

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

            # Ensure arrows render above the filled block tiles (dark theme).
            head.setZValue(2)
            head.setBrush(QBrush(QColor("#60a5fa")))
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
            line.setZValue(1)
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
        self.trains:list[Train] = []

    def build(self):
        used_xy: set[tuple[int, int]] = set()
        b1 = self.block(1)
        base_y = int(getattr(b1, "y", int(self.height * 0.5))) if b1 is not None else int(self.height * 0.5)
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
                if b.directionality in "+bs": b0 = self.block(min(b.prev))
                else:                         b0 = self.block(min(b.next))
                if b0.num == 0:               b0 = self.block([x for x in b.prev if x != 0][0])
                # Some CSV orderings / directionality choices can reference a neighbor
                # that hasn't been assigned coordinates yet. Fall back to a safe default
                # so build never crashes; positions will still be deterministic.
                if b0 is not None and not hasattr(b0, "y"):
                    try:
                        b0.setx(int(self.width * 0.75))
                        b0.sety(int(self.height * 0.5))
                    except Exception:
                        pass
                
                # print(f"from:{b0.num}")
                # print(f"to{b.num}")
                
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

            # Ensure 2–12 sit on the intended row (after initial placement).
            if 2 <= int(b.num) <= 12:
                b.sety(base_y + 3)

            # Prevent blocks from landing on top of each other.
            if b.x and b.y:
                try:
                    x = int(b.x)
                    y = int(b.y)
                except Exception:
                    x, y = int(b.x), int(b.y)
                while (x, y) in used_xy:
                    y += 1
                b.setx(x)
                b.sety(y)
                used_xy.add((x, y))

            # for n in b.next: print(str(b.num)+"->"+str(n))
            # print(str(b.num) +":"+str(b.x) + "," + str(b.y) + "|" + b.card)
    
    def block(self, n):
        for b in self.blocks:
            if b.num == int(n):
                return b
        return None
    
    def view(self) -> QGraphicsScene:
        self.build()
        
        scene = QGraphicsScene()
        scene.setBackgroundBrush(QBrush(TM_BG))
        
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
        view.setBackgroundBrush(QBrush(TM_BG))
        view.setStyleSheet("QGraphicsView { border: 1px solid #374151; }")
        view.setGeometry(0,0,(self.width*BOXSIZE)+100,(self.height*BOXSIZE)+100)
        view.setMaximumSize(view.width(),view.height())
        return view
    
    def update(self, tickrate = TICKSPEED):
        if tickrate is None: tickrate = TICKSPEED
        for t in self.trains:
            #km/hr * 1hr/3600s * 1000m/1km = 10/36 m/s, and each tick is 0.1s
            if t.speed != 0:
                old = t.pos_on_b
                t.pos_on_b += t.speed * (10/36) * tickrate
                
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
                        
                    # next/prev store block numbers, not Block objects
                    if int(b.num) in getattr(to_b, "next", []):
                        t.dir = "-"
                    elif int(b.num) in getattr(to_b, "prev", []):
                        t.dir = "+"

                    print(f"traveling from block {b.num}")
                    print(f"to block {to_b.num}")

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
                    
            if t in self.trains: t.block.occupy()
        
        for it in self.items: it.update()

    def get_train_track_data(self, train_index: int):
        """Return track data dict for train at train_index (0-based)."""
        if train_index < 0 or train_index >= len(self.trains):
            return {}
        t = self.trains[train_index]
        b = t.block

        def safe_float(v, default=0.0):
            try:
                return float(v)
            except (ValueError, TypeError):
                return default

        cmd_kmh = float(t.integrated_cmd_kmh) if t.integrated_cmd_kmh is not None else safe_float(b.speed)
        auth_km = float(t.integrated_auth_km) if t.integrated_auth_km is not None else safe_float(b.authority)

        return {
            "block_num":           int(b.num),
            "commanded_speed_kmh": cmd_kmh,
            "authority_km":        auth_km,
            "track_grade_percent": float(b.grade),
            "speed_limit_kmh":     float(b.speed_limit),
            "beacon_data":         t.beacon or "",
            "rail_broken":         bool(b.brknrail),
            "circuit_failed":      bool(b.dsrptrck),
            "power_lost":          bool(b.nopower),
            "boarding_passengers": int(getattr(b, "num_boarding", 0)) if b.is_station() else 0,
        }

    def set_train_speed(self, train_index: int, speed_kmh: float):
        """Feed Train Model velocity back into the track to move trains."""
        if 0 <= train_index < len(self.trains):
            self.trains[train_index].speed = float(speed_kmh)

class MainWindow(QWidget):
    def __init__(self, tkm:TrackMap):
        super().__init__()
        self.setWindowTitle("Train Track Model")
        self.setMinimumSize(400,400)
        self.tkm = tkm
        import tkm_testui as tui
        self.testui = tui.TestUI(self)
        self.ui: UIControls = None

    def closeEvent(self, a0):
        self.testui.hide()
        return super().closeEvent(a0)

class UIControls:
    def __init__(self, m: MainWindow):
        global ui; ui = self
        self.controls = QWidget()
        self.selectedRect:TrackRectItem = None
        self.m = m
        controls = self.controls
        hl = QHBoxLayout(controls)

        self.binfo = QLabel("Block info", controls)
        binfo = self.binfo
        binfo.setStyleSheet("""
            background-color: #0b1020;
            color: #e5e7eb;
            border: 1px solid #374151;
            padding: 6px;
        """)
        binfo.setGeometry(0,0,500,220)
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
        # Always define a default to avoid UnboundLocalError for unexpected values.
        dir = str(getattr(b, "directionality", "") or "Unknown")
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
        
        auth_mi = round(float(b.authority) * 0.621371192, 1) if b.authority else 0
        spd_mph = round(float(b.speed) * 0.621371192, 1) if b.speed else 0
        lim_mph = round(float(b.speed_limit) * 0.621371192, 1) if b.speed_limit else 0
        self.binfo.setText(
            f"Directionality: {dir}"
            f"\nCommanded Authority: {auth_mi} mi"
            f"\nCommanded Speed: {spd_mph} mi/hr"
            f"\nGrade: {b.grade}%"
            f"\nSpeed Limit: {lim_mph} mi/hr"
            f"\nInfrastructure: {type}"
            f"\nOccupied: {b.is_occupied}"
        )
    
    def update(self):
        if self.selectedRect: 
            self.display_block(self.selectedRect.block)
            for it in self.m.tkm.items:
                it.is_selected = False
                if not it.isUnderMouse(): it.setPen(NONEPEN)
            self.selectedRect.setPen(PURPPEN)
            self.selectedRect.is_selected = True
        for c in [self.chkbrk,self.chkcirc,self.chkpower]: c.setEnabled(self.selectedRect != None)

def make_widget() -> MainWindow:
    tkm = TrackMap("assets/greenline.csv")
    window = MainWindow(tkm)
    window.ui = UIControls(window)

    layout = QVBoxLayout(window)
    layout.addWidget(tkm.view())
    layout.addWidget(window.ui.controls)

    return window

def main():
    app = QApplication(sys.argv)

    widget = make_widget()
    widget.show()

    widget.tkm.trains.append(Train(1, widget.tkm))
    widget.tkm.trains.append(Train(2, widget.tkm))

    def tick():
        widget.tkm.update()
        widget.ui.update()
        widget.testui.update()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(int(TICKSPEED*1000))

    sys.exit(app.exec())

if __name__ == "__main__":
    main()