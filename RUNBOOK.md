# 매일 건강정보 글 발행 절차 (workbench 브랜치)

이 브랜치(`workbench`)는 사이트 원고와 생성 도구만 담습니다. 실제 사이트는 `main` 브랜치이고 Cloudflare Pages가 main을 배포합니다.

## 구성
- `tools/titles.py <main폴더>` — 현재 발행된 제목을 주제별로 출력(중복 방지)
- `tools/build.py <main폴더> posts/<날짜>-A.json posts/<날짜>-B.json --out <출력폴더>` — 새 글 추가, 목록·주제 페이지(페이지네이션)·sitemap·rss 재생성, 글 하단 대표키워드 백링크
- `tools/check.py <출력폴더>` — 깨진 링크·noindex·백링크·금칙어·분량·유사도 검사(문제 있으면 종료코드 1)
- `briefs/WRITING_GUIDE.md` — 원고 규칙과 JSON 형식, `briefs/site.md` — 병원 사실 정보(이것만 사실로 사용)
- `allocation.json` — 하루 30편의 주제별 배분(A 15편 / B 15편)
- `posts/` — 날짜별 원고 보관

## 하루 절차
1. 날짜 = 오늘(KST, YYYY-MM-DD). main과 workbench를 각각 체크아웃.
2. `python3 tools/titles.py <main>` 결과를 작성자에게 전달.
3. 작성자 2명(A·B)이 `allocation.json` 배분대로 각 15편을 `posts/<날짜>-A.json`, `-B.json`에 작성.
   - 외부 글을 긁어와 표현만 바꾸지 않는다. 공공·학회 자료는 사실 확인용, 문장은 전부 새로 쓴다.
   - 기존 제목과 각도가 겹치지 않게. 같은 뼈대 반복 금지.
4. build → check. 문제가 있으면 해당 글을 고치거나 빼고 다시 빌드.
5. 출력 폴더 내용을 main에 그대로 덮어쓰고(.git 제외) 커밋·푸시. workbench에는 posts만 커밋·푸시.
6. 새 글 URL 하나를 열어 배포 확인.
