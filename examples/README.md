# Hy3 API Examples

鏈洰褰曞寘鍚?6 涓彲鐩存帴杩愯鐨?Python 绀轰緥锛岃鐩?Hy3 API 鐨勪富瑕佽兘鍔涖€?
## 绀轰緥鍒楄〃

| # | 鏂囦欢 | 璇存槑 | 鍏抽敭鑳藉姏 |
|---|------|------|----------|
| 1 | `01_basic_chat.py` | 鍗曡疆 & 澶氳疆瀵硅瘽 | `chat.completions.create`, system prompt, JSON 杈撳嚭 |
| 2 | `02_streaming.py` | 娴佸紡璇锋眰 + 閫?chunk 瑙ｆ瀽 | `stream=True`, delta 瑙ｆ瀽, reasoning_content |
| 3 | `03_latency_compare.py` | 娴佸紡 vs 闈炴祦寮忓欢杩熷姣?| TTFT, 鎬昏€楁椂, 鐢ㄦ埛浣撻獙鍒嗘瀽 |
| 4 | `04_tool_calling.py` | 宸ュ叿璋冪敤涓庡杞惊鐜?| tools 瀹氫箟, tool_choice, 澶氳疆宸ュ叿寰幆 |
| 5 | `05_reasoning_mode.py` | 鎬濊€冩ā寮?寮€/鍏?瀵规瘮 | reasoning_effort, 蹇參鎬濊€? reasoning_content |
| 6 | `06_error_handling.py` | 閿欒澶勭悊涓庢寚鏁伴€€閬块噸璇?| 閲嶈瘯瑁呴グ鍣? 瓒呮椂澶勭悊, 鐢熶骇绾фā鏉?|

## 杩愯鏂瑰紡

```bash
# 1. 璁剧疆 API Key
export HY3_API_KEY="your-api-key-here"

# 2. (鍙€? 鑷畾涔?Base URL
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"

# 3. 杩愯浠绘剰绀轰緥
python 01_basic_chat.py
```

## 鐜瑕佹眰

- Python 3.8+
- `openai` 鍖咃細`pip install openai`

## 杈撳嚭璇存槑

姣忎釜绀轰緥杩愯鍚庝細鎵撳嵃锛?1. 馃摛 **瀹屾暣璇锋眰** 鈥?璇锋眰鍙傛暟鍜岄厤缃?2. 馃摜 **瀹屾暣 Response 瑙ｆ瀽** 鈥?鍝嶅簲鐨勫叧閿瓧娈?3. 馃挰 **绀轰緥杈撳嚭** 鈥?妯″瀷鐨勫疄闄呭洖澶嶏紙鎴彇鍏抽敭閮ㄥ垎锛?
## 娉ㄦ剰浜嬮」

- 绀轰緥涓娇鐢ㄤ簡妯℃嫙鏁版嵁锛堝澶╂皵鏌ヨ銆佸揩閫掓煡璇㈢粨鏋滐級锛岀‘淇濆湪娌℃湁澶栭儴渚濊禆鐨勬儏鍐典笅涔熻兘璺戦€?- 璇锋浛鎹?`your-api-key-here` 涓虹湡瀹炵殑 API Key锛屾垨閫氳繃鐜鍙橀噺 `HY3_API_KEY` 浼犲叆
- 涓嶅悓 Hy3 API 骞冲彴鐨勫弬鏁颁紶閫掓柟寮忓彲鑳界暐鏈夊樊寮傦紝璇峰弬鑰?`quickstart.md`
