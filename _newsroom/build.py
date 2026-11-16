#!/usr/bin/env python3
"""Mednomics 데일리 뉴스 생성기.

_newsroom/data/YYYY-MM-DD.json 을 읽어 다음을 만든다.
  news/YYYY-MM-DD.html   일자별 브리핑
  news/index.html        뉴스 첫 화면(최신 브리핑 + 지난 브리핑)
  news/feed.xml          뉴스 RSS
  assets/og/news-YYYY-MM-DD.png  공유 이미지(없을 때만, Pillow 필요)
그리고 index.html(홈) 뉴스 블록, sitemap.xml, search-index.json 을 갱신한다.

사용:  python3 _newsroom/build.py      (저장소 루트에서)
_newsroom 폴더는 밑줄로 시작해 GitHub Pages에 공개되지 않는다.
"""
import datetime as dt
import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://mednomics.co.kr"
WD = "월화수목금토일"
CATS = {"정책": "c-pol", "규제": "c-pol", "개원·의원": "c-clinic", "병원": "c-clinic",
        "제약·바이오": "c-bio", "의료기기·AI": "c-tech", "학술": "c-sci", "학회": "c-sci",
        "의사와 돈": "c-money", "사건·사고": "c-case"}
E = html.escape


def J(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def kdate(d, short=False):
    x = dt.date.fromisoformat(d)
    if short:
        return f"{x.month}월 {x.day}일({WD[x.weekday()]})"
    return f"{x.year}. {x.month}. {x.day} ({WD[x.weekday()]})"


def load():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "_newsroom/data/*.json")), reverse=True):
        b = json.load(open(p, encoding="utf-8"))
        b.setdefault("watch", [])
        for i, it in enumerate(b["items"], 1):
            it["n"] = i
            it.setdefault("take", "")
        out.append(b)
    return out


def head(title, desc, url, og, ld, pre="../"):
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="author" content="닥터조단">
<link rel="canonical" href="{url}">
<link rel="alternate" type="application/rss+xml" title="Mednomics 의료 뉴스" href="{SITE}/news/feed.xml">
<meta property="og:site_name" content="Mednomics">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="article">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{og}">
<meta name="theme-color" content="#07090c">
<link rel="icon" href="{pre}assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{pre}assets/logo-512.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{pre}style.css">
{"".join(f'<script type="application/ld+json">{J(x)}</script>' for x in ld)}
</head>
<body>

<div class="progress" id="progress"></div>
<a class="skip" href="#main">본문으로 건너뛰기</a>
<header class="bar"><div class="in">
  <a class="logo" href="{pre}" aria-label="Mednomics 홈"><i></i><b>MEDNOMICS</b></a>
  <nav class="menu" aria-label="주 메뉴">
    <a href="{pre}news/" aria-current="page">뉴스</a>
    <a href="{pre}series/">연재</a>
    <a href="{pre}board.html">이슈 보드</a>
    <a href="{pre}trackers/">트래커</a>
    <a href="{pre}glossary.html">용어사전</a>
    <a href="{pre}about.html">필자</a>
    <button class="sbtn" type="button" id="open-search" aria-label="검색">검색</button>
  </nav>
</div></header>
<div class="search" id="search" hidden role="dialog" aria-label="사이트 검색">
  <div class="sbox"><input id="q" type="search" placeholder="간납사, 위고비, 특사경 ..." autocomplete="off"><button type="button" id="close-search" aria-label="닫기">닫기</button>
  <ul id="results"></ul></div>
</div>
<main id="main">
'''


def foot(pre="../"):
    return f'''<section class="sec"><div class="sub-box" id="subscribe">
    <p>매일 의료 뉴스는 뉴스 RSS로, 연재 새 글은 네이버 블로그로 먼저 알려 드립니다. 이메일 뉴스레터는 준비 중입니다.</p>
    <div class="btnrow"><a class="btn" href="https://blog.naver.com/jordanam">네이버 블로그 이웃 추가</a><a class="btn" href="/news/feed.xml">뉴스 RSS</a></div>
    <small>EMAIL NEWSLETTER · COMING SOON</small>
  </div></section>
