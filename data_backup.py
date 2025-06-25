import json
import os
import shutil
from datetime import datetime, date
from typing import Dict, List

class DataBackupManager:
    """Manages automated backups and data integrity checks for MLB predictions"""
    
    def __init__(self):
        self.backup_dir = 'data/backups'
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Create backup directory if it doesn't exist"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def create_daily_backup(self):
        """Create timestamped backup of all prediction data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_folder = os.path.join(self.backup_dir, f'backup_{timestamp}')
        os.makedirs(backup_folder, exist_ok=True)
        
        # Backup critical files
        files_to_backup = [
            'data/prediction_history.json',
            'data/top_3_picks_history.json',
            'data/simple_rankings_cache.json',
            'data/rankings_cache.json'
        ]
        
        backed_up = []
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                backup_path = os.path.join(backup_folder, os.path.basename(file_path))
                shutil.copy2(file_path, backup_path)
                backed_up.append(file_path)
        
        print(f"Backup created: {backup_folder}")
        print(f"Files backed up: {len(backed_up)}")
        return backup_folder
    
    def verify_data_integrity(self) -> Dict[str, bool]:
        """Verify data integrity and check for missing dates"""
        integrity_report = {
            'prediction_history_exists': False,
            'top_3_picks_exists': False,
            'has_recent_data': False,
            'no_missing_dates': True,
            'all_elite_players': True
        }
        
        try:
            # Check prediction history exists
            if os.path.exists('data/prediction_history.json'):
                integrity_report['prediction_history_exists'] = True
                
                with open('data/prediction_history.json', 'r') as f:
                    predictions = json.load(f)
                
                # Check for recent data (within last 3 days)
                today = date.today()
                recent_dates = [(today.replace(day=today.day-i)).isoformat() for i in range(3)]
                has_recent = any(d in predictions for d in recent_dates)
                integrity_report['has_recent_data'] = has_recent
                
                # Check for missing consecutive dates
                sorted_dates = sorted(predictions.keys())
                if len(sorted_dates) >= 2:
                    for i in range(len(sorted_dates)-1):
                        current = date.fromisoformat(sorted_dates[i])
                        next_date = date.fromisoformat(sorted_dates[i+1])
                        if (next_date - current).days > 2:  # Allow 1 day gap for off days
                            integrity_report['no_missing_dates'] = False
                            print(f"Gap detected between {sorted_dates[i]} and {sorted_dates[i+1]}")
                
                # Check all predictions are elite (score >= 2.0)
                for date_key, daily_preds in predictions.items():
                    for player_id, pred in daily_preds.items():
                        if pred.get('hit_score', 0) < 2.0:
                            integrity_report['all_elite_players'] = False
                            break
            
            # Check top 3 picks exists
            if os.path.exists('data/top_3_picks_history.json'):
                integrity_report['top_3_picks_exists'] = True
        
        except Exception as e:
            print(f"Error during integrity check: {e}")
        
        return integrity_report
    
    def auto_record_verification(self):
        """Verify auto-recording is working properly"""
        today = date.today().isoformat()
        
        # Check if today's predictions were recorded
        try:
            with open('data/prediction_history.json', 'r') as f:
                predictions = json.load(f)
            
            if today in predictions:
                count = len(predictions[today])
                print(f"Today's predictions recorded: {count} elite players")
                return True
            else:
                print(f"WARNING: No predictions recorded for {today}")
                return False
        except Exception as e:
            print(f"Error checking auto-recording: {e}")
            return False
    
    def emergency_recovery(self, target_date: str) -> bool:
        """Attempt to recover missing data from backups"""
        print(f"Attempting emergency recovery for {target_date}")
        
        # Look for backups containing the target date
        backup_folders = [d for d in os.listdir(self.backup_dir) if d.startswith('backup_')]
        backup_folders.sort(reverse=True)  # Most recent first
        
        for backup_folder in backup_folders:
            backup_path = os.path.join(self.backup_dir, backup_folder, 'prediction_history.json')
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r') as f:
                        backup_predictions = json.load(f)
                    
                    if target_date in backup_predictions:
                        # Merge missing data
                        with open('data/prediction_history.json', 'r') as f:
                            current_predictions = json.load(f)
                        
                        current_predictions[target_date] = backup_predictions[target_date]
                        
                        with open('data/prediction_history.json', 'w') as f:
                            json.dump(current_predictions, f, indent=2)
                        
                        print(f"Successfully recovered {target_date} from {backup_folder}")
                        return True
                except Exception as e:
                    print(f"Error reading backup {backup_folder}: {e}")
        
        print(f"Could not recover data for {target_date}")
        return False
    
    def cleanup_old_backups(self, keep_days: int = 30):
        """Remove backups older than specified days"""
        if not os.path.exists(self.backup_dir):
            return
        
        cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        
        for backup_folder in os.listdir(self.backup_dir):
            backup_path = os.path.join(self.backup_dir, backup_folder)
            if os.path.isdir(backup_path) and backup_folder.startswith('backup_'):
                if os.path.getctime(backup_path) < cutoff_date:
                    shutil.rmtree(backup_path)
                    print(f"Removed old backup: {backup_folder}")