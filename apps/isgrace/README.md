<p align="left">
    <a href="README_CN.md">中文</a>&nbsp;｜&nbsp;English
</p>

# isGrace — Your AI Study Partner, Powered by Hy3

> Turn reading into knowing.

**[github.com/KarlLeen/hy3Isgrace](https://github.com/KarlLeen/hy3Isgrace)**

isGrace is a free, open-source web app that turns any textbook into a structured, personal course. You don't just chat with an AI about your material — Grace walks you through it in two calibrated passes, checks that you actually understood before moving on, then tests you on exactly what was covered. Every response is required to come from *your* uploaded material, not the model's background knowledge.

![isGrace](public/assets/grace-avatar.png)

## Two ways to use it

isGrace has no separate "mode switcher" — which mode you're in falls out naturally from what you upload.

- **📚 Self-study mode** — upload just a textbook (or lecture notes, or any PDF you're curious about). isGrace splits it into modules using the textbook's *own* chapter structure — no syllabus required. This is the flagship use case: pick any subject you want to learn and go.
- **🎓 Course mode** — upload your course's syllabus / module outline, and (optionally) an exam guide. isGrace extracts the *course's own* module breakdown instead of guessing from the textbook, and when it's time to generate a quiz or a pre-exam cheatsheet, it scopes coverage to match your actual exam guide's topics and difficulty — not a generic recap.

### The per-module flow (both modes)

1. **High-school pass** — Grace explains the module using plain language and everyday analogies, strictly from the concepts your uploaded material actually covers.
2. **College pass** — once you confirm you have no more questions, Grace re-explains the same module at full academic depth: definitions, worked examples, comparison tables, edge cases — everything a rigorous exam would expect, still grounded in your material.
3. **Gated quiz** — once you confirm the college pass is clear too, Grace generates exam questions for that module. In course mode with an exam guide uploaded, question scope and difficulty are matched to the guide; otherwise the quiz covers the module's material comprehensively.

Each stage transition is an **explicit button click**, not something the model infers from your wording — so the flow behaves the same way every time.

### Exam prep (course mode)

Near a midterm or final, click **Prepare for exam** (shown once an exam guide is uploaded) to get a single cheatsheet plus a practice quiz built from your exam guide + textbook together, matching the guide's stated scope and difficulty.

## Powered by Hy3

isGrace calls **Tencent Hunyuan Hy3** (via [OpenRouter](https://openrouter.ai/), model slug `tencent/hy3`) for every piece of intelligence in the app — there is no local inference, fine-tuning, or training involved. Specifically, Hy3 is responsible for:

- **Structuring the course** — reading an uploaded textbook's table of contents (self-study) or a syllabus (course mode) and returning a clean, ordered module list as structured JSON.
- **Teaching, twice, at two different levels** — generating the high-school pass and the college pass for each module, strictly grounded in the uploaded material (see [`gracePrompt.ts`](src/renderer/services/gracePrompt.ts) for the "source fidelity" rules Hy3 is instructed to follow — it must use the material's own terminology, categories, and examples, never substitute its own background knowledge).
- **Writing the cheatsheet and the quiz** — turning what was just taught (or an exam guide's stated scope) into a structured cheatsheet and a JSON-schema exam (multiple choice, essay, and code questions, each with a grading rubric derived from the material).
- **Grading free-response answers** — essay and code answers are graded by Hy3 against the rubric it wrote when generating the question, with a written explanation of what was right, what was missing, and why.

Why Hy3 specifically fits this app well:
- **256K context** means a full textbook chapter, a syllabus, and an exam guide can all be sent in full, uncompressed, in a single turn — no lossy chunking or retrieval needed for the material the student is actively studying.
- **Anti-hallucination tuning** is exactly the property this app leans on hardest: every pass, cheatsheet, and quiz question must come from the uploaded material specifically, not "a plausible answer for this subject in general." isGrace's system prompt repeatedly enforces "use the material's own terms — never substitute a more common set from training data," which only works if the underlying model is reliably grounded.
- **Reliable structured output** — the app asks Hy3 to emit specific tagged blocks (`<MODULES_JSON>`, `<CHEATSHEET>`, `<TEST_JSON>`) that the frontend parses out of the streamed response and turns into real UI (a module list, a cheatsheet panel, a quiz). This depends on the model consistently respecting output-format instructions turn after turn.

Every LLM call in the app funnels through one function, [`streamChat()`](server/services/llmService.ts), which is provider-agnostic — Hy3 via OpenRouter is simply the default and the one used throughout development and testing, but swapping providers only requires changing the Settings panel.

## How it works

```
┌─────────────────────────┐        ┌──────────────────────────┐        ┌─────────────┐
│  React + Vite frontend  │  fetch │   Express backend         │  HTTPS │  OpenRouter  │
│  (chat UI, modules,     │◄──────►│   (server/) — file parsing,│◄──────►│  → Hy3       │
│   cheatsheet, tests)    │  /api  │   prompt assembly, SSE     │        │              │
└─────────────────────────┘        └──────────────────────────┘        └─────────────┘
```

- The **frontend** (`src/`) never talks to OpenRouter directly — it calls the local Express backend, which streams the model's response back over Server-Sent Events. Your API key lives only in the backend's local `data/settings.json` (gitignored), never in browser code.
- Uploaded materials (PDF/DOCX/TXT/MD, or a URL) are parsed server-side and sent to Hy3 in full on every relevant turn — see the "Uploaded Learning Materials" section of the system prompt in `gracePrompt.ts`.
- The model's replies are streamed token-by-token into the chat. When a reply finishes, the frontend scans it for `<MODULES_JSON>`, `<CHEATSHEET>`, and `<TEST_JSON>` tags, extracts and parses each one, strips the raw tag out of the visible chat text, and turns the parsed data into real app state (a module list, a saved cheatsheet, a graded quiz) — see [`dispatchGrace.ts`](src/renderer/services/dispatchGrace.ts).

## Features

- Two study modes (self-study from a bare textbook, or course mode with a syllabus + exam guide) sharing one teaching engine
- Two-pass teaching (high-school → college level) strictly grounded in your own uploaded material
- Explicit, button-gated progression through each module — no guessing whether the AI thinks you're ready to move on
- Auto-generated tests (multiple-choice, essay, and code questions) with AI grading and rubric-based feedback
- Exam-prep mode: cheatsheet + practice quiz scoped to your actual exam guide
- Upload PDFs, Word docs, plain text, or paste a URL
- Bilingual support (English & 中文)
- Bring your own OpenRouter (or Anthropic / OpenAI / Gemini / DeepSeek / Qwen / Kimi) API key — no subscription, no middleman

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) 18+
- An API key from [OpenRouter](https://openrouter.ai/keys) (recommended — this is how the app reaches Hy3), or from Anthropic / OpenAI / Google AI Studio if you'd rather use a different model

### Run in development

```bash
npm install
npm run dev
```

This starts two processes together: the Vite dev server (frontend, default `http://localhost:5173`) and the Express backend (`http://localhost:3001`), proxied so the frontend can call `/api/*` with no CORS setup needed.

On first launch, open **Settings** in the app, select **OpenRouter** as the provider, paste your key, and pick **Tencent Hy3** from the model list (it's the default). Your key is written to a local, gitignored `data/settings.json` — it never leaves your machine except in requests to OpenRouter.

### Build for production

```bash
npm run build
```

Type-checks and bundles the frontend into `dist/`. Run the backend with `npm run server` (or `tsx server/index.ts` directly) alongside a static file server for `dist/`, or point Express at `dist/` yourself — this is a small hackathon-scoped backend, not a hardened multi-tenant deployment (no auth, no database; storage is a local `data/` directory).

### Environment variables (all optional)

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `3001` | Backend port |
| `WORKSPACE_DIR` | `./data` | Where materials, config, and settings are stored |
| `CLIENT_ORIGIN` | `http://localhost:5173` | Allowed CORS origin for the frontend |
| `VITE_API_BASE_URL` | `/api` | Override if the frontend and backend aren't served from the same origin |

## Tech Stack

- [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) — UI
- [Vite](https://vitejs.dev/) — frontend bundler & dev server
- [Tailwind CSS v4](https://tailwindcss.com/) — styling
- [Zustand](https://zustand-demo.pmnd.rs/) — client state management
- [Express](https://expressjs.com/) — backend API + SSE streaming proxy to OpenRouter/Hy3
- `pdf-parse`, `mammoth`, `turndown` — PDF / DOCX / URL-to-markdown material parsing

## Project structure

```
src/                       Frontend (React + Zustand)
  renderer/
    components/            ChatPanel, ResourcePanel, TestPanel, Settings, ...
    services/
      gracePrompt.ts        The full Grace system prompt + per-turn "directive" scoping
      dispatchGrace.ts       Sends a turn to Hy3, streams the reply, extracts tagged output
      api.ts                 Thin fetch/SSE client for the backend
    store/useStore.ts        Zustand store (subjects, materials, modules, chat, tests)
  types/index.ts             Shared types + LLM provider configs (Hy3 default lives here)
server/                    Backend (Express)
  routes.ts                  REST + SSE endpoints
  services/                  Material parsing, LLM streaming, local storage — mostly
                              provider-agnostic, reusable outside this app
```

## License

MIT
