import streamlit as st
import pandas as pd
from datetime import datetime
from simple_rankings import SimpleMLBRankings

def style_hit_score(score):
    """Style hit score with color coding"""
    if score >= 3.0:
        return f'<span style="background-color: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{score:.2f}</span>'
    elif score >= 2.5:
        return f'<span style="background-color: #fd7e14; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{score:.2f}</span>'
    elif score >= 2.0:
        return f'<span style="background-color: #6f42c1; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{score:.2f}</span>'
    else:
        return f'<span style="background-color: #6c757d; color: white; padding: 4px 8px; border-radius: 4px;">{score:.2f}</span>'

def get_team_logo_url(team_abbr):
    """Get MLB team logo URL"""
    team_mapping = {
        'LAA': 'angels', 'HOU': 'astros', 'OAK': 'athletics', 'ATH': 'athletics', 'TOR': 'bluejays',
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
    return f'<img src="{logo_url}" width="30" height="30" style="vertical-align: middle;" title="{team_abbr}">'

def main():
    st.set_page_config(
        page_title="MLB Hit Score Rankings",
        page_icon="⚾",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Header with logo
    try:
        st.image("attached_assets/file_00000000037861f89e3668cd1c9b6a85.png", use_container_width=True)
    except:
        try:
            st.image("assets/hit_score_logo.png", use_container_width=True)
        except:
            st.markdown("<h1 style='text-align: center; font-size: 3em; margin: 20px 0;'>⚾ Hit Score ⚾</h1>", unsafe_allow_html=True)
    
    st.markdown("<p style='text-align: center; margin-top: 10px;'><strong>Reliable daily rankings with guaranteed 2025 season data</strong></p>", unsafe_allow_html=True)
    
    # Initialize simple rankings system
    rankings_system = SimpleMLBRankings()
    
    # Sidebar controls
    st.sidebar.title("Controls")
    
    if st.sidebar.button("🔄 Refresh Rankings", type="primary"):
        with st.spinner("Fetching fresh 2025 season data..."):
            rankings_df = rankings_system.get_rankings(force_refresh=True)
        st.rerun()
    
    # Formula explanation
    with st.expander("📊 Hit Score Formula"):
        st.markdown("""
        **Guaranteed Current Data Strategy:**
        - Direct MLB API calls for authentic 2025 season statistics
        - Real-time batting averages and recent performance data
        - No complex caching layers that can cause data integrity issues
        
        **Hit Score Formula (Equal 33.3% weighting):**
        1. **Player Hotness:** (L5 + L10 + L20) ÷ 26.25 expected hits
        2. **Pitcher Difficulty:** Opposing pitcher's 2025 OBA ÷ 0.238 league average
        3. **Player Skill:** Batter's 2025 season batting average ÷ 0.238 league average
        
        **Score Ranges:**
        - 🔥 **3.0+:** Elite picks with highest probability
        - 🎯 **2.5-2.9:** Strong picks with good probability  
        - ⚡ **2.0-2.4:** Solid picks worth considering
        - 📊 **Under 2.0:** Lower probability picks
        """)
    
    # Get rankings
    try:
        with st.spinner("Loading 2025 season rankings..."):
            rankings_df = rankings_system.get_rankings()
        
        if rankings_df is None or rankings_df.empty:
            st.error("Unable to load current MLB data. Please try refreshing.")
            st.info("Click 'Refresh Rankings' to fetch the latest 2025 season data.")
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
            teams_today = len(rankings_df['team'].unique())
            st.metric("⚾ Teams Today", teams_today)
        
        # Main rankings table
        st.markdown("### 🏆 Today's Hit Score Rankings")
        st.markdown("*Using live 2025 season data from MLB Stats API*")
        
        # Prepare display dataframe
        display_df = rankings_df.copy()
        
        # Add team logos using team abbreviation
        display_df['team_logo'] = display_df['team'].apply(create_team_logo_html)
        
        # Format columns for display
        display_df['hit_score_formatted'] = display_df['hit_score'].apply(style_hit_score)
        display_df['batting_avg_formatted'] = display_df['batting_avg'].apply(lambda x: f"{x:.3f}")
        display_df['home_away'] = display_df['is_home'].apply(lambda x: 'H' if x else 'A')
        
        # Add pitcher OBA formatting with error handling
        if 'pitcher_oba' in display_df.columns:
            display_df['pitcher_oba_formatted'] = display_df['pitcher_oba'].apply(lambda x: f"{x:.3f}")
        else:
            display_df['pitcher_oba_formatted'] = '0.250'
        
        if 'opposing_pitcher' not in display_df.columns:
            display_df['opposing_pitcher'] = 'TBD'
        
        # Select and rename columns for display
        final_df = display_df[[
            'team_logo', 'player_name', 'hit_score_formatted', 'batting_avg_formatted',
            'last_5', 'last_10', 'last_20', 'pitcher_oba_formatted', 'opposing_pitcher', 'position', 'home_away'
        ]].copy()
        
        final_df.columns = [
            '🏟️', 'Player', 'Hit Score', '2025 BA', 'L5', 'L10', 'L20', 'P-OBA', 'Opposing Pitcher', 'Pos', 'H/A'
        ]
        
        # Display the table
        st.markdown(final_df.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # Show data freshness info
        st.markdown("---")
        st.caption(f"Rankings generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} with authentic 2025 season data")
        
    except Exception as e:
        st.error(f"Error loading rankings: {str(e)}")
        st.info("Please try refreshing or check that the MLB Stats API is accessible.")

if __name__ == "__main__":
    main()