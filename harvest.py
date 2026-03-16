#!/usr/bin/env python3
"""
web-content-harvester
批量采集小红书、闲鱼搜索结果，输出 CSV

用法：
  python harvest.py --platform xhs --keyword 露营装备 --pages 5
  python harvest.py --platform xianyu --keyword 复古相机 --pages 3
  python harvest.py --platform xhs --keyword 健身食谱 --pages 2 --cookie "a1=xxx; web_session=yyy"
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

# ── 依赖检查 ──────────────────────────────────────────────
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("缺少依赖，请先运行：pip install requests beautifulsoup4")
    sys.exit(1)

# ── 公共工具 ──────────────────────────────────────────────

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

CSV_FIELDS = ["标题", "正文", "评论数", "点赞数", "转发数", "链接", "平台"]


def parse_number(text) -> int:
    """把 '1.2万'、'3k'、'999+' 等格式统一转成整数"""
    if not text:
        return 0
    text = str(text).strip().replace(",", "").replace("+", "")
    if "万" in text:
        return int(float(text.replace("万", "")) * 10000)
    if "k" in text.lower():
        return int(float(text.lower().replace("k", "")) * 1000)
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums else 0


def save_csv(results: list, filepath: Path):
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f"\n✅ 已保存 {len(results)} 条数据到 {filepath}")


def print_preview(results: list, n=3):
    print(f"\n{'─'*50}")
    print(f"前 {min(n, len(results))} 条预览：")
    for i, r in enumerate(results[:n], 1):
        title = r["标题"][:30] + "…" if len(r["标题"]) > 30 else r["标题"]
        print(f"  {i}. {title} | 点赞:{r['点赞数']} | 评论:{r['评论数']} | 转发:{r['转发数']}")
    print(f"{'─'*50}")


# ── Cookie 获取引导 ────────────────────────────────────────

COOKIE_GUIDE = {
    "xhs": {
        "name": "小红书",
        "url": "https://www.xiaohongshu.com",
        "fields": "a1、web_session、webId",
    },
    "xianyu": {
        "name": "闲鱼",
        "url": "https://2.taobao.com",
        "fields": "cookie2、_tb_token_、cna",
    },
}


def guide_cookie(platform: str) -> str:
    """打印 Cookie 获取步骤，提示用户输入"""
    info = COOKIE_GUIDE[platform]
    print(f"""
{'='*55}
  {info['name']} 需要登录 Cookie 才能采集数据
{'='*55}

请按以下步骤获取 Cookie：

  1. 用 Chrome/Edge 打开 {info['url']}，确保已登录
  2. 按 F12 打开开发者工具
  3. 点击顶部 「Network（网络）」 选项卡
  4. 在网站上随便点一下（触发请求）
  5. 在左侧请求列表点任意一条 fetch 或 xhr 请求
  6. 在右侧 「Request Headers」 找到 cookie: 那行
  7. 把 cookie: 后面的内容全部复制

  【重点确认这些字段存在】：{info['fields']}

