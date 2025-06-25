import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from daily_cache import DailyCacheManager
from data_fetcher import MLBDataFetcher

def style_hit_score(score):
    """Style hit score with green color and better formatting"""
    if score >= 3.0:
        return f'<span style="background-color: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{score:.2f}</span>'
    elif score >= 2.5:
        return f'<span style="background-color: #fd7e14; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{score:.2f}</span>'
    elif score >= 2.0:
        return f'<span style="background-color: #6f42c1; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{score:.2f}</span>'
    else:
        return f'<span style="background-color: #6c757d; color: white; padding: 4px 8px; border-radius: 4px;">{score:.2f}</span>'

def get_team_logo_url(team_abbr):
    """Get official MLB team logo URL from ESPN"""
    team_mapping = {
        'LAA': 'angels', 'HOU': 'astros', 'OAK': 'athletics', 'TOR': 'bluejays',
        'ATL': 'braves', 'MIL': 'brewers', 'STL': 'cardinals', 'CHC': 'cubs',
        'ARI': 'diamondbacks', 'LAD': 'dodgers', 'SF': 'giants', 'CLE': 'guardians',
        'SEA': 'mariners', 'MIA': 'marlins', 'NYM': 'mets', 'WSH': 'nationals',
        'BAL': 'orioles', 'SD': 'padres', 'PHI': 'phillies', 'PIT': 'pirates',
        'TEX': 'rangers', 'TB': 'rays', 'BOS': 'redsox', 'CIN': 'reds',
        'COL': 'rockies', 'KC': 'royals', 'DET': 'tigers', 'MIN': 'twins',
        'CWS': 'whitesox', 'NYY': 'yankees'
    }
    
    espn_name = team_mapping.get(team_abbr, team_abbr.lower())
    return f"https://a.espncdn.com/i/teamlogos/mlb/500/{espn_name}.png"

def create_team_logo_html(team_abbr):
    """Create HTML for team logo display"""
    logo_url = get_team_logo_url(team_abbr)
    if logo_url:
        return f'<img src="{logo_url}" width="30" height="30" style="vertical-align: middle;" title="{team_abbr}">'
    else:
        return f'<strong>{team_abbr}</strong>'

