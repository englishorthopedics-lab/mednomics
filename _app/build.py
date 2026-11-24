#!/usr/bin/env python3
"""Mednomics 사이트 빌드: 설치형 웹앱 껍데기, 뉴스·인사이트·링크 페이지, 영어판(/en/)을 한 번에 만든다.

사용:  python3 _app/build.py        (저장소 루트에서)

- 손으로 쓴 한국어 페이지(index.html, series/, topics/, trackers/ 등)가 원본이다.
  빌드는 이 페이지들의 머리글·바닥글·하단 탭바만 새로 끼우고, 본문은 건드리지 않는다.
- 뉴스는 _newsroom/data/날짜.json, 인사이트는 _app/data/*.json 에서 만든다.
- 영어판은 _app/i18n/en.txt 사전으로 한국어 페이지를 문단 단위로 옮겨 /en/ 아래에 만든다.
  번역이 빠진 문장은 _app/i18n/catalog.txt 에 모이고, 빌드 끝에 개수를 알려 준다.
"""
import datetime as dt
import glob
import hashlib
import html
import json
import os
import posixpath
import re
import sys
from urllib.parse import urlparse

APP = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP)
sys.path.insert(0, APP)
import i18n  # noqa: E402

SITE = "https://mednomics.co.kr"
E = html.escape
WD_KO = "월화수목금토일"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WD_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STRICT = "--strict" in sys.argv

# ───────────────────────── 화면 문구 ─────────────────────────
U = {
    "skip": ("본문으로 건너뛰기", "Skip to content"),
    "home_aria": ("Mednomics 홈", "Mednomics home"),
    "menu_aria": ("주 메뉴", "Main menu"),
    "news": ("뉴스", "News"), "insight": ("인사이트", "Insight"), "series": ("연재", "Series"),
    "trackers": ("트래커", "Trackers"), "links": ("링크", "Links"), "glossary": ("용어사전", "Glossary"),
    "about": ("필자", "About"), "search": ("검색", "Search"), "board": ("이슈 보드", "Issue board"),
    "industry": ("산업 지도", "Industry map"), "saved": ("저장한 글", "Saved"), "today": ("오늘", "Today"),
    "more": ("더보기", "More"), "start": ("처음 오셨다면", "Start here"), "about_long": ("필자 소개", "About the author"),
    "lang_other": ("EN", "KO"), "lang_other_label": ("English", "한국어"),
    "search_ph": ("간납사, 위고비, 특사경 ...", "GPO, Wegovy, rebates ..."), "close": ("닫기", "Close"),
    "install": ("앱으로 설치", "Install app"),
    "install_ios": ("iPhone은 Safari 공유 버튼 → '홈 화면에 추가'를 누르세요.", "On iPhone, tap Safari's Share button, then 'Add to Home Screen'."),
    "tab_aria": ("빠른 이동", "Quick navigation"),
    "print": ("인쇄할 수 없습니다.", "Printing is disabled."),
    "foot_1": ("Mednomics의 글은 공개된 자료를 바탕으로 한 산업 해설이며, 특정 종목의 매수나 매도를 권하지 않습니다. 투자 판단과 그 결과의 책임은 투자자 본인에게 있습니다. 개별 환자의 진료를 대신하지도 않습니다.",
               "Mednomics offers industry commentary based on public sources. It is not a recommendation to buy or sell any security, and it does not replace individual medical care. Investment decisions and their results are the reader's own responsibility."),
    "foot_2": ("이 사이트의 글과 그림의 저작권은 닥터조단에게 있으며, 무단 복제와 재배포를 금합니다. 인용할 때는 출처(mednomics.co.kr)를 밝혀 주세요.",
               "All text and graphics on this site are © Dr. Jordan. Do not copy or redistribute without permission. When quoting, please credit mednomics.co.kr."),
    "foot_3": ("뉴스 요약에 인용한 각 기사의 저작권은 해당 언론사에 있습니다.", "Copyright in each news article cited in our briefs belongs to its publisher."),
    "tagline": ("MEDNOMICS · 두 개의 차트", "MEDNOMICS · Two Charts"),
    "sub_text": ("매일 의료 뉴스는 뉴스 RSS로, 연재 새 글은 네이버 블로그로 먼저 알려 드립니다. 이메일 뉴스레터는 준비 중입니다.",
                 "Daily news is on the news RSS feed; new series posts appear first on our Naver blog. An email newsletter is coming."),
    "sub_blog": ("네이버 블로그 이웃 추가", "Follow on Naver Blog"), "sub_rss": ("뉴스 RSS", "News RSS"),
    "home": ("홈", "Home"),
}


def t(key, lang):
    return U[key][0 if lang == "ko" else 1]


def J(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def L(obj, key, lang):
    """데이터의 언어별 값: 영어는 key_en, 없으면 None."""
    if lang == "ko":
        return obj.get(key, "")
    return obj.get(key + "_en")


def kdate(d, lang, style="long"):
    x = dt.date.fromisoformat(d)
    if lang == "ko":
        if style == "short":
            return f"{x.month}월 {x.day}일({WD_KO[x.weekday()]})"
        if style == "md":
            return f"{x.month}. {x.day}"
        return f"{x.year}. {x.month}. {x.day} ({WD_KO[x.weekday()]})"
    if style == "short":
        return f"{WD_EN[x.weekday()]}, {MON[x.month - 1]} {x.day}"
    if style == "md":
        return f"{MON[x.month - 1]} {x.day}"
    return f"{WD_EN[x.weekday()]}, {MON[x.month - 1]} {x.day}, {x.year}"


def read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def write(p, s):
    full = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    old = open(full, encoding="utf-8").read() if os.path.exists(full) else None
    if old != s:
        open(full, "w", encoding="utf-8").write(s)


def jload(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))


# ───────────────────────── 페이지 목록 ─────────────────────────
HAND = sorted([p for p in glob.glob("*.html", root_dir=ROOT) if not p.startswith("naver")] +
              glob.glob("series/*.html", root_dir=ROOT) + glob.glob("topics/*.html", root_dir=ROOT) +
              glob.glob("trackers/*.html", root_dir=ROOT))
HAND = [p for p in HAND if p not in ("saved.html",)]
NO_EN = {"404.html"}
GENERATED = set()          # 이번 빌드가 만든 페이지(언어 루트 기준 경로)
EN_PAGES = set()           # 영어판이 있는 페이지


def section_of(path):
    first = path.split("/")[0]
    return {"news": "news", "insight": "insight", "series": "series", "trackers": "trackers", "links": "links",
            "glossary.html": "glossary", "about.html": "about", "board.html": "board", "topics": "series",
            "saved.html": "saved"}.get(first, "home" if path == "index.html" else "")


def url_of(path, lang):
    p = path[:-10] if path.endswith("index.html") else path
    return f"{SITE}/{'en/' if lang == 'en' else ''}{p}"


def prefix(path):
    return "../" * path.count("/")


def pre_of(path):
    """링크용 접두어. 404는 어느 주소에서나 열리므로 절대 경로를 쓴다."""
    return "/" if path == "404.html" else prefix(path)


# ───────────────────────── 공통 껍데기 ─────────────────────────
def header_html(lang, path):
    pre = pre_of(path)
    sec = section_of(path)
    other = other_href(lang, path)
    items = [("news", "news/"), ("insight", "insight/"), ("series", "series/"), ("trackers", "trackers/"),
             ("links", "links/"), ("glossary", "glossary.html"), ("about", "about.html")]
    nav = "\n".join(f'    <a href="{pre}{h}"{" aria-current=\"page\"" if sec == k else ""}>{t(k, lang)}</a>' for k, h in items)
    home = pre or "./"
    return f'''<header class="bar"><div class="in">
  <a class="logo" href="{home}" aria-label="{t('home_aria', lang)}"><i></i><b>MEDNOMICS</b></a>
  <nav class="menu" aria-label="{t('menu_aria', lang)}">
{nav}
    <button class="sbtn" type="button" id="open-search" aria-label="{t('search', lang)}">{t('search', lang)}</button>
    <a class="lang" href="{other}" hreflang="{'en' if lang == 'ko' else 'ko'}" lang="{'en' if lang == 'ko' else 'ko'}" aria-label="{t('lang_other_label', lang)}">{t('lang_other', lang)}</a>
  </nav>
</div></header>'''


def search_html(lang):
    return f'''<div class="search" id="search" hidden role="dialog" aria-label="{t('search', lang)}">
  <div class="sbox"><input id="q" type="search" placeholder="{t('search_ph', lang)}" autocomplete="off"><button type="button" id="close-search" aria-label="{t('close', lang)}">{t('close', lang)}</button>
  <ul id="results"></ul></div>
</div>'''


def other_href(lang, path):
    """같은 페이지의 다른 언어판으로 가는 상대 주소."""
    pre = pre_of(path)
    target = path[:-10] if path.endswith("index.html") else path
    if lang == "ko":
        if path in NO_EN:
            return pre + "en/"
        return pre + "en/" + target
    return "../" + pre + target


def fnav_html(lang, path):
    pre = pre_of(path)
    rss = "/en/news/feed.xml" if lang == "en" else "/rss.xml"
    return (f'<nav class="fnav"><a href="{pre}start.html">{t("start", lang)}</a><a href="{pre}news/">{t("news", lang)}</a>'
            f'<a href="{pre}insight/">{t("insight", lang)}</a><a href="{pre}series/">{t("series", lang)}</a>'
            f'<a href="{pre}board.html">{t("board", lang)}</a><a href="{pre}trackers/">{t("trackers", lang)}</a>'
            f'<a href="{pre}links/">{t("links", lang)}</a><a href="{pre}glossary.html">{t("glossary", lang)}</a>'
            f'<a href="{pre}about.html">{t("about_long", lang)}</a><a href="{rss}">RSS</a></nav>')


