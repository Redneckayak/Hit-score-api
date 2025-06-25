#!/usr/bin/env python3
"""
Daily verification script to ensure data integrity and prevent loss.
Runs automated checks and alerts on any issues.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from data_backup import DataBackupManager

def run_daily_verification():
    """Run comprehensive daily verification checks"""
    print(f"Running daily verification for {date.today()}")
    
    backup_manager = DataBackupManager()
    issues_found = []
    
    # 1. Check if today's predictions were recorded
    today = date.today().isoformat()
    try:
        with open('data/prediction_history.json', 'r') as f:
            predictions = json.load(f)
        
        if today not in predictions:
            issues_found.append(f"CRITICAL: No predictions recorded for {today}")
        else:
            count = len(predictions[today])
            if count == 0:
                issues_found.append(f"WARNING: Zero predictions recorded for {today}")
            elif count < 10:
                issues_found.append(f"WARNING: Only {count} predictions recorded for {today} (expected 15-25)")
            else:
                print(f"✓ {count} predictions recorded for {today}")
    except Exception as e:
        issues_found.append(f"CRITICAL: Cannot read prediction history - {e}")
    
    # 2. Check for data gaps in last 7 days
    try:
        sorted_dates = sorted(predictions.keys(), reverse=True)
        last_7_days = [(date.today() - timedelta(days=i)).isoformat() for i in range(7)]
        
        missing_dates = []
        for check_date in last_7_days:
            if check_date not in predictions:
                # Check if it's a known off day (Sunday/Monday MLB off days)
                check_day = datetime.fromisoformat(check_date).weekday()
                if check_day not in [6, 0]:  # Not Sunday or Monday
                    missing_dates.append(check_date)
        
        if missing_dates:
            issues_found.append(f"WARNING: Missing predictions for {missing_dates}")
        else:
            print("✓ No missing dates in last 7 days")
    except Exception as e:
        issues_found.append(f"ERROR: Cannot check for data gaps - {e}")
    
    # 3. Verify Top 3 picks consistency
    try:
        with open('data/top_3_picks_history.json', 'r') as f:
            top_3_data = json.load(f)
        
        for date_key in sorted_dates[:7]:  # Last 7 dates
            if date_key in predictions and date_key not in top_3_data:
                issues_found.append(f"WARNING: Missing Top 3 picks for {date_key}")
        
        print("✓ Top 3 picks consistency verified")
    except Exception as e:
        issues_found.append(f"ERROR: Cannot verify Top 3 picks - {e}")
    
    # 4. Check data quality (elite players only)
    try:
        for date_key in sorted_dates[:3]:  # Last 3 dates
            for player_id, pred in predictions[date_key].items():
                hit_score = pred.get('hit_score', 0)
                if hit_score < 2.0:
                    issues_found.append(f"WARNING: Non-elite player in {date_key} - {pred['player_name']} ({hit_score})")
        
        print("✓ Data quality verified (elite players only)")
    except Exception as e:
        issues_found.append(f"ERROR: Cannot verify data quality - {e}")
    
    # 5. Verify backups exist
    try:
        backup_dir = 'data/backups'
        if not os.path.exists(backup_dir):
            issues_found.append("CRITICAL: Backup directory missing")
        else:
            backups = [d for d in os.listdir(backup_dir) if d.startswith('backup_')]
            if len(backups) == 0:
                issues_found.append("CRITICAL: No backups found")
            else:
                # Check if we have a recent backup (within 24 hours)
                latest_backup = max(backups)
                backup_time = datetime.strptime(latest_backup.replace('backup_', ''), '%Y%m%d_%H%M%S')
                if (datetime.now() - backup_time).total_seconds() > 86400:  # 24 hours
                    issues_found.append("WARNING: No recent backup (older than 24 hours)")
                else:
                    print(f"✓ Recent backup found: {latest_backup}")
    except Exception as e:
        issues_found.append(f"ERROR: Cannot verify backups - {e}")
    
    # 6. Run integrity check
    try:
        integrity_report = backup_manager.verify_data_integrity()
        failed_checks = [k for k, v in integrity_report.items() if not v]
        if failed_checks:
            issues_found.append(f"WARNING: Failed integrity checks: {failed_checks}")
        else:
            print("✓ All integrity checks passed")
    except Exception as e:
        issues_found.append(f"ERROR: Cannot run integrity check - {e}")
    
    # 7. Create daily backup if none exists
    try:
        backup_manager.create_daily_backup()
        print("✓ Daily backup created")
    except Exception as e:
        issues_found.append(f"ERROR: Cannot create backup - {e}")
    
    # Summary
    if issues_found:
        print("\n❌ ISSUES DETECTED:")
        for issue in issues_found:
            print(f"  • {issue}")
        
        # Write issues to log file
        with open('data/verification_log.txt', 'a') as f:
            f.write(f"\n{datetime.now().isoformat()} - Verification Issues:\n")
            for issue in issues_found:
                f.write(f"  {issue}\n")
        
        return False
    else:
        print("\n✅ All verification checks passed")
        with open('data/verification_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - All checks passed\n")
        return True

def auto_fix_issues():
    """Attempt to automatically fix common issues"""
    print("Attempting auto-fix for common issues...")
    
    backup_manager = DataBackupManager()
    today = date.today().isoformat()
    
    # Try to recover missing today's data from cache
    if not backup_manager.auto_record_verification():
        print("Attempting to generate today's predictions from cache...")
        try:
            from simple_rankings import SimpleMLBRankings
            rankings_system = SimpleMLBRankings()
            fresh_rankings = rankings_system.get_rankings(force_refresh=True)
            if fresh_rankings is not None and not fresh_rankings.empty:
                print(f"Successfully generated {len(fresh_rankings)} rankings for today")
            else:
                print("Failed to generate fresh rankings")
        except Exception as e:
            print(f"Auto-fix failed: {e}")

if __name__ == "__main__":
    # Run verification
    success = run_daily_verification()
    
    # If issues found, attempt auto-fix
    if not success:
        auto_fix_issues()
        # Re-run verification after auto-fix
        print("\nRe-running verification after auto-fix...")
        run_daily_verification()
    
    sys.exit(0 if success else 1)