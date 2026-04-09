from google import genai
import json

class StrategyExecutor:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
        self.model_id = None

    def find_best_model(self):
        """민성님의 환경에서 사용 가능한 최신 모델을 찾습니다."""
        try:
            models = self.client.models.list()
            available = [m.name for m in models if "gemini" in m.name.lower()]
            # 성공 가능성이 높은 순서대로 시도
            for p in ["gemini-2.5-flash", "gemini-3.1-flash", "gemini-1.5-flash-latest"]:
                for m in available:
                    if p in m: return m
            return available[0] if available else None
        except: return None

    def get_new_strategy(self, data_summary):
        if not self.model_id:
            self.model_id = self.find_best_model()
        
        prompt = f"""
        당신은 퀀트 트레이더입니다. 아래 데이터를 보고 가장 적합한 지표를 선택하세요.
        데이터: {data_summary}
        
        응답은 반드시 아래 JSON 형식만 출력하세요:
        {{
            "indicator": "RSI" 또는 "EMA" 또는 "BB",
            "period": 14,
            "threshold": 35,
            "tp": 0.03,
            "sl": -0.02,
            "reasoning": "왜 이 지표와 수치를 선택했는지 분석 근거"
        }}
        """
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt)
            txt = res.text.strip()
            # JSON만 정교하게 추출
            if "{" in txt and "}" in txt:
                txt = txt[txt.find("{"):txt.rfind("}")+1]
            
            plan = json.loads(txt)
            # 만약 제미나이가 '기본'이라는 단어를 쓰면 다시 분석하도록 유도 (선택사항)
            return plan
        except Exception as e:
            # 진짜 에러 시에만 작동하는 최후의 보루
            return {
                "indicator": "RSI", "period": 14, "threshold": 30, 
                "tp": 0.03, "sl": -0.02, 
                "reasoning": f"시스템 연결 지연으로 인한 안전모드 가동 (Error: {str(e)[:20]})"
            }