ICON = {
    "home": '<path d="M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z"/>',
    "news": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    "insight": '<path d="M4 19h16"/><path d="M6 15l4-5 3 3 5-7"/>',
    "series": '<path d="M5 5.5A2.5 2.5 0 0 1 7.5 3H19v15H7.5A2.5 2.5 0 0 0 5 20.5z"/><path d="M5 20.5A2.5 2.5 0 0 0 7.5 23H19"/>',
    "more": '<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>',
}


def svg(name):
    return f'<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICON[name]}</svg>'


def tabbar_html(lang, path):
    pre = pre_of(path)
    sec = section_of(path)
    tabs = [("home", pre or "./", "today"), ("news", pre + "news/", "news"), ("insight", pre + "insight/", "insight"),
            ("series", pre + "series/", "series")]
    a = "".join(f'<a href="{h}"{" aria-current=\"page\"" if sec == k else ""}>{svg(k)}<span>{t(lab, lang)}</span></a>' for k, h, lab in tabs)
    more = [("board.html", "board"), ("trackers/", "trackers"), ("insight/industry.html", "industry"), ("links/", "links"),
            ("glossary.html", "glossary"), ("saved.html", "saved"), ("about.html", "about_long"), ("start.html", "start")]
    ml = "".join(f'<a href="{pre}{h}">{t(k, lang)}</a>' for h, k in more)
    return f'''<!--APP:TAB-->
<nav class="tabbar" aria-label="{t('tab_aria', lang)}">{a}<button type="button" id="more-open" aria-haspopup="dialog">{svg('more')}<span>{t('more', lang)}</span></button></nav>
<div class="sheet" id="more-sheet" hidden role="dialog" aria-label="{t('more', lang)}"><div class="sheet-in">
  <div class="sheet-links">{ml}</div>
  <div class="sheet-row"><a class="sheet-lang" href="{other_href(lang, path)}" lang="{'en' if lang == 'ko' else 'ko'}">{t('lang_other_label', lang)}</a><button type="button" class="sheet-install" id="install-app" hidden>{t('install', lang)}</button></div>
  <p class="sheet-ios" id="install-ios" hidden>{t('install_ios', lang)}</p>
  <button type="button" class="sheet-close" id="more-close">{t('close', lang)}</button>
</div></div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<!--/APP:TAB-->'''


def app_head(lang, path):
    pre = prefix(path) if path != "404.html" else "/"
    man = (pre + "en/manifest.webmanifest") if lang == "en" else (pre + "manifest.webmanifest")
    if lang == "en":
        man = "../" * (path.count("/") + 1) + "en/manifest.webmanifest"
    alts = ""
    if path not in NO_EN:
        alts = (f'<link rel="alternate" hreflang="ko" href="{url_of(path, "ko")}">'
                f'<link rel="alternate" hreflang="en" href="{url_of(path, "en")}">'
                f'<link rel="alternate" hreflang="x-default" href="{url_of(path, "ko")}">')
    return (f'<!--APP:HEAD--><link rel="manifest" href="{man}"><meta name="apple-mobile-web-app-capable" content="yes">'
            f'<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Mednomics">'
            f'<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">{alts}<!--/APP:HEAD-->')


def apply_shell(src, lang, path, asset_pre):
    """머리글·바닥글 메뉴·탭바·웹앱 태그를 새로 끼운다(여러 번 돌려도 같은 결과)."""
    s = re.sub(r"<!--APP:HEAD-->.*?<!--/APP:HEAD-->", "", src, flags=re.S)
    s = s.replace('<meta name="viewport" content="width=device-width, initial-scale=1">', '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')
    s = s.replace('<meta name="theme-color" content="#07090c">', '<meta name="theme-color" content="#07090c">' + app_head(lang, path), 1)
    s = re.sub(r'<header class="bar">.*?</header>', lambda m: header_html(lang, path), s, count=1, flags=re.S)
    s = re.sub(r'<div class="search" id="search".*?</ul></div>\n</div>', lambda m: search_html(lang), s, count=1, flags=re.S)
    s = re.sub(r'<nav class="fnav">.*?</nav>', lambda m: fnav_html(lang, path), s, count=1, flags=re.S)
    s = re.sub(r"\n?<!--APP:TAB-->.*?<!--/APP:TAB-->", "", s, flags=re.S)
    s = re.sub(r'\n?<div class="toast" id="toast"[^>]*></div>', "", s)
    s = s.replace('<div class="print-block">', tabbar_html(lang, path) + '\n<div class="print-block">', 1)
    s = re.sub(r'\n?<script src="[^"]*assets/app\.js" defer></script>', "", s)
    s = s.replace("</body>", f'<script src="{asset_pre}assets/app.js" defer></script>\n</body>', 1)
    if '<div class="print-block">' not in s:
        print("  ! print-block 없음:", path)
    return s


# ───────────────────────── 생성 페이지 공통 ─────────────────────────
def page_head(lang, path, title, desc, og, ld=(), og_type="article"):
    apre = asset_prefix(lang, path)
    url = url_of(path, lang)
    rss = f"{SITE}/en/news/feed.xml" if lang == "en" else f"{SITE}/news/feed.xml"
    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="author" content="{'닥터조단' if lang == 'ko' else 'Dr. Jordan'}">
<link rel="canonical" href="{url}">
<link rel="alternate" type="application/rss+xml" title="Mednomics" href="{rss}">
<meta property="og:site_name" content="Mednomics">
<meta property="og:locale" content="{'ko_KR' if lang == 'ko' else 'en_US'}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{og}">
<meta name="theme-color" content="#07090c">
<link rel="icon" href="{apre}assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{apre}assets/icons/icon-192.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{apre}style.css">
{"".join(f'<script type="application/ld+json">{J(x)}</script>' for x in ld)}
</head>
<body>

<div class="progress" id="progress"></div>
<a class="skip" href="#main">{t('skip', lang)}</a>
<header class="bar"></header>
{search_html(lang)}
<main id="main">
'''


def page_foot(lang, path, extra_js=""):
    apre = asset_prefix(lang, path)
    return f'''<section class="sec"><div class="sub-box" id="subscribe">
    <p>{t('sub_text', lang)}</p>
    <div class="btnrow"><a class="btn" href="https://blog.naver.com/jordanam">{t('sub_blog', lang)}</a><a class="btn" href="{'/en/news/feed.xml' if lang == 'en' else '/news/feed.xml'}">{t('sub_rss', lang)}</a></div>
    <small>EMAIL NEWSLETTER · COMING SOON</small>
  </div></section>
</main>
<footer><div class="in">
  <span class="fl">{t('tagline', lang)}</span>
  <nav class="fnav"></nav>
  <p>{t('foot_1', lang)}</p>
  <p>{t('foot_2', lang)} {t('foot_3', lang)}</p>