</main>
<footer><div class="in">
  <span class="fl">MEDNOMICS · 두 개의 차트</span>
  <nav class="fnav"><a href="{pre}start.html">처음 오셨다면</a><a href="{pre}news/">뉴스</a><a href="{pre}series/">연재</a><a href="{pre}board.html">이슈 보드</a><a href="{pre}trackers/">트래커</a><a href="{pre}glossary.html">용어사전</a><a href="{pre}about.html">필자 소개</a><a href="{pre}rss.xml">RSS</a></nav>
  <p>Mednomics의 글은 공개된 자료를 바탕으로 한 산업 해설이며, 특정 종목의 매수나 매도를 권하지 않습니다. 투자 판단과 그 결과의 책임은 투자자 본인에게 있습니다. 개별 환자의 진료를 대신하지도 않습니다.</p>
  <p>이 사이트의 글과 그림의 저작권은 닥터조단에게 있으며, 무단 복제와 재배포를 금합니다. 인용할 때는 출처(mednomics.co.kr)를 밝혀 주세요. 뉴스 요약에 인용한 각 기사의 저작권은 해당 언론사에 있습니다.</p>
</div></footer>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<div class="print-block">인쇄할 수 없습니다.</div>
<script src="{pre}protect.js"></script>
<script src="{pre}assets/search.js" defer></script>
<script src="{pre}assets/news.js" defer></script>
</body>
</html>
'''


def sharebar(label="이 브리핑 공유"):
    return f'''<div class="sharebar" aria-label="{label}">
  <button type="button" class="sh main" data-share="native">공유하기</button>
  <button type="button" class="sh" data-share="text">카톡·문자용 복사</button>
  <button type="button" class="sh" data-share="link">링크 복사</button>
  <button type="button" class="sh ic" data-share="naver" aria-label="네이버 블로그로 공유">N 블로그</button>
  <button type="button" class="sh ic" data-share="band" aria-label="밴드로 공유">밴드</button>
  <button type="button" class="sh ic" data-share="facebook" aria-label="페이스북으로 공유">f</button>
  <button type="button" class="sh ic" data-share="x" aria-label="X로 공유">X</button>
</div>'''


def srcline(it):
    return " · ".join(f'<a href="{E(s["url"])}" target="_blank" rel="noopener nofollow">{E(s["name"])}</a>' for s in it["sources"])


def item_html(it):
    cls = CATS.get(it["cat"], "c-etc")
    take = f'<p class="take"><b>닥터조단</b>{E(it["take"])}</p>' if it["take"] else ""
    return f'''<li class="brief-item" id="n{it["n"]}">
  <div class="bi-top"><span class="num">{it["n"]:02d}</span><span class="cat {cls}">{E(it["cat"])}</span></div>
  <h3>{E(it["title"])}</h3>
  <p class="sum">{E(it["summary"])}</p>
  {take}
  <div class="bi-foot"><span class="src">원문 {srcline(it)}</span><button type="button" class="sh mini" data-share="item" data-n="{it["n"]}">이 소식 공유</button></div>
