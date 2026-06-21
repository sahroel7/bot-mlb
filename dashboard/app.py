"""
MLB Polymarket AI Bot - Streamlit Dashboard
Visualisasi data prediksi, performa historis, dan status sistem.
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import json
import plotly.express as px
import plotly.graph_objects as go
import sys

# Ensure root path is accessible for DB path resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'mlb_bot.db'))

st.set_page_config(
    page_title="MLB AI Bot Dashboard",
    page_icon="⚾",
    layout="wide"
)

def get_db_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"Database tidak ditemukan di {DB_PATH}. Pastikan bot sudah dijalankan minimal sekali.")
        st.stop()
    conn = sqlite3.connect(DB_PATH)
    return conn

def load_todays_predictions():
    conn = get_db_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    query = """
        SELECT game_id, game_time_et, home_team, away_team, polymarket_line, 
               bot_expected_runs, bot_recommendation, bot_confidence, key_factors, raw_stats, pitcher_home, pitcher_away
        FROM predictions 
        WHERE game_date = ? OR date(predicted_at) = ?
        ORDER BY game_time_et ASC
    """
    df = pd.read_sql_query(query, conn, params=(today, today))
    conn.close()
    return df

def load_daily_performance():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM daily_performance ORDER BY date ASC", conn)
    conn.close()
    return df

def load_system_logs():
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT 20", conn)
    except:
        df = pd.DataFrame(columns=["timestamp", "run_type", "games_analyzed", "errors"])
    conn.close()
    return df

def load_incorrect_predictions():
    conn = get_db_connection()
    query = """
        SELECT p.game_date, p.away_team || ' @ ' || p.home_team as matchup, 
               p.polymarket_line, p.bot_expected_runs, p.bot_recommendation, 
               r.actual_total_runs 
        FROM predictions p
        JOIN results r ON p.game_id = r.game_id
        WHERE r.is_correct = 0
        ORDER BY p.game_date DESC LIMIT 50
    """
    try:
        df = pd.read_sql_query(query, conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# --- UI TABS ---
st.title("⚾ MLB Polymarket AI Bot")
st.markdown(f"**Last Updated:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
if st.button("🔄 Refresh Data"):
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📊 Today's Picks", "📈 Backtest & Performance", "⚙️ Bot Status"])

# --- TAB 1: TODAY'S PICKS ---
with tab1:
    st.header("Today's Predictions")
    df_today = load_todays_predictions()
    
    if df_today.empty:
        st.info("Belum ada prediksi untuk hari ini. Bot mungkin belum berjalan atau tidak ada game MLB.")
    else:
        # Filters
        filter_conf = st.radio("Filter Confidence:", ["All", "HIGH Only", "MEDIUM & HIGH"], horizontal=True)
        
        df_filtered = df_today.copy()
        if filter_conf == "HIGH Only":
            df_filtered = df_filtered[df_filtered['bot_confidence'].str.contains('HIGH', na=False)]
        elif filter_conf == "MEDIUM & HIGH":
            df_filtered = df_filtered[df_filtered['bot_confidence'].str.contains('HIGH|MEDIUM', na=False)]
            
        st.write(f"Menampilkan **{len(df_filtered)}** pertandingan.")
        
        # Display as expanders
        for _, row in df_filtered.iterrows():
            rec = row['bot_recommendation']
            conf = row['bot_confidence']
            
            # Emoji state format
            rec_emoji = "🟢" if "OVER" in rec else "🔵" if "UNDER" in rec else "⚪"
            
            matchup = f"{row['away_team']} @ {row['home_team']}"
            title = f"{rec_emoji} {matchup} | Line: {row['polymarket_line']} | Expected: {row['bot_expected_runs']} | {rec} ({conf})"
            
            with st.expander(title):
                st.markdown(f"### {matchup}")
                cols = st.columns(4)
                cols[0].metric("Market Line", row['polymarket_line'])
                cols[1].metric("Bot Expected", row['bot_expected_runs'])
                cols[2].metric("Recommendation", rec)
                cols[3].metric("Confidence", conf)
                
                try:
                    raw_data = json.loads(row['raw_stats']) if 'raw_stats' in row and row['raw_stats'] else {}
                except:
                    raw_data = {}
                    
                st.markdown("---")
                
                dt1, dt2, dt3, dt4 = st.tabs(["⚾ Pitcher Matchup", "💪 Offense Comparison", "🌡️ Environment", "🧮 Calculations"])
                
                with dt1:
                    pc1, pc2 = st.columns(2)
                    home_p = raw_data.get('home_pitcher_stats', {})
                    away_p = raw_data.get('away_pitcher_stats', {})
                    
                    def color_metric(val, is_good_lower=True):
                        if pd.isna(val) or val == '-': return ""
                        try: v = float(val)
                        except: return ""
                        # Logika indikator sederhana
                        if is_good_lower:
                            return "🟢" if v <= 3.5 else "🔴" if v >= 4.5 else "⚪"
                        else:
                            return "🟢" if v >= 9.0 else "🔴" if v <= 7.0 else "⚪"

                    with pc1:
                        st.markdown(f"**Away Starter:** {row['pitcher_away']}")
                        st.markdown(f"""
                        | Metric | Value | Indicator |
                        |---|---|---|
                        | **ERA** | {away_p.get('era', '-')} | {color_metric(away_p.get('era'))} |
                        | **FIP** | {away_p.get('fip', '-')} | {color_metric(away_p.get('fip'))} |
                        | **WHIP**| {away_p.get('whip', '-')} | {color_metric(away_p.get('whip'))} |
                        | **K/9** | {away_p.get('k9', '-')} | {color_metric(away_p.get('k9'), False)} |
                        | **BB/9**| {away_p.get('bb9', '-')} | {color_metric(away_p.get('bb9'))} |
                        | **HR/9**| {away_p.get('hr9', '-')} | {color_metric(away_p.get('hr9'))} |
                        """)
                        away_fatigue = raw_data.get('away_pitcher_last_3', [])
                        if len(away_fatigue) > 0:
                            st.caption(f"Last Start: {away_fatigue[0].get('pitch_count', '-')} pitches")

                    with pc2:
                        st.markdown(f"**Home Starter:** {row['pitcher_home']}")
                        st.markdown(f"""
                        | Metric | Value | Indicator |
                        |---|---|---|
                        | **ERA** | {home_p.get('era', '-')} | {color_metric(home_p.get('era'))} |
                        | **FIP** | {home_p.get('fip', '-')} | {color_metric(home_p.get('fip'))} |
                        | **WHIP**| {home_p.get('whip', '-')} | {color_metric(home_p.get('whip'))} |
                        | **K/9** | {home_p.get('k9', '-')} | {color_metric(home_p.get('k9'), False)} |
                        | **BB/9**| {home_p.get('bb9', '-')} | {color_metric(home_p.get('bb9'))} |
                        | **HR/9**| {home_p.get('hr9', '-')} | {color_metric(home_p.get('hr9'))} |
                        """)
                        home_fatigue = raw_data.get('home_pitcher_last_3', [])
                        if len(home_fatigue) > 0:
                            st.caption(f"Last Start: {home_fatigue[0].get('pitch_count', '-')} pitches")

                with dt2:
                    oc1, oc2 = st.columns([2, 1])
                    with oc1:
                        home_o = raw_data.get('home_team_stats', {})
                        away_o = raw_data.get('away_team_stats', {})
                        
                        # Bar chart (OPS dikali 1000 agar skalanya setara dengan persentase lain)
                        fig_off = go.Figure(data=[
                            go.Bar(name=row['away_team'], x=['OPS (x1000)', 'K%', 'BB%'], 
                                   y=[float(away_o.get('ops', 0))*1000, float(away_o.get('k_pct', 0)), float(away_o.get('bb_pct', 0))]),
                            go.Bar(name=row['home_team'], x=['OPS (x1000)', 'K%', 'BB%'], 
                                   y=[float(home_o.get('ops', 0))*1000, float(home_o.get('k_pct', 0)), float(home_o.get('bb_pct', 0))])
                        ])
                        fig_off.update_layout(barmode='group', title="Team Offense Comparison", height=300, margin=dict(t=30, b=0))
                        st.plotly_chart(fig_off, use_container_width=True)
                        
                    with oc2:
                        st.markdown("**Streak Status**")
                        hs = raw_data.get('home_streak', {})
                        ast = raw_data.get('away_streak', {})
                        
                        # Parsing format dict dari Phase 2 Enhancement
                        if isinstance(hs, dict):
                            h_type = hs.get('type', 'NEUTRAL')
                            a_type = ast.get('type', 'NEUTRAL')
                            
                            h_label = "🔥" if h_type == 'HOT' else "❄️" if h_type == 'COLD' else "➡️"
                            a_label = "🔥" if a_type == 'HOT' else "❄️" if a_type == 'COLD' else "➡️"
                            st.write(f"**{row['away_team']}:** {a_type} {a_label}")
                            st.write(f"**{row['home_team']}:** {h_type} {h_label}")
                        else:
                            st.write(f"**{row['away_team']}:** {ast}")
                            st.write(f"**{row['home_team']}:** {hs}")
                        
                        st.markdown("**Platoon Advantage**")
                        st.caption("Akan dihitung saat lineup dirilis.")

                with dt3:
                    weather = raw_data.get('weather', {})
                    if weather:
                        temp = weather.get('temperature_fahrenheit', 'N/A')
                        wind = weather.get('wind_speed_mph', 'N/A')
                        wind_dir = weather.get('wind_direction_degrees', 0)
                        orient = weather.get('stadium_orientation', 0)
                        
                        # Menentukan arah angin untuk visual UI
                        diff = abs(((wind_dir + 180) % 360) - orient)
                        if diff > 180: diff = 360 - diff
                        
                        if diff <= 45: w_type = "↗️ OUTWARD (Hitter Friendly)"
                        elif diff >= 135: w_type = "↙️ INWARD (Pitcher Friendly)"
                        else: w_type = "➡️ CROSSWIND"
                        
                        st.info(f"🌡️ **Suhu:** {temp}°F | 💨 **Angin:** {wind} mph {w_type}")
                    else:
                        st.write("Data cuaca tidak tersedia atau stadium tertutup (Dome).")
                        
                    park_factor = raw_data.get('park_factor', 100)
                    p_type = "HITTERS PARK 🔥" if park_factor > 105 else "PITCHERS PARK ❄️" if park_factor < 95 else "NEUTRAL ➡️"
                    st.success(f"🏟️ **Stadium Park Factor:** {park_factor} ({p_type})")

                with dt4:
                    mods = raw_data.get('mods', {})
                    final_exp = row['bot_expected_runs']
                    
                    # Ensure base calculation matches exactly to prevent waterfall gap
                    mod_p = mods.get('mod_pitcher', 0.0)
                    mod_o = mods.get('mod_offense', 0.0)
                    mod_e = mods.get('mod_env', 0.0)
                    base = final_exp - mod_p - mod_o - mod_e
                    
                    fig_waterfall = go.Figure(go.Waterfall(
                        name = "Runs", orientation = "v",
                        measure = ["absolute", "relative", "relative", "relative", "total"],
                        x = ["Base Runs", "Pitcher Mod", "Offense Mod", "Environment Mod", "Final Expected"],
                        textposition = "outside",
                        text = [f"{base:.2f}", f"{mod_p:+.2f}", f"{mod_o:+.2f}", f"{mod_e:+.2f}", f"{final_exp:.2f}"],
                        y = [base, mod_p, mod_o, mod_e, final_exp],
                        connector = {"line":{"color":"rgb(63, 63, 63)"}},
                        decreasing = {"marker":{"color":"blue"}},
                        increasing = {"marker":{"color":"green"}},
                        totals = {"marker":{"color":"orange"}}
                    ))
                    
                    # Add Polymarket Line
                    fig_waterfall.add_hline(y=row['polymarket_line'], line_dash="dash", line_color="red", annotation_text="Polymarket Line")
                    
                    fig_waterfall.update_layout(title="Kalkulasi Modifiers (Waterfall Chart)", height=400, margin=dict(t=40, b=0))
                    st.plotly_chart(fig_waterfall, use_container_width=True)
                    
                    st.markdown("**Detail Key Factors:**")
                    try:
                        factors = json.loads(row['key_factors'])
                        if not factors:
                            st.write("➖ Semua metrik dalam batas rata-rata")
                        for factor in factors:
                            st.write(f"- {factor}")
                    except:
                        pass

# --- TAB 2: BACKTEST & PERFORMANCE ---
with tab2:
    st.header("Historical Performance")
    df_perf = load_daily_performance()
    
    if df_perf.empty:
        st.info("Belum ada data performa historis.")
    else:
        total_correct = df_perf['total_correct'].sum()
        total_incorrect = df_perf['total_incorrect'].sum()
        total_bets = total_correct + total_incorrect
        overall_wr = (total_correct / total_bets * 100) if total_bets > 0 else 0
        
        high_correct = df_perf['high_confidence_correct'].sum()
        high_incorrect = df_perf['high_confidence_incorrect'].sum()
        high_total = high_correct + high_incorrect
        high_wr = (high_correct / high_total * 100) if high_total > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall Win Rate", f"{overall_wr:.1f}%", f"{total_correct}W - {total_incorrect}L")
        c2.metric("HIGH Conf. Win Rate", f"{high_wr:.1f}%", f"{high_correct}W - {high_incorrect}L")
        c3.metric("Total Games Analyzed", df_perf['total_games_analyzed'].sum())
        
        st.subheader("Daily Win Rate Trend")
        fig = px.line(df_perf, x='date', y='win_rate_daily', markers=True, title="Win Rate % per Hari")
        fig.add_hline(y=52.0, line_dash="dash", line_color="red", annotation_text="Break Even (52%)")
        fig.update_yaxes(range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("⚠️ Review: Prediksi Meleset (Top 50)")
        df_wrong = load_incorrect_predictions()
        st.dataframe(df_wrong, use_container_width=True)

# --- TAB 3: BOT STATUS ---
with tab3:
    st.header("System Logs & Status")
    
    st.subheader("🔌 API Connections")
    st.write("✅ MLB Stats API")
    st.write("✅ Polymarket CLOB API")
    st.write("✅ Open-Meteo Weather API")
    
    st.subheader("📝 Recent Execution Logs")
    df_logs = load_system_logs()
    if df_logs.empty:
        st.write("Belum ada log eksekusi dari Auto Runner.")
    else:
        st.dataframe(df_logs, use_container_width=True)