</div></footer>
<div class="print-block">{t('print', lang)}</div>
<script src="{apre}protect.js"></script>
<script src="{apre}assets/search.js" defer></script>
{extra_js}</body>
</html>
'''


def asset_prefix(lang, path):
    return "../" * (path.count("/") + (1 if lang == "en" else 0))


def emit(path, lang, body_html):
    """생성 페이지를 저장한다. path는 언어 루트 기준 경로."""
    s = apply_shell(body_html, lang, path, asset_prefix(lang, path))
    write(("en/" if lang == "en" else "") + path, s)
    GENERATED.add(path)
    if lang == "en":
        EN_PAGES.add(path)


def crumbs(lang, path, trail):
    pre = prefix(path)
    parts = [f'<a href="{pre or "./"}">{t("home", lang)}</a>']
    for label, href in trail[:-1]:
        parts.append(f'<a href="{href}">{E(label)}</a>')
    parts.append(f"<span>{E(trail[-1][0])}</span>")
    aria = "현재 위치" if lang == "ko" else "You are here"
    return f'<nav class="crumbs" aria-label="{aria}">{" / ".join(parts)}</nav>'


def breadcrumb_ld(lang, path, trail):
    items = [{"@type": "ListItem", "position": 1, "name": t("home", lang), "item": url_of("index.html", lang)}]
    for i, (name, p) in enumerate(trail, 2):
        items.append({"@type": "ListItem", "position": i, "name": name, "item": url_of(p, lang)})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}


# ───────────────────────── 뉴스 ─────────────────────────
CATS = {"정책": "c-pol", "규제": "c-pol", "개원·의원": "c-clinic", "병원": "c-clinic", "약국": "c-clinic",
        "보장성": "c-pay", "제약·바이오": "c-bio", "의료기기·AI": "c-tech", "학술": "c-sci", "학회": "c-sci",
        "의사와 돈": "c-money", "사건·사고": "c-case"}
NU = {
    "brief": ("의료 뉴스", "medical news"), "today_line": ("오늘의 한 줄", "Today in one line"),
    "watch": ("이번 주 이어서 볼 것", "What to watch this week"), "orig": ("원문", "Source"),
    "share_item": ("이 소식 공유", "Share"), "save": ("저장", "Save"),
    "share": ("공유하기", "Share"), "copy_text": ("카톡·문자용 복사", "Copy as text"), "copy_link": ("링크 복사", "Copy link"),
    "share_box": ("<b>도움이 됐다면 동료에게 보내 주세요.</b> 카톡·문자용 복사를 누르면 제목과 요약이 정리된 텍스트가 복사됩니다.",
                  "<b>Found this useful? Send it to a colleague.</b> 'Copy as text' copies the headlines and link, ready to paste."),
    "about_brief": ("이 브리핑에 대해", "About this brief"),
    "about_text": ("각 소식은 닥터조단이 원문을 읽고 직접 요약한 것이며, 기사의 저작권은 해당 언론사에 있습니다. 자세한 내용과 맥락은 원문에서 확인해 주세요. 요약이 원문과 다르면 확인되는 대로 고치고 밝힙니다.",
                   "Each item is summarized by Dr. Jordan after reading the original, which remains the copyright of its publisher (most sources are in Korean). Please read the original for full context. If a summary differs from the source, we correct it and say so."),
    "policy": ("편집 원칙", "Editorial policy"), "pub": ("발행", "Published"), "by": ("정리 닥터조단", "Edited by Dr. Jordan"),
    "prev": ("이전 브리핑", "Previous brief"), "next": ("다음 브리핑", "Next brief"),
    "first": ("첫 브리핑입니다", "This is the first brief"), "tomorrow": ("내일 아침에 이어집니다", "Next brief tomorrow morning"),
    "things": ("오늘 챙겨 볼 {n}가지", "{n} things to know today"),
    "idx_title": ("오늘의 의료 뉴스", "Korea healthcare news today"),
    "idx_sub": ("의사가 매일 골라 읽는 의료계 소식. 짧게 요약하고, 원문으로 연결합니다.", "A doctor's daily pick of Korean healthcare news, summarized in English with links to the originals."),
    "full": ("요약까지 전체 보기 →", "Read the full brief →"), "archive": ("지난 브리핑", "Past briefs"),
    "by_cat": ("분야별로 보기", "Browse by topic"), "all": ("전체", "All"),
    "items_n": ("{n}건", "{n} items"),
    "principle": ("뉴스 브리핑 원칙", "How we brief"),
    "principle_text": ("요약은 직접 쓰고, 출처는 언론사 이름과 원문 링크로 밝힙니다. 기사 본문은 옮기지 않습니다.", "We write every summary ourselves and credit each source by name and link. We do not republish articles."),
    "policy_all": ("편집 원칙 전체 보기", "Read the editorial policy"),
    "tip": ("제보와 정정 요청은 <a href=\"https://blog.naver.com/jordanam\">네이버 블로그</a> 댓글이나 쪽지로 보내 주세요.", "Send tips and corrections via a comment or message on our <a href=\"https://blog.naver.com/jordanam\">Naver blog</a>."),
    "desc": ("{oneline} 오늘 챙겨 볼 의료 뉴스 {n}건을 닥터조단이 골라 요약했습니다.", "{oneline} {n} Korean healthcare stories, picked and summarized by Dr. Jordan."),
    "idx_desc": ("의사가 매일 골라 읽는 의료계 뉴스. 메디게이트뉴스, 청년의사, 의학신문, 데일리팜 등 의료 전문지의 주요 소식을 짧게 요약하고 원문으로 연결합니다.",
                 "Korean healthcare news, picked daily by a practicing doctor and summarized in English, with links to the original Korean trade-press reports."),
}


SRC_EN = {"의학신문": "Bosa", "데일리팜": "Dailypharm", "서울경제": "Seoul Economic Daily", "데일리메디": "Dailymedi",
          "메디게이트뉴스": "Medigate News", "대한민국 정책브리핑": "Korea.kr", "간호사신문": "Nurse News", "병원신문": "Khanews",
          "청년의사": "Docdocdoc", "코메디닷컴": "Kormedi", "메디칼타임즈": "Medical Times", "의협신문": "Doctors News",
          "히트뉴스": "Hit News", "약업신문": "Yakup", "메디파나뉴스": "Medipana", "뉴시스": "Newsis", "연합뉴스": "Yonhap"}


def src_name(name, lang):
    return name if lang == "ko" else SRC_EN.get(name, name)


def nu(k, lang, **kw):
    v = NU[k][0 if lang == "ko" else 1]
    for a, b in kw.items():
        v = v.replace("{" + a + "}", str(b))
    return v


def load_briefs():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "_newsroom/data/*.json")), reverse=True):
        b = json.load(open(p, encoding="utf-8"))
        b.setdefault("watch", [])
        for i, it in enumerate(b["items"], 1):
            it["n"] = i
        b["has_en"] = bool(b.get("headline_en")) and all(it.get("title_en") and it.get("summary_en") for it in b["items"])
        out.append(b)
    return out


def sharebar(lang):
    return f'''<div class="sharebar">
  <button type="button" class="sh main" data-share="native">{nu('share', lang)}</button>
  <button type="button" class="sh" data-share="text">{nu('copy_text', lang)}</button>
  <button type="button" class="sh" data-share="link">{nu('copy_link', lang)}</button>
  <button type="button" class="sh ic" data-share="naver" aria-label="Naver blog">N</button>
  <button type="button" class="sh ic" data-share="band" aria-label="Band">Band</button>
  <button type="button" class="sh ic" data-share="facebook" aria-label="Facebook">f</button>
  <button type="button" class="sh ic" data-share="x" aria-label="X">X</button>
</div>'''


def news_item(it, lang, b):
    cat = L(it, "cat", lang)
    cls = CATS.get(it["cat"], "c-etc")
    take = L(it, "take", lang)
    take_html = f'<p class="take"><b>{"닥터조단" if lang == "ko" else "Dr. Jordan"}</b>{E(take)}</p>' if take else ""
    src = " · ".join(f'<a href="{E(s["url"])}" target="_blank" rel="noopener nofollow">{E(src_name(s["name"], lang))}</a>' for s in it["sources"])
    title = L(it, "title", lang)
    url = url_of(f"news/{b['date']}.html", lang) + f"#n{it['n']}"
    return f'''<li class="brief-item" id="n{it["n"]}" data-cat="{E(it["cat"])}">
  <div class="bi-top"><span class="num">{it["n"]:02d}</span><span class="cat {cls}">{E(cat)}</span></div>
  <h3>{E(title)}</h3>
  <p class="sum">{E(L(it, "summary", lang))}</p>
  {take_html}
  <div class="bi-foot"><span class="src">{nu('orig', lang)} {src}</span><span class="bi-act"><button type="button" class="sh mini" data-save="{E(url)}" data-title="{E(title)}" data-kind="news">{nu('save', lang)}</button><button type="button" class="sh mini" data-share="item" data-n="{it["n"]}">{nu('share_item', lang)}</button></span></div>
</li>'''


def news_daily(b, prev, nxt, lang):
    d = b["date"]
    path = f"news/{d}.html"
    head_l = L(b, "headline", lang)
    one = L(b, "oneline", lang)
    n = len(b["items"])
    title = (f"{kdate(d, lang, 'short')} {nu('brief', lang)} · {head_l} · Mednomics" if lang == "ko"
             else f"Korea healthcare news, {kdate(d, lang, 'short')} · {head_l} · Mednomics")
    desc = nu("desc", lang, oneline=one, n=n)
    og = f"{SITE}/assets/og/news-{d}{'-en' if lang == 'en' else ''}.png"
    ld = [{"@context": "https://schema.org", "@type": "NewsArticle", "headline": f"{kdate(d, lang, 'short')} {nu('brief', lang)}: {head_l}",
           "description": desc, "datePublished": d, "dateModified": d, "inLanguage": lang,
           "author": {"@type": "Person", "name": "닥터조단" if lang == "ko" else "Dr. Jordan", "url": url_of("about.html", lang)},
           "publisher": {"@type": "Organization", "name": "Mednomics", "url": SITE,
                         "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/logo-512.png"}},
           "mainEntityOfPage": url_of(path, lang), "image": og},
          breadcrumb_ld(lang, path, [(t("news", lang), "news/index.html"), (kdate(d, lang, "short"), path)])]
    data = {"date": d, "label": kdate(d, lang, "short"), "url": url_of(path, lang), "headline": head_l, "lang": lang,
            "items": [{"n": it["n"], "title": L(it, "title", lang), "summary": L(it, "summary", lang)} for it in b["items"]]}
    watch = ""
    if b["watch"]:
        lis = "".join(f'<li>{E(L(w, "text", lang) or w["text"])}' +
                      (f' <a href="{E(w["url"])}" target="_blank" rel="noopener nofollow">{E(src_name(w.get("name"), lang) if w.get("name") else nu("orig", lang))}</a>' if w.get("url") else "") + "</li>"
                      for w in b["watch"])
        watch = f'<div class="watch"><h3>{nu("watch", lang)}</h3><ol>{lis}</ol></div>'
    ok = (lambda x: x and (lang == "ko" or x["has_en"]))
    pn = '<nav class="nav-posts">'
    pn += (f'<a href="{prev["date"]}.html"><small>{nu("prev", lang)}</small>{kdate(prev["date"], lang, "short")} · {E(L(prev, "headline", lang))}</a>'
           if ok(prev) else f'<span><small>{nu("prev", lang)}</small>{nu("first", lang)}</span>')
    pn += (f'<a class="r" href="{nxt["date"]}.html"><small>{nu("next", lang)}</small>{kdate(nxt["date"], lang, "short")} · {E(L(nxt, "headline", lang))}</a>'
           if ok(nxt) else f'<span class="r"><small>{nu("next", lang)}</small>{nu("tomorrow", lang)}</span>')
    pn += "</nav>"
    body = f'''
