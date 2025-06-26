import os
import json
from datetime import datetime
from pathlib import Path

class DataBackupManager:
    def __init__(self, backup_dir: str = "data/backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.prediction_file = Path("data/prediction_history.json")
        self.top_3_file = Path("data/top_3_picks_history.json")

    def create_daily_backup(self):
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            if self.prediction_file.exists():
                backup_path = self.backup_dir / f"predictions_{today}.json"
                with open(self.prediction_file, "r") as src, open(backup_path, "w") as dst:
                    dst.write(src.read())
            if self.top_3_file.exists():
                backup_path = self.backup_dir / f"top3_{today}.json"
                with open(self.top_3_file, "r") as src, open(backup_path, "w") as dst:
                    dst.write(src.read())
            print("✅ Daily backups created.")
        except Exception as e:
            print(f"❌ Error creating backup: {e}")

    def auto_record_verification(self) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            if not self.prediction_file.exists():
                return False
            with open(self.prediction_file, "r") as f:
                data = json.load(f)
            return today in data
        except Exception as e:
            print(f"❌ Error verifying predictions: {e}")
            return False
