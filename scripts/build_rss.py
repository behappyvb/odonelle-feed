"""Build Yandex «Свежее и актуальное» RSS feed for odonelle.ru blog.
Usage: python3 -I build_rss.py <pages_dir> <sitemap.xml> <out.xml>
"""
import sys, re, os, html
from datetime import datetime
from email.utils import format_datetime
from bs4 import BeautifulSoup

pages, sitemap, out = sys.argv[1:4]

# Articles about the product itself are advertising -> excluded from the feed
EXCLUDE = {"kavitatsiya"}
BRAND = re.compile(r"ОДОНЭЛЛ|ОДОНЕЛЛ|ODONELLE|САНМО|SANMO|₽|в каталоге|Выбрать курс|Купить|заказ", re.I)
SKIP_CLASSES = ("block-0-menu", "block-store", "block-html", "block-13-", "block-35-", "footer")

lastmod = dict(re.findall(r"<loc>https://odonelle\.ru/blog/([^/<]+)/</loc><lastmod>([^<]+)</lastmod>",
                          open(sitemap, encoding="utf-8").read()))

def clean(t):
    t = re.sub(r"[ \t ]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return t.strip()

items = []
for fn in sorted(os.listdir(pages)):
    if not fn.endswith(".html"):
        continue
    slug = fn[:-5]
    if slug in EXCLUDE:
        continue
    s = BeautifulSoup(open(os.path.join(pages, fn), encoding="utf-8"), "lxml")
    title = clean(s.find("h1").get_text(" ")) if s.find("h1") else ""
    if not title:
        title = s.find("meta", property="og:title")["content"]
    desc_tag = s.find("meta", attrs={"name": "description"})
    desc = desc_tag["content"].strip() if desc_tag else ""
    if BRAND.search(desc):
        desc = ""
    parts = []
    for b in s.select("div.block-wrapper"):
        cls = " ".join(b.get("class", []))
        if any(c in cls for c in SKIP_CLASSES):
            continue
        txt = b.get_text("\n", strip=True)
        if txt.startswith("ODONELLE") and "Читайте больше" in txt:
            break  # end of article body
        if BRAND.search(txt):
            continue  # product insert / CTA / disclaimer
        parts.append(clean(txt))
    body = "\n\n".join(p for p in parts if p)
    # drop the H1 repeated at the start of the body
    body = body.replace(title, "", 1).strip() if body.find(title) < 200 else body
    dt = datetime.fromisoformat(lastmod[slug])
    items.append(dict(slug=slug, title=title.rstrip("."), desc=desc, body=body, dt=dt))

items.sort(key=lambda i: i["dt"], reverse=True)
e = lambda x: html.escape(x, quote=True)
xml = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<rss xmlns:yandex="http://news.yandex.ru" xmlns:media="http://search.yahoo.com/mrss/" version="2.0">',
       '<channel>',
       '<title>ОДОНЭЛЛЬ: блог о здоровье и долголетии</title>',
       '<link>https://odonelle.ru</link>',
       '<description>Статьи о детоксе, здоровье кишечника и активном долголетии после 45 лет</description>',
       '<language>ru</language>']
for i in items:
    xml += ['<item>',
            f'<title>{e(i["title"])}</title>',
            f'<link>https://odonelle.ru/blog/{i["slug"]}/</link>',
            f'<pubDate>{format_datetime(i["dt"])}</pubDate>',
            f'<description>{e(i["desc"])}</description>',
            '<yandex:genre>article</yandex:genre>',
            f'<yandex:full-text>{e(i["body"])}</yandex:full-text>',
            '</item>']
xml += ['</channel>', '</rss>']
open(out, "w", encoding="utf-8").write("\n".join(xml) + "\n")
for i in items:
    print(i["dt"].date(), len(i["title"]), len(i["body"]), i["slug"], "|", i["title"])
