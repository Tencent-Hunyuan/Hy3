# Minimal FastAPI App

A minimal FastAPI application exposing `GET /health` which returns:

```json
{"status": "ok"}
```

## Files

- `app.py` — the FastAPI application with the `/health` endpoint.

## Run with uvicorn

Install dependencies:

```bash
pip install fastapi uvicorn
```

Start the server:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
# => {"status":"ok"}
```

For development with auto-reload, use:

```bash
uvicorn app:app --reload
```
