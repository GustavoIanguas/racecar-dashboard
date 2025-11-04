# Dashboard Automotivo (Python + Pygame)

Painel em tempo real para Raspberry Pi 3 (ARM64/ARMHF) e também x86_64, com tema escuro e indicadores:
- **Velocidade (número grande)**  
- **RPM** (barra vertical: verde até 3500, amarelo até 6500, vermelho até 8000)
- **Nível de combustível** (vertical, com marca de reserva)
- **Temperatura da água** (ponteiro, 10–120 °C)
- **Temperatura do óleo** (ponteiro, 60–130 °C)
- **Pressão do óleo** (ponteiro, 0–7 bar)
- **Pressão do turbo** (ponteiro, −1–3 bar)
- **Setas** esquerda/direita (pisca)
- **Freio de mão** (on/off vermelho)
- **Lanterna**, **farol baixo**, **farol alto** (on/off)
- **Voltagem da bateria** (ponteiro, 9–16 V)
- **Sonda lambda** (número 0.6–3.0)

Por enquanto usa **dados simulados**, mas você pode alimentar via **UDP/JSON** (exemplo incluído).

---

## Instalação

### Raspberry Pi OS (Pi 3)
```bash
sudo apt update
sudo apt install -y python3 python3-pip libsdl2-2.0-0 libsdl2-image-2.0-0 \
  libsdl2-ttf-2.0-0 libsdl2-mixer-2.0-0
pip3 install pygame==2.5.2
```

### Ubuntu/Debian (amd64)
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-pygame
# ou: pip3 install pygame==2.5.2
```

> Se estiver em ambiente minimalista (Docker/CLI), instalar as libs SDL2 é importante para evitar erros do Pygame.

---

## Como executar

Janela 1280x720 (PC):
```bash
python3 dashboard.py --w 1280 --h 720 --fps 60
```

Tela cheia (Pi 3):
```bash
python3 dashboard.py --fullscreen --fps 60
```

Receber dados por UDP na porta 5005 (substitui o simulador):
```bash
python3 dashboard.py --fullscreen --udp-port 5005
```

Enviar dados de teste por UDP (em outro terminal):
```bash
python3 udp_demo_sender.py --host 127.0.0.1 --port 5005
```

Formato esperado do JSON (campos opcionais; os não enviados caem no simulador):
```json
{
  "speed_kmh": 123, "rpm": 3456, "fuel_level": 0.42,
  "coolant_temp_c": 90, "oil_temp_c": 100,
  "oil_pressure_bar": 3.2, "turbo_bar": 1.8,
  "batt_v": 13.9, "lambda_value": 1.02,
  "left_blinker": true, "right_blinker": false,
  "handbrake": false, "lights_parking": true,
  "lights_low": true, "lights_high": false
}
```

---

## Dicas de performance (Pi 3)

- Prefira `--fullscreen` para evitar composições extras do window manager.
- Use `--fps 60` (padrão). Se notar esforço, teste `--fps 40`.
- Execute em console (sem ambiente desktop) para reduzir overhead.
- Desative screen blanking no Pi se necessário: `sudo raspi-config` → Display → Screen Blanking.
- Se usar mais de um Pi Zero como “coletor analógico”, envie pacotes UDP com **timestamp** caso precise sincronizar.

---

## Estrutura de código

- O **simulador** gera valores suaves e realistas.
- O **receiver UDP** é *non-blocking*; se chegar JSON válido, substitui o simulador naquele frame.
- **Widgets**:
  - `LinearBar` (RPM), com zonas coloridas (verde/amarelo/vermelho).
  - `VerticalFuel` (combustível), com marca de **reserva** em 12%.
  - `RadialGauge` (ponteiro) para água, óleo, turbo, bateria.
- Ícones vetoriais simples para setas, lanterna/faróis e freio de mão.

---

## Próximos passos (integração com sensores reais)

- Padronizar protocolo UDP entre os Pis (ex.: JSON com `ts_ms` e `source_id`).
- Alternativa: gRPC ou ZeroMQ em rede local.
- Camada de *debounce* e *smoothing* para sinais ruidosos (moving average, filtro IIR leve).
- Watchdog de *staleness* (se não chegar dado por X ms, volta para simulador ou congela último valor).

---

Feito para o projeto **dashboard automotivo**.
