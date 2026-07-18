#!/usr/bin/env python3
"""为录制 demo 准备简易样例文档：复制到 data/uploads/ 并通过 API 入库。

用法（在 hy3-rag 根目录、且应用已启动的前提下执行）:
    .venv/Scripts/python.exe demo/prepare_demo_data.py

前置：先启动应用  ->  .venv\\Scripts\\python.exe run.py  (http://127.0.0.1:8766)
说明：应用只在「上传」时入库，不会自动扫描 data/uploads/ 里的文件，
      所以本脚本在复制文件后，会逐个调用 /api/documents/upload 真正入库。
样例文档位于 demo/sample/（Hy3模型简介.md、Hy3常见问题.md），简洁适合演示。
"""
from pathlib import Path
import shutil
import sys
import urllib.request

# 简易演示文档所在目录（随仓库提交，随时可取用）
SAMPLE_DIR = Path(__file__).resolve().parent / "sample"
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
API_BASE = "http://127.0.0.1:8766"


def _server_up() -> bool:
    try:
        with urllib.request.urlopen(f"{API_BASE}/api/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _upload_via_api(path: Path) -> bool:
    import json
    url = f"{API_BASE}/api/documents/upload"
    boundary = "----hy3ragboundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode("utf-8"))
            print(f"[入库]   {path.name} -> {resp.get('chunk_count')} chunks")
            return True
    except Exception as e:
        print(f"[失败]   {path.name}: {e}")
        return False


def main() -> None:
    if not SAMPLE_DIR.exists():
        print(f"[跳过] 样例目录不存在: {SAMPLE_DIR}")
        return
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 复制 demo/sample/ 下全部文档
    targets = []
    for src in sorted(SAMPLE_DIR.iterdir()):
        if not src.is_file():
            continue
        dst = UPLOADS_DIR / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"[复制]   {src.name} -> data/uploads/")
        targets.append(dst)

    if not targets:
        print("没有匹配的演示文档。")
        return

    # 2) 入库
    if not _server_up():
        print("\n[警告] 应用未运行或无法访问 http://127.0.0.1:8766。")
        print("        文件已复制到 data/uploads/，但还没入库。")
        print("        请先启动应用 (.venv\\Scripts\\python.exe run.py)，再运行本脚本。")
        sys.exit(0)

    print("\n开始通过 API 入库...")
    ok = 0
    for p in targets:
        if _upload_via_api(p):
            ok += 1
    print(f"\n完成：{ok}/{len(targets)} 个文档已入库。可以开始录制 demo 了。")


if __name__ == "__main__":
    main()