{'─'*55}""")

    cookie = input("请粘贴 Cookie（直接回车跳过，但可能采集失败）：").strip()
    return cookie


# ── 小红书采集 ─────────────────────────────────────────────

def fetch_xhs_page(keyword: str, page: int, cookie: str) -> list:
    url = "https://www.xiaohongshu.com/api/sns/web/v1/search/notes"
    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.xiaohongshu.com/",
        "Origin": "https://www.xiaohongshu.com",
        "Accept": "application/json, text/plain, */*",
        "Cookie": cookie,
    }
    params = {
        "keyword": keyword,
        "page": page,
        "page_size": 20,
        "sort": "general",
        "note_type": 0,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
    except requests.RequestException as e:
        print(f"  ⚠ 网络错误：{e}")
        return []

    if resp.status_code == 461:
        print("  ⚠ 触发验证码，请在浏览器完成验证后重新获取 Cookie")
        return []
    if resp.status_code in (401, 403):
        print("  ⚠ Cookie 无效或已过期，请重新获取")
        return []
    if not resp.ok:
        print(f"  ⚠ HTTP {resp.status_code}")
        return []

    try:
        data = resp.json()
    except Exception:
        print("  ⚠ 返回内容不是 JSON，可能被反爬拦截")
        return []

    items = []
    for note in data.get("data", {}).get("items", []):
        card = note.get("note_card", {})
        interact = card.get("interact_info", {})
        items.append({
            "标题": card.get("title", ""),
            "正文": card.get("desc", ""),
            "评论数": parse_number(interact.get("comment_count", 0)),
            "点赞数": parse_number(interact.get("liked_count", 0)),
            "转发数": parse_number(interact.get("share_count", 0)),
            "链接": f"https://www.xiaohongshu.com/explore/{note.get('id', '')}",
            "平台": "小红书",
        })
    return items


def harvest_xhs(keyword: str, pages: int, cookie: str) -> list:
    results = []
    for page in range(1, pages + 1):
        print(f"  正在采集第 {page}/{pages} 页...", end=" ")
        items = fetch_xhs_page(keyword, page, cookie)
        if not items:
            print("无数据，停止")
            break
        results.extend(items)
        print(f"获取 {len(items)} 条（累计 {len(results)} 条）")
        if page < pages:
            time.sleep(2)
    return results


# ── 闲鱼采集 ──────────────────────────────────────────────

def fetch_xianyu_page(keyword: str, page: int, cookie: str) -> list:
    url = "https://2.taobao.com/search.htm"
    headers = {
        **HEADERS_BASE,
        "Referer": "https://2.taobao.com/",
        "Cookie": cookie,
    }
    params = {
        "q": keyword,
        "s": (page - 1) * 20,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
    except requests.RequestException as e:
        print(f"  ⚠ 网络错误：{e}")
        return []

    if "请登录" in resp.text or resp.status_code in (401, 403):
        print("  ⚠ 需要登录，请更新 Cookie")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []

    # 优先尝试解析页面内嵌 JSON
    for script in soup.find_all("script"):
        text = script.string or ""
        match = re.search(r'window\.__data__\s*=\s*(\{.*?\});', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                for item in data.get("itemList", []):
                    items.append({
                        "标题": item.get("title", ""),
                        "正文": item.get("desc", "") or item.get("content", ""),
                        "评论数": parse_number(item.get("wantCount", 0)),
                        "点赞数": parse_number(item.get("collectCount", 0)),
                        "转发数": 0,
                        "链接": f"https://2.taobao.com/item.htm?id={item.get('itemId', '')}",
                        "平台": "闲鱼",
                    })
                if items:
                    break
            except Exception:
                pass

    # 备用：HTML 解析
    if not items:
        for card in soup.select(".item-list .item, .search-item, [class*='ItemCard']"):
            title_el = card.select_one(".item-title, .title, h3, h4")
            desc_el = card.select_one(".price, .item-price, .desc")
            want_el = card.select_one("[class*='want'], [class*='count']")
            link_el = card.select_one("a[href*='item']")
            title = title_el.get_text(strip=True) if title_el else ""
            if title:
                items.append({
                    "标题": title,
                    "正文": desc_el.get_text(strip=True) if desc_el else "",
                    "评论数": parse_number(want_el.get_text(strip=True)) if want_el else 0,
                    "点赞数": 0,
                    "转发数": 0,
                    "链接": link_el["href"] if link_el and link_el.get("href") else "",
                    "平台": "闲鱼",
                })

    return items


def harvest_xianyu(keyword: str, pages: int, cookie: str) -> list:
    results = []
    for page in range(1, pages + 1):
        print(f"  正在采集第 {page}/{pages} 页...", end=" ")
        items = fetch_xianyu_page(keyword, page, cookie)
        if not items:
            print("无数据，停止")
            break
        results.extend(items)
        print(f"获取 {len(items)} 条（累计 {len(results)} 条）")
        if page < pages:
            time.sleep(2.5)
    return results


# ── 主入口 ────────────────────────────────────────────────

PLATFORMS = {
    "xhs": ("小红书", harvest_xhs),
    "xianyu": ("闲鱼", harvest_xianyu),
}


def main():
    parser = argparse.ArgumentParser(
        description="批量采集小红书/闲鱼搜索结果，输出 CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python harvest.py --platform xhs --keyword 露营装备 --pages 5
  python harvest.py --platform xianyu --keyword 复古相机 --pages 3
  python harvest.py --platform xhs --keyword 健身食谱 --pages 2 --cookie "a1=xxx; web_session=yyy"
  python harvest.py --platform xhs --keyword 护肤 --pages 1 --output 护肤笔记.csv
        """,
    )
    parser.add_argument(
        "--platform", "-p",
        required=True,
        choices=list(PLATFORMS.keys()),
        help="平台：xhs（小红书）或 xianyu（闲鱼）",
    )
    parser.add_argument("--keyword", "-k", required=True, help="搜索关键词")
    parser.add_argument("--pages", "-n", type=int, default=3, help="采集页数（默认3页）")
    parser.add_argument("--cookie", "-c", default="", help="登录 Cookie（可选，不填则交互式引导）")
    parser.add_argument("--output", "-o", default="", help="输出文件名（默认自动生成）")

    args = parser.parse_args()

    platform_name, harvest_fn = PLATFORMS[args.platform]

    print(f"\n{'='*55}")
    print(f"  平台：{platform_name}")
    print(f"  关键词：{args.keyword}")
    print(f"  页数：{args.pages}")
    print(f"{'='*55}")

    # 处理 Cookie
    cookie = args.cookie
    if not cookie:
        cookie = guide_cookie(args.platform)

    if not cookie:
        print("\n⚠ 未提供 Cookie，继续尝试（可能失败）...")

    # 执行采集
    print(f"\n开始采集...\n")
    results = harvest_fn(args.keyword, args.pages, cookie)

    if not results:
        print("\n❌ 未采集到任何数据，请检查：")
        print("   1. Cookie 是否有效（重新从浏览器获取）")
        print("   2. 网络是否正常")
        print("   3. 关键词是否有搜索结果")
        sys.exit(1)

    # 保存
    output_file = args.output or f"{platform_name}_{args.keyword}.csv"
    save_csv(results, Path(output_file))
    print_preview(results)

    print(f"\n采集完成！共 {len(results)} 条数据")


if __name__ == "__main__":
    main()
