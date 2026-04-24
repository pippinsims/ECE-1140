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

def remdupes(l: list) -> list:
    found = None
    for i,x in enumerate(l[:-1]):
        for y in l[i+1:]:
            if x == y:
                found = x
    l = [x for x in l if x != found]
    return l

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

        self.up = -1
        self.lo = -1
        self.next = []
        self.prev = []

        #if 3 connections, if missing a neighbor, that is the unknown connection (i think 3way is always missing a neighbor)
        #if 2 connections, the unknown connection is the neighbor on that side (prev <, next >)
        if self.is_switch():
            self.switch_state = 0
            import re
            a = [int(i) for i in re.findall(r'\d+',self.token("w"))] #array of all digit sequences in token
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

                flip = False
                flipp = False

                if a[1] == n and a[3] == n:
                    self.prev = remall(n,a)
                    self.next = [other_neighbor]
                elif a[0] == n and a[3] == n:
                    self.next.append(a[1])
                    self.prev.append(a[2])
                    if abs(a[1] - n) == 1: 
                        self.prev.append(other_neighbor)
                        flip = True
                    else:
                        self.next.append(other_neighbor)
                        flipp = True
                elif a[1] == n and a[2] == n:
                    self.next.append(a[3])
                    self.prev.append(a[0])
                    if abs(a[3] - n) == 1: 
                        self.prev.append(other_neighbor)
                        flip = True
                    else:
                        self.next.append(other_neighbor)
                        flipp = True
                elif a[0] == n and a[2] == n:
                    self.next = remall(n,a)
                    self.prev = [other_neighbor]
                
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
            n = self.token("e")
            if len(n) > 0:
                self.next = [int(x.strip("e")) for x in n.split(",")]
                if flip: list.reverse(self.next)
            p = self.token("p")
            if len(p) > 0:
                self.prev = [int(x.strip("p")) for x in p.split(",")]
                if flipp: list.reverse(self.prev)
        else:
            if self.directionality in "+b":
                self.prev.append(self.num-1)
                self.next.append(self.num+1)
            else:
                self.prev.append(self.num+1)
                self.next.append(self.num-1)

        print(f"{self.num}prev:{self.prev}")
        print(f"{self.num}next:{self.next}")
        
        if self.has_light(): self.light_state = "green"
            
        if self.is_crossing(): self.crossing_state = False

        if self.is_station(): 
            self.tickets = 0
            self.num_boarding = 0
            self.num_standing = 0
            self.gentickets()
    
    def tokens           (self) -> list[str]: return self.type.split(";")
    def is_switch        (self) -> bool: return len(self.token("w")) > 0
    def is_station       (self) -> bool: return len(self.token("t")) > 0
    def is_beacon        (self) -> bool: return len(self.token("b")) > 0
    def is_main_switch   (self) -> bool: return self.is_switch() and "l" not in self.tokens()
    def is_branch_switch (self) -> bool: return self.is_switch() and "l" in self.tokens()
    def has_light        (self) -> bool: return self.is_beacon() or self.is_branch_switch()
    def is_crossing      (self) -> bool: return "c" in self.tokens()
    def is_tunnel        (self) -> bool: return "u" in self.tokens()

    def station_name(self) -> str: return self.token("t").split(",")[1]

    def token(self, c:str) -> str: 
        try: return [x for x in self.tokens() if x[0] == c][0]
        except: return []

    def first_switch_option(self) -> tuple[int,int]: #from,to
        def guts():
            tok = self.token("w")[1:]
            if "," in tok: return tok.split(",")[0].split("-")
            else: return tok.split("-")
        return [int(x) for x in guts()]
    def first(self) -> int: return [x for x in self.first_switch_option() if x != self.num][0]
    def second_switch_option(self) -> tuple[int,int]: #from,to
        def guts():
            tok = self.token("w")[1:]
            return tok.split(",")[1].split("-")
        return [int(x) for x in guts()]
    def second(self) -> int: return [x for x in self.second_switch_option() if x != self.num][0]

    def cur_switch_option(self):
        return [self.first_switch_option(),self.second_switch_option()][self.switch_state]
    def cur(self) -> int: [x for x in self.cur_switch_option() if x != self.num][0]

    def chosen_next(self):
        if len(self.next) > 1:
            check = self.cur()
            if check in self.next:
                return check
            else:
                unwanted = [x for x in [self.first()]+[self.second()] if x != check][0]
                return [x for x in self.next if x != unwanted][0]
        else:
            return self.next[0]

    def chosen_prev(self):
        if len(self.prev) > 1:
            check = self.cur()
            if check in self.prev: 
                return check
            else:
                unwanted = [x for x in [self.first()]+[self.second()] if x != check][0]
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
        return self.token("b")[2:] if self.is_beacon() else None
    
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
        self.from_b = 0
        self.block:Block = tkm.blocks[0]
        self.speed = 0
        self.num_riding = 0
        self.beacon = ''
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
        import random
        r = random.randint(0, self.num_riding)
        self.num_riding -= r
        self.block.num_standing += r
        # print(f"{r} got off of the train")
        # print(f"{self.block.num_standing} are standing")

        self.block.num_standing -= self.block.num_boarding
        self.num_riding += self.block.num_boarding
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
        text.setPen(WHITPEN)
        self.setZValue(0)

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
            if self.block.directionality == "b": addHead((ex,ey),(sx,sy), downward)

        if self.block.is_main_switch():
            b = self.block

            # print(f"building switch:{b.num}")
            # print(f"p{b.prev}")
            # print(f"n{b.next}")
            # print(f"f{b.first_switch_option()}")
            # print(f"s{b.second_switch_option()}")

            self.text.setX(self.text.x()-10)
            self.text.setY(self.text.y()+20)

            shared = None
            prevnext = b.prev+b.next
            for i,x in enumerate(prevnext[:-1]):
                for y in prevnext[i+1:]:
                    if x == y:
                        shared = x #the prevnext duplicate
            if len(b.next) == 1 or shared == b.num+1:
                addArrow((1,0),(0,0.5))
                addArrow((1,1),(0,0.5),True)
            if len(b.prev) == 1 or shared == b.num-1:
                addArrow((1,0.5),(0,0))
                addArrow((1,0.5),(0,1),True)                

            u,d = str(b.first()),str(b.second())

            def make(it:QGraphicsSimpleTextItem,y):
                it.setFont(QFont("Segoe UI", 12))
                it.setPos((b.x+0.5)*BOXSIZE-div(it.boundingRect().width(),2),b.y*BOXSIZE+y)
                it.setPen(WHITPEN)

            make(QGraphicsSimpleTextItem(u, self), -10)
            make(QGraphicsSimpleTextItem(d, self), +50)
        else:
            sx,ex,sy,ey = [0.5]*4
            sx,ex = 1,0
            if self.block.directionality in "+bs":
                addArrow((sx,sy),(ex,ey))
            # elif self.block.directionality == "s":
            #     print("HELLO")#TODO
            else:
                addArrow((ex,ey),(sx,sy))
    
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
        for b in self.blocks:
            if b.num == 0: 
                b.setx(0)
                b.sety(0)
            elif b.num == 1:
                b.setx(int(self.width*0.75))
                b.sety(int(self.height*0.5))
            else:
                print(b.num)
                if b.directionality in "+bs": b0 = self.block(min(b.prev))
                else:                         b0 = self.block(min(b.next))
                if b0.num == 0:               b0 = self.block([x for x in b.prev if x != 0][0])
                    
                if b0.is_main_switch():
                    if   b0.first()  == b.num: b.sety(b0.y-1)
                    elif b0.second() == b.num: b.sety(b0.y+1)
                    else:                      b.sety(b0.y)
                else: 
                    b.sety(b0.y)
                
                if (b.directionality in "s+" and b0.directionality == "-") or (b.directionality == "-" and b0.directionality in "s+"):
                    b.sety(b.y+2)
                
                b.setx(b0.x-1)
    
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
                
                while t.pos_on_b > t.block.mylength:
                    b = t.block
                    if b.is_switch():
                        if b.directionality == "s": 
                            k = b.first_switch_option() #must be branch if "s"
                            if k[0] == b.num: c = k[1]
                            else:             c = b.num+1 #default for "s" seems to be fine to be "+"
                        else:
                            chsn_sw_opt = b.chosen_next(),b.chosen_prev() #to,from
                            if t.dir == "-": chsn_sw_opt = chsn_sw_opt[::-1]
                            bad_dir = chsn_sw_opt[0] == t.from_b 
                            if bad_dir: t.dir = "-" if t.dir == "+" else "+"
                            c = chsn_sw_opt[to_int(bad_dir)]
                        if c == 0:
                            self.trains.remove(t)
                            b.deoccupy()
                            break
                        else:
                            to_b = self.blocks[c-1]
                            if c == b.chosen_prev(): t.dir = "+"

                    elif b.directionality == "+":
                        t.dir = "+"
                        if b.next[0] > b.num:to_b = self.blocks[b.next[0]-1]
                        else:                to_b = self.blocks[b.prev[0]-1]

                    elif b.directionality == "-":
                        t.dir = "-"
                        if b.prev[0] < b.num:to_b = self.blocks[b.prev[0]-1]
                        else:                to_b = self.blocks[b.next[0]-1]
                        
                    elif b.directionality == "b":
                        if t.dir == "+": to_b = self.blocks[b.next[0]-1]
                        else:            to_b = self.blocks[b.prev[0]-1]

                    if to_b.num == b.num-1: t.dir = "-"

                    t.from_b = b.num

                    print(f"traveling from block {b.num}")
                    print(f"to block {to_b.num}")
                    print(f"dir:{t.dir}")

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
                    t.pos_on_b -= t.block.mylength
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

        lay = QVBoxLayout()
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

    widget.tkm.blocks[12].switch_state = 1
    widget.tkm.blocks[56].switch_state = 1
    widget.tkm.blocks[62].switch_state = 1

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