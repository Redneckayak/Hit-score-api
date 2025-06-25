import streamlit as st
import pandas as pd
from datetime import datetime
from data_cache import DataCache
from data_fetcher import MLBDataFetcher

# Simple working version with caching
def main():
    st.title("🥎 MLB Hitter Power Rankings")
    st.markdown("**Advanced daily rankings with authentic split data**")
    
    # Initialize session state
    if 'rankings_data' not in st.session_state:
        st.session_state.rankings_data = None
    
    # Initialize data cache
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = DataCache(cache_duration_minutes=30)
    
    data_cache = st.session_state.data_cache
    
    # Show cache status
    cache_status = data_cache.get_cache_status()
    if cache_status['last_update']:
        last_update_time = datetime.fromisoformat(cache_status['last_update']).strftime("%I:%M %p")
        refresh_status = "⚠️ Expired" if cache_status['is_expired'] else "✅ Fresh"
        st.info(f"Data last updated: {last_update_time} ({refresh_status}) | Cache refreshes every {cache_status['cache_duration_minutes']} minutes")
    
    # Add manual refresh buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh Data"):
            rankings_df = data_cache.get_rankings(force_refresh=True)
            st.session_state.rankings_data = rankings_df
            st.rerun()
    
    with col2:
        if st.button("📊 Load Cached"):
            rankings_df = data_cache.get_rankings(force_refresh=False)
            st.session_state.rankings_data = rankings_df
            st.rerun()
    
    # Load data
    if st.session_state.rankings_data is None:
        with st.spinner("Loading MLB rankings data..."):
            rankings_df = data_cache.get_rankings(force_refresh=False)
            st.session_state.rankings_data = rankings_df
    else:
        rankings_df = st.session_state.rankings_data
    
    # Display results
    if rankings_df is not None and not rankings_df.empty:
        st.success(f"Loaded {len(rankings_df)} players with scheduled games today")
        
        # Display first few players
        display_cols = ['player_name', 'team', 'position', 'hits_last_5', 'hits_last_10', 'hits_last_20', 
                       'opposing_pitcher', 'pitcher_hand', 'vs_LHP', 'vs_RHP', 'pitcher_oba', 'hit_score']
        
        # Filter columns that exist
        available_cols = [col for col in display_cols if col in rankings_df.columns]
        
        if available_cols:
            st.dataframe(rankings_df[available_cols].head(20))
        else:
            st.dataframe(rankings_df.head(20))
    else:
        st.warning("No data available. Try refreshing.")

if __name__ == "__main__":
    main()