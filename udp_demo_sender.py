#!/usr/bin/env python3
# Envia pacotes UDP com JSON de sensores para testar o dashboard (substitui o simulador).
# Exemplo de uso: python3 udp_demo_sender.py --host 127.0.0.1 --port 5005

import time
import json
import math
import argparse
import socket
import random

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5005)
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t0 = time.perf_counter()

    while True:
        t = time.perf_counter() - t0
        payload = {
            "speed_kmh": 100 + 60 * (0.5 + 0.5 * math.sin(t*0.6)),
            "rpm": 1200 + 5000 * (0.5 + 0.5 * math.sin(t*1.1)),
            "fuel_level": 0.5 + 0.4 * math.sin(t*0.2),
            "coolant_temp_c": 80 + 10 * math.sin(t*0.3),
            "oil_temp_c": 95 + 12 * math.sin(t*0.27),
            "oil_pressure_bar": 2.0 + 2.5 * (0.5 + 0.5 * math.sin(t*0.9)),
            "turbo_bar": -0.1 + 2.2 * (0.5 + 0.5 * math.sin(t*0.8)),
            "batt_v": 13.8 + 0.3 * math.sin(t*0.25),
            "lambda_value": 1.0 + 0.1 * math.sin(t*1.5),
            "left_blinker": (math.sin(t*5) > 0),
            "right_blinker": (math.sin(t*5) <= 0),
            "handbrake": (math.sin(t*0.7) > 0.92),
            "lights_parking": True,
            "lights_low": True,
            "lights_high": (math.sin(t*0.3) > 0.85)
        }
        data = json.dumps(payload).encode("utf-8")
        sock.sendto(data, (args.host, args.port))
        time.sleep(0.033)  # ~30 Hz

if __name__ == "__main__":
    main()
