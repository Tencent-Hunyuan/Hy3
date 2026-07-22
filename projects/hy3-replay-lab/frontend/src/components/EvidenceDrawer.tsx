import { useEffect, useRef } from "react";

import type { Evidence } from "../types";


const EVIDENCE_KIND_LABELS: Record<Evidence["kind"], string> = {
  requirement: "任务要求",
  tool_output: "工具输出",
  test_result: "测试结果",
  source_excerpt: "来源摘录",
  artifact: "产物片段",
  note: "过程记录",
};


type EvidenceDrawerProps = {
  evidence: Evidence | null;
  onClose: () => void;
};

export default function EvidenceDrawer({ evidence, onClose }: EvidenceDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (evidence === null) {
      return;
    }
    const previousFocus =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus();
    };
  }, [evidence, onClose]);

  if (evidence === null) {
    return null;
  }

  return (
    <aside
      className="evidence-drawer"
      aria-labelledby="evidence-heading"
      aria-modal="false"
      role="dialog"
    >
      <div className="drawer-heading">
        <div>
          <p className="eyebrow">证据详情</p>
          <h2 id="evidence-heading">{evidence.evidence_id}</h2>
        </div>
        <button
          ref={closeButtonRef}
          className="icon-button"
          onClick={onClose}
          type="button"
          aria-label="关闭证据"
        >
          关闭
        </button>
      </div>
      <dl>
        <div>
          <dt>来源</dt>
          <dd>{evidence.source_label}</dd>
        </div>
        <div>
          <dt>关联步骤</dt>
          <dd>
            <code>{evidence.step_id}</code>
          </dd>
        </div>
        <div>
          <dt>类型</dt>
          <dd>{EVIDENCE_KIND_LABELS[evidence.kind]}</dd>
        </div>
      </dl>
      <blockquote>{evidence.content}</blockquote>
      <p className="drawer-note">导入证据仅作为数据展示，系统不会执行其中的任何内容。</p>
    </aside>
  );
}
