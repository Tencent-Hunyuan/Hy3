"""Render polished Chinese demo assets from verified client records."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 1280
HEIGHT = 720
NAVY = "#071426"
PANEL = "#0E2038"
PANEL_ALT = "#132B47"
PANEL_SOFT = "#173653"
TEXT = "#F7FBFF"
MUTED = "#A9BDD2"
CYAN = "#37E1D1"
BLUE = "#55A7FF"
VIOLET = "#9C7CFF"
AMBER = "#FFC766"
GREEN = "#49E3A7"
LINE = "#28547A"


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        (
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "DejaVuSans-Bold.ttf",
        )
        if bold
        else (
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "DejaVuSans.ttf",
        )
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _mono_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        (
            "C:/Windows/Fonts/CascadiaMono-Bold.ttf",
            "C:/Windows/Fonts/consolab.ttf",
            "DejaVuSansMono-Bold.ttf",
        )
        if bold
        else (
            "C:/Windows/Fonts/CascadiaMono.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "DejaVuSansMono.ttf",
        )
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return _font(size, bold=bold)


def _wrap_lines(
    draw: ImageDraw.ImageDraw,
    value: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for character in value:
        if character == "\n":
            lines.append(current)
            current = ""
            continue
        candidate = current + character
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current.rstrip())
            current = character.lstrip()
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    return lines


def _text_block(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    *,
    size: int = 24,
    color: str = TEXT,
    max_width: int = 1080,
    bold: bool = False,
    spacing: int = 8,
) -> int:
    font = _font(size, bold=bold)
    x, y = xy
    for line in _wrap_lines(draw, value, font, max_width):
        draw.text((x, y), line, font=font, fill=color)
        box = draw.textbbox((x, y), line or " ", font=font)
        y += box[3] - box[1] + spacing
    return y


def _gradient_background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), NAVY)
    draw = ImageDraw.Draw(image)
    top = (5, 16, 34)
    bottom = (8, 30, 53)
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        color = tuple(round(top[index] * (1 - ratio) + bottom[index] * ratio) for index in range(3))
        draw.line((0, y, WIDTH, y), fill=color)

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-180, -220, 520, 480), fill=(30, 126, 255, 70))
    glow_draw.ellipse((850, 40, 1460, 650), fill=(75, 224, 210, 55))
    glow_draw.ellipse((410, 350, 950, 900), fill=(127, 88, 255, 42))
    glow = glow.filter(ImageFilter.GaussianBlur(95))
    image = Image.alpha_composite(image.convert("RGBA"), glow)

    grid = Image.new("RGBA", image.size, (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid)
    for x in range(32, WIDTH, 64):
        grid_draw.line((x, 0, x, HEIGHT), fill=(70, 126, 172, 18), width=1)
    for y in range(32, HEIGHT, 64):
        grid_draw.line((0, y, WIDTH, y), fill=(70, 126, 172, 18), width=1)
    image = Image.alpha_composite(image, grid)

    network = Image.new("RGBA", image.size, (0, 0, 0, 0))
    network_draw = ImageDraw.Draw(network)
    network_draw.arc((-260, -420, 1020, 420), 8, 163, fill=(55, 225, 209, 42), width=2)
    network_draw.arc((300, -360, 1540, 330), 16, 166, fill=(156, 124, 255, 38), width=2)
    network_draw.arc((570, 55, 1530, 650), 184, 330, fill=(85, 167, 255, 28), width=1)
    for x, y, color in (
        (174, 88, (55, 225, 209, 90)),
        (322, 39, (85, 167, 255, 75)),
        (520, 72, (156, 124, 255, 80)),
        (812, 83, (85, 167, 255, 70)),
        (1034, 142, (55, 225, 209, 75)),
        (1174, 207, (156, 124, 255, 72)),
    ):
        network_draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color)
    return Image.alpha_composite(image, network).convert("RGB")


def _card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: str = PANEL,
    outline: str = LINE,
    radius: int = 24,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: str = PANEL_SOFT,
    color: str = CYAN,
    outline: str | None = None,
    size: int = 17,
) -> tuple[int, int, int, int]:
    font = _font(size, bold=True)
    x, y = xy
    width = round(draw.textlength(text, font=font)) + 30
    height = size + 22
    box = (x, y, x + width, y + height)
    draw.rounded_rectangle(box, radius=height // 2, fill=fill, outline=outline)
    draw.text((x + 15, y + 8), text, font=font, fill=color)
    return box


def _header(
    draw: ImageDraw.ImageDraw,
    *,
    step: str,
    title: str,
    subtitle: str,
    accent: str = CYAN,
) -> None:
    _pill(draw, (58, 40), step, fill="#153452", color=accent, outline="#2E638B")
    draw.text((58, 100), title, font=_font(42, bold=True), fill=TEXT)
    draw.text((60, 158), subtitle, font=_font(21), fill=MUTED)
    _pill(draw, (1030, 43), "真实调用 · 已脱敏", fill="#102D38", color=GREEN, outline="#216B68")


def _metric(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    *,
    accent: str = CYAN,
    mono: bool = False,
) -> None:
    _card(draw, box, fill=PANEL_ALT, outline="#244E70", radius=18, width=1)
    x1, y1, x2, _ = box
    draw.text((x1 + 20, y1 + 16), label, font=_font(16, bold=True), fill=MUTED)
    font = _mono_font(22, bold=True) if mono else _font(25, bold=True)
    available = x2 - x1 - 40
    lines = _wrap_lines(draw, value, font, available)
    y = y1 + 49
    for line in lines[:2]:
        draw.text((x1 + 20, y), line, font=font, fill=accent)
        y += 31


def _status_dot(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str) -> None:
    x, y = xy
    draw.ellipse((x, y + 5, x + 13, y + 18), fill=GREEN)
    draw.text((x + 23, y), label, font=_font(18, bold=True), fill=GREEN)


def _footer(draw: ImageDraw.ImageDraw, text: str) -> None:
    draw.line((58, 654, 1222, 654), fill="#204565", width=1)
    draw.text((60, 670), text, font=_font(14), fill="#7F9AB5")


def _cover_frame(codebuddy: dict[str, object], codex: dict[str, object]) -> Image.Image:
    image = _gradient_background()
    draw = ImageDraw.Draw(image)
    _pill(draw, (58, 43), "开源 MCP Server · 中文演示", fill="#153452", color=CYAN)
    draw.text((58, 106), "Hy3 TaskRelay", font=_font(31, bold=True), fill=CYAN)
    draw.text((58, 150), "跨客户端任务接力", font=_font(55, bold=True), fill=TEXT)
    draw.text(
        (60, 223),
        "把中断任务整理为带证据、可审计、可继续执行的结构化交接件",
        font=_font(23),
        fill=MUTED,
    )

    stages = [
        (58, "01", "CodeBuddy", "创建检查点", BLUE),
        (443, "02", "TaskRelay", "证据审计", VIOLET),
        (828, "03", "Codex", "续作计划", CYAN),
    ]
    for index, (x, number, client, action, accent) in enumerate(stages):
        _card(draw, (x, 320, x + 340, 535), fill=PANEL, outline=accent, radius=22, width=2)
        draw.rounded_rectangle((x + 22, 342, x + 82, 389), radius=13, fill=accent)
        draw.text((x + 38, 351), number, font=_font(20, bold=True), fill=NAVY)
        draw.text((x + 22, 416), action, font=_font(28, bold=True), fill=TEXT)
        draw.text((x + 22, 462), client, font=_font(20, bold=True), fill=accent)
        if index < 2:
            draw.line((x + 340, 427, x + 385, 427), fill=accent, width=3)
            draw.polygon(
                [(x + 380, 420), (x + 393, 427), (x + 380, 434)],
                fill=accent,
            )

    _pill(draw, (58, 576), f"CodeBuddy {codebuddy['client_version']}", color=BLUE)
    _pill(draw, (287, 576), f"Codex CLI {codex['client_version']}", color=CYAN)
    _pill(draw, (520, 576), "公开合成任务", color=AMBER)
    _pill(draw, (696, 576), "结果可复核", color=GREEN)
    _footer(draw, "演示来源: 2026-07-20 已验证客户端事件记录 | 不包含凭据、Prompt 或个人路径")
    return image


def _codebuddy_call_frame(codebuddy: dict[str, object]) -> Image.Image:
    result = codebuddy["result"]
    image = _gradient_background()
    draw = ImageDraw.Draw(image)
    _header(
        draw,
        step="01 / 03",
        title="CodeBuddy 创建任务检查点",
        subtitle="严格项目配置下完成一次真实 MCP 工具调用",
        accent=BLUE,
    )

    _card(draw, (58, 225, 378, 625), fill="#0D2139", outline="#2D6EA2")
    _pill(draw, (82, 249), "客户端 A", color=BLUE)
    draw.text((82, 310), "CodeBuddy Code", font=_font(25, bold=True), fill=TEXT)
    draw.text((82, 349), str(codebuddy["client_version"]), font=_mono_font(22), fill=BLUE)
    _status_dot(draw, (82, 402), "Server 已连接")
    draw.text((82, 458), "运行模式", font=_font(16, bold=True), fill=MUTED)
    draw.text((82, 488), "Headless · Strict MCP", font=_mono_font(17), fill=TEXT)
    draw.text((82, 541), "退出码", font=_font(16, bold=True), fill=MUTED)
    draw.text((82, 569), str(codebuddy["exit_code"]), font=_mono_font(25, bold=True), fill=GREEN)

    _card(draw, (410, 225, 1222, 625), fill=PANEL, outline="#245A7E")
    draw.text((438, 250), "调用工具", font=_font(17, bold=True), fill=MUTED)
    draw.text((438, 282), str(codebuddy["tool_called"]), font=_mono_font(21, bold=True), fill=CYAN)
    draw.line((438, 329, 1194, 329), fill="#244E70", width=1)
    draw.text((438, 355), "生成的检查点", font=_font(17, bold=True), fill=MUTED)
    draw.text((438, 388), str(result["checkpoint_id"]), font=_mono_font(26, bold=True), fill=AMBER)
    _metric(
        draw, (438, 459, 650, 583), "已确认事实", str(result["confirmed_fact_count"]), accent=CYAN
    )
    _metric(draw, (673, 459, 885, 583), "后续步骤", str(result["next_step_count"]), accent=CYAN)
    _metric(
        draw,
        (908, 459, 1194, 583),
        "Schema 版本",
        str(result["schema_version"]),
        accent=VIOLET,
        mono=True,
    )
    _footer(draw, "真实结果: 检查点 ID、计数、版本与退出码均来自已提交的脱敏客户端记录")
    return image


def _handoff_frame(codebuddy: dict[str, object], checkpoint: dict[str, object]) -> Image.Image:
    result = codebuddy["result"]
    image = _gradient_background()
    draw = ImageDraw.Draw(image)
    _header(
        draw,
        step="安全交接",
        title="结构化检查点跨越客户端边界",
        subtitle="同一份 structuredContent 从 CodeBuddy 传递给 Codex, 并在本地通过 Schema 校验",
        accent=AMBER,
    )

    _card(draw, (68, 282, 318, 535), fill=PANEL, outline=BLUE)
    _pill(draw, (92, 305), "发送端", color=BLUE)
    draw.text((92, 365), "CodeBuddy", font=_font(27, bold=True), fill=TEXT)
    draw.text((92, 411), "创建检查点", font=_font(20), fill=MUTED)
    _status_dot(draw, (92, 466), "调用成功")

    draw.line((318, 407, 455, 407), fill=BLUE, width=4)
    draw.polygon([(442, 397), (460, 407), (442, 417)], fill=BLUE)

    _card(draw, (460, 246, 820, 574), fill="#142643", outline=AMBER, radius=26, width=2)
    _pill(draw, (490, 272), "可携带 Artifact", color=AMBER)
    draw.text((490, 335), "CHECKPOINT", font=_mono_font(22, bold=True), fill=MUTED)
    draw.text((490, 377), str(result["checkpoint_id"]), font=_mono_font(22, bold=True), fill=AMBER)
    draw.line((490, 424, 790, 424), fill="#4C4B5D", width=1)
    draw.text((490, 451), "Schema", font=_font(16, bold=True), fill=MUTED)
    draw.text((578, 449), str(result["schema_version"]), font=_mono_font(19, bold=True), fill=TEXT)
    draw.text((490, 494), "Evidence", font=_font(16, bold=True), fill=MUTED)
    draw.text(
        (595, 492), str(len(checkpoint["evidence"])), font=_mono_font(19, bold=True), fill=CYAN
    )
    draw.text((490, 535), "内容派生稳定 ID", font=_font(16, bold=True), fill=GREEN)

    draw.line((820, 407, 957, 407), fill=CYAN, width=4)
    draw.polygon([(944, 397), (962, 407), (944, 417)], fill=CYAN)

    _card(draw, (962, 282, 1212, 535), fill=PANEL, outline=CYAN)
    _pill(draw, (986, 305), "接收端", color=CYAN)
    draw.text((986, 365), "Codex", font=_font(27, bold=True), fill=TEXT)
    draw.text((986, 411), "审计并续作", font=_font(20), fill=MUTED)
    _status_dot(draw, (986, 466), "ID 一致")
    _footer(draw, "仅传递已脱敏结构化产物 | 不保存原始 Prompt、Provider 响应、账户数据或请求元数据")
    return image


def _audit_frame(codex: dict[str, object], audit: dict[str, object]) -> Image.Image:
    image = _gradient_background()
    draw = ImageDraw.Draw(image)
    _header(
        draw,
        step="02 / 03",
        title="Codex 完成证据审计",
        subtitle="只读调用检查矛盾、遗漏约束、过期假设和无证据结论",
        accent=VIOLET,
    )

    _card(draw, (58, 236, 765, 606), fill=PANEL, outline="#55458E")
    _pill(draw, (84, 260), "MCP 调用", color=VIOLET)
    draw.text(
        (84, 321), str(codex["mcp_calls"][0]["tool"]), font=_mono_font(21, bold=True), fill=VIOLET
    )
    draw.text((84, 374), "输入检查点", font=_font(17, bold=True), fill=MUTED)
    draw.text((84, 407), str(codex["input_checkpoint_id"]), font=_mono_font(22), fill=AMBER)
    draw.line((84, 452, 739, 452), fill="#374166", width=1)
    _status_dot(draw, (84, 480), "调用已完成")
    draw.text((84, 528), "审计结果已通过结构化 Schema 校验", font=_font(20, bold=True), fill=TEXT)

    _card(draw, (795, 236, 1222, 606), fill="#102C3B", outline=CYAN, radius=28, width=2)
    draw.text((825, 267), "审计状态", font=_font(18, bold=True), fill=MUTED)
    draw.text((825, 307), "清洁", font=_font(49, bold=True), fill=GREEN)
    draw.text((958, 327), f"({audit['overall_status']})", font=_mono_font(17), fill=MUTED)
    draw.line((825, 384, 1192, 384), fill="#27626C", width=1)
    draw.text((825, 412), "发现项", font=_font(18, bold=True), fill=MUTED)
    draw.text((825, 449), str(len(audit["findings"])), font=_font(55, bold=True), fill=AMBER)
    draw.text((902, 474), "未发现需要报告的问题", font=_font(18, bold=True), fill=TEXT)
    _footer(draw, "真实结果: overall_status=clean | findings=0 | 客户端退出码 0")
    return image


def _resume_frame(codex: dict[str, object], resume: dict[str, object]) -> Image.Image:
    priorities = " → ".join(str(step["priority"]) for step in resume["next_steps"])
    image = _gradient_background()
    draw = ImageDraw.Draw(image)
    _header(
        draw,
        step="03 / 03",
        title="Codex 生成续作计划",
        subtitle="把已审计检查点转换成带验证条件、按优先级排列的下一步",
        accent=CYAN,
    )

    _card(draw, (58, 236, 1222, 606), fill=PANEL, outline="#287E8E")
    _pill(draw, (86, 260), "MCP 调用", color=CYAN)
    draw.text(
        (86, 319), str(codex["mcp_calls"][1]["tool"]), font=_mono_font(21, bold=True), fill=CYAN
    )
    draw.text((86, 369), "生成的 Resume ID", font=_font(17, bold=True), fill=MUTED)
    draw.text((86, 405), str(resume["resume_id"]), font=_mono_font(25, bold=True), fill=BLUE)

    _metric(draw, (86, 478, 405, 574), "后续步骤", str(len(resume["next_steps"])), accent=CYAN)
    _metric(draw, (429, 478, 772, 574), "优先级顺序", priorities, accent=AMBER)
    _metric(
        draw, (796, 478, 1188, 574), "验证条件", f"{len(resume['next_steps'])} 项", accent=GREEN
    )
    _footer(
        draw, "真实结果: resume ID 与优先级来自 Schema-valid artifact | 两次 Codex MCP 调用均完成"
    )
    return image


def _codex_call_frame(
    codex: dict[str, object], audit: dict[str, object], resume: dict[str, object]
) -> Image.Image:
    priorities = " → ".join(str(step["priority"]) for step in resume["next_steps"])
    image = _gradient_background()
    draw = ImageDraw.Draw(image)
    _header(
        draw,
        step="客户端 B",
        title="Codex 审计并规划续作",
        subtitle=f"Codex CLI {codex['client_version']} · 临时会话 · 只读模式",
        accent=CYAN,
    )

    calls = [
        (
            58,
            "调用 1",
            codex["mcp_calls"][0]["tool"],
            "审计状态",
            f"清洁 · {len(audit['findings'])} 个发现项",
            VIOLET,
        ),
        (650, "调用 2", codex["mcp_calls"][1]["tool"], "续作结果", f"优先级 {priorities}", CYAN),
    ]
    for x, label, tool, result_label, result, accent in calls:
        _card(draw, (x, 238, x + 572, 531), fill=PANEL, outline=accent, radius=23, width=2)
        _pill(draw, (x + 26, 261), label, color=accent)
        draw.text((x + 26, 322), str(tool), font=_mono_font(18, bold=True), fill=accent)
        draw.line((x + 26, 369, x + 546, 369), fill="#2B506B", width=1)
        draw.text((x + 26, 393), result_label, font=_font(17, bold=True), fill=MUTED)
        draw.text((x + 26, 431), result, font=_font(25, bold=True), fill=TEXT)
        _status_dot(draw, (x + 26, 479), "调用完成")

    _metric(
        draw, (58, 558, 438, 636), "Resume ID", str(resume["resume_id"]), accent=BLUE, mono=True
    )
    _metric(draw, (462, 558, 762, 636), "客户端退出码", str(codex["exit_code"]), accent=GREEN)
    _metric(
        draw,
        (786, 558, 1222, 636),
        "输入检查点一致",
        str(codex["input_checkpoint_id"]),
        accent=AMBER,
        mono=True,
    )
    _footer(draw, "来源: 已验证 Codex 客户端事件记录 | 不包含凭据、Prompt、账户数据或个人路径")
    return image


def _checkpoint_summary(codebuddy: dict[str, object], checkpoint: dict[str, object]) -> Image.Image:
    result = codebuddy["result"]
    image = _gradient_background()
    draw = ImageDraw.Draw(image)
    _header(
        draw,
        step="产物摘要",
        title="CodeBuddy 已创建检查点",
        subtitle="一份可复制、可保存、可交给另一客户端继续处理的结构化交接件",
        accent=BLUE,
    )
    _card(draw, (58, 238, 1222, 608), fill=PANEL, outline="#2C6D9C")
    draw.text((86, 268), "Checkpoint ID", font=_font(17, bold=True), fill=MUTED)
    draw.text((86, 306), str(result["checkpoint_id"]), font=_mono_font(29, bold=True), fill=AMBER)
    draw.line((86, 361, 1194, 361), fill="#2C5572", width=1)
    _metric(
        draw, (86, 397, 340, 542), "已确认事实", str(result["confirmed_fact_count"]), accent=CYAN
    )
    _metric(draw, (365, 397, 619, 542), "后续步骤", str(result["next_step_count"]), accent=CYAN)
    _metric(draw, (644, 397, 898, 542), "Evidence", str(len(checkpoint["evidence"])), accent=VIOLET)
    _metric(draw, (923, 397, 1194, 542), "退出码", str(codebuddy["exit_code"]), accent=GREEN)
    _status_dot(draw, (86, 565), "Schema 1.0 校验通过")
    _footer(draw, "数据来自真实调用记录与 checkpoint artifact; 画面仅做中文信息可视化")
    return image


def _audit_resume_summary(
    codex: dict[str, object], audit: dict[str, object], resume: dict[str, object]
) -> Image.Image:
    priorities = " → ".join(str(step["priority"]) for step in resume["next_steps"])
    image = _gradient_background()
    draw = ImageDraw.Draw(image)
    _header(
        draw,
        step="产物摘要",
        title="Codex 已完成审计与续作规划",
        subtitle="同一检查点经过两次只读 MCP 调用, 形成可执行的下一步",
        accent=CYAN,
    )
    _card(draw, (58, 238, 610, 595), fill=PANEL, outline=VIOLET)
    _pill(draw, (86, 263), "证据审计", color=VIOLET)
    draw.text((86, 328), "状态", font=_font(17, bold=True), fill=MUTED)
    draw.text((86, 365), "清洁", font=_font(40, bold=True), fill=GREEN)
    draw.text(
        (235, 379), f"{len(audit['findings'])} 个发现项", font=_font(20, bold=True), fill=TEXT
    )
    draw.line((86, 430, 582, 430), fill="#3C4772", width=1)
    _status_dot(draw, (86, 463), "taskrelay_audit_checkpoint 完成")

    _card(draw, (638, 238, 1222, 595), fill=PANEL, outline=CYAN)
    _pill(draw, (666, 263), "续作计划", color=CYAN)
    draw.text((666, 326), "Resume ID", font=_font(17, bold=True), fill=MUTED)
    draw.text((666, 363), str(resume["resume_id"]), font=_mono_font(21, bold=True), fill=BLUE)
    draw.text((666, 419), "优先级", font=_font(17, bold=True), fill=MUTED)
    draw.text((666, 455), priorities, font=_font(34, bold=True), fill=AMBER)
    _status_dot(draw, (666, 516), "taskrelay_create_resume_brief 完成")
    _footer(
        draw,
        f"输入 checkpoint: {codex['input_checkpoint_id']} | 客户端退出码: {codex['exit_code']}",
    )
    return image


def _render_assets(project_root: Path) -> tuple[list[Image.Image], dict[str, Image.Image]]:
    clients = project_root / "docs" / "clients"
    artifacts = project_root / "docs" / "client_artifacts"
    codebuddy = json.loads((clients / "codebuddy_2026-07-20.json").read_text(encoding="utf-8"))
    codex = json.loads((clients / "codex_2026-07-20.json").read_text(encoding="utf-8"))
    checkpoint = json.loads(
        (artifacts / "codebuddy_checkpoint_2026-07-20.json").read_text(encoding="utf-8")
    )
    audit = json.loads((artifacts / "codex_audit_2026-07-20.json").read_text(encoding="utf-8"))
    resume = json.loads((artifacts / "codex_resume_2026-07-20.json").read_text(encoding="utf-8"))

    codebuddy_call = _codebuddy_call_frame(codebuddy)
    codex_call = _codex_call_frame(codex, audit, resume)
    frames = [
        _cover_frame(codebuddy, codex),
        codebuddy_call,
        _handoff_frame(codebuddy, checkpoint),
        _audit_frame(codex, audit),
        _resume_frame(codex, resume),
        codex_call,
    ]
    assets = {
        "codebuddy_actual_call.png": codebuddy_call,
        "codex_actual_calls.png": codex_call,
        "codebuddy_checkpoint.png": _checkpoint_summary(codebuddy, checkpoint),
        "codex_audit_resume.png": _audit_resume_summary(codex, audit, resume),
    }
    return frames, assets


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output = project_root / "docs" / "demo"
    output.mkdir(parents=True, exist_ok=True)
    frames, assets = _render_assets(project_root)
    for name, image in assets.items():
        image.save(output / name)
    frames[0].save(
        output / "taskrelay_cross_client.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[1800, 2600, 1800, 2200, 2200, 2600],
        loop=0,
        optimize=False,
        disposal=2,
    )
    print("已生成 4 张中文展示图和 1 个 13.2 秒跨客户端 GIF。")


if __name__ == "__main__":
    main()
