# Hy3 API Quickstart

> **5 鍒嗛挓璺戦€氱涓€娆¤皟鐢紝鍗婂皬鏃朵笂鎵嬩富瑕佽兘鍔?*

Hy3 鏄吘璁贩鍏冨洟闃熺爺鍙戠殑 295B MoE锛堟贩鍚堜笓瀹讹級澶фā鍨嬶紝鎻愪緵 OpenAI 鍏煎鐨?API 鎺ュ彛銆傛湰鏂囨。甯姪浣犲揩閫熸帴鍏ュ苟寮€濮嬩娇鐢ㄣ€?
---

## 鐩綍

- [1. 鍩虹淇℃伅](#1-鍩虹淇℃伅)
- [2. 鐜鍑嗗](#2-鐜鍑嗗)
- [3. 5 鍒嗛挓蹇€熷紑濮媇(#3-5-鍒嗛挓蹇€熷紑濮?
- [4. 鏍稿績鍙傛暟璇存槑](#4-鏍稿績鍙傛暟璇存槑)
- [5. 杩涢樁鑳藉姏](#5-杩涢樁鑳藉姏)
- [6. 甯歌鎶ラ敊涓庢帓鏌(#6-甯歌鎶ラ敊涓庢帓鏌?
- [7. 鏇村绀轰緥](#7-鏇村绀轰緥)

---

## 1. 鍩虹淇℃伅

### 1.1 API 绔偣

Hy3 鏀寔浠ヤ笅鎺ュ叆鏂瑰紡锛?
| 鎺ュ叆鏂瑰紡 | Base URL | 閫傜敤鍦烘櫙 |
|----------|----------|----------|
| **TokenHub锛堟帹鑽愶級** | `https://tokenhub.tencentmaas.com/v1` | 浜?API锛屽紑绠卞嵆鐢?|
| **鑵捐浜?LKEAP** | `https://api.lkeap.cloud.tencent.com/plan/v3` | 鑵捐浜戠敤鎴?|
| **鑷儴缃?(vLLM/SGLang)** | `http://127.0.0.1:8000/v1` | 绉佹湁鍖栭儴缃?|

### 1.2 鍙敤妯″瀷

| 妯″瀷鍚?| 璇存槑 |
|--------|------|
| `hy3` | Hy3 姝ｅ紡鐗堬紙鎺ㄨ崘锛?|
| `hy3-preview` | Hy3 Preview 鐗?|
| `hunyuan/hy3` | EdgeOne 骞冲彴涓婄殑鍚嶇О |

### 1.3 API Key

- **TokenHub**锛氬湪 [TokenHub 鎺у埗鍙癩(https://tokenhub.tencentmaas.com) 鍒涘缓 API Key
- **鑵捐浜?*锛氬湪 [鑵捐浜戞帶鍒跺彴](https://console.cloud.tencent.com) 鑾峰彇 SecretId/SecretKey
- **鑷儴缃?*锛氭湰鍦伴儴缃叉椂鏃犻渶璁よ瘉锛宍api_key` 浼?`"EMPTY"` 鍗冲彲

### 1.4 閫熺巼闄愬埗涓庡畾浠?
| 椤圭洰 | 璇存槑 |
|------|------|
| **涓婁笅鏂囩獥鍙?* | 256K tokens |
| **鏈€澶ц緭鍑?* | 32K tokens锛堟寮忕増锛? 128K tokens锛圥review锛?|
| **杈撳叆浠锋牸** | 楼1.00 / 鐧句竾 tokens |
| **杈撳嚭浠锋牸** | 楼4.00 / 鐧句竾 tokens |
| **缂撳瓨鍛戒腑** | 楼0.25 / 鐧句竾 tokens |
| **骞跺彂闄愬埗** | 瑙嗗叿浣撳钩鍙板椁愯€屽畾锛屽厤璐圭増閫氬父涓?5锝?0 QPS |

### 1.5 妯″瀷瑙勬牸

| 灞炴€?| 鍊?|
|------|-----|
| 鏋舵瀯 | Mixture-of-Experts (MoE) |
| 鎬诲弬鏁?| 295B |
| 婵€娲诲弬鏁?| 21B |
| MTP 灞傚弬鏁?| 3.8B |
| 涓婁笅鏂囬暱搴?| 256K |
| 涓撳鏁伴噺 | 192 涓紝top-8 婵€娲?|

---

## 2. 鐜鍑嗗

### 瀹夎 Python SDK

```bash
pip install openai
```

### 璁剧疆鐜鍙橀噺

```bash
# Linux / macOS
export HY3_API_KEY="your-api-key-here"
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"

# Windows PowerShell
$env:HY3_API_KEY = "your-api-key-here"
$env:HY3_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
```

---

## 3. 5 鍒嗛挓蹇€熷紑濮?
### 3.1 鏈€绠€璋冪敤 鈥?Python (OpenAI SDK)

```python
import os
from openai import OpenAI

# 1. 鍒涘缓瀹㈡埛绔?client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "your-api-key"),
    base_url=os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"),
)

# 2. 鍙戣捣瀵硅瘽璇锋眰
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "浣犲ソ锛佽鐢ㄤ竴鍙ヨ瘽浠嬬粛浣犺嚜宸便€?},
    ],
    temperature=0.9,
    max_tokens=512,
)

# 3. 鎵撳嵃缁撴灉
print(response.choices[0].message.content)
```

**杩愯锛?*
```bash
python quickstart_demo.py
```

### 3.2 鏈€绠€璋冪敤 鈥?curl

```bash
curl https://tokenhub.tencentmaas.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "浣犲ソ锛佽鐢ㄤ竴鍙ヨ瘽浠嬬粛浣犺嚜宸便€?}
    ],
    "temperature": 0.9,
    "max_tokens": 512
  }'
```

**棰勬湡杈撳嚭锛堢ず渚嬶級锛?*
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1720000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "浣犲ソ锛佹垜鏄吘璁贩鍏?Hy3锛屼竴涓?295B 鍙傛暟鐨勬贩鍚堜笓瀹跺ぇ妯″瀷锛屾搮闀挎帹鐞嗐€佺紪绋嬪拰鏅鸿兘浣撲换鍔°€?
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 35,
    "total_tokens": 55
  }
}
```

### 3.3 鑷儴缃叉柟寮忚皟鐢?
濡傛灉浣犲凡閫氳繃 vLLM 鎴?SGLang 鑷閮ㄧ讲 Hy3锛?
```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "浣犲ソ锛佽绠€鍗曚粙缁嶄竴涓嬩綘鑷繁銆?},
    ],
    temperature=0.9,
    top_p=1.0,
    # 鑷儴缃叉椂閫氳繃 extra_body 浼犲叆 reasoning_effort
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print(response.choices[0].message.content)
```

---

## 4. 鏍稿績鍙傛暟璇存槑

### 4.1 鍩虹鍙傛暟

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| `temperature` | float | 0.9 | 閲囨牱娓╁害銆?锝?锛岃秺楂樿秺闅忔満锛岃秺浣庤秺纭畾銆傛帹鑽?0.9 |
| `top_p` | float | 1.0 | 鏍搁噰鏍枫€傚彧浠庣疮绉鐜囪揪鍒?top_p 鐨?token 涓噰鏍枫€傛帹鑽?1.0 |
| `max_tokens` | int | 鈥?| 鏈€澶ц緭鍑?token 鏁般€備笉浼犲垯鐢辨ā鍨嬭嚜鍔ㄥ喅瀹?|
| `stop` | str / list | 鈥?| 鍋滄璇嶃€傞亣鍒拌鍐呭鏃跺仠姝㈢敓鎴?|
| `stream` | bool | false | 鏄惁鍚敤娴佸紡杈撳嚭 |

### 4.2 鎺ㄧ悊妯″紡 (reasoning_effort)

Hy3 鏀寔銆屽揩鎱㈡€濊€冭瀺鍚堛€嶁€斺€斿彲鏍规嵁浠诲姟澶嶆潅搴﹀垏鎹㈡帹鐞嗘繁搴︺€?
| 鍊?| 妯″紡 | 閫傜敤鍦烘櫙 |
|----|------|----------|
| `"no_think"` / `"low"` | 蹇€濊€冿紙鐩存帴鍥炲锛?| 鏃ュ父瀵硅瘽銆佺畝鍗曢棶绛?|
| `"medium"` | 涓瓑鎺ㄧ悊 | 涓€鑸垎鏋愪换鍔?|
| `"high"` | 鎱㈡€濊€冿紙娣卞害鎬濈淮閾撅級 | 鏁板銆佺紪绋嬨€佸鏉傛帹鐞?|

**浜?API 璋冪敤鏂瑰紡锛?*
```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "璇佹槑鈭?鏄棤鐞嗘暟"}],
    reasoning_effort="high",  # 寮€鍚繁搴︽€濊€?)
```

**鑷儴缃?(vLLM) 璋冪敤鏂瑰紡锛?*
```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "璇佹槑鈭?鏄棤鐞嗘暟"}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

> **娉ㄦ剰**锛氬紑鍚繁搴︽€濊€冨悗锛屽搷搴斾腑浼氬寘鍚?`reasoning_content` 瀛楁锛堟€濊€冭繃绋嬶級锛宍content` 瀛楁涓烘渶缁堢瓟妗堛€?
### 4.3 宸ュ叿璋冪敤 (Tools / Function Calling)

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "鑾峰彇鎸囧畾鍩庡競鐨勫ぉ姘斾俊鎭?,
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "鍩庡競鍚嶇О"}
                },
                "required": ["city"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "鍖椾含浠婂ぉ澶╂皵鎬庝箞鏍凤紵"}],
    tools=tools,
    tool_choice="auto",  # auto / none / required
)
```

`tool_choice` 閫夐」锛?| 鍊?| 璇存槑 |
|----|------|
| `"auto"` | 妯″瀷鑷姩鍐冲畾鏄惁璋冪敤宸ュ叿锛堥粯璁わ級 |
| `"none"` | 涓嶈皟鐢ㄥ伐鍏凤紝鐩存帴鍥炲 |
| `"required"` | 寮哄埗璋冪敤宸ュ叿 |
| `{"type": "function", "function": {"name": "xxx"}}` | 寮哄埗璋冪敤鎸囧畾宸ュ叿 |

---

## 5. 杩涢樁鑳藉姏

### 5.1 娴佸紡杈撳嚭 (Streaming)

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "鍐欎竴棣栧叧浜庝汉宸ユ櫤鑳界殑璇?}],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
```

### 5.2 澶氳疆瀵硅瘽

```python
messages = [
    {"role": "system", "content": "浣犳槸涓€涓笓涓氱殑 Python 缂栫▼鍔╂墜銆?},
    {"role": "user", "content": "Python 涓浣曞弽杞竴涓垪琛紵"},
    {"role": "assistant", "content": "鍙互浣跨敤 `list.reverse()` 鏂规硶鎴栧垏鐗?`list[::-1]`銆?},
    {"role": "user", "content": "杩欎袱绉嶆柟寮忔湁浠€涔堝尯鍒紵"},
]

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
)
```

### 5.3 缁撴瀯鍖栬緭鍑?
Hy3 鏀寔 `response_format` 鍙傛暟寮哄埗 JSON 杈撳嚭锛?
```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "鍒楀嚭 3 绉嶆帓搴忕畻娉曠殑鍚嶇О鍜屽鏉傚害"}],
    response_format={"type": "json_object"},
)
```

### 5.4 鑾峰彇 Token 鐢ㄩ噺

姣忔璇锋眰鐨勫搷搴斾腑鍧囧寘鍚?`usage` 瀛楁锛?
```python
print(f"杈撳叆 tokens: {response.usage.prompt_tokens}")
print(f"杈撳嚭 tokens: {response.usage.completion_tokens}")
print(f"鎬昏 tokens: {response.usage.total_tokens}")
```

---

## 6. 甯歌鎶ラ敊涓庢帓鏌?
### 6.1 璁よ瘉閿欒 (401 Unauthorized)

```
Error: 401 - Invalid API Key
```

**鍘熷洜**锛欰PI Key 鏃犳晥鎴栨湭浼犲叆銆?**瑙ｅ喅**锛?- 妫€鏌?`Authorization: Bearer <key>` 澶撮儴鏄惁姝ｇ‘
- 纭 API Key 鏈繃鏈燂紙TokenHub 鎺у埗鍙板彲鏌ョ湅锛?- 妫€鏌ョ幆澧冨彉閲忔槸鍚︽纭缃?
### 6.2 闄愭祦閿欒 (429 Too Many Requests)

```
Error: 429 - Rate limit exceeded
```

**鍘熷洜**锛氳秴鍑?API 閫熺巼闄愬埗銆?**瑙ｅ喅**锛?- 闄嶄綆璇锋眰棰戠巼锛屽疄鐜版寚鏁伴€€閬块噸璇曪紙鍙傝 [06_error_handling.py](examples/06_error_handling.py)锛?- 鍗囩骇濂楅浠ヨ幏寰楁洿楂樺苟鍙戦厤棰?
### 6.3 瓒呮椂閿欒

```
Error: Request timed out / ReadTimeout
```

**鍘熷洜**锛氳姹傛椂闂磋繃闀匡紝鏈嶅姟鍣ㄦ棤鍝嶅簲銆?**瑙ｅ喅**锛?- 澧炲ぇ `timeout` 鍙傛暟锛歚OpenAI(..., timeout=60.0)`
- 鍑忓皬 `max_tokens` 浠ョ缉鐭敓鎴愭椂闂?- 鍚敤 `stream=True` 鑾峰彇澧為噺杈撳嚭

### 6.4 妯″瀷涓嶅彲鐢?(404 Not Found)

```
Error: 404 - Model not found
```

**鍘熷洜**锛氭ā鍨嬪悕閿欒鎴栨湭寮€閫氥€?**瑙ｅ喅**锛?- 纭妯″瀷鍚嶆嫾鍐欙細搴斾负 `hy3` 鎴?`hy3-preview`
- TokenHub 闇€鍦ㄦ帶鍒跺彴鍏堝紑閫氬搴旀ā鍨?
### 6.5 鍐呭杩囨护 (400 Bad Request)

```
Error: 400 - Content filtered
```

**鍘熷洜**锛氳緭鍏ユ垨杈撳嚭瑙﹀彂瀹夊叏瀹℃牳銆?**瑙ｅ喅**锛?- 淇敼 prompt 鎺緸
- 纭鍐呭涓嶈繚鍙嶄娇鐢ㄦ潯娆?
### 6.6 杩炴帴閿欒

```
Error: ConnectionError / Connection refused
```

**鍘熷洜**锛氱綉缁滀笉閫氭垨 Base URL 涓嶆纭€?**瑙ｅ喅**锛?- 纭 `base_url` 鎷煎啓姝ｇ‘锛堟敞鎰?`/v1` 鍚庣紑锛?- 妫€鏌ラ槻鐏/浠ｇ悊璁剧疆
- 鑷儴缃叉椂纭鏈嶅姟宸插惎鍔細`curl http://127.0.0.1:8000/v1/models`

---

## 7. 鏇村绀轰緥

瀹屾暣鐨勫彲杩愯绀轰緥璇锋煡鐪?[examples/](examples/) 鐩綍锛?
| # | 绀轰緥 | 鏂囦欢 | 璇存槑 |
|---|------|------|------|
| 1 | Basic Chat | [`01_basic_chat.py`](examples/01_basic_chat.py) | 鍗曡疆 & 澶氳疆瀵硅瘽 |
| 2 | Streaming | [`02_streaming.py`](examples/02_streaming.py) | 娴佸紡璇锋眰 + 閫?chunk 瑙ｆ瀽 |
| 3 | Latency Comparison | [`03_latency_compare.py`](examples/03_latency_compare.py) | 娴佸紡 vs 闈炴祦寮忥細棣?token 鏃跺欢 & 鎬昏€楁椂 |
| 4 | Tool Calling | [`04_tool_calling.py`](examples/04_tool_calling.py) | 鍗曟璋冪敤 + 澶氳疆宸ュ叿寰幆 |
| 5 | Reasoning Mode | [`05_reasoning_mode.py`](examples/05_reasoning_mode.py) | 娣卞害鎬濊€?寮€/鍏?瀵规瘮 |
| 6 | Error Handling | [`06_error_handling.py`](examples/06_error_handling.py) | 瓒呮椂/闄愭祦/缃戠粶閿欒鐨勯噸璇曚笌閫€閬?|

鎵€鏈夌ず渚嬪彲鐩存帴杩愯锛?
```bash
export HY3_API_KEY="your-key"
cd examples
python 01_basic_chat.py
```

---

## 闄勫綍锛歷LLM 閮ㄧ讲蹇€熷弬鑰?
```bash
# 1. 鍚姩 vLLM 鏈嶅姟
export VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm
vllm serve tencent/Hy3 \
  --tensor-parallel-size 8 \
  --speculative-config.method mtp \
  --speculative-config.num_speculative_tokens 2 \
  --tool-call-parser hy_v3 \
  --reasoning-parser hy_v3 \
  --enable-auto-tool-choice \
  --port 8000 \
  --served-model-name hy3

# 2. 楠岃瘉鏈嶅姟
curl http://127.0.0.1:8000/v1/models
```

## 闄勫綍锛歋GLang 閮ㄧ讲蹇€熷弬鑰?
```bash
python3 -m sglang.launch_server \
  --model tencent/Hy3 \
  --tp-size 8 \
  --tool-call-parser hunyuan \
  --reasoning-parser hunyuan \
  --speculative-num-steps 2 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 3 \
  --speculative-algorithm EAGLE \
  --port 8000 \
  --served-model-name hy3
```
