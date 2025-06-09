import csv
import json
import hashlib
import sys
from pathlib import Path
from AssemblyController import AssemblyController
import yaml

def load_config(config_path: Path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def hash_offset_list(offset_list):
    canonical_str = json.dumps(offset_list, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

def process_asm_file(asm_path, controller):
    with open(asm_path, 'r') as f:
        content = f.read()
    result = controller.parseAsmCodes(content)
    opcode_hash = {}
    for _, file_info in result.items():
        for opcode, offsetlist in file_info.op_asm_offset_list.items():
            opcode_hash[opcode] = hash_offset_list(offsetlist)
    return opcode_hash

def load_project_features(feature_dir: Path):
    feature_sets = {}
    for csv_file in feature_dir.glob("*.csv"):
        project = csv_file.stem
        features = {}
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) == 2:
                    opcode, hashval = row
                    features[opcode] = hashval
        feature_sets[project] = features
    return feature_sets

def classify_asm_file(asm_path: Path, all_project_features, controller):
    asm_features = process_asm_file(asm_path, controller)
    print(f"🔍 分析結果：{len(asm_features)} 個操作碼特徵")
    best_match = None
    best_score = -1

    for project, features in all_project_features.items():
        matched = 0
        total = len(features)
        #print(f"🔍 比對專案：{project}，特徵數量：{total}")
        for opcode, hashval in features.items():
            if opcode in asm_features and asm_features[opcode] == hashval:
                matched += 1
        #print(f"🔍 專案 {project} 匹配：{matched}/{total} ({matched/total*100:.2f}%)")
        if total > 0:
            similarity = matched / total
            if similarity > best_score:
                best_match = (project, similarity, matched, total)
                best_score = similarity

    return best_match

def main():
    if len(sys.argv) < 2:
        print("❌ 請提供 .asm 檔案的完整路徑作為參數。")
        sys.exit(1)

    asm_path = Path(sys.argv[1])
    if not asm_path.exists() or not asm_path.is_file():
        print(f"❌ 找不到檔案：{asm_path}")
        sys.exit(1)

    root = Path(__file__).resolve().parent
    feature_dir = root / "output" / "mini_feature"  # <-- 修改這裡
    print(f"🔍 特徵目錄：{feature_dir}")
    config_path = root / "config.yaml"

    config = load_config(config_path)
    controller = AssemblyController(
        set(config.get("branch_ops", [])),
        True,
        config.get("select_sections", [])
    )

    all_project_features = load_project_features(feature_dir)

    print(f"🔍 分析檔案：{asm_path.name}")
    try:
        result = classify_asm_file(asm_path, all_project_features, controller)
        if result and result[1] == 1.0:
            print(f"✅ 完全符合：{result[0]}")
        elif result:
            print(f"📌 最接近專案：{result[0]}")
        else:
            print("❌ 無比對結果。")
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")

if __name__ == "__main__":
    main()