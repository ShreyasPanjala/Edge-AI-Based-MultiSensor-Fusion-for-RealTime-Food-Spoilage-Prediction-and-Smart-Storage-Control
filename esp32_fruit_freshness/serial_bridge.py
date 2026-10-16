"""ESP32 Hardware Serial-to-Web Bridge.

Connects to the ESP32 microcontroller via USB Serial (115200 baud),
reads incoming sensor telemetry (MQ135, Temperature, Humidity),
and pushes the readings directly to the FastAPI backend at http://127.0.0.1:8000/api/sensor-data.
"""

import sys
import time
import json
import logging
import urllib.request
import urllib.error
import serial
import serial.tools.list_ports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ESP32_Bridge")

BACKEND_URL = "http://127.0.0.1:8000/api/sensor-data"
BAUD_RATE = 115200


def find_esp32_port() -> str | None:
    """Scan available COM ports and identify the ESP32 device."""
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None

    # Priority keywords for ESP32 USB-to-UART chips (CP210x, CH340, FTDI, ESP32)
    keywords = ["cp210", "ch340", "ch341", "usb serial", "esp32", "uart", "ftdi", "silicon labs"]

    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        for kw in keywords:
            if kw in desc or kw in hwid:
                logger.info(f"Found candidate ESP32 port: {p.device} ({p.description})")
                return p.device

    # Fallback to the first available COM port
    first_port = ports[0].device
    logger.info(f"Using available COM port: {first_port} ({ports[0].description})")
    return first_port


def post_telemetry(mq135: float, temperature: float, humidity: float) -> dict | None:
    """Send sensor reading to the local backend."""
    payload = {
        "mq135": float(mq135),
        "temperature": float(temperature),
        "humidity": float(humidity),
    }

    req = urllib.request.Request(
        BACKEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.URLError as err:
        logger.warning(f"Could not forward to backend ({BACKEND_URL}): {err}")
        return None


def run_bridge(target_port: str | None = None) -> None:
    """Main serial reading and forwarding loop."""
    print("=" * 70)
    print("  ESP32 Edge-AI E-Nose Hardware Serial Bridge")
    print(f"  Target Backend: {BACKEND_URL}")
    print(f"  Baud Rate:      {BAUD_RATE}")
    print("=" * 70)

    while True:
        port = target_port or find_esp32_port()
        if not port:
            print("\r[SCANNING] No USB Serial device detected. Plug in your ESP32 now...", end="", flush=True)
            time.sleep(2.0)
            continue

        print(f"\n[CONNECTING] Opening serial port {port} at {BAUD_RATE} baud...")
        try:
            with serial.Serial(port, BAUD_RATE, timeout=2.0) as ser:
                print(f"[CONNECTED] Successfully connected to {port}!")
                print("[STREAMING] Waiting for banana sensor readings...\n")

                curr_mq135 = None
                curr_temp = 25.0
                curr_hum = 65.0

                while True:
                    line = ser.readline().decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    # Print raw hardware debug line
                    print(f"  [RAW ESP32] {line}")

                    # 1. Parse JSON formatted lines
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            pkt = json.loads(line)
                            mq = float(pkt.get("mq135", 0))
                            temp = float(pkt.get("temperature", 25.0))
                            hum = float(pkt.get("humidity", 65.0))

                            res = post_telemetry(mq, temp, hum)
                            if res:
                                pred = res.get("prediction", "Unknown")
                                print(f"  ==> [POSTED TO WEBSITE] MQ135: {mq} ADC | Temp: {temp}°C | Hum: {hum}% | Prediction: {pred}\n")
                        except Exception as e:
                            logger.debug(f"JSON parse error: {e}")
                        continue

                    # 2. Parse key-value lines from esp32_fruit_freshness.ino
                    if line.startswith("MQ135:"):
                        try:
                            curr_mq135 = float(line.split("MQ135:")[1].strip())
                        except ValueError:
                            pass
                    elif line.startswith("Temperature:"):
                        val_str = line.split("Temperature:")[1].strip()
                        if "failed" not in val_str.lower():
                            try:
                                curr_temp = float(val_str)
                            except ValueError:
                                pass
                    elif line.startswith("Humidity:"):
                        val_str = line.split("Humidity:")[1].strip()
                        if "failed" not in val_str.lower():
                            try:
                                curr_hum = float(val_str)
                            except ValueError:
                                pass
                    elif line == "---" or line.startswith("===") or line.startswith("Prediction:"):
                        if curr_mq135 is not None:
                            res = post_telemetry(curr_mq135, curr_temp, curr_hum)
                            if res:
                                pred = res.get("prediction", "Unknown")
                                print(f"  ==> [POSTED TO WEBSITE] MQ135: {curr_mq135} ADC | Temp: {curr_temp}°C | Hum: {curr_hum}% | Prediction: {pred}\n")
                            curr_mq135 = None

        except serial.SerialException as err:
            logger.warning(f"Serial port {port} disconnected: {err}")
            print("\n[DISCONNECTED] Device unplugged. Reconnecting in 3s...")
            time.sleep(3.0)
        except KeyboardInterrupt:
            print("\n[STOPPED] Serial bridge terminated by user.")
            sys.exit(0)


if __name__ == "__main__":
    cli_port = sys.argv[1] if len(sys.argv) > 1 else None
    run_bridge(cli_port)
