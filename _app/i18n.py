"""Mednomics 한국어 원본을 영어로 옮긴다 (runjisu i18n.py에서 가져와 영어 전용으로 줄임).

화면 틀(HTML)은 문단 단위로, 스크립트는 문자열 단위로 번역 사전에서 찾아 바꾼다.
사전은 src/i18n/en.txt, ja.txt 이고 한 줄에 하나씩 `§아이디 번역문` 형식이다.
아이디는 한국어 원문(공백 정리)의 해시라서, 원문을 고치면 그 문장만 다시 번역하면 된다.
`python3 i18n.py` 를 실행하면 번역이 필요한 문장 목록(src/i18n/catalog.txt)을 새로 만든다.
"""
import hashlib, html, json, os, re
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
I18N = os.path.join(ROOT, 'i18n')
HANGUL = re.compile('[가-힣ㄱ-ㆎ]')
LANGS = ['ko', 'en']
META = {
    'ko': {'label': '한국어', 'short': 'KO', 'og': 'ko_KR', 'brand': 'Mednomics', 'prefix': ''},
    'en': {'label': 'English', 'short': 'EN', 'og': 'en_US', 'brand': 'Mednomics', 'prefix': 'en/'},
}
JOSA_KEYS = {'는', '은', '가', '이', '를', '을', '와', '과', '로', '으로'}   # 스크립트의 조사 고르기 인자는 번역하지 않는다
CUR = {'lang': 'ko'}


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def kid(s):
    return hashlib.sha1(norm(s).encode('utf-8')).hexdigest()[:7]


_tr = {}
MISSING = {}


def load():
    for L in ('en',):
        d = {}
        p = os.path.join(I18N, L + '.txt')
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                if line.startswith('§'):
                    k, _, v = line[1:].rstrip('\n').partition(' ')
                    d[k] = v.replace('␣', ' ').replace('\\n', '\n')
        _tr[L] = d


def lookup(ko, lang=None):
    lang = lang or CUR['lang']
    if lang == 'ko' or not HANGUL.search(ko):
        return ko
    k = kid(ko)
    v = _tr.get(lang, {}).get(k)
    if v is None:
        MISSING.setdefault(lang, {})[k] = norm(ko)
        return ko
    return v


def brand(lang=None):
    return META[lang or CUR['lang']]['brand']


def T(ko, **kw):
    """빌드 코드 안의 문장. {brand}와 {이름} 자리를 채운다."""
    v = lookup(ko)
    kw.setdefault('brand', brand())
    for k, val in kw.items():
        v = v.replace('{' + k + '}', str(val))
    return v


# ───────── HTML: 문단(블록 안에 인라인 태그만 있는 덩어리) 단위로 ─────────
INLINE = {'a', 'b', 'strong', 'em', 'i', 'small', 'br', 'span', 'code', 'sup', 'sub', 'abbr', 'time', 'kbd', 'wbr', 'mark', 'u', 's', 'q'}
VOID = {'br', 'img', 'input', 'meta', 'link', 'hr', 'wbr', 'source', 'area', 'base', 'col', 'embed', 'param', 'track'}
ATTRS = ('alt', 'title', 'placeholder', 'aria-label', 'content', 'data-on', 'data-off', 'label')
ATTR_RE = re.compile(r'\b(' + '|'.join(ATTRS) + r')="([^"]*)"')


class _Units(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.lines = [0]
        for m in re.finditer('\n', src):
            self.lines.append(m.end())
        self.stack = [{'tag': '#', 'start': 0, 'block': False, 'ko': False, 'skip': False}]
        self.units, self.texts, self.skips = [], [], []

    def off(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self.off()
        raw = self.get_starttag_text() or ''
        parent = self.stack[-1]
        if tag not in INLINE:
            parent['block'] = True
        if tag in VOID:
            return
        skip = parent['skip'] or dict(attrs).get('lang') == 'ko' or tag in ('script', 'style')
        self.stack.append({'tag': tag, 'start': start + len(raw), 'open': start, 'block': False, 'ko': False, 'skip': skip})

    def handle_startendtag(self, tag, attrs):
        if tag not in INLINE:
            self.stack[-1]['block'] = True

    def handle_endtag(self, tag):
        if not any(n['tag'] == tag for n in self.stack[1:]):
            return
        end = self.off()
        while True:
            n = self.stack.pop()
            if n['tag'] == tag:
                break
        parent = self.stack[-1]
        if n['skip'] and not parent['skip']:
            self.skips.append((n['open'], end))
        if tag in INLINE:
            parent['ko'] |= n['ko']
            parent['block'] |= n['block']
        elif n['ko'] and not n['block'] and not n['skip']:
            self.units.append((n['start'], end))

    def handle_data(self, data):
        if HANGUL.search(data):
            st = self.off()
            n = self.stack[-1]
            n['ko'] = True
            if not n['skip']:
                self.texts.append((st, st + len(data)))


def _spans(src):
    p = _Units(src)
    p.feed(src)
    p.close()
    units = sorted(p.units)
    inside = lambda a, b: any(s <= a and b <= e for s, e in units)
    texts = [(a, b) for a, b in p.texts if not inside(a, b)]
    return units, texts, p.skips


def _swap(seg, lang):
    lead = seg[:len(seg) - len(seg.lstrip())]
    trail = seg[len(seg.rstrip()):]
    core = seg.strip()
    if not core or not HANGUL.search(core):
        return seg
    return lead + lookup(core, lang) + trail


def tr_html(src, lang):
    if lang == 'ko':
        return src
    units, texts, skips = _spans(src)
    reps = sorted(units + texts)
    out, pos = [], 0
    for a, b in reps:
        out.append(src[pos:a])
        out.append(_swap(src[a:b], lang))
        pos = b
    out.append(src[pos:])
    res = ''.join(out)

    # 남은 속성값(문단 밖에 있는 aria-label 같은 것). lang="ko" 안은 그대로 둔다
    def attr(m):
        v = m.group(2)
        if not HANGUL.search(v):
            return m.group(0)
        return f'{m.group(1)}="{html.escape(lookup(html.unescape(v), lang), quote=True)}"'
    _, _, skips2 = _spans(res)
    out, pos = [], 0
    for a, b in sorted(skips2):
        out.append(ATTR_RE.sub(attr, res[pos:a]))
        out.append(res[a:b])
        pos = b
    out.append(ATTR_RE.sub(attr, res[pos:]))
    return ''.join(out)


def html_keys(src):
    units, texts, skips = _spans(src)
    keys = [norm(src[a:b]) for a, b in units + texts]
    for m in ATTR_RE.finditer(src):
        a = m.start()
        if HANGUL.search(m.group(2)) and not any(s <= a < e for s, e in units) and not any(s <= a < e for s, e in skips):
            keys.append(norm(html.unescape(m.group(2))))
    return keys


# ───────── 남은 한글 찾기(lang="ko" 안과 스크립트는 빼고) ─────────
def leftover(page):
    units, texts, skips = _spans(page)
    found = [norm(page[a:b]) for a, b in units + texts]
    for m in ATTR_RE.finditer(page):
        if HANGUL.search(m.group(2)) and not any(s <= m.start() < e for s, e in skips):
            found.append(norm(m.group(2)))
    return found



def add(lang, ko, val):
    """데이터 파일에 이미 번역이 있는 문장(뉴스 제목 등)을 사전에 더한다."""
    if ko and val:
        _tr.setdefault(lang, {})[kid(ko)] = val


load()