def main():
    st.set_page_config(
        page_title="MLB Hit Score Rankings",
        page_icon="⚾",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Header with full-width logo
    try:
        st.image("attached_assets/file_00000000037861f89e3668cd1c9b6a85.png", use_container_width=True)
    except:
        try:
            st.image("assets/hit_score_logo.png", use_container_width=True)
        except:
            st.markdown("<h1 style='text-align: center; font-size: 3em; margin: 20px 0;'>⚾ Hit Score ⚾</h1>", unsafe_allow_html=True)
    
    st.markdown("<p style='text-align: center; margin-top: 10px;'><strong>Optimized daily rankings with 2025 season data</strong></p>", unsafe_allow_html=True)
    
    # Initialize optimized cache manager
    cache_manager = DailyCacheManager()
    
    # Sidebar controls
    st.sidebar.title("Controls")
    
    # Separate refresh buttons for different data types
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("📊 Daily Stats", type="secondary", help="Refresh batting averages & season stats (6 AM ET schedule)"):
            cache_manager.get_complete_rankings(force_refresh_daily=True)
            st.rerun()
    
    with col2:
        if st.button("⚾ Lineups", type="primary", help="Refresh today's lineups & pitcher matchups (hourly)"):
            cache_manager.get_complete_rankings(force_refresh_matchups=True)
            st.rerun()
    
    # Toggle for starting lineups only
    show_starters_only = st.sidebar.checkbox(
        "Show Starting Lineups Only", 
        value=True, 
        help="Filter to only show players in today's starting lineups"
    )
    
    # Cache status display
    cache_status = cache_manager.get_cache_status()
    with st.sidebar.expander("Cache Status"):
        st.write("**Daily Data (Batting Averages)**")
        daily_last = cache_status['daily_cache']['last_update']
        st.write(f"Last Update: {daily_last[:19] if daily_last else 'Never'}")
        st.write(f"Status: {'Expired' if cache_status['daily_cache']['expired'] else 'Current'}")
        st.write(f"Schedule: {cache_status['daily_cache']['next_update']}")
        
        st.write("**Matchup Data (Lineups)**")
        matchup_last = cache_status['matchup_cache']['last_update']
        st.write(f"Last Update: {matchup_last[:19] if matchup_last else 'Never'}")
        st.write(f"Status: {'Expired' if cache_status['matchup_cache']['expired'] else 'Current'}")
        st.write(f"Schedule: {cache_status['matchup_cache']['next_update']}")
    
    # Formula explanation
    with st.expander("📊 Hit Score Formula & Optimization"):
        st.markdown("""
        **Optimized Data Strategy:**
        - **Daily Data (6 AM ET):** Batting averages, season stats, player performance data
        - **Hourly Updates:** Starting lineups, pitcher matchups, game schedules
        
        **Hit Score Formula (Equal 33.3% weighting):**
        1. **Player Hotness:** Recent hits over 5, 10, and 20 games
        2. **Pitcher Difficulty:** Opposing pitcher's season OBA 
        3. **Player Skill:** Batter's 2025 season batting average
        
        **Score Ranges:**
        - 🔥 **3.0+:** Elite picks with highest probability
        - 🎯 **2.5-2.9:** Strong picks with good probability  
        - ⚡ **2.0-2.4:** Solid picks worth considering
        - 📊 **Under 2.0:** Lower probability picks
        """)
    
    # Get rankings using optimized two-tier caching
    try:
        rankings_df = cache_manager.get_complete_rankings()
        
        if rankings_df is None or rankings_df.empty:
            st.error("Unable to load MLB data. The service may be temporarily unavailable.")
            st.info("Try refreshing the daily stats or lineups, or check back in a few minutes.")
            st.stop()
        
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Players", len(rankings_df))
        
        with col2:
            avg_score = rankings_df['hit_score'].mean()
            st.metric("📈 Avg Hit Score", f"{avg_score:.2f}")
        
        with col3:
            elite_count = len(rankings_df[rankings_df['hit_score'] >= 2.5])
            st.metric("🔥 Elite (2.5+)", elite_count)
        
        with col4:
            games_today = len(rankings_df['team'].unique()) // 2
            st.metric("⚾ Games Today", games_today)
        
        # Main rankings table
        st.markdown("### 🏆 Today's Hit Score Rankings")
        st.markdown("*Daily stats cached at 6 AM ET • Lineups updated hourly*")
        
        # Prepare display dataframe
        display_df = rankings_df.copy()
        
        # Add team logos
        display_df['team_logo'] = display_df['team_abbr'].apply(create_team_logo_html)
        
        # Format columns for display
        display_df['hit_score_formatted'] = display_df['hit_score'].apply(style_hit_score)
        display_df['batting_avg_formatted'] = display_df['batting_avg'].apply(lambda x: f"{x:.3f}")
        
        # Select and rename columns for display
        final_df = display_df[[
            'team_logo', 'player_name', 'hit_score_formatted', 'batting_avg_formatted',
            'last_5_hits', 'last_10_hits', 'last_20_hits', 'pitcher_oba', 
            'batting_order', 'home_away'
        ]].copy()
        
        final_df.columns = [
            '🏟️', 'Player', 'Hit Score', 'BA', 'L5', 'L10', 'L20', 
            'P-OBA', 'Order', 'H/A'
        ]
        
        # Display the table
        st.markdown(final_df.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # Show last update info
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            daily_time = cache_status['daily_cache']['last_update']
            if daily_time:
                st.caption(f"Daily data last updated: {daily_time[:19]}")
        with col2:
            matchup_time = cache_status['matchup_cache']['last_update']
            if matchup_time:
                st.caption(f"Lineups last updated: {matchup_time[:19]}")
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.write("Please try refreshing or contact support if the issue persists.")

if __name__ == "__main__":
    main()