</li>'''


def page_daily(b, prev, nxt):
    d = b["date"]
    url = f"{SITE}/news/{d}.html"
    title = f"{kdate(d, True)} 의료 뉴스 · {b['headline']} · Mednomics"
    desc = f"{b['oneline']} 오늘 챙겨 볼 의료 뉴스 {len(b['items'])}건을 닥터조단이 골라 요약했습니다."
    og = f"{SITE}/assets/og/news-{d}.png"
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": f"{kdate(d, True)} 의료 뉴스: {b['headline']}",
           "description": desc, "datePublished": d, "dateModified": d, "inLanguage": "ko",
           "author": {"@type": "Person", "name": "닥터조단", "url": f"{SITE}/about.html"},
           "publisher": {"@type": "Organization", "name": "Mednomics", "url": SITE,
                         "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/logo-512.png"}},
           "mainEntityOfPage": url, "image": og, "articleSection": "데일리 브리핑"},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "홈", "item": f"{SITE}/"},
              {"@type": "ListItem", "position": 2, "name": "뉴스", "item": f"{SITE}/news/"},
              {"@type": "ListItem", "position": 3, "name": kdate(d, True), "item": url}]}]
    data = {"date": d, "label": kdate(d, True), "url": url, "headline": b["headline"],
            "items": [{"n": it["n"], "title": it["title"], "summary": it["summary"]} for it in b["items"]]}
    watch = ""
    if b["watch"]:
        lis = "".join(
            f'<li>{E(w["text"])}' + (f' <a href="{E(w["url"])}" target="_blank" rel="noopener nofollow">{E(w.get("name", "원문"))}</a>' if w.get("url") else "") + "</li>"
            for w in b["watch"])
        watch = f'<div class="watch"><h3>이번 주 이어서 볼 것</h3><ol>{lis}</ol></div>'
    pn = '<nav class="nav-posts">'
    pn += f'<a href="{prev["date"]}.html"><small>이전 브리핑</small>{kdate(prev["date"], True)} · {E(prev["headline"])}</a>' if prev else '<span><small>이전 브리핑</small>첫 브리핑입니다</span>'
    pn += f'<a class="r" href="{nxt["date"]}.html"><small>다음 브리핑</small>{kdate(nxt["date"], True)} · {E(nxt["headline"])}</a>' if nxt else '<span class="r"><small>다음 브리핑</small>내일 아침에 이어집니다</span>'
    pn += "</nav>"
    body = f'''
<section class="page-head news-head"><div class="in">
  <p class="label" style="color:#8a9099">Daily Brief</p>
  <h1>{kdate(d, True)} 의료 뉴스</h1>
  <p>{E(b["headline"])} — 오늘 챙겨 볼 {len(b["items"])}가지</p>
  {sharebar()}
</div></section>
<article class="body news-body">
<nav class="crumbs" aria-label="현재 위치"><a href="../">홈</a> / <a href="./">뉴스</a> / <span>{kdate(d, True)}</span></nav>
<div class="oneline today"><b>오늘의 한 줄</b><p>{E(b["oneline"])}</p></div>
<ol class="brief">
{chr(10).join(item_html(it) for it in b["items"])}
</ol>
{watch}
<div class="sharebox"><p><b>도움이 됐다면 동료에게 보내 주세요.</b> 카톡·문자용 복사를 누르면 제목과 요약이 정리된 텍스트가 복사됩니다.</p>{sharebar()}</div>
<p class="refs"><b>이 브리핑에 대해</b><br>각 소식은 닥터조단이 원문을 읽고 직접 요약한 것이며, 기사의 저작권은 해당 언론사에 있습니다. 자세한 내용과 맥락은 원문에서 확인해 주세요. 요약이 원문과 다르면 확인되는 대로 고치고 밝힙니다. <a href="policy.html">편집 원칙</a></p>
<p class="upd">발행 {d} · 정리 닥터조단</p>
</article>
{pn}
<script type="application/json" id="brief-data">{J(data)}</script>
'''
    return head(title, desc, url, og, ld) + body + foot()


def page_index(briefs):
    latest = briefs[0]
    d = latest["date"]
    url = f"{SITE}/news/"
    desc = "의사가 매일 아침 골라 읽는 의료계 뉴스. 메디게이트뉴스, 청년의사, 의학신문 등 의료 전문지의 주요 소식을 짧게 요약하고 원문으로 연결합니다."
    ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": "Mednomics 의료 뉴스", "url": url,
           "description": desc, "inLanguage": "ko"}]
    heads = "".join(
        f'<li><a href="{d}.html#n{it["n"]}"><span class="cat {CATS.get(it["cat"], "c-etc")}">{E(it["cat"])}</span><b>{E(it["title"])}</b></a></li>'
        for it in latest["items"])
    arch = "".join(
        f'''<li><a href="{b["date"]}.html">
  <span class="meta">{kdate(b["date"])} · {len(b["items"])}건</span>
  <h3>{E(b["headline"])}</h3><p>{E(b["oneline"])}</p></a></li>
''' for b in briefs)
    body = f'''
<section class="page-head news-head"><div class="in">
  <p class="label" style="color:#8a9099">Daily Brief</p>
  <h1>오늘의 의료 뉴스</h1>
  <p>의사가 매일 아침 골라 읽는 의료계 소식. 짧게 요약하고, 원문으로 연결합니다.</p>
