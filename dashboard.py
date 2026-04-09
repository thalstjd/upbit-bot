import streamlit as st
import pandas as pd
import plotly.express as px
import os
import pyupbit
import json
from datetime import datetime

# 1. 럭셔리 다크 테마 및 페이지 설정
st.set_page_config(page_title="Minchacco BTC Intelligence", layout="wide")

# 블랙 & 골드 스타일링 CSS
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    .stMetric { 
        background-color: #161B22; 
        border-radius: 10px; 
        padding: 20px; 
        border: 1px solid #30363D;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    div[data-testid="stMetricValue"] { color: #FFD700 !format; } /* 골드 색상 강조 */
    h1, h2, h3 { color: #FFD700; font-family: 'Segoe UI', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 Minchacco Bitcoin Intelligence")

# 2. 업비트 연결 함수 (로컬/웹 환경 자동 감지)
def get_upbit():
    try:
        # Streamlit Cloud(웹) 환경의 Secrets 확인
        if "upbit_access_key" in st.secrets:
            access = st.secrets["upbit_access_key"]
            secret = st.secrets["upbit_secret_key"]
            return pyupbit.Upbit(access, secret)
    except:
        pass
    
    # 내 컴퓨터(로컬) 환경의 config.json 확인
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            return pyupbit.Upbit(config['upbit_access_key'], config['upbit_secret_key'])
    except:
        return None

upbit = get_upbit()

# 3. 상단 자산 현황 (KPI 섹션)
st.subheader("💰 실시간 자산 현황")
if upbit:
    try:
        krw_bal = upbit.get_balance("KRW") or 0
        btc_bal = upbit.get_balance("KRW-BTC") or 0
        cur_p = pyupbit.get_current_price("KRW-BTC") or 0
        avg_p = upbit.get_avg_buy_price("KRW-BTC") or 0
        
        btc_value = btc_bal * cur_p
        total_val = krw_bal + btc_value
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 자산 (평가금액)", f"{total_val:,.0f} KRW")
        col2.metric("보유 현금", f"{krw_bal:,.0f} KRW")
        col3.metric("비트코인 평가금", f"{btc_value:,.0f} KRW")
        
        if btc_bal > 0 and avg_p > 0:
            profit_p = ((cur_p - avg_p) / avg_p) * 100
            col4.metric("현재 포지션 수익률", f"{profit_p:+.2f}%")
        else:
            col4.metric("현재 포지션", "관망 중")
    except Exception as e:
        st.warning("업비트 잔고를 불러오는 중입니다... (키 설정을 확인하세요)")
else:
    st.info("API 키가 설정되지 않았습니다. Streamlit Secrets 설정을 완료해주세요.")

st.markdown("---")

# 4. 실시간 시장 상황 (status.json 연동)
if os.path.exists("status.json"):
    with open("status.json", "r") as f:
        status = json.load(f)
    
    st.subheader(f"📊 로봇 실시간 모니터링 ({status.get('update_time', 'N/A')})")
    m1, m2, m3 = st.columns(3)
    m1.metric("현재 비트코인 가격", f"{status['price']:,.0f} KRW")
    m2.metric(f"현재 {status['indicator']} 지수", f"{status['rsi']:.2f}")
    m3.metric("매수 목표치", f"{status['target']}")
    st.info(f"🎯 **전략 정보**: 익절 +{status['tp']*100}% | 손절 {status['sl']*100}% | 지표: {status['indicator']}")

st.markdown("---")

# 5. 매매 기록 및 그래프 (trade_history.csv 연동)
if os.path.exists("trade_history.csv"):
    df = pd.read_csv("trade_history.csv")
    df['date'] = pd.to_datetime(df['date'])

    st.subheader("📈 일일 수익률 추이")
    # 일별 수익률 합계 계산
    profit_df = df[df['type'] == 'SELL'].groupby('date')['profit'].sum().reset_index()
    
    if not profit_df.empty:
        fig = px.line(profit_df, x='date', y='profit', markers=True,
                      template="plotly_dark", 
                      title="Cumulative Daily Profits (%)",
                      color_discrete_sequence=['#FFD700']) # 골드 라인
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 전체 매매 기록")
    # 최신순 정렬 및 필터링 기능 (사이드바)
    st.sidebar.header("📅 기록 필터")
    years = sorted(df['date'].dt.year.unique(), reverse=True)
    sel_year = st.sidebar.selectbox("연도 선택", years)
    
    filtered_df = df[df['date'].dt.year == sel_year]
    st.dataframe(filtered_df.sort_values(by=['date', 'time'], ascending=False), use_container_width=True)
else:
    st.subheader("📋 매매 기록")
    st.write("아직 매매 기록이 없습니다. 로봇이 첫 거래를 마치면 여기에 데이터가 쌓입니다.")