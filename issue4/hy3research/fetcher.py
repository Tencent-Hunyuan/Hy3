"""Content fetcher: URL → HTML → plain text extraction."""

from __future__ import annotations

import concurrent.futures
import re
import time
import requests


USER_AGENT = "Mozilla/5.0 (compatible; hy3-research/0.1; +https://github.com/Tencent-Hunyuan/Hy3)"
FETCH_TIMEOUT = 30  # seconds

# File extensions to skip (non-HTML content)
SKIP_EXTENSIONS = {".pdf", ".mp4", ".avi", ".mov", ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".mp3", ".wav"}


def extract_text(html: str) -> str:
    """Extract readable text from HTML using BeautifulSoup.

    Removes script, style, nav, footer elements. Returns cleaned text.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Minimal fallback: strip tags with regex
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Get text from body, or whole document
    body = soup.find("body")
    target = body if body else soup
    text = target.get_text(separator=" ", strip=True)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _should_skip(url: str) -> bool:
    """Check if URL should be skipped (PDF, video, etc.)."""
    from urllib.parse import urlsplit
    import os.path
    path = urlsplit(url).path
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in SKIP_EXTENSIONS


def fetch_single(url: str, timeout: int = FETCH_TIMEOUT) -> dict:
    """Fetch a single URL and extract text.

    Returns:
        {url, raw_text, fetch_status, fetch_time}
    """
    start = time.time()
    if _should_skip(url):
        return {
            "url": url,
            "raw_text": "",
            "fetch_status": "skipped",
            "fetch_time": 0,
        }

    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        resp.raise_for_status()
        # Only process HTML responses
        content_type = resp.headers.get("Content-Type", "")
        if "html" not in content_type.lower() and "text" not in content_type.lower():
            return {
                "url": url,
                "raw_text": "",
                "fetch_status": "skipped",
                "fetch_time": time.time() - start,
            }
        raw_text = extract_text(resp.text)
        elapsed = time.time() - start
        return {
            "url": url,
            "raw_text": raw_text,
            "fetch_status": "ok",
            "fetch_time": round(elapsed, 2),
        }
    except Exception:
        elapsed = time.time() - start
        return {
            "url": url,
            "raw_text": "",
            "fetch_status": "failed",
            "fetch_time": round(elapsed, 2),
        }


def fetch_all(sources: list[dict], mock: bool = False) -> list[dict]:
    """Fetch all source URLs in parallel and extract text.

    Args:
        sources: List of {url, title, index, ...} from searcher.
        mock: If True, return synthetic content.

    Returns:
        List of {url, title, raw_text, fetch_status, fetch_time, index}.
    """
    if mock:
        return _mock_fetch(sources)

    # Build lookup for titles
    title_map = {s["url"]: s.get("title", "") for s in sources}

    results = []
    urls = [s["url"] for s in sources]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_single, url): url for url in urls}
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            try:
                result = future.result()
            except Exception:
                result = {
                    "url": url,
                    "raw_text": "",
                    "fetch_status": "failed",
                    "fetch_time": 0,
                }
            result["title"] = title_map.get(url, "")
            result["index"] = next(
                (s["index"] for s in sources if s["url"] == url), 0
            )
            results.append(result)

    # Sort by index to maintain order
    results.sort(key=lambda r: r.get("index", 0))
    return results


def _mock_fetch(sources: list[dict]) -> list[dict]:
    """Generate synthetic fetched content for offline demo."""
    results = []
    for s in sources:
        idx = s.get("index", 0)
        title = s.get("title", "")
        results.append({
            "url": s["url"],
            "title": title,
            "raw_text": (
                f"这是关于「{s.get('query', '')}」的研究文章《{title}》的正文内容。\n\n"
                f"本文详细探讨了该主题的多个方面。首先，从背景来看，该领域近年来吸引了大量关注和研究投入。"
                f"多个权威机构和学者都发表了相关研究，推动了理论和实践的同步发展。\n\n"
                f"在技术层面，核心创新包括新的方法论和工具链的成熟。与传统方法相比，新技术在效率、准确性和"
                f"可扩展性方面都有显著提升。多项基准测试结果证实了这些优势。\n\n"
                f"从应用角度，已经有多个实际案例证明了其价值。在工业界，大型科技公司已经开始将其整合到"
                f"生产环境中；在学术界，相关论文数量在过去两年增长了200%。\n\n"
                f"然而，也存在一些挑战和限制。包括数据质量、计算资源需求、以及在一些边缘场景下的鲁棒性问题。"
                f"研究者正在积极应对这些挑战，预计在未来1-2年内会有突破性进展。\n\n"
                f"总的来说，该主题代表了当前技术发展的重要方向，值得持续关注和深入研究。"
            ),
            "fetch_status": "ok",
            "fetch_time": 0.0,
            "index": idx,
        })
    return results
