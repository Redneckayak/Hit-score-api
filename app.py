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
    """Create HTML for team abbreviation display"""
    return f'<span style="font-weight: bold; color: #1f4e79; background-color: #f8f9fa; padding: 3px 6px; border-radius: 3px; font-size: 0.9em;">{team_abbr}</span>'

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
    
    # Fast cached rankings loading
    @st.cache_data(ttl=600, show_spinner=False)  # Cache for 10 minutes
    def load_rankings_cached():
        rankings_system = SimpleMLBRankings()
        return rankings_system.get_rankings(force_refresh=False)
    
    # Sidebar controls
    st.sidebar.title("Controls")
    
    if st.sidebar.button("🔄 Refresh Rankings", type="primary"):
        st.cache_data.clear()  # Clear cache to force refresh
        st.rerun()
    
    # Formula explanation
    with st.expander("📊 Hit Score Formula"):
        st.markdown("""
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
    
    # Get rankings - fast cached loading
    try:
        rankings_df = load_rankings_cached()
        
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
        
        # Streamlined display preparation with pitcher OBA
        columns_to_use = ['team', 'player_name', 'hit_score', 'batting_avg', 'last_5', 'last_10', 'last_20', 'opposing_pitcher', 'position']
        
        # Add pitcher_oba if available - insert after last_20
        if 'pitcher_oba' in rankings_df.columns:
            columns_to_use.insert(-2, 'pitcher_oba')
        
        final_df = rankings_df[columns_to_use].copy()
        
        # Simple formatting
        final_df['batting_avg'] = final_df['batting_avg'].round(3)
        final_df['hit_score'] = final_df['hit_score'].round(2)
        final_df['opposing_pitcher'] = final_df['opposing_pitcher'].astype(str).replace('nan', 'TBD')
        
        # Format pitcher OBA if present
        if 'pitcher_oba' in final_df.columns:
            final_df['pitcher_oba'] = final_df['pitcher_oba'].round(3)
            final_df.columns = [
                'Team', 'Player', 'Hit Score', '2025 BA', 'L5', 'L10', 'L20', 'P-OBA', 'Opposing Pitcher', 'Pos'
            ]
        else:
            final_df.columns = [
                'Team', 'Player', 'Hit Score', '2025 BA', 'L5', 'L10', 'L20', 'Opposing Pitcher', 'Pos'
            ]
        
        # Color-code hit scores for visual impact
        def color_hit_scores(val):
            if val >= 2.5:
                return 'background-color: #0f5132; color: white'  # Dark green
            elif val >= 2.0:
                return 'background-color: #198754; color: white'  # Medium green
            elif val >= 1.0:
                return 'background-color: #fd7e14; color: white'  # Orange
            else:
                return 'background-color: #dc3545; color: white'  # Red
        
        # Apply styling to hit score column only
        styled_df = final_df.style.applymap(
            color_hit_scores, 
            subset=['Hit Score']
        ).format({'Hit Score': '{:.2f}'})
        
        # Display styled dataframe
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Show data freshness info
        st.markdown("---")
        st.caption(f"Rankings generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} with authentic 2025 season data")
        
    except Exception as e:
        st.error(f"Error loading rankings: {str(e)}")
        st.info("Please try refreshing or check that the MLB Stats API is accessible.")

if __name__ == "__main__":
    main()