<section class="page-head news-head"><div class="in">
  <p class="label" style="color:#8a9099">Daily Brief</p>
  <h1>{kdate(d, lang, 'short')} {nu('brief', lang) if lang == 'ko' else 'brief'}</h1>
  <p>{E(head_l)} — {nu('things', lang, n=n)}</p>
  {sharebar(lang)}
</div></section>
<article class="body news-body">
{crumbs(lang, path, [(t('news', lang), './'), (kdate(d, lang, 'short'), '')])}
<div class="oneline today"><b>{nu('today_line', lang)}</b><p>{E(one)}</p></div>
<ol class="brief">
{chr(10).join(news_item(it, lang, b) for it in b["items"])}
</ol>
{watch}
<div class="sharebox"><p>{nu('share_box', lang)}</p>{sharebar(lang)}</div>
<p class="refs"><b>{nu('about_brief', lang)}</b><br>{nu('about_text', lang)} <a href="policy.html">{nu('policy', lang)}</a></p>
<p class="upd">{nu('pub', lang)} {d} · {nu('by', lang)}</p>
</article>
{pn}
<script type="application/json" id="brief-data">{J(data)}</script>
'''
    apre = asset_prefix(lang, path)
    html_ = page_head(lang, path, title, desc, og, ld) + body + page_foot(lang, path, f'<script src="{apre}assets/news.js" defer></script>\n')
    emit(path, lang, html_)


def news_index(briefs, lang):
    path = "news/index.html"
    bs = [b for b in briefs if lang == "ko" or b["has_en"]]
    latest = bs[0]
    d = latest["date"]
    ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": nu("idx_title", lang), "url": url_of(path, lang),
           "description": nu("idx_desc", lang), "inLanguage": lang}]
    heads = "".join(f'<li><a href="{d}.html#n{it["n"]}"><span class="cat {CATS.get(it["cat"], "c-etc")}">{E(L(it, "cat", lang))}</span><b>{E(L(it, "title", lang))}</b></a></li>'
                    for it in latest["items"])
    # 분야별: 최근 14개 브리핑의 소식
    pool = [(b, it) for b in bs[:14] for it in b["items"]]
    cats = []
    for _, it in pool:
        if it["cat"] not in cats:
            cats.append(it["cat"])
    chips = f'<button type="button" class="fchip" aria-pressed="true" data-filter="">{nu("all", lang)}</button>' + "".join(
        f'<button type="button" class="fchip" aria-pressed="false" data-filter="{E(c)}">{E(next(L(it, "cat", lang) for _, it in pool if it["cat"] == c))}</button>' for c in cats)
    flist = "".join(f'<li data-cat="{E(it["cat"])}"><a href="{b["date"]}.html#n{it["n"]}"><span class="cat {CATS.get(it["cat"], "c-etc")}">{E(L(it, "cat", lang))}</span><b>{E(L(it, "title", lang))}</b><small>{kdate(b["date"], lang, "md")}</small></a></li>'
                    for b, it in pool)
    arch = "".join(f'''<li><a href="{b["date"]}.html">
  <span class="meta">{kdate(b["date"], lang)} · {nu("items_n", lang, n=len(b["items"]))}</span>
  <h3>{E(L(b, "headline", lang))}</h3><p>{E(L(b, "oneline", lang))}</p></a></li>
''' for b in bs)
    body = f'''
<section class="page-head news-head"><div class="in">
  <p class="label" style="color:#8a9099">Daily Brief</p>
  <h1>{nu('idx_title', lang)}</h1>
  <p>{nu('idx_sub', lang)}</p>
</div></section>
<section class="sec news-sec">
  {crumbs(lang, path, [(t('news', lang), '')])}
  <p class="label">Latest · {kdate(d, lang)}</p>
  <h2><a class="plain" href="{d}.html">{E(L(latest, "headline", lang))}</a></h2>
  <div class="oneline today"><b>{nu('today_line', lang)}</b><p>{E(L(latest, "oneline", lang))}</p></div>
  <ol class="headlines">{heads}</ol>
  <p class="more"><a href="{d}.html">{nu('full', lang)}</a></p>
  <p class="label" style="margin-top:60px">Topics</p>
  <h2>{nu('by_cat', lang)}</h2>
  <div class="fchips" role="group">{chips}</div>
  <ol class="headlines filtered" id="news-filter">{flist}</ol>
  <p class="label" style="margin-top:60px">Archive</p>
  <h2>{nu('archive', lang)}</h2>
  <ol class="posts">{arch}</ol>
  <p class="refs" style="margin-top:40px"><b>{nu('principle', lang)}</b><br>{nu('principle_text', lang)} <a href="policy.html">{nu('policy_all', lang)}</a> · {nu('tip', lang)}</p>
</section>
'''
    html_ = page_head(lang, path, f"{nu('idx_title', lang)} · Mednomics", nu("idx_desc", lang),
                      f"{SITE}/assets/og/news-{d}{'-en' if lang == 'en' else ''}.png", ld, "website") + body + page_foot(lang, path)
    emit(path, lang, html_)


POLICY = {
    "ko": ("뉴스 편집 원칙", "오늘의 의료 뉴스를 고르고, 요약하고, 고치는 기준입니다.", [
        ("무엇을 고르나", "의료 정책과 제도, 병원·개원 환경, 제약·바이오, 의료기기·AI, 학술 소식 가운데 진료실과 병원 경영에 영향을 주는 것을 고릅니다. 하루 5~10건을 목표로 합니다."),
        ("어디서 가져오나", "메디게이트뉴스, 청년의사, 의학신문, 데일리팜, 병원신문 등 의료 전문지와 정부·학회 발표를 봅니다. 같은 사안을 여러 매체가 다루면 함께 적습니다."),
        ("어떻게 요약하나", "제목과 요약은 닥터조단이 원문을 읽고 새로 씁니다. 기사 문장과 사진은 옮기지 않으며, 짧은 인용이 꼭 필요하면 따옴표와 출처를 붙입니다."),
        ("출처는 어떻게 밝히나", "모든 소식 아래에 언론사 이름과 원문 링크를 답니다. 자세한 내용과 맥락은 원문에서 확인하도록 안내합니다."),
        ("사실과 의견", "요약은 보도된 사실만 담습니다. 필자의 해석은 '닥터조단' 표시가 붙은 칸과 '오늘의 한 줄'에만 씁니다."),
        ("정정", "요약이 원문과 다르거나 사실이 바뀌면 확인하는 대로 고치고, 그 페이지에 고친 날짜와 내용을 적습니다."),
        ("이해관계", "필자는 현직 의사입니다. 광고나 협찬을 받은 내용을 싣게 되면 그 사실을 소식 옆에 표시합니다."),
        ("원문 저작권", "인용한 기사의 저작권은 해당 언론사에 있습니다. 언론사가 링크나 요약의 삭제를 요청하면 따릅니다.")],
        "연락", "제보, 정정 요청, 삭제 요청은 <a href=\"https://blog.naver.com/jordanam\">네이버 블로그</a> 댓글이나 쪽지로 보내 주세요.", "처음 공개 2026-11-16"),
    "en": ("Editorial policy", "How we pick, summarize and correct the daily healthcare news.", [
        ("What we pick", "Stories on health policy, hospitals and clinics, pharma and biotech, devices and AI, and research that affect clinical practice or hospital business. We aim for 5–10 a day."),
        ("Where it comes from", "Korean healthcare trade press such as Medigate News, Docdocdoc, Bosa, Dailypharm and Khanews, plus government and society announcements. When several outlets cover a story, we list them together."),
        ("How we summarize", "Dr. Jordan reads the original and writes a new headline and summary. We do not copy article text or photos; any short quotation carries quotation marks and a credit."),
        ("How we credit", "Every item lists the publisher and links to the original, where readers can find full detail and context. Most originals are in Korean."),
        ("Fact and opinion", "Summaries report only what was published. Interpretation appears only in boxes marked 'Dr. Jordan' and in 'Today in one line'."),
        ("Corrections", "If a summary differs from the source or facts change, we fix it as soon as we confirm it and note the date and change on the page."),
        ("Interests", "The author is a practicing physician. Any advertising or sponsorship will be labeled next to the item concerned."),
        ("Copyright", "Copyright in cited articles belongs to their publishers. We will remove a link or summary if a publisher asks.")],
        "Contact", "Send tips, corrections or takedown requests via a comment or message on our <a href=\"https://blog.naver.com/jordanam\">Naver blog</a>.", "First published 2026-11-16"),
}


def news_policy(lang):
    path = "news/policy.html"
    h1, sub, rules, ch, ct, first = POLICY[lang]
    body = f'''
<section class="page-head news-head"><div class="in">
  <p class="label" style="color:#8a9099">Editorial policy</p>
  <h1>{h1}</h1>
  <p>{sub}</p>
