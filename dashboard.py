import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# 페이지 설정 (럭셔리 다크 테마)
st.set_page_config(page_title="Minchacco BTC Intelligence", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    .stMetric { background-color: #161B22; border-radius: 10px; padding: 15px; border: 1px solid #30363D; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 Minchacco Bitcoin Intelligence")

# 데이터 로드
def load_data():
    if os.path.exists("trade_history.csv"):
        df = pd.read_csv("trade_history.csv")
        df['date'] = pd.to_datetime(df['date'])
        return df
    return None

df = load_data()

if df is not None:
    # 사이드바 필터링 (연/월/일)
    st.sidebar.header("📅 기간 필터")
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    
    selected_year = st.sidebar.selectbox("연도 선택", sorted(df['year'].unique(), reverse=True))
    selected_month = st.sidebar.selectbox("월 선택", sorted(df[df['year']==selected_year]['month'].unique(), reverse=True))
    
    filtered_df = df[(df['year'] == selected_year) & (df['month'] == selected_month)]

    # 상단 요약 지표
    total_profit = df[df['type'] == 'SELL']['profit'].sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("총 누적 수익률", f"{total_profit:+.2f}%")
    col2.metric("이번 달 매매 횟수", f"{len(filtered_df)}회")
    col3.metric("최근 매매가", f"{df.iloc[-1]['price']:,.0f} KRW")

    # 수익률 그래프
    st.subheader("📈 일일 수익률 추이")
    profit_df = df[df['type'] == 'SELL'].groupby('date')['profit'].sum().reset_index()
    fig = px.line(profit_df, x='date', y='profit', markers=True, 
                  template="plotly_dark", color_discrete_sequence=['#FFD700']) # 골드 컬러
    st.plotly_chart(fig, use_container_width=True)

    # 상세 내역 리스트
    st.subheader("📋 상세 매매 기록")
    st.dataframe(filtered_df.sort_values(by=['date', 'time'], ascending=False), use_container_width=True)
else:
    st.info("아직 매매 데이터가 없습니다. 첫 매매가 발생하면 자동으로 대시보드가 활성화됩니다.")