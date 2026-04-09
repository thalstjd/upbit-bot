import streamlit as st
import pandas as pd
import plotly.express as px
import os
import pyupbit
import json
from datetime import datetime

# 1. 페이지 설정 및 다크 테마 가독성 개선
st.set_page_config(page_title="Minchacco Trading Bot", layout="wide")

# CSS: 가독성을 위해 배경을 살짝 밝히고 텍스트 대비를 높임
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #adbac7; }
    .stMetric { 
        background-color: #1c2128; /* 박스 색상을 조금 더 밝게 변경 */
        border: 2px solid #FFD700; /* 테두리를 황금색으로 강조 */
        border-radius: 12px; 
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 16px !important; }
    [data-testid="stMetricValue"] { color: #FFD700 !important; font-size: 28px !important; font-weight: bold !important; }
    h1, h2, h3 { color: #FFD700; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 Minchacco Bitcoin Intelligence")

# 2. 업비트 계정 연결 (Secrets 우선 순위)
def get_upbit():
    try:
        # 웹 환경 (Streamlit Cloud Secrets)
        return pyupbit.Upbit(st.secrets["upbit_access_key"], st.secrets["upbit_secret_key"])
    except:
        try:
            # 로컬 환경 (config.json)
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return pyupbit.Upbit(cfg['upbit_access_key'], cfg['upbit_secret_key'])
        except:
            return None

upbit = get_upbit()

# 3. 실시간 자산 현황 (API 호출)
st.subheader("💰 실시간 자산 현황 (LIVE)")
c1, c2, c3, c4 = st.columns(4)

if upbit:
    try:
        krw = upbit.get_balance("KRW") or 0
        btc = upbit.get_balance("KRW-BTC") or 0
        price = pyupbit.get_current_price("KRW-BTC") or 0
        avg = upbit.get_avg_buy_price("KRW-BTC") or 0
        
        total = krw + (btc * price)
        
        c1.metric("총 자산", f"{total:,.0f} KRW")
        c2.metric("현금 잔고", f"{krw:,.0f} KRW")
        c3.metric("BTC 평가금", f"{(btc * price):,.0f} KRW")
        
        if btc > 0:
            yield_p = ((price - avg) / avg) * 100
            c4.metric("포지션 수익률", f"{yield_p:+.2f}%")
        else:
            c4.metric("포지션", "매수 대기 중")
    except:
        st.error("API 키가 올바르지 않거나 Secrets 설정이 필요합니다.")
else:
    st.info("⚠️ 상단 자산을 보려면 Streamlit Cloud 'Secrets'에 키를 입력하세요.")

st.markdown("<br>", unsafe_allow_html=True)

# 4. 로봇 모니터링 및 매매 기록 (파일 기반)
# ※ 주의: 이 섹션은 깃허브에 Push된 시점의 데이터만 보여줍니다.
st.subheader("🤖 로봇 상태 및 매매 로그")

col_left, col_right = st.columns([1, 1])

with col_left:
    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            status = json.load(f)
        st.write(f"✅ **마지막 동기화 시점**: {status.get('update_time', 'N/A')}")
        st.info(f"지표: {status['indicator']} | 목표: {status['target']} | 현재가: {status['price']:,.0f}")
    else:
        st.write("로봇 상태 파일이 없습니다.")

with col_right:
    if os.path.exists("trade_history.csv"):
        df = pd.read_csv("trade_history.csv")
        st.write("✅ **최근 매매 기록**")
        st.dataframe(df.sort_values(by='date', ascending=False).head(5), use_container_width=True)
    else:
        st.write("매매 기록이 없습니다.")