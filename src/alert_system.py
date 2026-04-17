import datetime
import logging
import os
import time
import cv2  # 🔑 CRITICAL: This was missing!

# 🔑 TELEGRAM CONFIG (Optional - leave blank if not using)
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" if TELEGRAM_BOT_TOKEN else None

os.makedirs("data/logs/snapshots", exist_ok=True)

logging.basicConfig(
    filename="data/logs/wildlife_alerts.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

class AlertSystem:
    def __init__(self, cooldown_sec: int = 10):
        self.cooldown = cooldown_sec
        self.last_alert = {}

    def trigger(self, animal: str, conf: float, bbox: list, frame=None):
        now = time.time()
        last = self.last_alert.get(animal, 0)
        if now - last < self.cooldown:
            return  # Skip duplicate alerts within cooldown
        self.last_alert[animal] = now

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"⚠️ {animal.upper()} detected (Conf: {conf:.2f}) at {ts}"
        print(f"\033[91m{msg}\033[0m")  # Red console output
        logging.info(msg)

        # Save snapshot if frame provided
        if frame is not None:
            try:
                fname = f"data/logs/snapshots/{animal}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(fname, frame)  # ✅ Now cv2 is defined!
                logging.debug(f"💾 Snapshot saved: {fname}")
            except Exception as e:
                logging.error(f"❌ Failed to save snapshot: {e}")

        # Optional: Send Telegram alert (if configured)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            self._send_telegram(msg, frame)

    def _send_telegram(self, msg: str, frame=None):
        """Internal method - skip if not using Telegram"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return
        try:
            import requests
            if frame is not None:
                fname = f"data/logs/snapshots/telegram_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(fname, frame)
                with open(fname, "rb") as img:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                        data={"chat_id": TELEGRAM_CHAT_ID, "caption": msg},
                        files={"photo": img},
                        timeout=10
                    )
            else:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
                    timeout=10
                )
        except Exception as e:
            logging.error(f"📱 Telegram send failed: {e}")