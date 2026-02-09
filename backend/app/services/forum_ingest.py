import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

THREAD_ID_RE = re.compile(r"/threads/[^/]*\.(\d+)/")
THREAD_ID_ALT_RE = re.compile(r"/threads/(\d+)/")
POST_ID_RE = re.compile(r"post-(\d+)")
POST_URL_RE = re.compile(r"/posts/(\d+)/")


@dataclass(frozen=True)
class ForumThreadItem:
    url: str
    title: str
    created_at: datetime
    external_id: str


@dataclass(frozen=True)
class ForumPost:
    external_id: str
    author: str | None
    created_at: datetime
    body: str
    score: int
    url: str | None


class ForumRateLimiter:
    def __init__(self, min_interval_seconds: float = 1.0):
        self.min_interval_seconds = min_interval_seconds
        self._last = 0.0

    def wait(self) -> None:
        now = time.time()
        delta = now - self._last
        if delta < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - delta)
        self._last = time.time()


def parse_rss_items(xml_text: str) -> list[ForumThreadItem]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    items: list[ForumThreadItem] = []
    for item in root.findall(".//item"):
        link = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        pub_date_raw = (item.findtext("pubDate") or "").strip()
        if not link or not pub_date_raw:
            continue
        created_at = _parse_datetime(pub_date_raw)
        external_id = extract_thread_id(link)
        if not external_id:
            continue
        items.append(ForumThreadItem(url=link, title=title, created_at=created_at, external_id=external_id))
    return items


def extract_thread_id(url: str) -> str | None:
    match = THREAD_ID_RE.search(url)
    if match:
        return match.group(1)
    match = THREAD_ID_ALT_RE.search(url)
    if match:
        return match.group(1)
    return None


def build_page_url(thread_url: str, page: int) -> str:
    if page <= 1:
        return thread_url
    if thread_url.endswith("/"):
        return f"{thread_url}page-{page}"
    return f"{thread_url}/page-{page}"


def _parse_datetime(value: str) -> datetime:
    dt = date_parser.parse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _extract_post_id(tag) -> str | None:
    for attr in ("id", "data-content"):
        if tag.has_attr(attr):
            match = POST_ID_RE.search(str(tag.get(attr, "")))
            if match:
                return match.group(1)
    for attr_value in tag.attrs.values():
        if isinstance(attr_value, str):
            match = POST_ID_RE.search(attr_value)
            if match:
                return match.group(1)
    link = tag.find("a", href=POST_URL_RE)
    if link and link.has_attr("href"):
        match = POST_URL_RE.search(link["href"])
        if match:
            return match.group(1)
    return None


def _extract_created_at(container) -> datetime | None:
    abbr = container.select_one("abbr.DateTime")
    if abbr and abbr.has_attr("data-time"):
        try:
            return datetime.fromtimestamp(int(abbr["data-time"]), tz=timezone.utc)
        except ValueError:
            pass

    time_tag = container.find("time")
    if time_tag:
        if time_tag.has_attr("data-time"):
            try:
                return datetime.fromtimestamp(int(time_tag["data-time"]), tz=timezone.utc)
            except ValueError:
                pass
        if time_tag.has_attr("datetime"):
            try:
                return _parse_datetime(time_tag["datetime"])
            except (ValueError, TypeError):
                pass
        text_value = time_tag.get_text(strip=True)
        if text_value:
            try:
                return _parse_datetime(text_value)
            except (ValueError, TypeError):
                pass
    return None


def _extract_author(container) -> str | None:
    author_tag = container.select_one(".message-name a, .message-name span, .username")
    if author_tag:
        text = author_tag.get_text(strip=True)
        if text:
            return text
    return None


def _extract_score(container) -> int:
    for attr in ("data-score", "data-reactionscore", "data-reaction-score"):
        node = container.find(attrs={attr: True})
        if node:
            try:
                return int(node.get(attr, 0))
            except ValueError:
                pass
    summary = container.select_one(".reactionsBar-summary")
    if summary:
        digits = re.findall(r"\d+", summary.get_text(" ", strip=True))
        if digits:
            return int(digits[0])
    return 0


