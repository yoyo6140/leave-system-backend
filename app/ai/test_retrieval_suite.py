from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.ai.retrieval import search

TEST_CASES = [
    {"question": "特休有幾天", "expect": "第 38 條"},
    {"question": "工資的定義是什麼", "expect": "第 2 條"},
    {"question": "平均工資怎麼計算", "expect": "第 2 條"},
    {"question": "每週工作時間上限幾小時", "expect": "第 30 條"},
    {"question": "加班費怎麼計算", "expect": "第 24 條"},
    {"question": "資遣費怎麼計算", "expect": "第 17 條"},
    {"question": "特別休假沒休完會怎樣", "expect": "第 38 條"},
    {"question": "童工是幾歲到幾歲", "expect": "第 44 條"},
    {"question": "產假有幾天", "expect": "第 50 條"},
    {"question": "退休金怎麼給付", "expect": "第 55 條"},
    {"question": "職業災害補償怎麼規定", "expect": "第 59 條"},
    {"question": "雇主可以不經預告終止契約的情況有哪些", "expect": "第 12 條"},
    {"question": "勞工可以不經預告終止契約的情況有哪些", "expect": "第 14 條"},
    {"question": "例假怎麼規定", "expect": "第 36 條"},
    {"question": "國定假日有規定嗎", "expect": "第 37 條"},
    {"question": "請假的法源依據是什麼", "expect": "第 43 條"},
    {"question": "工作規則要報請誰核備", "expect": "第 70 條"},
    {"question": "最低服務年限的約定條件", "expect": "第 15-1 條"},
    {"question": "離職後競業禁止最長可以約定多久", "expect": "第 9-1 條"},
    {"question": "調職有哪些限制原則", "expect": "第 10-1 條"},
    {"question": "女性勞工夜間工作有限制嗎", "expect": "第 49 條"},
    {"question": "出勤紀錄要保存多久", "expect": "第 30 條"},
    {"question": "工資多久要發一次", "expect": "第 23 條"},
    {"question": "勞工名卡要保管多久", "expect": "第 7 條"},
    {"question": "基本工資由誰決定", "expect": "第 21 條"},
]

TOP_K = 5

db = SessionLocal()

passed = 0
failed_cases = []

for case in TEST_CASES:
    results = search(db, case["question"], top_k=TOP_K)
    contents = [r["content"] for r in results]
    hit = any(case["expect"] in c for c in contents)

    if hit:
        passed += 1
        mark = "PASS"
    else:
        failed_cases.append(case)
        mark = "FAIL"

    print(f"[{mark}] {case['question']} (預期 {case['expect']})")
    if not hit:
        for i, c in enumerate(contents):
            print(f"       實際第{i+1}名: {c[:40]}")

db.close()

total = len(TEST_CASES)
print(f"\n=== 結果：{passed}/{total} 通過（top_{TOP_K} 命中率 {passed/total:.0%}） ===")
if failed_cases:
    print("未命中的題目：")
    for case in failed_cases:
        print(f"  - {case['question']}（預期 {case['expect']}）")
