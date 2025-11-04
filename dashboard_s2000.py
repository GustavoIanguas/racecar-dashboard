#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Automotivo - Estética S2000 (late 90s/early 2000s)
- Pygame puro (AMD64/ARM64)
- Simulador embutido + entrada UDP/JSON opcional (--udp-port 5005)
- Display sete segmentos (speed) sem fontes externas
"""
import math, json, random, time, argparse, socket
from dataclasses import dataclass, asdict
import pygame

BG=(5,5,8); PANEL=(12,12,16); EDGE=(28,28,32); WHITE=(240,240,245); MUTED=(150,150,160)
ORANGE=(255,150,60); RED=(255,70,60); RED_SEG=(255,40,30); RED_GLOW=(255,30,20)
AMBER=(255,180,80); GREEN=(80,230,120); BLUE=(90,180,255); CYAN=(0,220,220)

def clamp(v,a,b): return max(a,min(b,v))
def lerp(a,b,t): return a+(b-a)*t

@dataclass
class Sensors:
    speed_kmh: float = 0.0
    rpm: float = 800.0
    fuel_level: float = 0.65
    coolant_temp_c: float = 80.0
    oil_temp_c: float = 95.0
    oil_pressure_bar: float = 3.0
    turbo_bar: float = 0.2
    batt_v: float = 13.8
    lambda_value: float = 1.0
    left_blinker: bool = False
    right_blinker: bool = False
    handbrake: bool = False
    lights_parking: bool = False
    lights_low: bool = False
    lights_high: bool = False

class SensorSimulator:
    def __init__(self): self.t0=time.perf_counter()
    def update(self)->Sensors:
        t=time.perf_counter()-self.t0
        speed=140*(0.5+0.5*math.sin(t*0.40)); speed=clamp(speed+random.uniform(-1.0,1.0),0,260)
        rpm=1200+6000*(0.5+0.5*math.sin(t*1.05)); rpm=clamp(rpm+random.uniform(-40,40),650,8000)
        fuel=0.8-(t*0.00045); fuel=(fuel%1.0) if fuel<0 else clamp(fuel,0.02,0.98)
        coolant=clamp(75+25*(0.5+0.5*math.sin(t*0.18)),10,120)
        oil_temp=clamp(85+25*(0.5+0.5*math.sin(t*0.16+0.8)),60,130)
        oil_press=clamp(0.9+(rpm/8000.0)*5.6+0.1*math.sin(t*1.4),0.3,6.9)
        turbo=clamp(-0.2+(rpm/8000.0)*2.4+0.1*math.sin(t*0.8),-0.9,2.9)
        batt=clamp(13.5+0.35*math.sin(t*0.25),9,16)
        lam=clamp(1.0+0.1*math.sin(t*1.6),0.6,3.0)
        blink=(math.sin(t*math.tau*0.75)>0.0)
        return Sensors(speed_kmh=speed,rpm=rpm,fuel_level=fuel,coolant_temp_c=coolant,oil_temp_c=oil_temp,
                       oil_pressure_bar=oil_press,turbo_bar=turbo,batt_v=batt,lambda_value=lam,
                       left_blinker=blink,right_blinker=not blink,handbrake=(math.sin(t*0.07)>0.94),
                       lights_parking=(math.sin(t*0.15)>0.6),lights_low=True,lights_high=(math.sin(t*0.12)>0.85))

class UdpReceiver:
    def __init__(self,host="0.0.0.0",port=5005):
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); self.sock.setblocking(False); self.sock.bind((host,port)); self.last=None
    def poll(self):
        try:
            data,_=self.sock.recvfrom(8192); self.last=json.loads(data.decode("utf-8"))
        except BlockingIOError: pass
        except Exception: pass
        return self.last

def sensors_from_dict(obj:dict,fallback:Sensors)->Sensors:
    d=asdict(fallback)
    for k in d.keys():
        if k in obj: d[k]=obj[k]
    return Sensors(**d)

def draw_text(surf,text,font,color,pos,align="center"):
    img=font.render(text,True,color); r=img.get_rect(); setattr(r,align,pos); surf.blit(img,r)

def ring_point(center,radius,angle_deg):
    a=math.radians(angle_deg); return (center[0]+radius*math.cos(a), center[1]+radius*math.sin(a))

def rounded_rect(s, rect, color, radius=12, width=0):
    pygame.draw.rect(s,color,rect,width=width,border_radius=radius)

class SevenSeg:
    DIGITS={'0':(1,1,1,1,1,1,0),'1':(0,1,1,0,0,0,0),'2':(1,1,0,1,1,0,1),'3':(1,1,1,1,0,0,1),
            '4':(0,1,1,0,0,1,1),'5':(1,0,1,1,0,1,1),'6':(1,0,1,1,1,1,1),'7':(1,1,1,0,0,0,0),
            '8':(1,1,1,1,1,1,1),'9':(1,1,1,1,0,1,1),'-':(0,0,0,0,0,0,1),' ':(0,0,0,0,0,0,0)}
    def __init__(self, seg_w=16, seg_h=80, seg_gap=4, color=RED_SEG):
        self.seg_w=seg_w; self.seg_h=seg_h; self.seg_gap=seg_gap; self.color=color; self.off=(60,20,20)
    def draw_digit(self,surf,x,y,w,h,ch,glow=True):
        a=pygame.Rect(x+self.seg_w,y,w-2*self.seg_w,self.seg_w)
        d=pygame.Rect(x+self.seg_w,y+h-self.seg_w,w-2*self.seg_w,self.seg_w)
        g=pygame.Rect(x+self.seg_w,y+(h-self.seg_w)//2,w-2*self.seg_w,self.seg_w)
        f=pygame.Rect(x,y+self.seg_w,self.seg_w,(h-3*self.seg_w)//2)
        e=pygame.Rect(x,y+(h+self.seg_w)//2,self.seg_w,(h-3*self.seg_w)//2)
        b=pygame.Rect(x+w-self.seg_w,y+self.seg_w,self.seg_w,(h-3*self.seg_w)//2)
        c=pygame.Rect(x+w-self.seg_w,y+(h+self.seg_w)//2,self.seg_w,(h-3*self.seg_w)//2)
        rects=[a,b,c,d,e,f,g]
        on=self.DIGITS.get(ch,self.DIGITS[' '])
        for i,r in enumerate(rects):
            if on[i]:
                pygame.draw.rect(surf,self.color,r,border_radius=6)
                if glow:
                    glow_rect=r.inflate(12,12)
                    glow_surf=pygame.Surface(glow_rect.size,pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf,(*RED_GLOW,40),glow_surf.get_rect(),border_radius=10)
                    surf.blit(glow_surf,glow_rect.topleft,special_flags=pygame.BLEND_ADD)
            else:
                pygame.draw.rect(surf,(60,20,20),r,border_radius=6)
    def draw_string(self,surf,pos,text,scale=1.0,spacing=12):
        x,y=pos; w=int(64*scale); h=int(110*scale)
        for ch in text:
            self.draw_digit(surf,x,y,w,h,ch); x+=w+spacing

class TachArc:
    def __init__(self, center, radius, width=28, start=-172, end=-8, red_from=8000):
        self.center=center; self.radius=radius; self.width=width; self.start=start; self.end=end; self.red_from=red_from
        self.segments=[]; self.scale_marks=[]; self._build()
    def _build(self):
        angle_span=self.end-self.start; seg_angle=2.9
        a=self.start
        while a<self.end-0.001:
            b=min(a+seg_angle,self.end); self.segments.append((a,b)); a=b
        step=angle_span/9.0
        for i in range(10):
            ang=self.start+i*step; self.scale_marks.append((i,ang))
    def draw(self,surf,rpm):
        rect=pygame.Rect(0,0,self.radius*2,self.radius*2); rect.center=self.center; rect.inflate_ip(-20,-20)
        val_per_seg=9000.0/len(self.segments); cur_val=0.0
        for (a,b) in self.segments:
            pygame.draw.arc(surf,(60,35,18),rect,math.radians(a),math.radians(b),self.width)
        for (a,b) in self.segments:
            cur_val+=val_per_seg
            if cur_val<=clamp(rpm,0,9000):
                col=ORANGE if (cur_val<self.red_from) else RED
                pygame.draw.arc(surf,col,rect,math.radians(a),math.radians(b),self.width)
        font=pygame.font.SysFont(None,26,bold=True)
        for i,ang in self.scale_marks:
            p1=ring_point(self.center,self.radius-6,ang); p2=ring_point(self.center,self.radius-6-self.width,ang)
            pygame.draw.line(surf,WHITE,p1,p2,2)
            tpos=ring_point(self.center,self.radius-self.width-24,ang-2)
            draw_text(surf,str(i),font,WHITE,(int(tpos[0]),int(tpos[1])),"center")
        font2=pygame.font.SysFont(None,20); draw_text(surf,"x1000 r/min",font2,MUTED,(self.center[0]-self.radius+40,self.center[1]+18),"center")

class MiniArc:
    def __init__(self, center, radius, start=200, end=340, width=18, segs=16):
        self.center=center; self.radius=radius; self.start=start; self.end=end; self.width=width; self.segs=segs
    def draw(self,surf,value01,labels=("L","H")):
        rect=pygame.Rect(0,0,self.radius*2,self.radius*2); rect.center=self.center; rect.inflate_ip(-16,-16)
        ang_span=self.end-self.start; per=clamp(value01,0.0,1.0); fill_to=self.start+ang_span*per
        for i in range(self.segs):
            a=lerp(self.start,self.end,i/self.segs); b=lerp(self.start,self.end,(i+1)/self.segs)-1.5
            bg=(40,35,30); pygame.draw.arc(surf,bg,rect,math.radians(a),math.radians(b),self.width)
            if b<=fill_to:
                col=ORANGE if i<self.segs*0.8 else RED
                pygame.draw.arc(surf,col,rect,math.radians(a),math.radians(b),self.width)
        font=pygame.font.SysFont(None,22,bold=True)
        pL=ring_point(self.center,self.radius-self.width-8,self.start-4); pH=ring_point(self.center,self.radius-self.width-8,self.end+4)
        draw_text(surf,labels[0],font,WHITE,(int(pL[0]),int(pL[1])),"center")
        draw_text(surf,labels[1],font,WHITE,(int(pH[0]),int(pH[1])),"center")

class FuelBar:
    def __init__(self, rect, segments=14):
        self.rect=pygame.Rect(rect); self.segments=segments
    def draw(self,surf,level01):
        r=self.rect.inflate(-8,-8); seg_h=r.height/self.segments; reserve_cut=int(self.segments*0.12)
        rounded_rect(surf,self.rect,PANEL,radius=14,width=0); pygame.draw.rect(surf,EDGE,self.rect,width=3,border_radius=14)
        for i in range(self.segments):
            y0=r.bottom-(i+1)*seg_h; cell=pygame.Rect(r.left,y0+2,r.width,seg_h-4)
            pygame.draw.rect(surf,(35,32,28),cell,border_radius=6)
            if (i/(self.segments-1))<=clamp(level01,0,1):
                col=AMBER if i>reserve_cut else RED; pygame.draw.rect(surf,col,cell,border_radius=6)
        font=pygame.font.SysFont(None,22,bold=True)
        draw_text(surf,"E",font,WHITE,(self.rect.centerx,self.rect.bottom+16),"center")
        draw_text(surf,"F",font,WHITE,(self.rect.centerx,self.rect.top-16),"center")

def icon_arrow(surf,center,left=True,on=True):
    x,y=center; col=GREEN if on else (60,70,60)
    if left: pts=[(x+28,y-12),(x-12,y),(x+28,y+12)]; cut=[(x+18,y-6),(x-4,y),(x+18,y+6)]
    else:    pts=[(x-28,y-12),(x+12,y),(x-28,y+12)];  cut=[(x-18,y-6),(x+4,y),(x-18,y+6)]
    pygame.draw.polygon(surf,col,pts); pygame.draw.polygon(surf,BG,cut)
def icon_circle_P(surf,center,on):
    col=RED if on else (70,40,40); pygame.draw.circle(surf,col,center,14,3); f=pygame.font.SysFont(None,22,bold=True); draw_text(surf,"P",f,col,center,"center")
def icon_lights(surf,center,mode,on):
    x,y=center
    if mode=='park':
        col=GREEN if on else (60,70,60); pygame.draw.circle(surf,col,(x-8,y),7,2)
        for i in range(-1,2): pygame.draw.arc(surf,col,(x-2,y-12+i*2,26,26),math.radians(-35),math.radians(35),2)
    elif mode=='low':
        col=CYAN if on else (55,60,70); pygame.draw.circle(surf,col,(x-8,y),7,2)
        for i in range(-1,2): pygame.draw.line(surf,col,(x+2,y-8+i*8),(x+24,y-4+i*8),2)
    else:
        col=BLUE if on else (55,60,70); pygame.draw.circle(surf,col,(x-8,y),7,2)
        for i in range(-2,3): pygame.draw.line(surf,col,(x+2,y-10+i*5),(x+26,y-10+i*5),2)

class Dashboard:
    def __init__(self,width=1280,height=720,fullscreen=False,fps=60,udp_port=None):
        pygame.init(); flags=pygame.FULLSCREEN if fullscreen else pygame.SCALED
        self.screen=pygame.display.set_mode((width,height),flags); pygame.display.set_caption("Dashboard Retro S2000")
        self.clock=pygame.time.Clock(); self.fps=fps; self.running=True
        self.font_small=pygame.font.SysFont(None,22); self.font_med=pygame.font.SysFont(None,28,bold=True)
        self.sevseg=SevenSeg(); self.sim=SensorSimulator(); self.udp=UdpReceiver(port=udp_port) if udp_port else None
        self.W,self.H=self.screen.get_size()
        self.center=(self.W//2,int(self.H*0.40))
        self.tach=TachArc(center=(self.center[0],int(self.H*0.36)),radius=int(self.W*0.42))
        self.mini1=MiniArc(center=(int(self.W*0.80),int(self.H*0.48)),radius=int(self.W*0.16))
        self.mini2=MiniArc(center=(int(self.W*0.72),int(self.H*0.72)),radius=int(self.W*0.13))
        fuel_w=int(self.W*0.04); fuel_h=int(self.H*0.50)
        self.fuel=FuelBar((int(self.W*0.08),int(self.H*0.30),fuel_w,fuel_h))
        self.speed_rect=pygame.Rect(0,0,int(self.W*0.26),int(self.H*0.18)); self.speed_rect.center=(self.center[0],int(self.H*0.53))
        self.icons_y=int(self.H*0.66); self.icon_spacing=int(self.W*0.08)
    def get_sensors(self)->Sensors:
        base=self.sim.update()
        if self.udp:
            data=self.udp.poll()
            if data: base=sensors_from_dict(data,base)
        return base
    def bg(self):
        self.screen.fill(BG)
        overlay=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA)
        pygame.draw.ellipse(overlay,(0,0,0,120),(-int(self.W*0.05),-int(self.H*0.70),int(self.W*1.1),int(self.H*1.2)))
        self.screen.blit(overlay,(0,0))
        rim=pygame.Rect(int(self.W*0.03),int(self.H*0.14),int(self.W*0.94),int(self.H*0.74))
        rounded_rect(self.screen,rim,PANEL,radius=30,width=0); pygame.draw.rect(self.screen,EDGE,rim,width=4,border_radius=30)
    def draw_speed(self,speed,lam):
        rounded_rect(self.screen,self.speed_rect,(20,8,8),radius=18,width=0); pygame.draw.rect(self.screen,(60,18,18),self.speed_rect,width=3,border_radius=18)
        s=f"{int(speed):3d}"[-3:].rjust(3," "); digit_w=64; spacing=14; total_w=3*digit_w+2*spacing
        x0=self.speed_rect.centerx-total_w//2; y0=self.speed_rect.top+8; self.sevseg.draw_string(self.screen,(x0,y0),s,scale=1.0,spacing=spacing)
        draw_text(self.screen,"km/h",self.font_small,MUTED,(self.speed_rect.right-12,self.speed_rect.centery+18),"midright")
        draw_text(self.screen,f"λ {lam:.2f}",self.font_med,CYAN,(self.speed_rect.centerx,self.speed_rect.bottom+26),"center")
    def draw_icons(self,s):
        cx=self.center[0]-2*self.icon_spacing; y=self.icons_y
        icon_arrow(self.screen,(cx,y),left=True,on=s.left_blinker)
        icon_lights(self.screen,(cx+self.icon_spacing,y),"park",s.lights_parking)
        icon_lights(self.screen,(cx+2*self.icon_spacing,y),"low",s.lights_low)
        icon_lights(self.screen,(cx+3*self.icon_spacing,y),"high",s.lights_high)
        icon_arrow(self.screen,(cx+4*self.icon_spacing,y),left=False,on=s.right_blinker)
        icon_circle_P(self.screen,(cx+5*self.icon_spacing,y),s.handbrake)
    def draw_mini_gauges(self,s):
        v1=(s.coolant_temp_c-10)/(120-10); self.mini1.draw(self.screen,v1,labels=("L","H"))
        draw_text(self.screen,"Temp. Água",self.font_small,MUTED,(self.mini1.center[0],self.mini1.center[1]+self.mini1.radius*0.65),"center")
        v2=(s.oil_pressure_bar-0)/7.0; self.mini2.draw(self.screen,v2,labels=("0","7"))
        draw_text(self.screen,"Press. Óleo",self.font_small,MUTED,(self.mini2.center[0],self.mini2.center[1]+self.mini2.radius*0.65),"center")
    def draw_footer(self):
        draw_text(self.screen,"Retro S2000 • UDP :5005 (opcional) • ESC para sair",self.font_small,MUTED,(self.W//2,int(self.H*0.95)),"center")
    def draw(self,s):
        self.bg(); self.tach.draw(self.screen,s.rpm); self.draw_speed(s.speed_kmh,s.lambda_value)
        self.fuel.draw(self.screen,s.fuel_level); draw_text(self.screen,"Fuel",self.font_small,MUTED,(self.fuel.rect.centerx,self.fuel.rect.bottom+28),"center")
        self.draw_mini_gauges(s)
        info=f"TUR {s.turbo_bar:+.1f} bar   BAT {s.batt_v:.1f} V   ÓLEO {s.oil_temp_c:.0f}°C"
        draw_text(self.screen,info,self.font_small,MUTED,(self.center[0],self.speed_rect.bottom+54),"center")
        self.draw_icons(s); self.draw_footer()
    def run(self):
        while self.running:
            for e in pygame.event.get():
                if e.type==pygame.QUIT: self.running=False
                if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: self.running=False
            s=self.get_sensors(); self.draw(s); pygame.display.flip(); self.clock.tick(self.fps)
        pygame.quit()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--w",type=int,default=1280); ap.add_argument("--h",type=int,default=720)
    ap.add_argument("--fullscreen",action="store_true"); ap.add_argument("--fps",type=int,default=60); ap.add_argument("--udp-port",type=int,default=None)
    args=ap.parse_args(); app=Dashboard(width=args.w,height=args.h,fullscreen=args.fullscreen,fps=args.fps,udp_port=args.udp_port); app.run()

if __name__=="__main__": main()
