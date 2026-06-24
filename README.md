# 📚 나의 독서 DNA · Reading DNA Report

3년 반(2023–2026) 동안 쌓인 **229권의 완독 기록**과 **583개의 밑줄**을 분석해, 한 독자의 독서 취향을 시각화한 정적 웹 리포트입니다. Bookmory 앱의 개인 독서 데이터베이스를 토대로 만들었습니다.

🔗 **배포:** Netlify (정적 호스팅) · https://dh-books.netlify.app

## 배포 (GitHub 자동연동)

별도 빌드가 없는 정적 사이트라, Netlify에 GitHub 저장소를 연결하면 푸시할 때마다 자동 배포됩니다.

1. Netlify 대시보드 → **dh-books** 사이트 → **Site configuration → Build & deploy → Continuous deployment**
2. **Link repository** → GitHub의 `POGNARU/dh-books` 선택 (이미 연결돼 있으면 이 단계는 건너뜀)
3. 빌드 설정 — **Build command:** 비움 / **Publish directory:** `.` (`netlify.toml`에 이미 지정됨)
4. **Production branch** 를 `claude/vigilant-galileo-rldqcr` (현재 저장소 기본 브랜치)로 지정 → **Deploy**

> 새 사이트로 만들 경우: **Add new site → Import an existing project → GitHub → `dh-books`** 선택 후 위 3·4번 설정만 확인하면 됩니다. 빌드 명령은 없습니다.

## 무엇을 담았나

- **한눈에 보기** — 완독 권수·페이지·평균 별점 등 핵심 지표
- **장르별** 취향과 장르별 평균 별점
- **국가별 · 시대별** 분포 (세계문학 순례 지도)
- **주제별** 마음의 지형 (6갈래 테마)
- **독서 유형 비중** — 매체·창작지·동행·재독·완독·형식 (도넛 6종)
- **타임라인** — 누적 완독 곡선 / 별점 분포 / 애독 작가
- **특별한 책장** — 재독·인생책·가장 많이 밑줄 친 책
- **나의 독서 동기** — 리뷰·밑줄 근거 기반 5가지 동기 분석
- **독서 DNA** — 종합 유형과 8가지 유전자 코드
- **밑줄 친 문장들** — 데이터에서 고른 12개 인용
- **추천 10권** — 아직 서재에 없는, 취향에 맞춘 다음 책

## 데이터 갱신 방법 (앞으로 쌓이는 기록 반영)

원천 데이터는 **Bookmory 앱**이고, 이 리포트는 특정 시점 백업(`new_bookmory.db`)의 스냅샷입니다.
갱신하려면:

1. **Bookmory 앱** → 백업 내보내기 → `Database_bookmory_YYMMDD.zip` 생성
2. 그 zip을 전달 (Google Drive 업로드 등)
3. 저장소에서 한 줄 실행 → 통계 재생성 + `data.js` 재번들 + 자동 배포:
   ```bash
   python analyze.py Database_bookmory_YYMMDD.zip   # zip 또는 .db 경로
   git add -A && git commit -m "데이터 갱신" && git push   # Netlify 자동 재배포
   ```

### 무엇이 자동이고 무엇이 수동인가
| 구분 | 산출물 | 생성 방식 |
|---|---|---|
| 숫자 통계 (장르·국가·시대·별점·타임라인·도넛 등) | `data/analysis.json` | `analyze.py` — **결정론적, 매번 동일 재현** |
| 메모 인용 · 독서 동기 | `data/curation.json` | **AI 해석** — 데이터가 크게 바뀌면 다시 생성 |
| 추천 도서 10권 | `data/recommendations.json` | **AI 리서치** — 보유 목록과 대조해 다시 생성 |

> 통계만 새로고침하면 `analyze.py` 한 번으로 끝. 인용/추천까지 새로 뽑으려면 AI(김리·나무)에게 `data/quotes.json`·`data/comments.json`(갱신 시 자동 생성됨)을 근거로 다시 큐레이션을 요청하세요.

### 개인정보 경계
- 공개 저장소에는 **집계 통계와 엄선된 인용 일부**(`data/curation.json`)만 올라갑니다.
- 원본 DB(`*.db`)와 **전체 메모/리뷰 원문**(`data/quotes.json`·`data/comments.json`)은 `.gitignore`로 **커밋되지 않습니다**(필요 시 백업에서 매번 재생성).

## 파일 구조

```
index.html              리포트 (구조·디자인·SVG 차트)
data.js                 웹 임베드용 번들 (자동 생성)
analyze.py              백업 → 통계 재생성 (원-커맨드)
build_data.py           data/ JSON → data.js 번들
data/
  analysis.json         통계 (커밋)
  curation.json         인용·동기, AI (커밋)
  recommendations.json  추천 10권, AI (커밋)
  quotes.json           메모 원문 전체 (gitignore)
  comments.json         리뷰 원문 전체 (gitignore)
source/                 원본 DB 두는 곳 (gitignore)
netlify.toml            배포 설정
```

## 기술

- 의존성 없는 **단일 페이지** + 직접 제작한 **SVG/CSS 차트** (외부 차트 라이브러리 없음)
- `index.html` (구조·디자인·차트) + `data.js` (집계 데이터)
- `build_data.py` — 분석 결과(JSON)를 `data.js`로 묶는 생성기

## 데이터 처리

원본 SQLite(Sembast) DB에서 도서·메모·태그·별점·독서기간을 추출하고,
도서 메타데이터 태그를 기준으로 장르·국가·시대를 분류한 뒤 보정했습니다.
개인 식별 정보는 포함하지 않으며, 집계 수치와 본인이 남긴 인용·감상만 담았습니다.

## 만든 팀

| 역할 | 이름 |
|---|---|
| 총괄 · 데이터 분석 · 디자인 | 바다 |
| 인용 큐레이션 · 동기 분석 | 김리 |
| 도서 추천 리서치 | 나무 |