</div></section>
<article class="body">
{crumbs(lang, path, [(t('news', lang), './'), (h1, '')])}
{"".join(f'<div class="pt"><span class="n">{i:02d}</span><p><b>{a}</b><br>{b}</p></div>' for i, (a, b) in enumerate(rules, 1))}
<p class="refs"><b>{ch}</b><br>{ct}</p>
<p class="upd">{first}</p>
</article>
'''
    ld = [{"@context": "https://schema.org", "@type": "WebPage", "name": h1, "url": url_of(path, lang), "inLanguage": lang}]
    emit(path, lang, page_head(lang, path, f"{h1} · Mednomics", sub, f"{SITE}/assets/og-default.png", ld, "website") + body + page_foot(lang, path))


def news_feed(briefs, lang):
    bs = [b for b in briefs if lang == "ko" or b["has_en"]][:30]
    items = ""
    for b in bs:
        d = b["date"]
        url = url_of(f"news/{d}.html", lang)
        pub = dt.datetime.fromisoformat(d + "T07:00:00").strftime("%a, %d %b %Y %H:%M:%S +0900")
        content = f"<p><b>{nu('today_line', lang)}</b> {E(L(b, 'oneline', lang))}</p><ol>" + "".join(
            f"<li><b>{E(L(it, 'title', lang))}</b><br>{E(L(it, 'summary', lang))}<br><small>{nu('orig', lang)}: " +
            ", ".join(f'<a href="{E(s["url"])}">{E(src_name(s["name"], lang))}</a>' for s in it["sources"]) + "</small></li>"
            for it in b["items"]) + f"</ol><p>{'출처: 닥터조단, mednomics.co.kr' if lang == 'ko' else 'Source: Dr. Jordan, mednomics.co.kr'}</p>"
        items += (f"<item><title>{E(kdate(d, lang, 'short') + ' · ' + L(b, 'headline', lang))}</title><link>{url}</link>"
                  f'<guid isPermaLink="true">{url}</guid><pubDate>{pub}</pubDate><category>Daily Brief</category>'
                  f"<description>{E(L(b, 'oneline', lang))}</description><content:encoded><![CDATA[{content}]]></content:encoded></item>\n")
    last = dt.datetime.fromisoformat(bs[0]["date"] + "T07:00:00").strftime("%a, %d %b %Y %H:%M:%S +0900")
    title = "Mednomics · 오늘의 의료 뉴스" if lang == "ko" else "Mednomics · Korea healthcare news"
    feed_url = url_of("news/feed.xml", lang)
    s = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
         f'xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>{title}</title>'
         f"<link>{url_of('news/index.html', lang)}</link><description>{E(nu('idx_sub', lang))}</description><language>{lang}</language>"
         f'<atom:link href="{feed_url}" rel="self" type="application/rss+xml"/><lastBuildDate>{last}</lastBuildDate>\n'
         + items + "</channel></rss>\n")
    write(("en/" if lang == "en" else "") + "news/feed.xml", s)


def og_news(b, lang):
    path = os.path.join(ROOT, f"assets/og/news-{b['date']}{'-en' if lang == 'en' else ''}.png")
    if os.path.exists(path):
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    fonts = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/System/Library/Fonts/AppleSDGothicNeo.ttc", "C:/Windows/Fonts/malgunbd.ttf"]
    fp = next((f for f in fonts if os.path.exists(f)), None)
    if not fp:
        return
    F = (lambda s: ImageFont.truetype(fp, s, index=1)) if fp.endswith(".ttc") else (lambda s: ImageFont.truetype(fp, s))
    im = Image.new("RGB", (1200, 630), (7, 9, 12))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1200, 8], fill=(255, 77, 94))
    d.text((70, 60), "MEDNOMICS · " + ("오늘의 의료 뉴스" if lang == "ko" else "KOREA HEALTHCARE NEWS"), font=F(26), fill=(138, 144, 153))
    d.text((70, 112), kdate(b["date"], lang, "short"), font=F(64), fill=(244, 246, 248))
    y = 230
    for it in b["items"][:4]:
        full = L(it, "title", lang)
        tt = full
        while d.textlength(tt, font=F(32)) > 1020 and len(tt) > 4:
            tt = tt[:-2]
        if tt != full:
            tt = tt.rstrip() + "…"
        d.ellipse([72, y + 16, 84, y + 28], fill=(47, 210, 127))
        d.text((104, y), tt, font=F(32), fill=(214, 219, 225))
        y += 66
    d.text((70, 548), "닥터조단 정리 · 원문 링크 포함" if lang == "ko" else "Picked by Dr. Jordan · links to originals", font=F(24), fill=(138, 144, 153))
    d.text((910, 548), "mednomics.co.kr", font=F(26), fill=(47, 210, 127))
    im.save(path)


# ───────────────────────── 인사이트 ─────────────────────────
IU = {
    "title": ("숫자로 읽는 의료산업", "Korean healthcare in numbers"),
    "sub": ("보험료, 수가, 의대 정원, 수출. 의료산업의 판을 정하는 숫자와 다가오는 일정을 한 화면에 모았습니다.",
            "Premiums, fees, medical school quotas and exports: the numbers that set the rules of Korean healthcare, plus the dates ahead."),
    "numbers": ("핵심 숫자", "Key numbers"), "asof": ("기준", "as of"), "src": ("출처", "Source"),
    "cal": ("다가오는 일정", "Coming up"), "pending": ("날짜를 기다리는 일", "Waiting for a date"),
    "map": ("산업 지도", "Industry map"),
    "map_sub": ("돈이 어디서 벌리고 어디로 흐르는지, 분야별로 나눠 봅니다.", "Where the money is made and where it flows, sector by sector."),
    "map_go": ("산업 지도 전체 보기 →", "Open the industry map →"),
    "trackers": ("이슈 트래커", "Issue trackers"),
    "links_go": ("정부·데이터·전문지 링크 모음 →", "Government, data and trade-press links →"),
    "note": ("숫자는 표시한 기준일의 보도·발표를 옮긴 것입니다. 이후 바뀐 값은 원문과 최신 발표를 확인해 주세요.",
             "Figures reflect reports and announcements as of the date shown. Check the source for later changes."),
    "dday_today": ("오늘", "Today"),
    "ind_title": ("의료산업 지도", "Korean healthcare industry map"),
    "ind_sub": ("제약에서 지불자까지, 아홉 갈래로 나눈 의료산업의 돈 흐름과 지켜볼 지표, 대표 상장사.",
                "From drugmakers to payers: nine segments, how each makes money, what to watch and representative listed companies."),
    "how": ("어떻게 버나", "How it makes money"), "watch": ("지켜볼 지표", "What to watch"),
    "cos": ("대표 상장사", "Representative listed companies"), "read": ("관련 글", "Related"),
    "ind_note": ("종목은 분야를 설명하기 위한 예시이며 매수·매도 권유가 아닙니다. 종목명을 누르면 네이버 증권 시세 페이지로 이동합니다.",
                 "Companies are examples to illustrate each segment, not buy or sell recommendations. Each name links to its quote page on Naver Finance (Korean)."),
    "links_title": ("의료산업 링크 허브", "Healthcare industry link hub"),
    "links_sub": ("정부 발표, 통계, 공시, 국회, 협회, 전문지, 해외 소식까지. 의료산업을 읽을 때 매일 여는 사이트를 모았습니다.",
                  "Government releases, statistics, filings, the legislature, associations, trade press and global sources: the sites we open every day to read the industry."),
    "partner": ("제휴·협업 문의", "Partnerships"),
    "partner_text": ("의료산업 관련 기관·기업·매체와의 콘텐츠 제휴, 링크 교환, 공동 기획을 환영합니다. <a href=\"https://blog.naver.com/jordanam\">네이버 블로그</a> 쪽지로 연락해 주세요. 광고나 협찬이 붙는 링크는 따로 표시합니다.",
                     "We welcome content partnerships, link exchanges and joint projects with healthcare organizations, companies and media. Contact us via our <a href=\"https://blog.naver.com/jordanam\">Naver blog</a>. Any sponsored or affiliate link will be labeled."),
    "links_note": ("링크는 각 기관의 공식 사이트로 바로 연결됩니다. 주소가 바뀐 곳을 발견하면 알려 주세요.",
                   "Links go straight to each organization's official site. Let us know if you find a broken one."),
    "ext": ("새 창", "opens in new tab"),
    "saved_title": ("저장한 글", "Saved"),
    "saved_sub": ("저장 버튼을 누른 연재 글과 뉴스가 이 기기의 브라우저에 모입니다.", "Articles and news items you save are kept in this browser on this device."),
    "saved_empty": ("아직 저장한 글이 없습니다. 연재 글 위쪽이나 뉴스 소식 아래의 저장 버튼을 눌러 보세요.",
                    "Nothing saved yet. Tap Save at the top of an article or under a news item."),
    "saved_clear": ("모두 지우기", "Clear all"),
}


def iu(k, lang):
    return IU[k][0 if lang == "ko" else 1]


def dday_attr(item):
    if item.get("date"):
        return f' data-dday="{item["date"]}"' + (f' data-end="{item["end"]}"' if item.get("end") else "")
    return ""


def cal_date(item, lang):
    if item.get("date"):
        s = kdate(item["date"], lang, "md")
        if item.get("end"):
            e = dt.date.fromisoformat(item["end"])
            s += f"–{e.day}" if lang == "en" else f"~{e.day}"
        y = item["date"][:4]
        return s, y
    y, m = item["month"].split("-")
    return (f"{int(m)}월" if lang == "ko" else MON[int(m) - 1]), y


def numbers_html(nums, lang, limit=None, link_pre=""):
    out = []
    for it in nums["items"][:limit] if limit else nums["items"]:
        val = it.get("value_en", it["value"]) if lang == "en" else it["value"]
        unit = it.get("unit_en", it["unit"]) if lang == "en" else it["unit"]
        out.append(f'''<div class="ntile">
  <span class="nl">{E(L(it, "label", lang))}</span>
  <b class="nv">{E(val)}<small>{E(unit)}</small></b>
  <p>{E(L(it, "note", lang))}</p>
  <a class="ns" href="{E(it["url"])}" target="_blank" rel="noopener nofollow">{iu("src", lang)} · {E(it["src"] if lang == "ko" else it.get("src_en", it["src"]))}</a>
