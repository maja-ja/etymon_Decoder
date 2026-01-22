import json
import os
import shutil
from datetime import datetime

DB_FILE = 'etymon_database.json'
PENDING_FILE = 'pending_data.json'
BACKUP_DIR = 'backups' # 增加備份資料夾

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                print(f"❌ 錯誤：{filename} 格式損壞。")
                return None
    return None

def merge_data():
    # 1. 讀取待合併資料
    pending = load_json(PENDING_FILE)
    if not pending:
        print(f"ℹ️ 提示：{PENDING_FILE} 是空的或不存在，無需合併。")
        return

    # 2. 讀取主資料庫（若不存在則建立空串列）
    main_db = load_json(DB_FILE)
    if main_db is None and os.path.exists(DB_FILE):
        print("⚠️ 警告：主資料庫損壞，停止合併以防覆蓋。")
        return
    main_db = main_db or []

    # 3. 備份主資料庫 (安全第一！)
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(DB_FILE):
        shutil.copy(DB_FILE, f"{BACKUP_DIR}/db_backup_{timestamp}.json")

    # 確保 pending 格式統一
    if isinstance(pending, dict):
        pending = [pending]

    # 4. 開始合併邏輯 (保留你原本優良的去重邏輯)
    for new_cat in pending:
        cat_name = new_cat.get("category")
        target_cat = next((c for c in main_db if c["category"] == cat_name), None)
        
        if not target_cat:
            main_db.append(new_cat)
            print(f"➕ 已新增全新分類：{cat_name}")
        else:
            for new_group in new_cat.get("root_groups", []):
                new_roots = set(new_group["roots"])
                target_group = next((g for g in target_cat["root_groups"] 
                                   if set(g["roots"]) == new_roots), None)
                
                if not target_group:
                    target_cat["root_groups"].append(new_group)
                    print(f"  └─ 🚀 新增字根組：{', '.join(new_group['roots'])}")
                else:
                    existing_words = {v["word"] for v in target_group["vocabulary"]}
                    added_count = 0
                    for v in new_group["vocabulary"]:
                        if v["word"] not in existing_words:
                            target_group["vocabulary"].append(v)
                            existing_words.add(v["word"])
                            added_count += 1
                    print(f"  └─ 🔄 合併字根組 {', '.join(new_group['roots'])}，新增 {added_count} 單字")

    # 5. 寫回主資料庫
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(main_db, f, ensure_ascii=False, indent=2)
    
    # 6. 【重要】合併成功後，清空 Pending 檔案防止重複合併
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f) # 寫回空陣列
    
    print(f"\n✅ 合併完成！資料已儲存至 {DB_FILE}，{PENDING_FILE} 已清空。")

if __name__ == "__main__":
    merge_data()
