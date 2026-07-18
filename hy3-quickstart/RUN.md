# Hy3 API quickstart & examples —— 运行说明

本目录是一套**可直接运行**的 Hy3 API 示例(腾讯混元 Hy3,经腾讯云 tokenhub,OpenAI 兼容接口)。

## 1. 准备
```bash
cd ~/犀牛鸟/hy3-quickstart
pip install -r requirements.txt          # openai + python-dotenv
cp .env.example .env
# 编辑 .env, 填入你的 tokenhub Key:  HY3_API_KEY=sk-xxxx
```

## 2. 依次运行 6 个 example(从根目录运行)
```bash
python examples/01_basic_chat.py
python examples/02_streaming.py
python examples/03_streaming_vs_nonstream.py
python examples/04_tool_calling.py
python examples/05_reasoning_mode.py
python examples/06_error_handling_retry.py
```

## 3. 把每个脚本的【完整 stdout】贴回来给我
我会用这些**真实输出**写成最终的 `quickstart.md` + 6 个 `.md` 文档(每个含:完整请求 + 完整 response 解析 + 真实示例输出)。

## 脚本对应 issue 要求
| 脚本 | issue 要求的 example |
|------|------|
| 01_basic_chat | basic chat(单轮 / 多轮) |
| 02_streaming | streaming(流式 + 逐 chunk 解析) |
| 03_streaming_vs_nonstream | non-streaming vs streaming(首 token 时延 / 总耗时) |
| 04_tool_calling | tool calling(一次调用 + 多轮工具循环) |
| 05_reasoning_mode | reasoning mode(思考过程 开/关 对比) |
| 06_error_handling_retry | error handling & retry(超时/限流/网络错误的重试与退避) |

> 05 是**探测脚本**:它会把不同 `reasoning_effort` 下 Hy3 的真实行为打出来,我们据此确定"思考模式开关"的准确写法。