</div>''')
    return '<div class="ntiles">' + "".join(out) + "</div>"


def cal_html(cal, lang, limit=None, today=None):
    today = today or dt.date.today().isoformat()
    items = [c for c in cal["items"] if (c.get("end") or c.get("date") or (c.get("month", "") + "-28")) >= today]
    if limit:
        items = items[:limit]
    lis = []
    for c in items:
        md, y = cal_date(c, lang)
        link = f' <a href="{E(c["url"])}" target="_blank" rel="noopener nofollow">↗</a>' if c.get("url") else ""
        lis.append(f'''<li{dday_attr(c)}><span class="cd"><b>{md}</b><small>{y}</small></span><span class="ct"><em class="ck">{E(L(c, "kind", lang))}</em><b>{E(L(c, "title", lang))}</b>{link}<small>{E(L(c, "note", lang))}</small></span><span class="dd"></span></li>''')
    return '<ol class="cal">' + "".join(lis) + "</ol>"


def insight_index(nums, cal, ind, lang):
    path = "insight/index.html"
    pend = "".join(f'<li><b>{E(L(p, "title", lang))}</b> — {E(L(p, "note", lang))}' + (f' <a href="{E(p["url"])}" target="_blank" rel="noopener nofollow">↗</a>' if p.get("url") else "") + "</li>" for p in cal.get("pending", []))
    segs = "".join(f'<a class="hub" href="industry.html#{s["id"]}"><b>{E(L(s, "name", lang))}</b><span>{E(L(s, "money", lang)[:60].rstrip())}…</span></a>' for s in ind["segments"])
    trk = [("aesthetic-market.html", "미용의료 상권 트래커", "Aesthetic clinic tracker"), ("gannapsa-ma.html", "간납사 M&A 트래커", "Purchasing-intermediary M&A tracker"),
           ("glp1-korea.html", "GLP-1 비만약 트래커", "GLP-1 obesity drug tracker"), ("mbk-healthcare.html", "MBK 헬스케어 트래커", "MBK healthcare tracker")]
    trks = "".join(f'<a class="hub" href="../trackers/{h}"><b>{a if lang == "ko" else b}</b></a>' for h, a, b in trk)
    body = f'''
<section class="page-head ins-head"><div class="in">
  <p class="label" style="color:#8a9099">Insight</p>
  <h1>{iu('title', lang)}</h1>
  <p>{iu('sub', lang)}</p>
</div></section>
<section class="sec wide">
  {crumbs(lang, path, [(t('insight', lang), '')])}
  <p class="label">Numbers · {iu('asof', lang)} {kdate(nums['asof'], lang, 'md')}, {nums['asof'][:4]}</p>
  <h2>{iu('numbers', lang)}</h2>
  {numbers_html(nums, lang)}
  <p class="refs">{iu('note', lang)}</p>
</section>
<section class="sec">
  <p class="label">Calendar</p>
  <h2>{iu('cal', lang)}</h2>
  {cal_html(cal, lang)}
  <h3 class="h3s">{iu('pending', lang)}</h3>
  <ul class="pending">{pend}</ul>
</section>
<section class="sec" style="padding-top:0">
  <p class="label">Industry map</p>
  <h2>{iu('map', lang)}</h2>
  <p class="lede">{iu('map_sub', lang)}</p>
  <div class="hubs">{segs}</div>
  <p class="more"><a href="industry.html">{iu('map_go', lang)}</a></p>
  <p class="label" style="margin-top:40px">Trackers</p>
  <div class="hubs">{trks}</div>
  <p class="more"><a href="../links/">{iu('links_go', lang)}</a></p>
</section>
'''
    ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": iu("title", lang), "url": url_of(path, lang), "inLanguage": lang,
           "description": iu("sub", lang)}, breadcrumb_ld(lang, path, [(t("insight", lang), path)])]
    emit(path, lang, page_head(lang, path, f"{iu('title', lang)} · Mednomics", iu("sub", lang), f"{SITE}/assets/og-default.png", ld, "website") + body + page_foot(lang, path))


def industry_page(ind, lang):
    path = "insight/industry.html"
    cards = []
    for s in ind["segments"]:
        cos = "".join(f'<a class="co" href="https://finance.naver.com/item/main.naver?code={c[2]}" target="_blank" rel="noopener nofollow">{E(c[0] if lang == "ko" else c[1])}<small>{c[2]}</small></a>' for c in s["companies"])
        posts = "".join(f'<a class="chip" href="../{p}">{E(lab)}</a>' for p, lab in s["posts"])
        cards.append(f'''<article class="seg" id="{s["id"]}">
  <h3>{E(L(s, "name", lang))}</h3>
  <dl><dt>{iu('how', lang)}</dt><dd>{E(L(s, "money", lang))}</dd>
  <dt>{iu('watch', lang)}</dt><dd>{E(L(s, "watch", lang))}</dd>
  {f'<dt>{iu("cos", lang)}</dt><dd class="cos">{cos}</dd>' if cos else ''}
  {f'<dt>{iu("read", lang)}</dt><dd>{posts}</dd>' if posts else ''}</dl>
</article>''')
    body = f'''
<section class="page-head ins-head"><div class="in">
  <p class="label" style="color:#8a9099">Industry map</p>
  <h1>{iu('ind_title', lang)}</h1>
  <p>{iu('ind_sub', lang)}</p>
</div></section>
<section class="sec wide">
  {crumbs(lang, path, [(t('insight', lang), './'), (iu('ind_title', lang), '')])}
  <div class="segs">{"".join(cards)}</div>
  <p class="refs">{iu('ind_note', lang)}</p>
</section>
'''
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": iu("ind_title", lang), "description": iu("ind_sub", lang),
           "inLanguage": lang, "mainEntityOfPage": url_of(path, lang), "author": {"@type": "Person", "name": "닥터조단" if lang == "ko" else "Dr. Jordan"}},
          breadcrumb_ld(lang, path, [(t("insight", lang), "insight/index.html"), (iu("ind_title", lang), path)])]
    emit(path, lang, page_head(lang, path, f"{iu('ind_title', lang)} · Mednomics", iu("ind_sub", lang), f"{SITE}/assets/og-default.png", ld) + body + page_foot(lang, path))


def links_page(links, lang):
    path = "links/index.html"
    groups = []
    for g in links["groups"]:
        cards = "".join(f'''<a class="lk" href="{E(u)}" target="_blank" rel="noopener"><b>{E(ko if lang == "ko" else en)}</b><span>{E(dk if lang == "ko" else de)}</span><small>{E(urlparse(u).netloc.replace("www.", "", 1))}</small></a>'''
                        for ko, en, u, dk, de in g["items"])
        groups.append(f'<section class="lgroup" id="{g["id"]}"><h2>{E(L(g, "name", lang))}</h2><div class="lks">{cards}</div></section>')
    toc = "".join(f'<a class="fchip" href="#{g["id"]}">{E(L(g, "name", lang))}</a>' for g in links["groups"])
    body = f'''
<section class="page-head ins-head"><div class="in">
  <p class="label" style="color:#8a9099">Links</p>
  <h1>{iu('links_title', lang)}</h1>
  <p>{iu('links_sub', lang)}</p>
</div></section>
<section class="sec wide">
  {crumbs(lang, path, [(t('links', lang), '')])}
  <div class="fchips">{toc}</div>
  {"".join(groups)}
  <div class="sub-box partner"><p><b>{iu('partner', lang)}</b><br>{iu('partner_text', lang)}</p></div>
  <p class="refs">{iu('links_note', lang)}</p>
</section>
'''
    ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": iu("links_title", lang), "url": url_of(path, lang), "inLanguage": lang},
          breadcrumb_ld(lang, path, [(t("links", lang), path)])]
    emit(path, lang, page_head(lang, path, f"{iu('links_title', lang)} · Mednomics", iu("links_sub", lang), f"{SITE}/assets/og-default.png", ld, "website") + body + page_foot(lang, path))


def saved_page(lang):
    path = "saved.html"
    body = f'''
<section class="page-head"><div class="in">
  <p class="label" style="color:#8a9099">Saved</p>
  <h1>{iu('saved_title', lang)}</h1>
  <p>{iu('saved_sub', lang)}</p>
</div></section>
<section class="sec">
  <ol class="posts" id="saved-list" data-empty="{E(iu('saved_empty', lang))}"></ol>
  <p class="more"><button type="button" class="sh mini" id="saved-clear">{iu('saved_clear', lang)}</button></p>
