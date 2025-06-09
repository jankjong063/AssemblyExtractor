# Assembly Feature Extractor

This project extracts opcode-offset metadata and generates SHA-256 feature hashes directly from `.asm` files inside `.7z` archives. It is primarily designed for analyzing disassembled ARM binaries for firmware classification or similarity analysis.

# Classify .asm by Feature Files (project.csv)

## Step 1:
clone git

Step 2:
cd AssemblyExtractor

## Step 3:
unzip output\mini_feature.7z to output\mini_feature dir
dir .\output\mini_feature
X:\GitHub\AssemblyExtractor\output\mini_feature

2025/06/10  上午 12:41    <DIR>          .
2025/06/10  上午 12:42    <DIR>          ..
2025/06/09  下午 10:03         2,286,609 3DRControlZeroG.csv
2025/06/09  下午 10:03         2,691,061 ACNSCM4Pilot.csv
2025/06/09  下午 10:03         3,494,250 AnyleafH7.csv
2025/06/09  下午 10:03         3,465,575 CubeRedSecondary.csv

## Step 4:
unzip example.7z to .\input\assemblies\
dir .\input\assemblies\
X:\GitHub\AssemblyExtractor\input\assemblies 的目錄

2025/06/10  上午 12:56    <DIR>          .
2025/05/14  下午 04:01    <DIR>          ..
2025/06/09  下午 11:53        30,016,929 3DRControlZeroG.asm
2025/06/09  下午 11:56        16,335,845 ACNSCM4Pilot.asm
2025/06/09  下午 11:57        26,167,153 AnyleafH7.asm
2025/01/24  下午 12:56        27,421,228 CubeRedSecondary.asm
2025/06/10  上午 12:56        21,094,767 example.7z
2025/05/10  上午 01:41        27,204,150 example.asm
2025/01/24  上午 10:54        30,617,554 unknown.asm

## Step 5: Test it
### Case 1: 有建 feature model
python3 classify_asm_by_feature.py .\input\assemblies\3DRControlZeroG.asm
🔍 特徵目錄：C:\FirmwareBirthmark\AssemblyExtractor\output\mini_feature
🔍 分析檔案：3DRControlZeroG.asm
🔍 分析結果：2003 個操作碼特徵
📌 最接近專案：3DRControlZeroG - 相似度 6.99% (150/2146)

### Case 2: 未知的firmware 沒有建 feature model
python3 classify_asm_by_feature.py .\input\assemblies\unknown.asm
🔍 特徵目錄：C:\FirmwareBirthmark\AssemblyExtractor\output\mini_feature
🔍 分析檔案：unknown.asm
🔍 分析結果：2277 個操作碼特徵
❌ 無比對結果。