def _extract_body(container) -> str:
    body = (
        container.select_one(".messageText")
        or container.select_one(".message-body .bbWrapper")
        or container.select_one(".message-body")
    )
    if body is None:
        return ""
    for selector in (".bbCodeBlock--quote", "blockquote", ".message-signature", ".message-lastEdit"):
        for node in body.select(selector):
            node.decompose()
    return body.get_text(" ", strip=True)


def parse_thread_html(html_text: str, thread_url: str) -> tuple[list[ForumPost], int]:
    soup = BeautifulSoup(html_text, "html.parser")
    posts: list[ForumPost] = []
    for message in soup.select("li.message, article.message"):
        post_id = _extract_post_id(message)
        created_at = _extract_created_at(message)
        if not post_id or not created_at:
            continue
        author = _extract_author(message)
        body = _extract_body(message)
        score = _extract_score(message)
        url = f"{thread_url}#post-{post_id}"
        posts.append(
            ForumPost(
                external_id=post_id,
                author=author,
                created_at=created_at,
                body=body,
                score=score,
                url=url,
            )
        )
    last_page = _extract_last_page(soup)
    return posts, last_page


def _extract_last_page(soup: BeautifulSoup) -> int:
    page_numbers = []
    for link in soup.select(".pageNav-page"):
        text = link.get_text(strip=True)
        if text.isdigit():
            page_numbers.append(int(text))
    if page_numbers:
        return max(page_numbers)
    page_nav = soup.select_one(".PageNav")
    if page_nav and page_nav.has_attr("data-last"):
        try:
            return int(page_nav["data-last"])
        except ValueError:
            pass
    nav = soup.find(attrs={"data-page-total": True})
    if nav:
        try:
            return int(nav.get("data-page-total", 1))
        except ValueError:
            pass
    return 1


def fetch_thread_posts(
    client: httpx.Client,
    limiter: ForumRateLimiter,
    thread: ForumThreadItem,
    cutoff: datetime,
    max_pages: int = 10,
) -> list[ForumPost]:
    limiter.wait()
    response = client.get(thread.url)
    response.raise_for_status()
    first_posts, last_page = parse_thread_html(response.text, thread.url)
    pages_to_fetch = list(range(last_page, max(1, last_page - max_pages + 1) - 1, -1))

    collected: list[ForumPost] = []
    if last_page == 1:
        for post in first_posts:
            if post.created_at >= cutoff:
                collected.append(post)
        return collected

    for page in pages_to_fetch:
        page_url = build_page_url(thread.url, page)
        limiter.wait()
        page_response = client.get(page_url)
        page_response.raise_for_status()
        posts, _ = parse_thread_html(page_response.text, thread.url)
        if not posts:
            continue
        newest = max(p.created_at for p in posts)
        if newest < cutoff:
            break
        for post in posts:
            if post.created_at >= cutoff:
                collected.append(post)
    return collected


def parse_feed_urls(value: str) -> list[str]:
    return [u.strip() for u in value.split(",") if u.strip()]


def forum_source_name(feed_url: str) -> str:
    parsed = urlparse(feed_url)
    parts = [p for p in parsed.path.split("/") if p]
    slug = parts[-1] if parts else "forum"
    if slug == "index.rss" and len(parts) >= 2:
        slug = parts[-2]
    return f"clutchfans-{slug}"


def iterate_recent_threads(
    client: httpx.Client,
    limiter: ForumRateLimiter,
    feed_url: str,
    cutoff: datetime,
) -> Iterable[ForumThreadItem]:
    limiter.wait()
    response = client.get(feed_url)
    response.raise_for_status()
    items = parse_rss_items(response.text)
    for item in items:
        if item.created_at >= cutoff:
            yield item