</div></section>
<section class="sec news-sec">
  <nav class="crumbs" aria-label="현재 위치"><a href="../">홈</a> / <span>뉴스</span></nav>
  <p class="label">Latest · {kdate(d)}</p>
  <h2><a class="plain" href="{d}.html">{E(latest["headline"])}</a></h2>
  <div class="oneline today"><b>오늘의 한 줄</b><p>{E(latest["oneline"])}</p></div>
  <ol class="headlines">{heads}</ol>
  <p class="more"><a href="{d}.html">요약까지 전체 보기 →</a></p>
  <p class="label" style="margin-top:60px">Archive</p>
  <h2>지난 브리핑</h2>
  <ol class="posts">{arch}</ol>
  <p class="refs" style="margin-top:40px"><b>뉴스 브리핑 원칙</b><br>요약은 직접 쓰고, 출처는 언론사 이름과 원문 링크로 밝힙니다. 기사 본문은 옮기지 않습니다. <a href="policy.html">편집 원칙 전체 보기</a> · 제보와 정정 요청은 <a href="https://blog.naver.com/jordanam">네이버 블로그</a> 댓글이나 쪽지로 보내 주세요.</p>
</section>
'''
    return head("오늘의 의료 뉴스 · Mednomics", desc, url, f"{SITE}/assets/og/news-{d}.png", ld) + body + foot()


def feed(briefs):
    items = ""
    for b in briefs[:30]:
        d = b["date"]
        url = f"{SITE}/news/{d}.html"
        pub = dt.datetime.fromisoformat(d + "T07:00:00").strftime("%a, %d %b %Y %H:%M:%S +0900")
        content = f"<p><b>오늘의 한 줄</b> {E(b['oneline'])}</p><ol>" + "".join(
            f"<li><b>{E(it['title'])}</b><br>{E(it['summary'])}<br><small>원문: " +
            ", ".join(f'<a href="{E(s["url"])}">{E(s["name"])}</a>' for s in it["sources"]) + "</small></li>"
            for it in b["items"]) + "</ol><p>출처: 닥터조단, mednomics.co.kr</p>"
        items += (f"<item><title>{E(kdate(d, True) + ' 의료 뉴스 · ' + b['headline'])}</title><link>{url}</link>"
                  f'<guid isPermaLink="true">{url}</guid><pubDate>{pub}</pubDate><category>데일리 브리핑</category>'
                  f"<description>{E(b['oneline'])}</description><content:encoded><![CDATA[{content}]]></content:encoded></item>\n")
    last = dt.datetime.fromisoformat(briefs[0]["date"] + "T07:00:00").strftime("%a, %d %b %Y %H:%M:%S +0900")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
            'xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Mednomics · 오늘의 의료 뉴스</title>'
            f"<link>{SITE}/news/</link><description>의사가 매일 아침 골라 읽는 의료계 뉴스</description><language>ko</language>"
            f'<atom:link href="{SITE}/news/feed.xml" rel="self" type="application/rss+xml"/><lastBuildDate>{last}</lastBuildDate>\n'
            + items + "</channel></rss>\n")


def home_block(b):
    d = b["date"]
    lis = "".join(f'<li><a href="news/{d}.html#n{it["n"]}"><span class="cat {CATS.get(it["cat"], "c-etc")}">{E(it["cat"])}</span><b>{E(it["title"])}</b></a></li>'
                  for it in b["items"][:5])
    return f'''<!--NEWS:START-->
<section class="sec home-news">
  <p class="label">Today · {kdate(d)}</p>
  <h2>오늘의 의료 뉴스</h2>
  <ol class="headlines">{lis}</ol>
  <p class="more"><a href="news/{d}.html">전체 {len(b["items"])}건과 요약 보기 →</a> · <a href="news/">지난 브리핑</a></p>
