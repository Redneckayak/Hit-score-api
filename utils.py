import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

def safe_float_conversion(value, default=0.0) -> float:
    """Safely convert a value to float with a default fallback"""
    try:
        if pd.isna(value) or value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int_conversion(value, default=0) -> int:
    """Safely convert a value to int with a default fallback"""
    try:
        if pd.isna(value) or value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def format_player_name(name: str) -> str:
    """Format player name for consistent display"""
    if not name or pd.isna(name):
        return "Unknown Player"
    
    # Remove extra whitespace and title case
    return ' '.join(name.strip().split()).title()

def format_team_abbreviation(team_abbr: str) -> str:
    """Format team abbreviation for consistent display"""
    if not team_abbr or pd.isna(team_abbr):
        return "UNK"
    
    return team_abbr.upper().strip()

def calculate_hits_per_game(hits: int, games: int) -> float:
    """Calculate hits per game with safe division"""
    if games <= 0:
        return 0.0
    return round(hits / games, 3)

def get_performance_tier(score: float) -> str:
    """Get performance tier based on composite score"""
    if score >= 7.0:
        return "Excellent"
    elif score >= 5.5:
        return "Good"
    elif score >= 4.0:
        return "Average"
    elif score >= 2.5:
        return "Below Average"
    else:
        return "Poor"

def get_performance_color(score: float) -> str:
    """Get color code for performance visualization"""
    if score >= 7.0:
        return "#28a745"  # Green
    elif score >= 5.5:
        return "#ffc107"  # Yellow
    elif score >= 4.0:
        return "#fd7e14"  # Orange
    else:
        return "#dc3545"  # Red

def validate_date_range(start_date: datetime, end_date: datetime) -> Tuple[datetime, datetime]:
    """Validate and adjust date range for data fetching"""
    now = datetime.now()
    
    # Ensure start_date is not in the future
    if start_date > now:
        start_date = now - timedelta(days=30)
    
    # Ensure end_date is not in the future
    if end_date > now:
        end_date = now
    
    # Ensure start_date is before end_date
    if start_date >= end_date:
        start_date = end_date - timedelta(days=1)
    
    return start_date, end_date

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize a dataframe"""
    if df.empty:
        return df
    
    # Remove duplicate rows
    df = df.drop_duplicates()
    
    # Clean string columns
    string_columns = df.select_dtypes(include=['object']).columns
    for col in string_columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace('nan', '')
        df[col] = df[col].replace('', np.nan)
    
    # Fill numeric NaN values with 0
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    df[numeric_columns] = df[numeric_columns].fillna(0)
    
    return df

def get_current_mlb_season() -> int:
    """Get the current MLB season year"""
    return 2025

def is_mlb_season_active() -> bool:
    """Check if MLB season is currently active"""
    now = datetime.now()
    
    # MLB season roughly runs from late March to late October
    if now.month >= 4 and now.month <= 10:
        return True
    elif now.month == 3 and now.day >= 20:
        return True
    elif now.month == 11 and now.day <= 15:
        return True
    else:
        return False

def format_batting_average(avg: float) -> str:
    """Format batting average for display"""
    if pd.isna(avg) or avg == 0:
        return ".000"
    
    # Format to 3 decimal places without leading zero
    formatted = f"{avg:.3f}"
    if formatted.startswith("0."):
        formatted = formatted[1:]  # Remove leading zero
    
    return formatted

def get_position_group(position: str) -> str:
    """Group positions into categories"""
    if not position or pd.isna(position):
        return "Unknown"
    
    position = position.upper().strip()
    
    if position in ['C']:
        return "Catcher"
    elif position in ['1B']:
        return "First Base"
    elif position in ['2B']:
        return "Second Base"
    elif position in ['3B']:
        return "Third Base"
    elif position in ['SS']:
        return "Shortstop"
    elif position in ['LF', 'CF', 'RF', 'OF']:
        return "Outfield"
    elif position in ['DH']:
        return "Designated Hitter"
    elif position in ['P']:
        return "Pitcher"
    else:
        return "Utility"

def create_error_message(error_type: str, details: str = "") -> str:
    """Create a standardized error message"""
    error_messages = {
        'api_error': "Unable to connect to MLB data service. Please check your internet connection and try again.",
        'no_games': "No MLB games are scheduled for today. Please check back during the regular season.",
        'no_data': "No player data available for the selected criteria. Try adjusting your filters.",
        'invalid_date': "Invalid date range specified. Please select a valid date range.",
        'rate_limit': "API rate limit exceeded. Please wait a moment and try again.",
        'timeout': "Request timed out. Please try again in a few moments.",
        'general': "An unexpected error occurred. Please try again."
    }
    
    base_message = error_messages.get(error_type, error_messages['general'])
    
    if details:
        return f"{base_message}\n\nDetails: {details}"
    
    return base_message
