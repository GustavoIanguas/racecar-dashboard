#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automotive Dashboard (Pygame) - AMD64 / ARM64 friendly
- Designed for Raspberry Pi 3 (fullscreen) and desktops (windowed)
- Uses simulated sensor data by default
- Optional UDP JSON input: --udp-port 5005 (see README)

Author: ChatGPT (dashboard automotivo)
"""

import math
import json
import random
import time
import argparse
import socket
from dataclasses import dataclass, asdict

import pygame

# -----------------------------
# Utility & Theme
# -----------------------------

BG = (10, 12, 16)
FG = (220, 230, 240)
MUTED = (120, 130, 140)
GREEN = (30, 200, 90)
YELLOW = (255, 200, 40)
RED = (240, 70, 60)
BLUE = (80, 180, 255)
CYAN = (0, 210, 210)
ORANGE = (255, 140, 0)
DARK = (26, 28, 34)

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def lerp(a, b, t):
    return a + (b - a) * t

# -----------------------------
# Sensor Model & Simulator
# -----------------------------

@dataclass
class Sensors:
    speed_kmh: float = 0.0            # 0..260
    rpm: float = 800.0                # 0..8000
    fuel_level: float = 0.65          # 0..1
    coolant_temp_c: float = 80.0      # 10..120
    oil_temp_c: float = 95.0          # 60..130
    oil_pressure_bar: float = 3.0     # 0..7
    turbo_bar: float = 0.2            # -1..3
    batt_v: float = 13.8              # 9..16
    lambda_value: float = 1.0         # 0.6..3.0
    left_blinker: bool = False
    right_blinker: bool = False
    handbrake: bool = False
    lights_parking: bool = False
    lights_low: bool = False
    lights_high: bool = False

class SensorSimulator:
    def __init__(self):
        self.t0 = time.perf_counter()

    def update(self) -> Sensors:
        t = time.perf_counter() - self.t0
        speed = 120 * (0.5 + 0.5 * math.sin(t * 0.35))
        speed = clamp(speed + random.uniform(-1.2, 1.2), 0, 240)

        rpm = 1000 + 3500 * (0.5 + 0.5 * math.sin(t * 0.9))
        rpm = clamp(rpm + random.uniform(-50, 50), 650, 7800)

        fuel = 0.7 - (t * 0.0005)
        fuel = (fuel % 1.0) if fuel < 0 else clamp(fuel, 0.02, 0.98)

        coolant = clamp(70 + 20 * (0.5 + 0.5 * math.sin(t * 0.2)), 10, 120)
        oil_temp = clamp(85 + 25 * (0.5 + 0.5 * math.sin(t * 0.17 + 1.2)), 60, 130)

        oil_press = clamp(1.0 + (rpm / 8000.0) * 5.5 + 0.1 * math.sin(t * 1.7), 0.4, 6.8)
        turbo = clamp(-0.2 + (rpm / 8000.0) * 2.5 + 0.1 * math.sin(t * 0.7), -0.9, 2.8)

        batt = clamp(13.4 + 0.4 * math.sin(t * 0.3), 9, 16)
        lam = clamp(0.95 + 0.15 * math.sin(t * 1.3), 0.6, 3.0)

        blink = (math.sin(t * math.tau * 0.8) > 0.0)
        left = blink
        right = not blink

        lights_parking = (math.sin(t * 0.15) > 0.6)
        lights_low = (math.sin(t * 0.09 + 1.1) > 0.2)
        lights_high = (math.sin(t * 0.12 - 0.5) > 0.8)
        handbrake = (math.sin(t * 0.07) > 0.95)

        return Sensors(
            speed_kmh=speed, rpm=rpm, fuel_level=fuel,
            coolant_temp_c=coolant, oil_temp_c=oil_temp,
            oil_pressure_bar=oil_press, turbo_bar=turbo,
            batt_v=batt, lambda_value=lam,
            left_blinker=left, right_blinker=right,
            handbrake=handbrake,
            lights_parking=lights_parking,
            lights_low=lights_low, lights_high=lights_high
        )

# -----------------------------
# UDP Sensor Receiver (optional)
# -----------------------------

class UdpReceiver:
    def __init__(self, host="0.0.0.0", port=5005):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.bind((host, port))
        self.last = None

    def poll(self):
        try:
            data, _ = self.sock.recvfrom(8192)
            obj = json.loads(data.decode("utf-8"))
            self.last = obj
        except BlockingIOError:
            pass
        except Exception:
            pass
        return self.last

def sensors_from_dict(obj: dict, fallback: Sensors) -> Sensors:
    d = asdict(fallback)
    for k in d.keys():
        if k in obj:
            d[k] = obj[k]
    return Sensors(**d)

# -----------------------------
# Drawing primitives
# -----------------------------

def draw_text(surf, text, font, color, pos, align="center"):
    tx = font.render(text, True, color)
    r = tx.get_rect()
    if align == "center":
        r.center = pos
    elif align == "topleft":
        r.topleft = pos
    elif align == "topright":
        r.topright = pos
    elif align == "midleft":
        r.midleft = pos
    elif align == "midright":
        r.midright = pos
    else:
        r.topleft = pos
    surf.blit(tx, r)

def draw_roundrect(surface, rect, color, radius=12, width=0):
    x, y, w, h = rect
    pygame.draw.rect(surface, color, (x + radius, y, w - 2*radius, h), width)
    pygame.draw.rect(surface, color, (x, y + radius, w, h - 2*radius), width)
    pygame.draw.circle(surface, color, (x + radius, y + radius), radius, width)
    pygame.draw.circle(surface, color, (x + w - radius, y + radius), radius, width)
    pygame.draw.circle(surface, color, (x + radius, y + h - radius), radius, width)
    pygame.draw.circle(surface, color, (x + w - radius, y + h - radius), radius, width)

def angle_for_value(value, vmin, vmax, amin, amax):
    t = 0.0 if vmax == vmin else (clamp(value, vmin, vmax) - vmin) / (vmax - vmin)
    return lerp(amin, amax, t)

def polar(center, radius, angle_deg):
    ang = math.radians(angle_deg)
    return (center[0] + radius * math.cos(ang), center[1] + radius * math.sin(ang))

def draw_tick_circle(surf, center, radius, amin, amax, step_deg, color=(60,70,80), thick=2, major_every=3):
    tick = 0
    a = amin
    while a <= amax + 0.001:
        inner = radius - (10 if (tick % major_every) else 16)
        outer = radius
        p1 = polar(center, inner, a)
        p2 = polar(center, outer, a)
        pygame.draw.line(surf, color, p1, p2, thick if (tick % major_every) else max(thick+1, 3))
        tick += 1
        a += step_deg

def draw_pointer(surf, center, angle_deg, length, color=FG, width=4):
    tip = polar(center, length, angle_deg)
    pygame.draw.line(surf, color, center, tip, width)
    pygame.draw.circle(surf, color, center, width+1, 0)

def draw_arc_section(surf, rect, start_deg, end_deg, color, width=8):
    pygame.draw.arc(surf, color, rect, math.radians(start_deg), math.radians(end_deg), width)

# -----------------------------
# Widgets
# -----------------------------

class LinearBar:
    def __init__(self, rect, vmin, vmax, zones):
        self.rect = pygame.Rect(rect)
        self.vmin = vmin
        self.vmax = vmax
        self.zones = zones  # list of (until_value, color)

    def draw_bg(self, surf):
        x, y, w, h = self.rect
        pygame.draw.rect(surf, DARK, self.rect, border_radius=12)
        last_val = self.vmin
        for val, color in self.zones:
            top = y + h - int((clamp(val, self.vmin, self.vmax) - self.vmin) / (self.vmax - self.vmin) * h)
            bot = y + h - int((last_val - self.vmin) / (self.vmax - self.vmin) * h)
            zone_h = bot - top
            if zone_h > 0:
                zrect = pygame.Rect(x+3, top+3, w-6, zone_h-6)
                draw_roundrect(surf, zrect, color, radius=8, width=0)
            last_val = val
        pygame.draw.rect(surf, (30, 32, 38), self.rect, width=3, border_radius=12)

    def draw_value(self, surf, value):
        x, y, w, h = self.rect
        level_h = int((clamp(value, self.vmin, self.vmax) - self.vmin) / (self.vmax - self.vmin) * h)
        level_rect = pygame.Rect(x+6, y + h - level_h + 6, w-12, level_h-12)
        draw_roundrect(surf, level_rect, (255, 255, 255, 20), radius=8, width=0)

class VerticalFuel:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)

    def draw(self, surf, fuel_level):
        x, y, w, h = self.rect
        pygame.draw.rect(surf, DARK, self.rect, border_radius=12)
        inner = self.rect.inflate(-10, -10)
        reserve_y = inner.bottom - int(0.12 * inner.height)
        pygame.draw.rect(surf, ORANGE, (inner.left, reserve_y-3, inner.width, 6), border_radius=2)
        level_h = int(clamp(fuel_level, 0, 1) * inner.height)
        level_rect = pygame.Rect(inner.left, inner.bottom - level_h, inner.width, level_h)
        pygame.draw.rect(surf, CYAN, level_rect, border_radius=6)
        pygame.draw.rect(surf, (30, 32, 38), self.rect, width=3, border_radius=12)

class RadialGauge:
    def __init__(self, center, radius, vmin, vmax, amin=-210, amax=30, label="", unit="", arc_zones=None):
        self.center = center
        self.radius = radius
        self.vmin = vmin
        self.vmax = vmax
        self.amin = amin
        self.amax = amax
        self.label = label
        self.unit = unit
        self.arc_zones = arc_zones or []  # list of (from_value, to_value, color)

    def draw(self, surf, fonts, value):
        small = fonts['small']
        draw_tick_circle(surf, self.center, self.radius, self.amin, self.amax, step_deg=12, color=(60,70,80))
        rect = pygame.Rect(0, 0, self.radius*2, self.radius*2)
        rect.center = self.center
        rect.inflate_ip(-16, -16)
        for v0, v1, color in self.arc_zones:
            a0 = angle_for_value(v0, self.vmin, self.vmax, self.amin, self.amax)
            a1 = angle_for_value(v1, self.vmin, self.vmax, self.amin, self.amax)
            draw_arc_section(surf, rect, a0, a1, color, width=10)
        ang = angle_for_value(value, self.vmin, self.vmax, self.amin, self.amax)
        draw_pointer(surf, self.center, ang, self.radius - 18, color=FG, width=5)
        draw_text(surf, self.label, small, MUTED, (self.center[0], self.center[1] + self.radius * 0.55))
        val_str = f"{value:.1f}{self.unit}" if self.unit else f"{int(value)}"
        draw_text(surf, val_str, small, FG, (self.center[0], self.center[1] + self.radius * 0.78))

# -----------------------------
# Icons (vector)
# -----------------------------

def icon_arrow_left(surf, center, on, bg=BG):
    color = GREEN if on else (50, 60, 70)
    x, y = center
    pygame.draw.polygon(surf, color, [(x+28, y-14), (x-14, y), (x+28, y+14)])
    pygame.draw.polygon(surf, bg, [(x+20, y-8), (x-6, y), (x+20, y+8)])

def icon_arrow_right(surf, center, on, bg=BG):
    color = GREEN if on else (50, 60, 70)
    x, y = center
    pygame.draw.polygon(surf, color, [(x-28, y-14), (x+14, y), (x-28, y+14)])
    pygame.draw.polygon(surf, bg, [(x-20, y-8), (x+6, y), (x-20, y+8)])

def icon_parking_brake(surf, center, on):
    x, y = center
    color = RED if on else (70, 50, 50)
    pygame.draw.circle(surf, color, (x, y), 18, 4)
    f = pygame.font.SysFont(None, 26, bold=True)
    draw_text(surf, "P", f, color, (x, y))

def icon_parking_lights(surf, center, on):
    x, y = center
    color = GREEN if on else (50, 60, 70)
    pygame.draw.circle(surf, color, (x-8, y), 8, 2)
    for i in range(-1, 2):
        pygame.draw.arc(surf, color, (x-2, y-14+i*2, 28, 28), math.radians(-35), math.radians(35), 2)

def icon_low_beam(surf, center, on):
    x, y = center
    color = CYAN if on else (45, 55, 60)
    pygame.draw.circle(surf, color, (x-8, y), 8, 2)
    for i in range(-1, 2):
        pygame.draw.line(surf, color, (x+2, y-8+i*8), (x+26, y-4+i*8), 2)

def icon_high_beam(surf, center, on):
    x, y = center
    color = BLUE if on else (45, 55, 60)
    pygame.draw.circle(surf, color, (x-8, y), 8, 2)
    for i in range(-2, 3):
        pygame.draw.line(surf, color, (x+2, y-10+i*5), (x+28, y-10+i*5), 2)

# -----------------------------
# Main Dashboard
# -----------------------------

class Dashboard:
    def __init__(self, width=1280, height=720, fullscreen=False, fps=60, udp_port=None):
        pygame.init()
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("Raspberry Pi Automotive Dashboard")
        self.clock = pygame.time.Clock()
        self.fps = fps
        self.running = True

        self.fonts = {
            'huge': pygame.font.SysFont(None, 160, bold=True),
            'big': pygame.font.SysFont(None, 72, bold=True),
            'med': pygame.font.SysFont(None, 42, bold=True),
            'small': pygame.font.SysFont(None, 28),
            'tiny': pygame.font.SysFont(None, 20),
        }

        self.sim = SensorSimulator()
        self.udp = UdpReceiver(port=udp_port) if udp_port else None

        self.W, self.H = self.screen.get_size()
        self.margin = int(self.W * 0.02)
        self.panel_radius = int(min(self.W, self.H) * 0.16)

        bar_w = int(self.W * 0.06)
        bar_h = int(self.H * 0.7)
        bar_x = self.W - self.margin - bar_w
        bar_y = int((self.H - bar_h) / 2)
        self.rpm_bar = LinearBar(
            rect=(bar_x, bar_y, bar_w, bar_h),
            vmin=0, vmax=8000,
            zones=[(3500, GREEN), (6500, YELLOW), (8000, RED)]
        )

        fuel_w = int(self.W * 0.05)
        fuel_h = int(self.H * 0.5)
        fuel_x = self.margin
        fuel_y = int((self.H - fuel_h) / 2)
        self.fuel = VerticalFuel(rect=(fuel_x, fuel_y, fuel_w, fuel_h))

        cx1 = int(self.margin + self.panel_radius + 60)
        cy1 = int(self.margin + self.panel_radius + 10)
        cx2 = int(self.W - self.margin - self.panel_radius - 60)
        cy2 = cy1

        self.coolant_g = RadialGauge(
            center=(cx1, cy1), radius=self.panel_radius, vmin=10, vmax=120,
            amin=-210, amax=30, label="Água °C",
            arc_zones=[(10, 60, BLUE), (60, 100, GREEN), (100, 120, ORANGE)]
        )
        self.oiltemp_g = RadialGauge(
            center=(cx2, cy2), radius=self.panel_radius, vmin=60, vmax=130,
            amin=-210, amax=30, label="Óleo °C",
            arc_zones=[(60, 80, BLUE), (80, 115, GREEN), (115, 130, ORANGE)]
        )

        cyb = int(self.H - self.margin - self.panel_radius + 30)
        cx_oil = cx1
        cx_turbo = int(self.W * 0.5)
        cx_batt = cx2

        self.oilpress_g = RadialGauge(
            center=(cx_oil, cyb), radius=int(self.panel_radius*0.85), vmin=0, vmax=7,
            amin=-210, amax=30, label="Press. Óleo", unit=" bar",
            arc_zones=[(0, 1.0, RED), (1.0, 2.0, ORANGE), (2.0, 6.0, GREEN), (6.0, 7.0, ORANGE)]
        )
        self.turbo_g = RadialGauge(
            center=(cx_turbo, cyb), radius=int(self.panel_radius*0.85), vmin=-1, vmax=3,
            amin=-210, amax=30, label="Turbo", unit=" bar",
            arc_zones=[(-1.0, 0.0, BLUE), (0.0, 2.2, GREEN), (2.2, 3.0, RED)]
        )
        self.batt_g = RadialGauge(
            center=(cx_batt, cyb), radius=int(self.panel_radius*0.85), vmin=9, vmax=16,
            amin=-210, amax=30, label="Bateria", unit=" V",
            arc_zones=[(9.0, 11.5, RED), (11.5, 12.3, ORANGE), (12.3, 14.6, GREEN), (14.6, 16.0, ORANGE)]
        )

        self.center_area = pygame.Rect(0, 0, int(self.W*0.35), int(self.H*0.34))
        self.center_area.center = (self.W//2, int(self.H*0.34))
        self.icon_row_y = int(self.center_area.bottom + 60)

    def get_sensors(self) -> Sensors:
        base = self.sim.update()
        if self.udp:
            data = self.udp.poll()
            if data:
                base = sensors_from_dict(data, base)
        return base

    def draw_background(self):
        self.screen.fill(BG)
        pygame.draw.rect(self.screen, (18, 20, 26), self.screen.get_rect(), width=6, border_radius=18)
        self.rpm_bar.draw_bg(self.screen)
        draw_roundrect(self.screen, self.center_area, DARK, radius=24, width=0)
        pygame.draw.rect(self.screen, (30, 32, 38), self.center_area, width=3, border_radius=24)
        # draw fuel frame; level will be drawn again with real value
        self.fuel.draw(self.screen, 0.0)

    def draw_speed_and_lambda(self, s: Sensors):
        draw_text(self.screen, f"{int(s.speed_kmh):d}", self.fonts['huge'], FG, (self.center_area.centerx, self.center_area.centery - 10))
        draw_text(self.screen, "km/h", self.fonts['small'], MUTED, (self.center_area.centerx, int(self.center_area.centery + self.center_area.height*0.18)))
        box = pygame.Rect(0, 0, int(self.center_area.width*0.55), 64)
        box.centerx = self.center_area.centerx
        box.top = self.center_area.bottom + 8
        draw_roundrect(self.screen, box, DARK, radius=16, width=0)
        pygame.draw.rect(self.screen, (30, 32, 38), box, width=2, border_radius=16)
        draw_text(self.screen, f"λ {s.lambda_value:.2f}", self.fonts['big'], CYAN, box.center)

    def draw_icons(self, s: Sensors):
        spacing = int(self.W * 0.09)
        start_x = int(self.W * 0.5) - spacing*2
        y = self.icon_row_y
        icon_arrow_left(self.screen, (start_x, y), s.left_blinker)
        icon_parking_lights(self.screen, (start_x + spacing, y), s.lights_parking)
        icon_low_beam(self.screen, (start_x + 2*spacing, y), s.lights_low)
        icon_high_beam(self.screen, (start_x + 3*spacing, y), s.lights_high)
        icon_arrow_right(self.screen, (start_x + 4*spacing, y), s.right_blinker)
        icon_parking_brake(self.screen, (start_x + 5*spacing, y), s.handbrake)

    def draw(self, s: Sensors):
        self.draw_background()
        self.rpm_bar.draw_value(self.screen, s.rpm)
        draw_text(self.screen, "RPM", self.fonts['small'], MUTED, (self.rpm_bar.rect.centerx, self.rpm_bar.rect.bottom + 20))
        self.fuel.draw(self.screen, s.fuel_level)
        draw_text(self.screen, "Fuel", self.fonts['small'], MUTED, (self.fuel.rect.centerx, self.fuel.rect.bottom + 20))
        draw_text(self.screen, "E", self.fonts['tiny'], FG, (self.fuel.rect.centerx, self.fuel.rect.bottom + 40))
        draw_text(self.screen, "F", self.fonts['tiny'], FG, (self.fuel.rect.centerx, self.fuel.rect.top - 14))
        self.draw_speed_and_lambda(s)
        self.coolant_g.draw(self.screen, self.fonts, s.coolant_temp_c)
        self.oiltemp_g.draw(self.screen, self.fonts, s.oil_temp_c)
        self.oilpress_g.draw(self.screen, self.fonts, s.oil_pressure_bar)
        self.turbo_g.draw(self.screen, self.fonts, s.turbo_bar)
        self.batt_g.draw(self.screen, self.fonts, s.batt_v)
        self.draw_icons(s)
        draw_text(self.screen, "UDP JSON opcional em :5005 • ESC para sair",
                  self.fonts['tiny'], MUTED, (self.W//2, self.H - 18))

    def run(self):
        while self.running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    self.running = False
            s = self.get_sensors()
            self.draw(s)
            pygame.display.flip()
            self.clock.tick(self.fps)
        pygame.quit()

def main():
    parser = argparse.ArgumentParser(description="Automotive Dashboard (Raspberry Pi ready)")
    parser.add_argument("--w", type=int, default=1280, help="Largura da janela (ignore em fullscreen)")
    parser.add_argument("--h", type=int, default=720, help="Altura da janela (ignore em fullscreen)")
    parser.add_argument("--fullscreen", action="store_true", help="Tela cheia")
    parser.add_argument("--fps", type=int, default=60, help="Frames por segundo")
    parser.add_argument("--udp-port", type=int, default=None, help="Porta UDP para receber JSON de sensores")
    args = parser.parse_args()
    app = Dashboard(width=args.w, height=args.h, fullscreen=args.fullscreen, fps=args.fps, udp_port=args.udp_port)
    app.run()

if __name__ == "__main__":
    main()