</section>
<!--NEWS:END-->'''


def og_image(b):
    path = os.path.join(ROOT, f"assets/og/news-{b['date']}.png")
    if os.path.exists(path):
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow 없음: 공유 이미지 건너뜀")
        return
    fonts = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/System/Library/Fonts/AppleSDGothicNeo.ttc",
             "C:/Windows/Fonts/malgunbd.ttf"]
    fp = next((f for f in fonts if os.path.exists(f)), None)
    if not fp:
        print("한글 글꼴 없음: 공유 이미지 건너뜀")
        return
    F = lambda s: ImageFont.truetype(fp, s, index=1) if fp.endswith(".ttc") else ImageFont.truetype(fp, s)
    im = Image.new("RGB", (1200, 630), (7, 9, 12))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1200, 8], fill=(255, 77, 94))
    d.text((70, 60), "MEDNOMICS · 오늘의 의료 뉴스", font=F(26), fill=(138, 144, 153))
    d.text((70, 112), kdate(b["date"], True), font=F(64), fill=(244, 246, 248))
    y = 230
    for it in b["items"][:4]:
        t = it["title"]
        while d.textlength(t, font=F(32)) > 1020 and len(t) > 4:
            t = t[:-2]
        if t != it["title"]:
            t = t.rstrip() + "…"
        d.ellipse([72, y + 16, 84, y + 28], fill=(47, 210, 127))
        d.text((104, y), t, font=F(32), fill=(214, 219, 225))
        y += 66
    d.text((70, 548), "닥터조단 정리 · 원문 링크 포함", font=F(24), fill=(138, 144, 153))
    d.text((910, 548), "mednomics.co.kr", font=F(26), fill=(47, 210, 127))
    im.save(path)


def update_home(b):
    p = os.path.join(ROOT, "index.html")
    s = open(p, encoding="utf-8").read()
    s2 = re.sub(r"<!--NEWS:START-->.*?<!--NEWS:END-->", lambda m: home_block(b), s, flags=re.S)
    open(p, "w", encoding="utf-8").write(s2)


def update_sitemap(briefs):
    p = os.path.join(ROOT, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"\s*<url><loc>https://mednomics\.co\.kr/news/[^<]*</loc>.*?</url>", "", s)
    today = briefs[0]["date"]
    add = [f"  <url><loc>{SITE}/news/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>0.9</priority></url>",
           f"  <url><loc>{SITE}/news/policy.html</loc><lastmod>2026-11-16</lastmod><priority>0.4</priority></url>"]
    add += [f"  <url><loc>{SITE}/news/{b['date']}.html</loc><lastmod>{b['date']}</lastmod><priority>0.7</priority></url>" for b in briefs]
    s = s.replace("</urlset>", "\n".join(add) + "\n</urlset>")
    s = re.sub(r"(<loc>https://mednomics\.co\.kr/</loc><lastmod>)[^<]*", r"\g<1>" + today, s)
    open(p, "w", encoding="utf-8").write(s)


def update_search(briefs):
    p = os.path.join(ROOT, "search-index.json")
    si = [x for x in json.load(open(p, encoding="utf-8")) if not x["u"].startswith("news/")]
    new = [{"t": f"{kdate(b['date'], True)} 의료 뉴스 · {b['headline']}", "u": f"news/{b['date']}.html", "d": b["oneline"],
            "x": " ".join(f"{it['title']} {it['summary']}" for it in b["items"])[:1500]} for b in briefs[:60]]
    json.dump(new + si, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def main():
    briefs = load()
    os.makedirs(os.path.join(ROOT, "news"), exist_ok=True)
    asc = list(reversed(briefs))
    for i, b in enumerate(asc):
        prev = asc[i - 1] if i > 0 else None
        nxt = asc[i + 1] if i + 1 < len(asc) else None
        open(os.path.join(ROOT, f"news/{b['date']}.html"), "w", encoding="utf-8").write(page_daily(b, prev, nxt))
        og_image(b)
    open(os.path.join(ROOT, "news/index.html"), "w", encoding="utf-8").write(page_index(briefs))
    open(os.path.join(ROOT, "news/feed.xml"), "w", encoding="utf-8").write(feed(briefs))
    update_home(briefs[0])
    update_sitemap(briefs)
    update_search(briefs)
    print(f"브리핑 {len(briefs)}개 생성, 최신 {briefs[0]['date']}")


if __name__ == "__main__":
    main()
