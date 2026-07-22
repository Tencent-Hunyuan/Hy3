import { useEffect, useRef, useState } from "react";

import {
  analyzeFixture,
  analyzeImportedTask,
  getHealth,
  importTaskFile,
  listFixtures,
  ReplayApiError,
} from "./api";
import CoverageMatrix from "./components/CoverageMatrix";
import EvidenceDrawer from "./components/EvidenceDrawer";
import ReplayPlanPanel from "./components/ReplayPlanPanel";
import Timeline from "./components/Timeline";
import type {
  AnalysisProvider,
  AnalysisResponse,
  Evidence,
  FixtureSummary,
  TaskSpec,
} from "./types";
import "./styles.css";


type ViewStatus = "loading" | "ready" | "analyzing" | "success" | "error";

const FIXTURE_ICONS: Record<string, string> = {
  "coding-loop": "</>",
  "research-grounding": "⌕",
};

const SEVERITY_LABELS: Record<string, string> = {
  low: "低风险",
  medium: "中风险",
  high: "高风险",
  critical: "严重风险",
};


export default function App() {
  const [fixtures, setFixtures] = useState<FixtureSummary[]>([]);
  const [status, setStatus] = useState<ViewStatus>("loading");
  const [activeFixtureId, setActiveFixtureId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [providerMode, setProviderMode] = useState<AnalysisProvider>("fake");
  const [liveConfigured, setLiveConfigured] = useState(false);
  const [importedTask, setImportedTask] = useState<TaskSpec | null>(null);
  const [importedFilename, setImportedFilename] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const requestController = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    requestController.current = controller;
    void Promise.all([listFixtures(controller.signal), getHealth(controller.signal)])
      .then(([items, health]) => {
        setFixtures(items);
        setLiveConfigured(health.live_provider_configured);
        setStatus("ready");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setErrorMessage(toUserMessage(error));
        setStatus("error");
      });
    return () => controller.abort();
  }, []);

  async function reloadFixtureCatalog() {
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setStatus("loading");
    setErrorMessage(null);
    try {
      const [items, health] = await Promise.all([
        listFixtures(controller.signal),
        getHealth(controller.signal),
      ]);
      setFixtures(items);
      setLiveConfigured(health.live_provider_configured);
      setStatus("ready");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      setErrorMessage(toUserMessage(error));
      setStatus("error");
    }
  }

  async function runAnalysis(fixtureId: string) {
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setActiveFixtureId(fixtureId);
    setAnalysis(null);
    setSelectedEvidenceId(null);
    setErrorMessage(null);
    setStatus("analyzing");
    try {
      const result = await analyzeFixture(fixtureId, providerMode, controller.signal);
      setAnalysis(result);
      setStatus("success");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setStatus("ready");
        return;
      }
      setErrorMessage(toUserMessage(error));
      setStatus("error");
    }
  }

  async function runImportedAnalysis() {
    if (importedTask === null) {
      return;
    }
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setProviderMode("hy3");
    setActiveFixtureId("custom-import");
    setAnalysis(null);
    setSelectedEvidenceId(null);
    setErrorMessage(null);
    setStatus("analyzing");
    try {
      const result = await analyzeImportedTask(importedTask, controller.signal);
      setAnalysis(result);
      setStatus("success");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setStatus("ready");
        return;
      }
      setErrorMessage(toUserMessage(error));
      setStatus("error");
    }
  }

  async function handleImport(file: File | undefined) {
    if (file === undefined) {
      return;
    }
    setImportError(null);
    setImportedTask(null);
    setImportedFilename(null);
    if (file.size > 128_000) {
      setImportError("文件超过 128000 字节上限。");
      return;
    }
    const controller = new AbortController();
    setIsImporting(true);
    try {
      const content = await file.text();
      const task = await importTaskFile(
        file.name,
        file.type || inferContentType(file.name),
        content,
        controller.signal,
      );
      setImportedTask(task);
      setImportedFilename(file.name);
      if (liveConfigured) {
        setProviderMode("hy3");
      }
    } catch (error) {
      setImportError(toUserMessage(error));
    } finally {
      setIsImporting(false);
    }
  }

  function stopWaiting() {
    requestController.current?.abort();
  }

  function retry() {
    if (activeFixtureId === "custom-import" && importedTask !== null) {
      void runImportedAnalysis();
    } else if (activeFixtureId !== null) {
      void runAnalysis(activeFixtureId);
    } else {
      void reloadFixtureCatalog();
    }
  }

  function selectProvider(provider: AnalysisProvider) {
    setProviderMode(provider);
    setAnalysis(null);
    setSelectedEvidenceId(null);
    setErrorMessage(null);
    setStatus("ready");
  }

  const selectedEvidence: Evidence | null =
    analysis?.report.evidence.find((item) => item.evidence_id === selectedEvidenceId) ?? null;
  const divergenceStep = analysis?.report.timeline.find(
    (step) => step.step_id === analysis.report.finding.first_divergence_step_id,
  );
  const firstFindingEvidenceId = analysis?.report.finding.evidence_ids[0] ?? null;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="#workspace" aria-label="Hy3 轨迹复盘台首页">
            <span className="brand-mark" aria-hidden="true">H3</span>
            <span className="brand-copy">
              <strong>Hy3 轨迹复盘台</strong>
              <small>让智能体的每一步都有据可查</small>
            </span>
          </a>
          <div className="topbar-meta">
            <div className="provider-switch" role="group" aria-label="分析模式">
              <button
                aria-pressed={providerMode === "fake"}
                disabled={status === "analyzing"}
                onClick={() => selectProvider("fake")}
                type="button"
              >
                离线演示
              </button>
              <button
                aria-pressed={providerMode === "hy3"}
                disabled={!liveConfigured || status === "analyzing"}
                onClick={() => selectProvider("hy3")}
                title={liveConfigured ? "使用服务端 Hy3 模型" : "尚未配置 HY3_API_KEY"}
                type="button"
              >
                在线 Hy3
              </button>
            </div>
            {analysis !== null && (
              <span className="report-id">
                报告 <code>{analysis.report.report_id}</code>
              </span>
            )}
          </div>
        </div>
      </header>

      <main id="workspace">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy-block">
            <p className="eyebrow">证据驱动的智能体复盘</p>
            <h1 id="hero-title">Hy3 轨迹复盘台</h1>
            <p className="hero-slogan">看清首个偏航点，只重放必要步骤。</p>
            <p className="hero-copy">
              导入智能体决策轨迹，定位最早出现且有证据支撑的偏航，保留有效工作，
              并为每个重放步骤设置可验证闸门。
            </p>
          </div>
          <div className="safety-card">
            <span className="safety-icon" aria-hidden="true">✓</span>
            <div>
              <strong>默认只读，边界清晰</strong>
              <p>不执行代码、不访问仓库或网址，也不展示隐藏推理过程。</p>
            </div>
          </div>
        </section>

        <section className="fixture-strip" aria-labelledby="fixtures-heading">
          <div className="strip-heading">
            <div>
              <p className="eyebrow">快速开始</p>
              <h2 id="fixtures-heading">选择一个复盘场景</h2>
            </div>
            {status === "loading" && <span className="loading-label">正在加载场景…</span>}
          </div>

          <div className="fixture-grid">
            {fixtures.map((fixture, index) => (
              <article
                className={`fixture-card${activeFixtureId === fixture.fixture_id ? " is-active" : ""}`}
                key={fixture.fixture_id}
              >
                <span className="fixture-icon" aria-hidden="true">
                  {FIXTURE_ICONS[fixture.fixture_id] ?? String(index + 1).padStart(2, "0")}
                </span>
                <div className="fixture-content">
                  <p>{fixture.domain}</p>
                  <h3>{fixture.title}</h3>
                  <span>{fixture.description}</span>
                </div>
                <button
                  aria-label={`分析${fixture.title}`}
                  className="card-action"
                  disabled={status === "analyzing"}
                  onClick={() => void runAnalysis(fixture.fixture_id)}
                  type="button"
                >
                  开始复盘 <span aria-hidden="true">→</span>
                </button>
              </article>
            ))}

            <article className={`fixture-card import-card${activeFixtureId === "custom-import" ? " is-active" : ""}`}>
              <span className="fixture-icon" aria-hidden="true">⇧</span>
              <div className="fixture-content">
                <p>自定义任务</p>
                <h3>导入自定义轨迹</h3>
                <span>支持 JSON、Markdown 和文本格式，单个文件不超过 128 KB。</span>
              </div>
              <div className="import-actions">
                <label className="card-action import-button">
                  {isImporting ? "正在校验…" : importedFilename === null ? "选择轨迹文件" : "更换轨迹文件"}
                  <input
                    accept=".json,.md,.txt,application/json,text/markdown,text/plain"
                    aria-label="导入 JSON、Markdown 或文本轨迹"
                    disabled={isImporting || status === "analyzing"}
                    onChange={(event) => void handleImport(event.target.files?.[0])}
                    type="file"
                  />
                </label>
                {importedTask !== null && importedFilename !== null && (
                  <button
                    className="primary-button import-analyze"
                    disabled={!liveConfigured || status === "analyzing"}
                    onClick={() => void runImportedAnalysis()}
                    title={liveConfigured ? "使用 Hy3 分析标准化导入轨迹" : "自定义导入需要配置 HY3_API_KEY"}
                    type="button"
                  >
                    分析导入轨迹
                  </button>
                )}
              </div>
              {importedFilename !== null && (
                <span className="imported-file">已就绪：<code>{importedFilename}</code></span>
              )}
            </article>
          </div>

          {importError !== null && <p className="import-error" role="alert">{importError}</p>}
        </section>

        <div className="status-region" aria-live="polite">
          {status === "analyzing" && (
            <div className="analysis-progress">
              <div className="progress-copy">
                <span className="spinner" aria-hidden="true" />
                <div>
                  <strong>正在追踪证据边界</strong>
                  <p>
                    {providerMode === "hy3"
                      ? "正在校验最小重放计划。停止等待只中断本页响应，服务端请求可能继续至超时。"
                      : "正在标准化步骤、闭合引用并校验最小重放计划。"}
                  </p>
                </div>
              </div>
              <button className="secondary-button" onClick={stopWaiting} type="button">
                停止等待
              </button>
            </div>
          )}
          {status === "error" && errorMessage !== null && (
            <div className="error-banner" role="alert">
              <div>
                <strong>分析已安全停止</strong>
                <p>{errorMessage}</p>
              </div>
              <button className="secondary-button" onClick={retry} type="button">重试</button>
            </div>
          )}
        </div>

        {analysis !== null && (
          <div className="report-workspace">
            <header className="report-header">
              <div>
                <p className="eyebrow">复盘结果</p>
                <h2>{analysis.report.task.title}</h2>
                <p>{analysis.report.task.description}</p>
              </div>
              <div className="analysis-metadata" aria-label="分析元数据">
                <span className="mode-badge">
                  {analysis.report.metadata.mode === "live" ? "在线 Hy3" : "离线演示"}
                </span>
                {typeof analysis.report.metadata.latency_ms === "number" && (
                  <span>{analysis.report.metadata.latency_ms.toLocaleString("zh-CN")} 毫秒</span>
                )}
                {typeof analysis.report.metadata.total_tokens === "number" && (
                  <span>{analysis.report.metadata.total_tokens.toLocaleString("zh-CN")} 个令牌</span>
                )}
              </div>
            </header>

            <div className="workspace-grid">
              <Timeline
                steps={analysis.report.timeline}
                firstDivergenceStepId={analysis.report.finding.first_divergence_step_id}
                impactStepIds={analysis.report.finding.impact_step_ids}
                onEvidenceSelect={setSelectedEvidenceId}
              />

              <section className="panel diagnosis-panel" aria-label="偏航诊断与验收覆盖">
                <section className="finding-card" aria-labelledby="finding-heading">
                  <div className="finding-title-row">
                    <span className="warning-symbol" aria-hidden="true">!</span>
                    <div>
                      <p className="eyebrow">首个偏航点</p>
                      <h2 id="finding-heading">
                        {divergenceStep === undefined
                          ? "未发现关键偏航"
                          : `第 ${String(divergenceStep.sequence).padStart(2, "0")} 步`}
                        {analysis.report.finding.first_divergence_step_id !== null && (
                          <code>{analysis.report.finding.first_divergence_step_id}</code>
                        )}
                      </h2>
                    </div>
                    <span className={`severity-pill severity-${analysis.report.finding.severity}`}>
                      {SEVERITY_LABELS[analysis.report.finding.severity] ?? analysis.report.finding.severity}
                    </span>
                  </div>
                  <p className="finding-explanation">{analysis.report.finding.explanation}</p>
                  <div className="evidence-links">
                    {analysis.report.finding.evidence_ids.map((evidenceId) => (
                      <button
                        className="evidence-chip finding-chip"
                        key={evidenceId}
                        onClick={() => setSelectedEvidenceId(evidenceId)}
                        type="button"
                      >
                        {evidenceId}
                      </button>
                    ))}
                  </div>
                </section>
                <CoverageMatrix
                  coverage={analysis.report.coverage}
                  criteria={analysis.report.criteria}
                  onEvidenceSelect={setSelectedEvidenceId}
                />
              </section>

              <aside className="panel replay-panel" aria-label="最小重放计划">
                <ReplayPlanPanel report={analysis.report} onEvidenceSelect={setSelectedEvidenceId} />
              </aside>
            </div>

            <nav className="action-dock" aria-label="报告操作">
              <button
                className="primary-button"
                disabled={firstFindingEvidenceId === null}
                onClick={() => setSelectedEvidenceId(firstFindingEvidenceId)}
                type="button"
              >
                <span aria-hidden="true">▤</span> 查看关键证据
              </button>
              <button
                className="secondary-button"
                onClick={() => downloadText(analysis.exports.json, "轨迹复盘报告.json", "application/json")}
                type="button"
              >
                <span aria-hidden="true">↓</span> 导出 JSON
              </button>
              <button
                className="secondary-button"
                onClick={() => downloadText(analysis.exports.markdown, "轨迹复盘报告.md", "text/markdown")}
                type="button"
              >
                <span aria-hidden="true">↓</span> 导出 Markdown
              </button>
            </nav>
          </div>
        )}
      </main>

      <EvidenceDrawer evidence={selectedEvidence} onClose={() => setSelectedEvidenceId(null)} />

      <footer>
        <span>Hy3 轨迹复盘台 0.1</span>
        <p>所有判断都必须闭合到已导入的步骤与证据编号。</p>
      </footer>
    </div>
  );
}


function toUserMessage(error: unknown): string {
  if (error instanceof ReplayApiError) {
    if (error.status === 429 && error.retryAfterSeconds !== null) {
      return `Hy3 请求受限，请在 ${error.retryAfterSeconds} 秒后重试。`;
    }
    return error.message;
  }
  return "本地服务不可用，请确认轨迹复盘台后端已启动。";
}


function downloadText(content: string, filename: string, mimeType: string) {
  const objectUrl = URL.createObjectURL(new Blob([content], { type: `${mimeType};charset=utf-8` }));
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}


function inferContentType(filename: string): string {
  const suffix = filename.toLowerCase().split(".").pop();
  if (suffix === "json") {
    return "application/json";
  }
  if (suffix === "md") {
    return "text/markdown";
  }
  return "text/plain";
}
