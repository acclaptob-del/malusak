"""
اسکریپت واکشی اخبار برای «ملوسک».
این فایل توسط GitHub Actions هر ساعت اجرا می‌شود، فیدهای RSS گوگل‌نیوز را
می‌خواند و نتیجه را در data/news.json ذخیره می‌کند. سایت (index.html) فقط
همین فایل JSON را می‌خواند، بنابراین هیچ درخواست شبکه‌ای از مرورگر کاربر
به سرویس خارجی زده نمی‌شود و مشکل CORS به‌کلی حذف می‌شود.
"""

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.request import urlopen, Request

FEEDS = {
    # کوتیشن دور عبارت‌ها باعث می‌شود گوگل‌نیوز عبارت را عیناً جست‌وجو کند
    # (match دقیق‌تر)، به‌جای اینکه هر کلمه را جدا و با OR در نظر بگیرد.
    "iran": 'https://news.google.com/rss/search?q=%22%D8%A7%DB%8C%D8%B1%D8%A7%D9%86%22&hl=fa&gl=IR&ceid=IR:fa',
    "war": 'https://news.google.com/rss/search?q=%22%D8%B1%D9%88%D8%B3%DB%8C%D9%87%22+%22%D8%A7%D9%88%DA%A9%D8%B1%D8%A7%DB%8C%D9%86%22&hl=fa&gl=IR&ceid=IR:fa',
    "tech": 'https://news.google.com/rss/search?q=%22%D8%AA%DA%A9%D9%86%D9%88%D9%84%D9%88%DA%98%DB%8C%22&hl=fa&gl=IR&ceid=IR:fa',
    "energy": 'https://news.google.com/rss/search?q=%22%D8%A7%D9%86%D8%B1%DA%98%DB%8C%22&hl=fa&gl=IR&ceid=IR:fa',
}

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")


def strip_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", text).strip()


def fetch_feed(url: str, limit: int = 12):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MalusakBot/1.0)",
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.1",
        },
    )
    with urlopen(req, timeout=20) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    items = []
    for item in root.findall("./channel/item")[:limit]:
        title = strip_html(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        description = strip_html(item.findtext("description") or "")
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        items.append(
            {
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "source": source,
                "description": description[:220],
            }
        )
    return items


def main():
    existing = {}
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    data = {"generated_at": datetime.now(timezone.utc).isoformat()}
    for key, url in FEEDS.items():
        try:
            items = fetch_feed(url)
            if items:
                data[key] = items
            else:
                data[key] = existing.get(key, [])
        except Exception as exc:
            print(f"[warn] failed to fetch {key}: {exc}")
            data[key] = existing.get(key, [])

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("news.json updated")


if __name__ == "__main__":
    main()
