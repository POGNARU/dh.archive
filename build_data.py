#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_data.py — data/ 의 JSON들을 묶어 웹 임베드용 data.js 생성.

읽는 파일 (모두 저장소 data/ 폴더):
    - analysis.json        : 통계 (analyze.py 가 생성, 결정론적)
    - curation.json        : 메모 인용 + 독서 동기 (AI 김리 생성)
    - recommendations.json : 추천 도서 10권 (AI 나무 생성)

통계만 다시 뽑을 때는 analyze.py 가 끝에서 이 스크립트를 자동 호출합니다.
추천/인용만 바꿨을 때는 이 스크립트만 단독 실행하면 됩니다:  python build_data.py
"""
import json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load(name, default=None):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print("warn: failed", name, e)
    else:
        print("warn: missing", p)
    return default


bundle = {
    "generated": datetime.date.today().isoformat(),
    "analysis": load("analysis.json", {}),
    "recommendations": load("recommendations.json", []),
    "curation": load("curation.json", {}),
}

out = os.path.join(HERE, "data.js")
with open(out, "w", encoding="utf-8") as f:
    f.write("// 자동 생성 — analyze.py / build_data.py 로 갱신. 직접 수정 금지.\n")
    f.write("window.DATA = ")
    json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")

print("wrote", out)
print("recs:", len(bundle["recommendations"]),
      "| curation:", list(bundle["curation"].keys()) if bundle["curation"] else "none")
