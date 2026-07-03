"""
自動從 Google My Maps 抓取最新 KML 資料，轉成 data.json
由 GitHub Actions 排程執行，不需要手動操作。
"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import sys
import datetime

# 你的 My Maps 地圖 ID（來自分享連結中的 mid= 參數）
MID = "1ADop55NH8z0UXBGimCIbJy5HlRH6jGE"
URL = f"https://www.google.com/maps/d/kml?mid={MID}&forcekml=1"

NS = {"kml": "http://www.opengis.net/kml/2.2"}


def fetch_kml() -> bytes:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def parse(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    cases = []
    case_id = 0

    for folder in root.findall(".//kml:Folder", NS):
        name_el = folder.find("kml:name", NS)
        layer_name = name_el.text.strip() if name_el is not None and name_el.text else "未分類"

        for pm in folder.findall("kml:Placemark", NS):
            title_el = pm.find("kml:name", NS)
            title = title_el.text.strip() if title_el is not None and title_el.text else ""

            coord_el = pm.find(".//kml:coordinates", NS)
            lat = lng = None
            if coord_el is not None and coord_el.text:
                parts = coord_el.text.strip().split(",")
                lng, lat = float(parts[0]), float(parts[1])

            data = {}
            for d in pm.findall(".//kml:ExtendedData/kml:Data", NS):
                dname = d.get("name")
                val_el = d.find("kml:value", NS)
                data[dname] = val_el.text.strip() if val_el is not None and val_el.text else ""

            photos = data.get("gx_media_links", "").split()

            case_id += 1
            cases.append({
                "id": case_id,
                "layer": layer_name,
                "title": title,
                "lat": lat,
                "lng": lng,
                "位置": data.get("位置", ""),
                "建議人": data.get("建議人", ""),
                "催辦": data.get("催辦", "0"),
                "危險": data.get("危險", "0"),
                "完成日期": data.get("完成日期", ""),
                "逾期天數": data.get("逾期天數", ""),
                "狀態": data.get("狀態", ""),
                "photos": photos,
            })

    return cases


def main():
    try:
        xml_bytes = fetch_kml()
    except Exception as e:
        print(f"抓取 KML 失敗: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        cases = parse(xml_bytes)
    except Exception as e:
        print(f"解析 KML 失敗: {e}", file=sys.stderr)
        sys.exit(1)

    if not cases:
        # 安全機制：如果這次抓到空資料（可能是權限或格式問題），
        # 不要覆蓋掉現有的 data.json，避免網站被清空。
        print("解析結果是空的，保留舊資料，不覆蓋 data.json", file=sys.stderr)
        sys.exit(1)

    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "cases": cases,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"更新完成，共 {len(cases)} 筆案件")


if __name__ == "__main__":
    main()
