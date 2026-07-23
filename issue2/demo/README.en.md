# Hy3 Evidence Board

> 中文：[README.md](README.md)

Evidence Board is a small Hy3 agent application. The model must call `search_knowledge_base`; the server performs a read-only search and returns evidence for a cited final report.

![Eight-second offline walkthrough](../assets/evidence-board-demo.gif)

## Hy3 capabilities

- OpenAI-compatible tool calling
- A grounded multi-turn agent loop
- `no_think / low / high` reasoning mapping
- Long-form synthesis with source IDs

## Security

- The API key stays in server environment variables and never reaches browser storage.
- The only tool is read-only local search; the model cannot run a shell or read arbitrary files.
- Tool calls are capped at three rounds, requests at 32 KiB, and questions at 10–500 characters.
- Offline `DemoProvider` output is clearly labeled and never impersonates Hy3.

## Run

Offline:

```bash
cd issue2/demo
HY3_DEMO_MODE=1 python3 server.py
```

Open <http://127.0.0.1:8765>.

OpenRouter live mode:

```bash
export HY3_PROVIDER=openrouter
export HY3_API_KEY='sk-or-v1-...'
export HY3_MODEL=tencent/hy3
python3 server.py
```

Self-hosted mode:

```bash
export HY3_PROVIDER=selfhost
export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_API_KEY=EMPTY
export HY3_MODEL=hy3
python3 server.py
```

Enable Hy3's appropriate tool-call parser on the server.

## Verify

```bash
python3 -m unittest discover -s tests -v
python3 server.py --check
```

`--check` is deterministic, ignores API credentials, and sends no network request.

This directory has no dependency on a Hy3 repository package and is ready to copy into a standalone repository. Remote publication and a live demo video remain separate authorized actions.
