import json
import os

DB_FILE = 'etymon_database.json'
PENDING_FILE = 'pending_data.json'

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return None
    return None

def merge_data():
    main_db = load_json(DB_FILE) or []
    pending = load_json(PENDING_FILE)

    if not pending:
        print(f"❌ 錯誤：找不到 {PENDING_FILE} 或格式不正確。")
        return

    # 確保 pending 格式統一為串列 (如果是單一物件則包裝起來)
    if isinstance(pending, dict):
        pending = [pending]

    for new_cat in pending:
        cat_name = new_cat.get("category")
        
        # 尋找主資料庫中是否已有此分類
        target_cat = next((c for c in main_db if c["category"] == cat_name), None)
        
        if not target_cat:
            # 情況 A: 主庫沒這個分類，直接整類新增
            main_db.append(new_cat)
            print(f"➕ 已新增全新分類：{cat_name}")
        else:
            # 情況 B: 已有分類，需合併內部的 root_groups
            for new_group in new_cat.get("root_groups", []):
                new_roots = set(new_group["roots"])
                
                # 在該分類下找是否有相同的字根組
                target_group = next((g for g in target_cat["root_groups"] 
                                   if set(g["roots"]) == new_roots), None)
                
                if not target_group:
                    # 分類內沒這個字根組，直接新增
                    target_cat["root_groups"].append(new_group)
                    print(f"  └─ 🚀 新增字根組：{', '.join(new_group['roots'])}")
                else:
                    # 已有字根組，合併單字庫並去重
                    existing_words = {v["word"] for v in target_group["vocabulary"]}
                    added_count = 0
                    for v in new_group["vocabulary"]:
                        if v["word"] not in existing_words:
                            target_group["vocabulary"].append(v)
                            existing_words.add(v["word"])
                            added_count += 1
                    print(f"  └─ 🔄 已合併字根組 {', '.join(new_group['roots'])}，新增了 {added_count} 個單字")

    # 寫回檔案
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(main_db, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 合併完成！資料已儲存至 {DB_FILE}")

if __name__ == "__main__":
    merge_data()
