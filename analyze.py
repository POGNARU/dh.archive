#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze.py — Bookmory 백업 → 독서 통계 재생성 파이프라인 (결정론적)

사용법:
    python analyze.py <백업파일>      # .zip(백업) 또는 new_bookmory.db 경로
    python analyze.py                  # 인자 없으면 ./source/new_bookmory.db 사용

하는 일:
    1) Bookmory(Sembast/SQLite) DB에서 도서·메모·태그·별점을 추출
    2) 도서 메타데이터 태그로 장르·국가·시대를 분류
    3) data/analysis.json (통계) + data/quotes.json + data/comments.json 생성
    4) build_data.py 를 호출해 data.js 재번들

주의:
    - 숫자 통계는 이 스크립트로 100% 재현됩니다.
    - 메모 인용(curation.json)·추천 도서(recommendations.json)는 AI 해석 결과라
      이 스크립트가 건드리지 않습니다. 데이터가 크게 바뀌면 그 두 파일은
      AI(김리·나무)로 다시 생성해 data/ 에 갱신하세요. (README 참고)
"""
import sqlite3, json, collections, datetime, statistics, sys, os, zipfile, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

# ----------------------------------------------------------------------------- 분류 사전
GENRE = [
    ("SF·판타지", ["SF", "판타지", "SF/판타지", "SF읽기클럽", "멀티버스", "드래곤", "장르소설"]),
    ("추리·미스터리·스릴러", ["추리", "추리/미스터리", "스릴러", "미스터리", "캐드펠"]),
    ("시·희곡", ["한국시", "외국시", "시", "희곡"]),
    ("에세이·산문", ["에세이", "한국에세이", "외국에세이", "인문에세이", "산문집", "그림에세이", "회고록"]),
    ("과학·교양과학", ["물리학", "양자역학", "과학일반", "교양과학", "자연과학", "생명과학", "과학", "과학철학", "쉽게읽는과학"]),
    ("철학·사상", ["서양철학", "교양철학", "철학일반", "서양철학의이해/서양철학사", "사회이론/사상", "기호학"]),
    ("종교·신앙", ["가톨릭", "천주교(가톨릭)", "종교", "종교/역학", "신앙", "성경", "가톨릭출판사", "수도원배경", "가톨릭배경"]),
    ("자기계발·경제경영", ["자기계발", "자기계발서", "성공/처세", "경제경영", "경제", "마케팅/세일즈", "마케팅/브랜드", "부모교육", "육아"]),
    ("독서·글쓰기", ["독서/글쓰기", "글쓰기", "독서법", "글쓰기일반", "서지/출판"]),
    ("역사", ["역사", "한국역사", "중세"]),
    ("인문·교양", ["인문학", "인문", "교양인문", "인문고전", "미술", "정치일반"]),
    ("어린이·청소년", ["어린이문학", "청소년문학", "어린이", "그림책"]),
    ("고전문학", ["고전", "고전문학", "서양고전문학", "세계의문학", "서양근대문학", "현대고전", "서양현대고전", "인문고전"]),
    ("소설(일반·문학)", ["소설/시/희곡", "한국소설", "영미소설", "영미장편소설", "독일소설", "프랑스소설", "러시아소설",
        "일본소설", "이탈리아소설", "스페인문학", "아일랜드문학", "북유럽소설", "미국문학", "영국문학", "기타국가소설",
        "한국단편소설", "한국장편소설", "독일문학", "러시아문학", "세계각국소설", "세계의소설", "세계문학", "역사소설",
        "영화소설", "테마소설", "테마문학", "어른을위한동화/우화", "작품집"]),
]
NAT = [
    ("미국", ["미국문학"]),
    ("영국", ["영국문학"]),
    ("독일", ["독일소설", "독일문학", "괴테", "요한볼프강폰괴테", "헤르만헤세"]),
    ("프랑스", ["프랑스소설", "알베르카뮈", "생텍쥐페리", "로랑스드빌레르"]),
    ("러시아", ["러시아소설", "러시아문학", "톨스토이"]),
    ("일본", ["일본소설"]),
    ("이탈리아", ["이탈리아소설", "카를로로벨리"]),
    ("스페인", ["스페인문학"]),
    ("아일랜드", ["아일랜드문학", "클레어키건"]),
    ("북유럽", ["북유럽소설"]),
    ("영미(영·미)", ["영미소설", "영미장편소설"]),
    ("기타·세계", ["기타국가소설", "세계각국소설", "세계의소설", "세계문학", "외국에세이", "외국시", "원서"]),
    ("한국", ["한국소설", "한국에세이", "한국단편소설", "한국장편소설", "한국시", "한국역사", "국내도서",
        "한겨레", "경향신문", "조선일보", "동아일보", "중앙일보"]),
]
CLUBS = ["독서모임", "도란도란", "제스트", "책방기억의숲", "TWI", "루미랑", "월요낭독", "SF읽기클럽",
         "클럽필라멘트", "작가살롱", "인사이트세미나", "함께읽기", "낭독"]
GIFT = ["선물", "선물하기", "친구선물", "클북선물", "연인선물", "생일/축하", "응원/위로"]
REC = ["추천", "미디어추천", "추천받은책", "베스트셀러", "SNS핫", "YES24올해의책"]
LIB = ["도서관책"]
WRITE = ["글쓰기", "필사", "독서법", "창작자루틴", "작가살롱", "글쓰기일반", "독서/글쓰기"]
NAMEFIX = {"헤르만헤세": "헤르만 헤세", "클레어키건": "클레어 키건", "앤디위어": "앤디 위어",
           "카를로로벨리": "카를로 로벨리", "엘리스피터스": "엘리스 피터스", "에밀리브론테": "에밀리 브론테",
           "루이자메이올콧": "루이자 메이 올콧", "테드창": "테드 창"}


def classify_genre(tags):
    ts = set(tags)
    for name, keys in GENRE:
        if ts & set(keys):
            return name
    return "기타·미분류"


def classify_nat(tags, translators):
    ts = set(tags)
    for name, keys in NAT:
        if ts & set(keys):
            return name
    return "기타·세계" if translators else "한국"


def classify_era(tags):
    ts = set(tags)
    if ts & {"중세", "캐드펠", "수도원배경"}:
        return "중세·근세"
    if ts & {"서양고전문학", "고전문학", "서양근대문학", "톨스토이", "괴테", "요한볼프강폰괴테",
             "셰익스피어", "루이자메이올콧", "에밀리브론테", "생텍쥐페리"}:
        return "근대 고전(~1945)"
    if ts & {"현대고전", "서양현대고전", "세계의문학", "알베르카뮈", "헤르만헤세", "도리스레싱"}:
        return "20세기 고전"
    if ts & {"고전", "인문고전"}:
        return "고전(시대미상)"
    return "현대(전후~현재)"


# ----------------------------------------------------------------------------- DB 입력
def resolve_db(arg):
    """zip이면 new_bookmory.db 를 임시 추출, db면 그대로 사용."""
    if arg and arg.lower().endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="bookmory_")
        with zipfile.ZipFile(arg) as z:
            member = next((m for m in z.namelist() if m.endswith("new_bookmory.db")), None)
            if not member:
                sys.exit("zip 안에서 new_bookmory.db 를 찾지 못했습니다.")
            z.extract(member, tmp)
            return os.path.join(tmp, member)
    if arg:
        return arg
    default = os.path.join(HERE, "source", "new_bookmory.db")
    if os.path.exists(default):
        return default
    sys.exit("DB 경로를 인자로 주거나 ./source/new_bookmory.db 에 두세요.\n예) python analyze.py Database_bookmory_YYMMDD.zip")


def load_store(cur, store):
    cur.execute("SELECT key,value FROM entry WHERE store=? AND (deleted IS NULL OR deleted=0)", (store,))
    out = {}
    for k, v in cur.fetchall():
        try:
            out[str(k)] = json.loads(v)
        except Exception:
            out[str(k)] = v
    return out


def quill_text(n):
    raw = n.get("content_quill") or n.get("book_content") or ""
    try:
        return "".join(x.get("insert", "") for x in json.loads(raw)).strip()
    except Exception:
        return str(raw).strip()


def yr(ms):
    return datetime.datetime.utcfromtimestamp(ms / 1000).year if ms else None


def ym(ms):
    if not ms:
        return None
    d = datetime.datetime.utcfromtimestamp(ms / 1000)
    return f"{d.year}-{d.month:02d}"


# ----------------------------------------------------------------------------- 분석
def analyze(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    books = load_store(cur, "books")
    colls = load_store(cur, "collections")
    notes = load_store(cur, "notes")

    collname = {k: v.get("name") for k, v in colls.items()}
    for k, v in colls.items():
        if v.get("temp_key"):
            collname[str(v["temp_key"])] = v.get("name")

    recs = []
    for k, b in books.items():
        reads = b.get("reads", []) or []
        tags = [t.lstrip("#") for t in (b.get("tags") or "").split()]
        stars = [r.get("star") for r in reads if r.get("star")]
        recs.append(dict(
            id=k, title=b.get("title"), author=b.get("author"),
            authors=b.get("authors") or [], translators=b.get("translators") or [],
            publisher=b.get("publisher"), total_page=b.get("total_page") or 0,
            book_type=b.get("book_type"), wishlist=b.get("wishlist", False), tags=tags,
            collections=[collname.get(str(c), str(c)) for c in (b.get("collection_keys") or [])],
            statuses=[r.get("status") for r in reads],
            n_reads=len([r for r in reads if r.get("status") == "DONE"]),
            max_star=max(stars) if stars else None,
            comments=[(r.get("comment") or "").strip() for r in reads if (r.get("comment") or "").strip()],
            last_done=b.get("last_read_done_date"),
        ))

    done = [r for r in recs if any(s == "DONE" for s in r["statuses"])]
    for r in done:
        r["g"] = classify_genre(r["tags"])
        r["nat"] = classify_nat(r["tags"], r["translators"])
        r["era"] = classify_era(r["tags"])
    N = len(done)

    # 메모(하이라이트) → 인용/주석 통계
    byid = {r["id"]: r for r in done}
    quotes, comments = [], []
    for n in notes.values():
        bid = str(n.get("bid"))
        if bid in byid:
            t = quill_text(n)
            if 8 <= len(t) <= 200:
                quotes.append({"bid": bid, "title": byid[bid]["title"], "text": t,
                               "like": n.get("like", False), "page": n.get("page")})
    for r in done:
        for c in r["comments"]:
            if len(c) > 10:
                comments.append({"title": r["title"], "star": r["max_star"], "text": c,
                                 "genre": r["g"], "nat": r["nat"]})
    npb = collections.Counter(q["bid"] for q in quotes)

    def dist(key):
        return [{"name": k, "value": v} for k, v in collections.Counter(r[key] for r in done if r.get(key)).most_common()]

    def has(r, keys):
        return bool(set(r["tags"]) & set(keys))

    # 저자(정규화)
    ac = collections.Counter()
    for r in done:
        seen = set()
        for a in (r["authors"] or [r["author"]]):
            if a:
                a2 = a.replace(" ", "")
                if a2 not in seen:
                    ac[a2] += 1
                    seen.add(a2)

    # 타임라인
    yc, mc = collections.Counter(), collections.Counter()
    for r in done:
        d = r.get("last_done")
        if yr(d):
            yc[yr(d)] += 1
        if ym(d):
            mc[ym(d)] += 1
    months, cum, monthly = sorted(mc), 0, []
    for m in months:
        cum += mc[m]
        monthly.append({"name": m, "month": mc[m], "cum": cum})

    FIC = {"소설(일반·문학)", "고전문학", "SF·판타지", "추리·미스터리·스릴러", "시·희곡", "어린이·청소년"}
    gstar = collections.defaultdict(list)
    for r in done:
        if r["max_star"]:
            gstar[r["g"]].append(r["max_star"])

    A = {
        "summary": {
            "total_books": len(recs), "done": N,
            "unfinished": len([r for r in recs if not r["wishlist"] and not any(s == "DONE" for s in r["statuses"])]),
            "wishlist": len([r for r in recs if r["wishlist"]]),
            "pages": sum(int(r["total_page"]) for r in done if r.get("total_page")),
            "avg_star": round(statistics.mean([r["max_star"] for r in done if r["max_star"]]), 2),
            "translated": len([r for r in done if r["nat"] != "한국"]),
            "korean": len([r for r in done if r["nat"] == "한국"]),
            "rereads": len([r for r in done if r["n_reads"] > 1]),
            "notes_total": len(quotes), "annotated_books": len(set(q["bid"] for q in quotes)),
            "club_books": sum(1 for r in done if has(r, CLUBS)),
        },
        "genre": dist("g"), "nationality": dist("nat"), "era": dist("era"),
        "book_type": [{"name": {"paperBook": "종이책", "eBook": "전자책", "hardCover": "양장본"}.get(k, k), "value": v}
                      for k, v in collections.Counter(r["book_type"] for r in done).most_common()],
        "stars": [{"name": str(k), "value": v} for k, v in sorted(collections.Counter(r["max_star"] for r in done if r["max_star"]).items())],
        "yearly": [{"name": str(k), "value": yc[k]} for k in sorted(yc)],
        "monthly": monthly,
        "top_authors": [{"name": NAMEFIX.get(k, k), "value": v} for k, v in ac.most_common(14) if v >= 2 and k != "이재호"][:12],
        "top_publishers": [{"name": k, "value": v} for k, v in collections.Counter(r["publisher"] for r in done if r.get("publisher")).most_common(12)],
        "rereads": [{"title": r["title"], "n": r["n_reads"], "author": r["author"]}
                    for r in sorted(done, key=lambda r: r["n_reads"], reverse=True) if r["n_reads"] > 1],
        "life_books": [r["title"] for r in done if "인생책" in r["collections"]],
        "most_annotated": [{"title": byid[b]["title"], "n": n, "author": byid[b]["author"]} for b, n in npb.most_common(10)],
        "motivation": {
            "club": sum(1 for r in done if has(r, CLUBS)),
            "classics": sum(1 for r in done if r["era"] != "현대(전후~현재)"),
            "translated": len([r for r in done if r["nat"] != "한국"]),
            "gift": sum(1 for r in done if has(r, GIFT)),
            "recommend": sum(1 for r in done if has(r, REC)),
            "library": sum(1 for r in done if has(r, LIB)),
            "writing": sum(1 for r in done if has(r, WRITE)),
            "science": sum(1 for r in done if r["g"] == "과학·교양과학"),
            "religion": sum(1 for r in done if r["g"] == "종교·신앙"),
        },
        "five_star": [r["title"] for r in done if r["max_star"] == 5.0],
        "fiction": {"fiction": sum(1 for r in done if r["g"] in FIC), "nonfiction": sum(1 for r in done if r["g"] not in FIC)},
        "genre_avg_star": sorted(
            [{"name": g, "avg": round(statistics.mean(v), 2), "n": len(v)} for g, v in gstar.items() if len(v) >= 4],
            key=lambda x: -x["avg"]),
    }

    json.dump(A, open(os.path.join(DATA, "analysis.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(quotes, open(os.path.join(DATA, "quotes.json"), "w"), ensure_ascii=False)
    json.dump(comments, open(os.path.join(DATA, "comments.json"), "w"), ensure_ascii=False)
    con.close()
    return A


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    db = resolve_db(arg)
    print("DB:", db)
    A = analyze(db)
    s = A["summary"]
    print(f"완독 {s['done']}권 / 전체 {s['total_books']}권 · 번역 {s['translated']} · 재독 {s['rereads']} · 별평균 {s['avg_star']}")
    print("→ data/analysis.json, data/quotes.json, data/comments.json 갱신 완료")
    # data.js 재번들
    rc = subprocess.call([sys.executable, os.path.join(HERE, "build_data.py")])
    sys.exit(rc)
