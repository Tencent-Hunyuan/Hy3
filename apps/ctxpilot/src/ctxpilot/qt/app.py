"""Qt desktop client for CtxPilot.

This is a *second presentation layer* on top of the exact same ``CtxPilot`` facade
that the Web UI and CLI use (DESIGN.md §4). It talks to business logic directly —
no HTTP server — which is why it is the easiest surface for interactive testing on
the user's machine. It only ever calls:

    CtxPilot.scan_projects / detected_agents / monitor_status / monitor_poll
    CtxPilot.snapshot / brief / watch / export / import_handoff / set_credentials

Requires PySide6 (optional dependency). If missing, the `ctxpilot qt` CLI command
prints a friendly install hint instead of crashing.

Real-time monitoring is driven by a QTimer that calls ``monitor_poll()`` every
3 s. We deliberately do NOT start the Monitor's internal thread here, so there is
a single consumer of the diff and no race.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ctxpilot.config import Config
from ctxpilot.core import CtxPilot


class Worker(QThread):
    """Run a blocking facade call off the GUI thread; emit result or error."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        try:
            self.done.emit(self._fn())
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class SettingsDialog(QDialog):
    def __init__(self, cp: CtxPilot, parent=None) -> None:
        super().__init__(parent)
        self.cp = cp
        self.setWindowTitle("Hy3 接入设置")
        self.setMinimumWidth(420)
        lay = QFormLayout(self)

        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("sk-... / 云端 API Key")
        lay.addRow("API Key:", self.key)

        self.base = QLineEdit()
        self.base.setPlaceholderText("http://127.0.0.1:8000/v1 或云端网关")
        lay.addRow("Base URL:", self.base)

        self.model = QLineEdit()
        self.model.setPlaceholderText("hy3")
        lay.addRow("Model:", self.model)

        self.reasoning = QComboBox()
        self.reasoning.addItems(["no_think", "low", "high"])
        lay.addRow("推理强度:", self.reasoning)

        # prefill from current config
        cfg = cp.config
        self.key.setText(cfg.hy3_api_key)
        self.base.setText(cfg.hy3_base_url)
        self.model.setText(cfg.hy3_model)
        idx = self.reasoning.findText(cfg.hy3_reasoning_effort)
        if idx >= 0:
            self.reasoning.setCurrentIndex(idx)

        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self._test)
        lay.addRow(self.test_btn)

        self.ok = QPushButton("保存")
        self.ok.clicked.connect(self._save)
        lay.addRow(self.ok)

    def _test(self) -> None:
        # Build a throwaway client with the typed-in values to test reachability.
        key = self.key.text().strip()
        base = self.base.text().strip() or Config.DEFAULT_BASE_URL
        if not key:
            QMessageBox.warning(self, "缺少 Key", "请先填写 API Key。")
            return
        from ctxpilot.hy3.client import Hy3Client

        client = Hy3Client(
            api_key=key,
            base_url=base,
            model=self.model.text().strip() or Config.DEFAULT_MODEL,
            reasoning_effort=self.reasoning.currentText(),
        )
        try:
            client.chat([{"role": "user", "content": "ping"}])
            QMessageBox.information(self, "连接成功", "Hy3 端点可达。")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "连接失败", f"{e}")

    def _save(self) -> None:
        self.cp.set_credentials(
            api_key=self.key.text().strip(),
            base_url=self.base.text().strip() or None,
            model=self.model.text().strip() or None,
            reasoning=self.reasoning.currentText(),
        )
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, cp: CtxPilot) -> None:
        super().__init__()
        self.cp = cp
        self.setWindowTitle("CtxPilot · 跨会话上下文连续性层")
        self.resize(1100, 720)

        # ---- central splitter: left projects / right monitor ----
        split = QSplitter()
        self.setCentralWidget(split)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel("已发现项目（含 agent 历史）"))
        self.proj_list = QListWidget()
        self.proj_list.currentTextChanged.connect(self._on_project_selected)
        lv.addWidget(self.proj_list)
        self.refresh_btn = QPushButton("刷新项目")
        self.refresh_btn.clicked.connect(self._refresh_projects)
        lv.addWidget(self.refresh_btn)

        right = QWidget()
        rv = QVBoxLayout(right)
        self.agent_strip = QLabel("可监控 agent: …")
        self.agent_strip.setStyleSheet("padding:4px;background:#eef;")
        rv.addWidget(self.agent_strip)

        self.monitor_btn = QPushButton("▶ 开始监控")
        self.monitor_btn.clicked.connect(self._toggle_monitor)
        rv.addWidget(self.monitor_btn)

        rv.addWidget(QLabel("实时监听流（新开 agent 会话）"))
        self.feed = QListWidget()
        rv.addWidget(self.feed)

        rv.addWidget(QLabel("HANDOFF / 简报 / 看门狗 输出"))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        rv.addWidget(self.output)

        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)

        # ---- toolbar actions ----
        tb = self.addToolBar("actions")
        self.agent_sel = QComboBox()
        tb.addWidget(QLabel("目标 agent:"))
        tb.addWidget(self.agent_sel)
        for label, slot in [
            ("生成 HANDOFF", self._snapshot),
            ("启动简报", self._brief),
            ("看门狗", self._watch),
            ("导出", self._export),
            ("导入", self._import),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            tb.addWidget(b)
        settings = QPushButton("⚙ 设置")
        settings.clicked.connect(self._open_settings)
        tb.addWidget(settings)

        self.statusBar().showMessage("就绪")

        # real-time monitor timer (3 s)
        self.monitoring = False
        self.timer = QTimer()
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self._poll)

        self._refresh_projects()
        self._refresh_agents()

    # -- data refresh -----------------------------------------------------
    def _refresh_projects(self) -> None:
        self.proj_list.clear()
        for p in self.cp.scan_projects():
            item = QListWidgetItem(f"{p.path}  ({len(p.sessions)} 会话)")
            item.setData(1000, p.path)
            self.proj_list.addItem(item)
        if self.proj_list.count() == 0:
            self.proj_list.addItem("(未发现项目)")

    def _refresh_agents(self) -> None:
        agents = self.cp.detected_agents()
        parts = [f"{a['name']}: {a['session_count']} 会话" for a in agents]
        self.agent_strip.setText("可监控 agent — " + ("  ·  ".join(parts) or "无"))
        self.agent_sel.clear()
        self.agent_sel.addItems([a["name"] for a in agents] or ["(无)"])

    def _on_project_selected(self, text: str) -> None:
        item = self.proj_list.currentItem()
        self._current_project = item.data(1000) if item else None

    def _selected_project(self) -> str | None:
        item = self.proj_list.currentItem()
        if not item:
            return None
        path = item.data(1000)
        return path

    # -- monitoring -------------------------------------------------------
    def _toggle_monitor(self) -> None:
        self.monitoring = not self.monitoring
        if self.monitoring:
            self.cp.monitor_start()
            self.timer.start()
            self.monitor_btn.setText("⏹ 停止监控")
            self.statusBar().showMessage("监控中…")
        else:
            self.timer.stop()
            self.cp.monitor_stop()
            self.monitor_btn.setText("▶ 开始监控")
            self.statusBar().showMessage("已停止监控")

    def _poll(self) -> None:
        for s in self.cp.monitor_poll():
            proj = s.project_path or "(未关联)"
            self.feed.insertItem(
                0, f"[{s.agent}] 新会话 {s.session_id} → {proj} ({s.message_count} 消息)"
            )
        self._refresh_agents()

    # -- actions (each offloads to a Worker thread) -----------------------
    def _run(self, fn, on_done, busy="处理中…") -> None:
        self.statusBar().showMessage(busy)
        w = Worker(fn)
        w.done.connect(lambda r: (on_done(r), self.statusBar().showMessage("完成")))
        w.failed.connect(lambda e: (self._err(e), self.statusBar().showMessage("失败")))
        w.start()

    def _snapshot(self) -> None:
        proj = self._selected_project()
        if not proj:
            return self._err("请先选择一个项目")
        self._run(
            lambda: self.cp.snapshot_svc.write(self.cp.snapshot(proj), proj),
            lambda p: self.output.setText(f"已写入: {p}\n\n{Path(p).read_text(encoding='utf-8', errors='ignore')[:4000]}"),
            "生成 HANDOFF.md…",
        )

    def _brief(self) -> None:
        proj = self._selected_project()
        if not proj:
            return self._err("请先选择一个项目")
        self._run(
            lambda: self.cp.brief(proj),
            lambda b: self.output.setText(b),
            "生成启动简报…",
        )

    def _watch(self) -> None:
        proj = self._selected_project()
        if not proj:
            return self._err("请先选择一个项目")
        self._run(
            lambda: self.cp.watch(proj).to_dict(),
            lambda d: self.output.setText(
                f"漂移级别: {d.get('level')}  has_red={d.get('has_red')}\n\n"
                + "\n".join(d.get("flags", []))
            ),
            "运行看门狗…",
        )

    def _export(self) -> None:
        proj = self._selected_project()
        if not proj:
            return self._err("请先选择一个项目")
        target = self.agent_sel.currentText()
        target = None if target in ("(无)",) else target
        self._run(
            lambda: self.cp.export(proj, target_agent=target).to_dict(),
            lambda d: self.output.setText(
                f"target: {d.get('target_agent')}\n\n--- prompt ---\n{d.get('prompt', '')[:4000]}"
            ),
            "导出交接…",
        )

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 HANDOFF 文件", "", "Markdown (*.md)")
        if not path:
            return
        target = self.agent_sel.currentText()
        target = None if target in ("(无)",) else target
        self._run(
            lambda: self.cp.import_handoff(path, target_agent=target),
            lambda p: self.output.setText(f"注入目标 agent [{target or '默认'}] 的首条 prompt:\n\n{p}"),
            "导入交接…",
        )

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.cp, self)
        if dlg.exec():
            self._refresh_agents()
            self.statusBar().showMessage("设置已保存")

    def _err(self, msg: str) -> None:
        QMessageBox.warning(self, "提示", msg)


def run_qt(config: Config | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    cp = CtxPilot(config or Config.from_store())
    win = MainWindow(cp)
    win.show()
    return app.exec()
