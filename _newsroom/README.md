# 뉴스룸 (공개되지 않는 폴더)

밑줄로 시작하는 폴더라 GitHub Pages에 올라가도 사이트에 보이지 않습니다.

## 매일 하는 일
1. `data/YYYY-MM-DD.json` 을 하나 만든다 (기존 파일을 복사해 고치면 됨).
2. 저장소 루트에서 `python3 _newsroom/build.py` 실행.
3. 바뀐 파일을 올린다: `news/`, `index.html`, `sitemap.xml`, `search-index.json`, `assets/og/news-날짜.png`.

Claude에게 "오늘 의료 뉴스 만들어 줘"라고 하면 1~2번을 대신 하고 올릴 파일만 묶어 준다.

## JSON 항목
- `headline` 그날의 큰 제목, `oneline` 오늘의 한 줄(의견 가능)
- `items[]`: `cat`(정책·규제·개원·의원·병원·제약·바이오·의료기기·AI·학술·학회·의사와 돈·사건·사고), `title`(새로 쓴 제목), `summary`(직접 쓴 2~3문장 요약), `take`(닥터조단 한마디, 비워도 됨), `sources[]`(name, url)
- `watch[]`: 이어서 볼 것(text, 선택: url, name)

## 원칙
기사 문장·사진은 옮기지 않는다. 제목과 요약은 새로 쓴다. 출처는 언론사 이름과 원문 링크로 밝힌다. 자세한 기준은 `news/policy.html`.
