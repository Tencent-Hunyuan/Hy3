# Hy3 Research Canvas

Hy3 Research Canvas is an end-to-end Web application powered by the Hy3 OpenAI-compatible API. It demonstrates two practical workflows:

- Research brief generation: plan, evidence map, long-form report, citations, and next actions.
- Multilingual rewrite: translate and adjust tone while preserving factual claims.

The app has a real interactive frontend and a small Node.js backend. The backend calls Hy3 when `HY3_BASE_URL`, `HY3_API_KEY`, and `HY3_MODEL` are configured. `HY3_MOCK=1` enables deterministic demo output for local review without credentials.

## Run

```bash
cd examples/hy3-research-canvas
HY3_MOCK=1 npm start
```

Open http://127.0.0.1:4173.

For live Hy3 calls:

```bash
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
npm start
```

## End-to-End Demos

Demo 1 generates a research brief for a product manager:

```bash
node scripts/run-demos.js research
```

Demo 2 rewrites a release note in another language and tone:

```bash
node scripts/run-demos.js rewrite
```

Run both:

```bash
npm run demo
```

## Hy3 Role

Hy3 is the reasoning and language generation layer. The app sends structured prompts to Hy3 for planning, grounded synthesis, citation drafting, translation, and tone control. The frontend only orchestrates user interaction and renders the returned structured content.

## CodeBuddy Collaboration Notes

The app scaffold, Hy3 API wrapper, mock demo responses, and frontend interaction flow were created with CodeBuddy/Codex assistance for the Rhino-Bird issue. Manual review focused on API-key handling, mock/live mode separation, and demo reproducibility.

## Environment

- `HY3_BASE_URL`: OpenAI-compatible base URL, for example `http://127.0.0.1:8000/v1`.
- `HY3_API_KEY`: API key or `EMPTY` for a local vLLM/SGLang service.
- `HY3_MODEL`: Model name, default `hy3`.
- `HY3_MOCK`: Set to `1` for deterministic demos.
- `PORT`: Server port, default `4173`.
