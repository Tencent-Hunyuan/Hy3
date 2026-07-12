# Hy3 Review Workbench Design

## Goal

Build a small, polished, end-to-end web application that demonstrates Hy3 in a concrete code-review workflow. The application must be finishable within one day, use Hy3 only through an OpenAI-compatible API, and include two repeatable demo flows suitable for a video or GIF under two minutes.

## Scope

The workbench supports two actions:

1. Review a pasted unified diff for correctness, security, reliability, and test gaps.
2. Generate a focused test plan for a pasted unified diff.

It includes two built-in examples: a payment authorization flaw for the review flow and a retry-loop flaw for the test-plan flow. It does not include authentication, persistence, repository hosting integrations, local inference, training, fine-tuning, or automatic code modification.

## Architecture

Add a standalone Python package under `apps/review_workbench/`. FastAPI serves a single-page frontend and two JSON endpoints. The backend imports and reuses the existing `hy3_code_review_mcp` configuration, client, prompt builders, and review functions, so MCP and Web entry points share the same Hy3 behavior.

The browser never receives an API key. The backend reads Hy3 connection settings from the existing environment variables or repository `.env` file and calls the configured OpenAI-compatible Hy3 API.

## Components

- `app.py`: FastAPI application, static-page route, health/config status route, review endpoint, and test-plan endpoint.
- `schemas.py`: validated API request and response models with conservative input-size limits.
- `static/index.html`: the workbench structure and accessible controls.
- `static/styles.css`: responsive desktop and mobile presentation.
- `static/app.js`: mode switching, example loading, request lifecycle, result rendering, and copying.
- `examples.py`: two deterministic example diffs and their UI metadata.

## User Flow

The first screen is the working application. A compact header shows the Hy3 connection status. The main area uses a stable two-column layout on desktop and stacks on narrow screens.

The left side contains a segmented control for Review and Test Plan, example selectors, language or framework controls, optional context, and a diff editor. The primary action sends the request. The right side shows an empty state, loading state, formatted markdown-like output, request metadata, errors, and a copy action.

Demo flow one loads the payment example, runs Review, and highlights prioritized security and correctness findings. Demo flow two loads the retry example, switches to Test Plan, and returns unit, integration, edge-case, and regression suggestions.

## API And Data Flow

`POST /api/review` accepts `patch_text`, `language`, `focus`, and `context`. It calls `review_patch_with_client` and returns the Hy3 markdown plus metadata.

`POST /api/tests` accepts `diff_text`, `test_framework`, and `risk_level`. It calls `suggest_tests_with_client` and returns the Hy3 markdown plus metadata.

`GET /api/status` reports whether the endpoint, model, and usable credential configuration are present without returning secrets.

Inputs are normalized and limited to 24,000 characters before a Hy3 call. Results are rendered as text with a small safe markdown formatter that escapes model output before applying supported formatting.

## Error Handling

The API returns clear JSON errors for empty input, oversized input, invalid options, missing Hy3 configuration, upstream timeouts, and other Hy3 failures. The browser preserves the user's diff, exits the loading state, and presents a retryable message. Server logs do not include API keys or full source patches.

## Testing

Backend tests use FastAPI's test client and a fake completion client. They cover both successful endpoints, validation boundaries, status redaction, and translated upstream errors. Existing MCP tests must continue to pass.

Frontend logic is kept small and dependency-free. Verification includes syntax checks plus browser smoke testing at desktop and mobile viewport sizes for loading, success, error, example-selection, mode-switching, and copy states.

## Documentation And Demo Assets

The app README documents installation, environment setup, launch command, architecture, Hy3's role, both demo scripts, and which files were completed with CodeBuddy collaboration. The repository root README links to the workbench. A recording checklist keeps each demo flow within two minutes; the actual video or GIF is recorded after a live Hy3 endpoint is configured.

## Acceptance Criteria

- The implementation exists only on `feat/hy3-review-workbench` until explicitly merged.
- A user can launch one command and open the interactive Web UI.
- Both API flows call Hy3 through the existing client and work with a configured endpoint.
- Two examples can be loaded and run without manual patch preparation.
- Missing configuration and upstream failures are understandable and do not leak secrets.
- Automated backend tests and existing MCP tests pass.
- README text explains Hy3's role and CodeBuddy-assisted code blocks.
