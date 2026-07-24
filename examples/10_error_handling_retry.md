# 10 Error handling and retry

Retry connection errors, timeouts, rate limits, and server errors with exponential backoff and jitter.

```bash
uv run --env-file .env python examples/10_error_handling_retry.py
```

The script disables SDK automatic retries, allows three attempts, and retries `APIConnectionError`, `APITimeoutError`, `RateLimitError`, and `InternalServerError`. It logs the attempt and delay, then re-raises the final exception after the retry limit is reached. Production code should also record `request_id` and honor `Retry-After` when available.

## Output example

Successful output from one run:

```text
腾讯混元大模型是腾讯自主研发的通用大语言模型，具备多模态理解与生成能力……
```

English translation: “Tencent Hunyuan is a general-purpose large language model developed by Tencent, with multimodal understanding and generation capabilities.”

When a retryable error occurs, the script may print:

```text
Attempt 1 failed: RateLimitError; retrying in 1.23s
```
