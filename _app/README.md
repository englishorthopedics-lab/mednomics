# _app: Mednomics 빌드 (공개되지 않는 폴더)

밑줄로 시작하는 폴더라 GitHub Pages에 올라가도 사이트에는 보이지 않습니다.

## 한 번에 만들기
저장소 루트에서 `python3 _app/build.py` (Python 3.9 이상, 공유 이미지를 만들려면 Pillow).
`python3 _newsroom/build.py`도 같은 일을 합니다.

빌드가 하는 일
- 손으로 쓴 한국어 페이지(index.html, series/, topics/, trackers/, board, glossary 등)의 머리글·바닥글·하단 탭바·웹앱 태그를 새로 끼움. 본문은 건드리지 않음.
- 첫 화면의 `<!--APP:TODAY-->`, `<!--APP:DASH-->`, `<!--APP:MAP-->` 블록을 최신 뉴스·숫자·일정으로 채움.
- 뉴스(_newsroom/data), 인사이트(숫자·일정), 산업 지도, 링크 허브, 저장한 글 페이지를 한국어·영어로 만듦.
- 영어판 `/en/`을 만들고, sitemap.xml(hreflang 포함), 검색 색인(ko·en), 뉴스 RSS(ko·en), manifest, sw.js를 갱신.

## 매일 뉴스
1. `_newsroom/data/YYYY-MM-DD.json`을 만든다. 영어판도 내려면 `headline_en`, `oneline_en`, 각 소식의 `cat_en`, `title_en`, `summary_en`, `take_en`, `watch[].text_en`을 함께 넣는다. 영어 필드가 빠진 날은 한국어판만 나간다.
2. `python3 _app/build.py`
3. 바뀐 파일을 올린다(보통 news/, en/news/, index.html, en/index.html, sitemap.xml, search-index.json, en/search-index.json, sw.js, assets/og/news-날짜*.png).

## 숫자·일정·산업 지도·링크
`_app/data/numbers.json`, `calendar.json`, `industry.json`, `links.json`을 고치고 빌드한다. 숫자에는 반드시 출처(url)와 기준일(asof)을 적는다.

## 영어 번역
- 손으로 쓴 페이지는 `_app/i18n/en.txt` 사전으로 옮긴다. 한 줄에 `§아이디 번역문`. 아이디는 한국어 문단의 해시.
- 새 글을 쓰거나 한국어 문장을 고치면 빌드 끝에 "번역 필요 N개"가 뜨고 `_app/i18n/catalog.txt`에 목록이 생긴다. 그 줄들을 번역해 en.txt에 더하고 다시 빌드한다.
- 번역이 빠진 문장은 영어판에 한국어로 남으니, 올리기 전에 "번역 빠진 문장 없음"을 확인한다(`--strict`를 붙이면 빠진 게 있을 때 실패).

## 새 연재 글을 올릴 때
1. 기존 글(series/epXX-*.html)과 같은 틀로 한국어 글을 쓴다.
2. 빌드 → catalog.txt 번역 → en.txt에 추가 → 다시 빌드.