</section>
'''
    s = page_head(lang, path, f"{iu('saved_title', lang)} · Mednomics", iu("saved_sub", lang), f"{SITE}/assets/og-default.png", [], "website") + body + page_foot(lang, path)
    s = s.replace('content="index,follow,max-image-preview:large"', 'content="noindex"')
    emit(path, lang, s)


# ───────────────────────── 첫 화면 블록 ─────────────────────────
HU = {
    "today_lbl": ("오늘의 브리핑", "Today's brief"), "all": ("전체 {n}건 보기", "All {n} items"),
    "numbers": ("숫자로 보는 의료산업", "Healthcare in numbers"), "more_num": ("숫자 전체와 출처 →", "All numbers and sources →"),
    "cal": ("다가오는 일정", "Coming up"), "more_cal": ("일정 전체 →", "Full calendar →"),
    "map": ("산업 지도", "Industry map"), "map_sub": ("돈이 어디서 벌리고 어디로 흐르는지, 아홉 갈래로 나눠 봅니다.", "Nine segments: where the money is made and where it flows."),
    "map_go": ("산업 지도 보기 →", "Open the industry map →"),
    "links": ("링크 허브", "Link hub"), "links_sub": ("정부 발표, 통계, 공시, 국회, 협회, 의료 전문지, 해외 소식까지 46곳.", "46 sources: government, statistics, filings, legislature, associations, trade press and global."),
    "links_go": ("링크 허브 열기 →", "Open the link hub →"),
}


def hu(k, lang, **kw):
    v = HU[k][0 if lang == "ko" else 1]
    for a, b in kw.items():
        v = v.replace("{" + a + "}", str(b))
    return v


def home_blocks(lang, brief, nums, cal, ind):
    d = brief["date"]
    lis = "".join(f'<li><a href="news/{d}.html#n{it["n"]}"><span class="cat {CATS.get(it["cat"], "c-etc")}">{E(L(it, "cat", lang))}</span><b>{E(L(it, "title", lang))}</b></a></li>'
                  for it in brief["items"][:5])
    today = f'''<!--APP:TODAY-->
<section class="sec today-sec"><div class="today-card">
  <p class="tc-top"><span class="tc-lbl">{hu('today_lbl', lang)}</span><span class="tc-date">{kdate(d, lang)}</span></p>
  <h2><a href="news/{d}.html">{E(L(brief, "headline", lang))}</a></h2>
  <p class="tc-one">{E(L(brief, "oneline", lang))}</p>
  <ol class="headlines dark">{lis}</ol>
  <p class="tc-act"><a class="btn solid" href="news/{d}.html">{hu('all', lang, n=len(brief["items"]))}</a><a class="btn" href="news/">{nu('archive', lang)}</a></p>
</div></section>
<!--/APP:TODAY-->'''
    dash = f'''<!--APP:DASH-->
<section class="sec wide dash">
  <div class="dash-col">
    <p class="label">Numbers</p>
    <h2>{hu('numbers', lang)}</h2>
    {numbers_html(nums, lang, 4)}
    <p class="more"><a href="insight/">{hu('more_num', lang)}</a></p>
  </div>
  <div class="dash-col">
    <p class="label">Calendar</p>
    <h2>{hu('cal', lang)}</h2>
    {cal_html(cal, lang, 4)}
    <p class="more"><a href="insight/">{hu('more_cal', lang)}</a></p>
  </div>
</section>
<!--/APP:DASH-->'''
    segs = "".join(f'<a class="hub" href="insight/industry.html#{s["id"]}"><b>{E(L(s, "name", lang))}</b></a>' for s in ind["segments"])
    maps = f'''<!--APP:MAP-->
<section class="sec" style="padding-top:0">
  <p class="label">Industry</p>
  <h2>{hu('map', lang)}</h2>
  <p class="lede">{hu('map_sub', lang)}</p>
  <div class="hubs compact">{segs}</div>
  <p class="more"><a href="insight/industry.html">{hu('map_go', lang)}</a></p>
  <p class="label" style="margin-top:44px">Links</p>
  <h2>{hu('links', lang)}</h2>
  <p class="lede">{hu('links_sub', lang)}</p>
  <p class="more"><a href="links/">{hu('links_go', lang)}</a></p>
</section>
<!--/APP:MAP-->'''
    return {"TODAY": today, "DASH": dash, "MAP": maps}


def fill_home(src, blocks):
    for k, v in blocks.items():
        src = re.sub(rf"<!--APP:{k}-->.*?<!--/APP:{k}-->", lambda m: v, src, flags=re.S)
    return src


# ───────────────────────── 영어판 ─────────────────────────
def en_normalize(s):
    """번역 전에 날짜·분 같은 반복 표현을 영어로 바꾼다."""
    def ymd(m):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{MON[mo - 1]} {d}, {y}"
    s = re.sub(r"읽는 시간 약 (\d+)분", r"\1 min read", s)
    s = re.sub(r"(\d{4})\. (\d{1,2})\. (\d{1,2})(?: \([월화수목금토일]\))?", ymd, s)
    s = re.sub(r" · (\d+)분</span>", r" · \1 min</span>", s)
    return s


ASSET_RE = re.compile(r'\b(href|src)="([^"#?:]*?)((?:[?#][^"]*)?)"')


def en_paths(s, path):
    """영어판으로 옮긴 페이지의 상대 주소: 영어판이 있는 페이지는 그대로, 나머지(자산 등)는 한 단계 위로."""
    base = posixpath.dirname(path)

    def fix(m):
        attr, v, tail = m.group(1), m.group(2), m.group(3)
        if not v or v.startswith(("/", "data", "javascript", "mailto", "tel")):
            return m.group(0)
        target = posixpath.normpath(posixpath.join(base, v)) if v not in ("./", ".") else (base or ".")
        if target == ".":
            target = ""
        page = target
        if v.endswith("/") or target == "" or not posixpath.splitext(target)[1]:
            page = posixpath.join(target, "index.html") if target else "index.html"
        if page in EN_PAGES:
            return m.group(0)
        return f'{attr}="../{v}{tail}"'
    return ASSET_RE.sub(fix, s)


def en_jsonld(s):
    def walk(x):
        if isinstance(x, dict):
            return {k: ("en" if k == "inLanguage" else walk(v)) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str) and i18n.HANGUL.search(x) and not x.startswith("http"):
            return i18n.lookup(x, "en")
        return x

    def tr_ld(m):
        try:
            o = json.loads(m.group(1))
        except Exception:
            return m.group(0)
        return f'<script type="application/ld+json">{J(walk(o))}</script>'
    return re.sub(r'<script type="application/ld\+json">(.*?)</script>', tr_ld, s, flags=re.S)


def en_urls(s, path):
    ko, en = url_of(path, "ko"), url_of(path, "en")
    s = s.replace(f'<link rel="canonical" href="{ko}">', f'<link rel="canonical" href="{en}">')
    s = s.replace(f'<meta property="og:url" content="{ko}">', f'<meta property="og:url" content="{en}">')
    s = s.replace('<meta property="og:locale" content="ko_KR">', '<meta property="og:locale" content="en_US">')
    s = re.sub(r'<html lang="ko">', '<html lang="en">', s, count=1)
    s = s.replace('content="닥터조단">', 'content="Dr. Jordan">')
    s = s.replace('href="https://mednomics.co.kr/rss.xml"', 'href="https://mednomics.co.kr/en/news/feed.xml"')
    # JSON-LD 안의 사이트 주소를 영어판으로
    def ldurl(m):
        u = m.group(1)
        if "/assets/" in u or u.startswith(SITE + "/en/"):
            return m.group(0)
        return '"' + u.replace(SITE + "/", SITE + "/en/", 1) + '"'
    s = re.sub(r'<script type="application/ld\+json">.*?</script>', lambda m: re.sub(r'"(https://mednomics\.co\.kr/[^"]*)"', ldurl, m.group(0)), s, flags=re.S)
    return s


def make_en(path, ko_src, home_en=None):
    s = ko_src
    if home_en:
        s = fill_home(s, home_en)
    # 껍데기는 나중에 영어로 다시 끼우므로 지금은 비운다
    s = re.sub(r'<header class="bar">.*?</header>', '<header class="bar"></header>', s, count=1, flags=re.S)
    s = re.sub(r"<!--APP:TAB-->.*?<!--/APP:TAB-->", "", s, flags=re.S)
    s = re.sub(r'<nav class="fnav">.*?</nav>', '<nav class="fnav"></nav>', s, count=1, flags=re.S)
    s = re.sub(r"<!--APP:HEAD-->.*?<!--/APP:HEAD-->", "", s, flags=re.S)
    s = s.replace("<!--NEWS:START--><!--NEWS:END-->", "")
    s = re.sub(r'<html lang="ko">', '<html lang="en">', s, count=1)
    s = en_normalize(s)
    s = i18n.tr_html(s, "en")
    s = en_jsonld(s)
    s = en_urls(s, path)
    s = en_paths(s, path)
    s = apply_shell(s, "en", path, asset_prefix("en", path))
    s = s.replace('href="https://mednomics.co.kr/en/"', 'href="https://mednomics.co.kr/en/"')
    return s


# ───────────────────────── 웹앱 파일 ─────────────────────────
def icons():
    d = os.path.join(ROOT, "assets/icons")
    if os.path.exists(os.path.join(d, "maskable-512.png")):
        return
    from PIL import Image, ImageDraw
    os.makedirs(d, exist_ok=True)
    src = Image.open(os.path.join(ROOT, "assets/logo-512.png")).convert("RGB")
    # 둥근 모서리 바깥의 흰 여백을 배경색으로 채운다
    bg = (7, 9, 12)
    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 511, 511], radius=96, fill=255)
    full = Image.new("RGB", (512, 512), bg)
    full.paste(src, (0, 0), mask)
    full.save(os.path.join(d, "icon-512.png"))
    full.resize((192, 192), Image.LANCZOS).save(os.path.join(d, "icon-192.png"))
    full.resize((180, 180), Image.LANCZOS).save(os.path.join(d, "apple-180.png"))
    m = Image.new("RGB", (512, 512), bg)
    m.paste(full.resize((400, 400), Image.LANCZOS), (56, 56))
    m.save(os.path.join(d, "maskable-512.png"))


def manifests():
    for lang in ("ko", "en"):
        base = "/en/" if lang == "en" else "/"
        man = {
            "name": "Mednomics · 두 개의 차트" if lang == "ko" else "Mednomics · Two Charts",
            "short_name": "Mednomics",
            "description": ("의사가 읽는 헬스케어 산업과 돈. 오늘의 의료 뉴스, 숫자로 보는 의료산업, 산업 지도, 연재."
                            if lang == "ko" else "Korean healthcare business, read by a doctor: daily news, key numbers, industry map and analysis."),
            "lang": lang, "dir": "ltr", "id": base, "start_url": base + "?source=app", "scope": "/",
            "display": "standalone", "background_color": "#07090c", "theme_color": "#07090c",
            "icons": [{"src": "/assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "/assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
                      {"src": "/assets/icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
            "shortcuts": [{"name": "오늘의 의료 뉴스" if lang == "ko" else "Today's news", "url": base + "news/"},
                          {"name": "인사이트" if lang == "ko" else "Insight", "url": base + "insight/"},
                          {"name": "연재" if lang == "ko" else "Series", "url": base + "series/"}],
        }
        write(("en/" if lang == "en" else "") + "manifest.webmanifest", json.dumps(man, ensure_ascii=False, indent=2) + "\n")


def service_worker(pages):
    core = ["/", "/en/", "/style.css", "/protect.js", "/assets/app.js", "/assets/news.js", "/assets/search.js",
            "/assets/favicon.svg", "/assets/icons/icon-192.png", "/manifest.webmanifest", "/en/manifest.webmanifest",
            "/news/", "/en/news/", "/insight/", "/en/insight/", "/series/", "/en/series/", "/saved.html", "/en/saved.html"]
    h = hashlib.sha1()
    for p in sorted(pages):
        full = os.path.join(ROOT, p)
        if os.path.exists(full):
            h.update(open(full, "rb").read())
    for p in ("style.css", "assets/app.js", "assets/news.js", "assets/search.js", "protect.js"):
        h.update(open(os.path.join(ROOT, p), "rb").read())
    ver = h.hexdigest()[:10]
    sw = f'''/* Mednomics 설치형 웹앱 서비스 워커: 한 번 본 페이지는 인터넷이 없어도 열린다. */
