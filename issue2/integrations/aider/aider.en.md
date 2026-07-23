# Use Hy3 with Aider

> 中文：[aider.md](aider.md) · [Back to index](../README.en.md)

Aider is a terminal pair-programming agent. Its official docs support arbitrary OpenAI-compatible endpoints and require the `openai/` model prefix.

## Install

Follow the [official installer](https://aider.chat/docs/install.html):

```bash
python -m pip install aider-install
aider-install
aider --version
```

Use the current stable release. The settings below were checked against Aider's [OpenAI-compatible API](https://aider.chat/docs/llms/openai-compat.html) and [options](https://aider.chat/docs/config/options.html) docs on 2026-07-23.

## Configure

Self-hosted:

```bash
export OPENAI_API_BASE=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=EMPTY
aider --model openai/hy3 --edit-format diff
```

OpenRouter:

```bash
export OPENROUTER_API_KEY='sk-or-v1-...'
aider --model openrouter/tencent/hy3 --edit-format diff
```

Keep only non-secret defaults in `.aider.conf.yml`:

```yaml
model: openrouter/tencent/hy3
edit-format: diff
auto-commits: false
show-model-warnings: true
```

An unknown-price or metadata warning for a new model is not a failed request; judge the actual response and diff.

## First conversation

In a temporary Git repository, ask:

```text
/ask Inspect this repository read-only and list the files you can see. Do not modify anything.
```

Verify Aider shows the intended model and `git status --short` remains empty.

## End-to-end task

Ask Aider to implement `slugify(text)` in `src/slugify.py`, add at least six `unittest` edge cases in `tests/test_slugify.py`, avoid all other files, and run `python3 -m unittest discover -s tests -v`.

Use `/add` to scope files, inspect every diff, and trust the test exit code rather than a success sentence. `/undo` reverses the turn, while `auto-commits: false` prevents an unrequested commit.

The shared repository task produces this UI:

![Evidence Board offline screenshot](../../assets/evidence-board-offline.png)

## Troubleshooting

| Symptom | Fix |
|:---|:---|
| Unknown model warning | Keep the provider prefix and set `--edit-format diff` |
| Self-hosted connection fails | Include `/v1` in `OPENAI_API_BASE` and check the listener |
| Key appears in shell history | Inject it as an environment secret; never pass it inline |
| Too many files changed | `/add` only the required files and state the path boundary |
| Reasoning ignored | Aider's switch sends an OpenAI-style field; verify whether your Hy3 gateway maps it to `chat_template_kwargs` |
