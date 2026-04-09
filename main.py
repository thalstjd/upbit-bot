import time, json, datetime, pyupbit, requests, os
import pandas as pd
from strategy_executor import StrategyExecutor
from backtester import Backtester

class AutoTrader:
    def __init__(self):
        with open("config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.upbit = pyupbit.Upbit(self.config['upbit_access_key'], self.config['upbit_secret_key'])
        self.executor = StrategyExecutor(self.config['gemini_api_key'])
        self.backtester = Backtester()
        self.strategy, self.last_date, self.is_trading = None, None, False
        self.last_order_time = 0
        self.ticker = "KRW-BTC"

    def log_trade(self, side, price, profit=0):
        """매매 내역을 CSV에 저장 (웹 대시보드용)"""
        file_name = "trade_history.csv"
        now = datetime.datetime.now()
        new_log = {
            "date": now.strftime('%Y-%m-%d'),
            "time": now.strftime('%H:%M:%S'),
            "type": side,
            "price": price,
            "profit": round(profit * 100, 2) if side == "SELL" else 0,
            "reason": self.strategy.get('reasoning', '전략 매매')
        }
        df = pd.DataFrame([new_log])
        df.to_csv(file_name, mode='a', header=not os.path.exists(file_name), index=False, encoding='utf-8-sig')

    def log(self, msg):
        m = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(m)
        if self.config.get('discord_webhook_url'):
            try: requests.post(self.config['discord_webhook_url'], json={"content": m}, timeout=5)
            except: pass

    def get_indicators(self, p):
        """멀티 지표 계산기 (RSI, EMA, Bollinger)"""
        try:
            df = pyupbit.get_ohlcv(self.ticker, interval="minute60", count=50)
            delta = df['close'].diff()
            u, d = delta.copy(), delta.copy()
            u[u<0], d[d>0] = 0, 0
            rs = u.ewm(com=p-1, adjust=False).mean() / d.abs().ewm(com=p-1, adjust=False).mean()
            rsi = (100 - (100 / (1 + rs))).iloc[-1]
            ema = df['close'].ewm(span=p, adjust=False).mean().iloc[-1]
            ma20 = df['close'].rolling(20).mean()
            std20 = df['close'].rolling(20).std()
            lower_bb = (ma20 - (std20 * 2)).iloc[-1]
            return {"rsi": rsi, "ema": ema, "lower_bb": lower_bb, "price": df['close'].iloc[-1]}
        except:
            return {"rsi": 50, "ema": 0, "lower_bb": 0, "price": pyupbit.get_current_price(self.ticker)}

    def refresh(self):
        """심층 데이터를 수집하여 제미나이에게 전략을 요청합니다."""
        self.log("🔄 [인텔리전스] 10일간의 흐름을 심층 분석 중...")
        try:
            df_daily = pyupbit.get_ohlcv(self.ticker, interval="day", count=10)
            price_list = [int(p) for p in df_daily['close'].tolist()]
            current_price = pyupbit.get_current_price(self.ticker)
            high_10d = df_daily['high'].max()
            low_10d = df_daily['low'].min()
            
            summary = f"""
            [BTC 10일 시장 데이터]
            - 현재가: {current_price:,.0f} KRW
            - 10일 종가 리스트: {price_list}
            - 10일 최고가: {high_10d:,.0f} / 최저가: {low_10d:,.0f}
            """
            
            plan = self.executor.get_new_strategy(summary)
            if self.backtester.run(plan)['return'] > 0:
                self.strategy = plan
                self.last_date = datetime.datetime.now().date()
                tp_p, sl_p = plan['tp'] * 100, plan['sl'] * 100
                self.log(f"✅ 전략 승인: {plan['indicator']} | 익절:{tp_p:+.1f}% | 손절:{sl_p:+.1f}%")
                self.log(f"🧠 분석 근거: {plan.get('reasoning', '분석 완료')}")
        except Exception as e:
            self.log(f"⚠️ 전략 갱신 실패: {e}")

    def run(self):
        self.log("🚀 멀티 인텔리전스 엔진 가동!")
        wm = pyupbit.WebSocketManager("ticker", [self.ticker])
        while True:
            try:
                now = datetime.datetime.now()
                # 1. 자정 전략 갱신
                if self.last_date != now.date() and self.upbit.get_balance(self.ticker) < 0.0001:
                    self.refresh()
                
                data = wm.get()
                if not data or not self.strategy: continue
                price = data['trade_price']
                inds = self.get_indicators(self.strategy.get('period', 14))
                
                # 대시보드용 실시간 데이터 저장
                status = {
                    "price": price, "rsi": inds['rsi'], "target": self.strategy['threshold'],
                    "tp": self.strategy['tp'], "sl": self.strategy['sl'],
                    "update_time": now.strftime('%H:%M:%S'), "indicator": self.strategy['indicator']
                }
                with open("status.json", "w") as f: json.dump(status, f)

                # 지표별 매수 판단
                target = self.strategy['indicator']
                if target == "RSI": buy_signal = inds['rsi'] <= self.strategy['threshold']
                elif target == "EMA": buy_signal = price <= inds['ema'] * (1 - self.strategy['threshold']/100)
                elif target == "BB": buy_signal = price <= inds['lower_bb']
                else: buy_signal = False

                print(f"[{now.strftime('%H:%M:%S')}] {price:,.0f}원 | {target} 감시 중 | 익절:{self.strategy['tp']*100}%", end='\r')
                
                # 2. 매수 로직 (중복 방지 30초 쿨다운 적용)
                if buy_signal and not self.is_trading and (time.time() - self.last_order_time > 30):
                    if self.upbit.get_balance(self.ticker) < 0.0001:
                        self.is_trading = True
                        res = self.upbit.buy_market_order(self.ticker, self.config['max_buy_amount'])
                        if res:
                            self.last_order_time = time.time()
                            self.log(f"💰 매수체결({target}): {price:,.0f}원")
                            self.log_trade("BUY", price)
                        self.is_trading = False
                
                # 3. 매도 로직
                btc = self.upbit.get_balance(self.ticker)
                if btc > 0.0001 and not self.is_trading:
                    avg_p = self.upbit.get_avg_buy_price(self.ticker)
                    profit = (price - avg_p) / avg_p
                    if profit >= self.strategy['tp'] or profit <= self.strategy['sl']:
                        self.is_trading = True
                        res = self.upbit.sell_market_order(self.ticker, btc)
                        if res:
                            self.last_order_time = time.time()
                            self.log(f"📢 매도체결: {profit*100:.2f}%")
                            self.log_trade("SELL", price, profit)
                        self.is_trading = False
                time.sleep(0.1)
            except Exception as e:
                self.log(f"⚠️ 에러: {e}"); self.is_trading = False; time.sleep(1)

if __name__ == "__main__":
    AutoTrader().run()