const CACHE = 'mn-{ver}';
const CORE = {json.dumps(core)};
self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('mn-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
}});
self.addEventListener('fetch', e => {{
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  const url = new URL(req.url);
  if (req.mode === 'navigate' || url.pathname.endsWith('.json') || url.pathname.endsWith('.xml')) {{   // 페이지·데이터: 새 것을 먼저
    e.respondWith(fetch(req).then(res => {{
      if (res.ok) {{ const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }}
      return res;
    }}).catch(() => caches.match(req, {{ ignoreSearch: true }}).then(hit => hit || caches.match(url.pathname.startsWith('/en/') ? '/en/' : '/'))));
    return;
  }}
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {{   // 그 밖: 저장해 둔 것을 먼저
    if (res.ok) {{ const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }}
    return res;
  }})));
}});
'''
    write("sw.js", sw)
    return ver


# ───────────────────────── 사이트맵·검색 ─────────────────────────
def sitemap(ko_pages, en_pages, today):
    rows = []
    for p in sorted(set(ko_pages)):
        if p in ("404.html", "search.html", "saved.html"):
            continue
        alt = ""
        if p in en_pages:
            alt = (f'<xhtml:link rel="alternate" hreflang="ko" href="{url_of(p, "ko")}"/>'
                   f'<xhtml:link rel="alternate" hreflang="en" href="{url_of(p, "en")}"/>')
        mod = today if p in GENERATED or p == "index.html" else file_date(p)
        rows.append(f'  <url><loc>{url_of(p, "ko")}</loc><lastmod>{mod}</lastmod>{alt}</url>')
        if p in en_pages:
            rows.append(f'  <url><loc>{url_of(p, "en")}</loc><lastmod>{mod}</lastmod>{alt}</url>')
    s = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
         'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n")
    write("sitemap.xml", s)


def file_date(p):
    m = re.search(r'최종 수정 (\d{4}-\d\d-\d\d)', read(p))
    if m:
        return m.group(1)
    m = re.search(r'"dateModified":"(\d{4}-\d\d-\d\d)"', read(p))
    return m.group(1) if m else "2026-11-24"


def page_text(s):
    m = re.search(r"<main[^>]*>(.*)</main>", s, re.S)
    body = m.group(1) if m else s
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", body, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", html.unescape(body)).strip()


def search_index(lang, pages):
    out = []
    for p in sorted(pages):
        if p in ("404.html", "search.html", "saved.html"):
            continue
        full = os.path.join(ROOT, ("en/" if lang == "en" else "") + p)
        if not os.path.exists(full):
            continue
        s = open(full, encoding="utf-8").read()
        title = html.unescape(re.search(r"<title>(.*?)</title>", s, re.S).group(1)).replace(" · Mednomics", "")
        desc = re.search(r'<meta name="description" content="([^"]*)"', s)
        u = ("en/" if lang == "en" else "") + (p[:-10] if p.endswith("index.html") else p)
        out.append({"t": title, "u": u, "d": html.unescape(desc.group(1)) if desc else "", "x": page_text(s)[:1500]})
        if p == "glossary.html":
            for m in re.finditer(r'<div class="term" id="([^"]+)"><dt>(.*?)</dt><dd>(.*?)<small', s, re.S):
                out.append({"t": ("용어: " if lang == "ko" else "Term: ") + html.unescape(re.sub(r"<[^>]+>", "", m.group(2))),
                            "u": u + "#" + m.group(1), "d": html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip(), "x": ""})
    # 최신 뉴스가 맨 앞에 오도록
    news = sorted([e for e in out if "/news/2" in "/" + e["u"]], key=lambda e: e["u"], reverse=True)
    out = news + [e for e in out if e not in news]
    write(("en/" if lang == "en" else "") + "search-index.json", json.dumps(out, ensure_ascii=False, separators=(",", ":")))


# ───────────────────────── 실행 ─────────────────────────
def main():
    today = dt.date.today().isoformat()
    briefs = load_briefs()
    nums, cal = jload("_app/data/numbers.json"), jload("_app/data/calendar.json")
    ind, links = jload("_app/data/industry.json"), jload("_app/data/links.json")
    icons()

    # 영어판이 생길 페이지를 먼저 정한다(상대 주소 계산에 쓴다)
    en_briefs = [b for b in briefs if b["has_en"]]
    for p in HAND:
        if p not in NO_EN:
            EN_PAGES.add(p)
    EN_PAGES.update({"news/index.html", "news/policy.html", "insight/index.html", "insight/industry.html", "links/index.html", "saved.html"})
    EN_PAGES.update(f"news/{b['date']}.html" for b in en_briefs)

    # 1) 생성 페이지(한국어·영어)
    for lang in ("ko", "en"):
        bs = briefs if lang == "ko" else en_briefs
        asc = list(reversed(bs))
        for i, b in enumerate(asc):
            news_daily(b, asc[i - 1] if i else None, asc[i + 1] if i + 1 < len(asc) else None, lang)
            og_news(b, lang)
        news_index(briefs, lang)
        news_policy(lang)
        news_feed(briefs, lang)
        insight_index(nums, cal, ind, lang)
        industry_page(ind, lang)
        links_page(links, lang)
        saved_page(lang)

    # 2) 손으로 쓴 한국어 페이지: 껍데기 갱신(+첫 화면 블록)
    latest_ko = briefs[0]
    latest_en = en_briefs[0] if en_briefs else None
    for p in HAND:
        src = read(p)
        if p == "index.html":
            src = fill_home(src, home_blocks("ko", latest_ko, nums, cal, ind))
        pre = "/" if p == "404.html" else prefix(p)
        src = apply_shell(src, "ko", p, pre)
        write(p, src)

    # 3) 영어판
    for p in HAND:
        if p in NO_EN:
            continue
        home_en = home_blocks("en", latest_en, nums, cal, ind) if (p == "index.html" and latest_en) else None
        write("en/" + p, make_en(p, read(p), home_en))

    # 4) 웹앱 파일, 사이트맵, 검색
    manifests()
    ko_pages = set(HAND) | GENERATED
    en_pages = set(EN_PAGES)
    ver = service_worker([p for p in ko_pages] + ["en/" + p for p in en_pages])
    sitemap(ko_pages, en_pages, today)
    search_index("ko", ko_pages)
    search_index("en", en_pages)

    # 5) 번역 점검
    miss = i18n.MISSING.get("en", {})
    rows = [f"§{k} {v}" for k, v in miss.items()]
    open(os.path.join(APP, "i18n/catalog.txt"), "w", encoding="utf-8").write("\n".join(rows) + ("\n" if rows else ""))
    left = []
    for p in sorted(en_pages):
        s = read("en/" + p)
        lo = i18n.leftover(re.sub(r'<script.*?</script>', '', s, flags=re.S))
        if lo:
            left.append((p, len(lo)))
    print(f"한국어 {len(ko_pages)}쪽, 영어 {len(en_pages)}쪽, 최신 뉴스 {briefs[0]['date']}, 서비스 워커 {ver}")
    print(f"번역 필요 {len(miss)}개 → _app/i18n/catalog.txt" if miss else "번역 빠진 문장 없음")
    if left:
        print("한글이 남은 영어 페이지:", ", ".join(f"{p}({n})" for p, n in left[:12]), "…" if len(left) > 12 else "")
    if STRICT and (miss or left):
        sys.exit(1)


if __name__ == "__main__":
    main()
