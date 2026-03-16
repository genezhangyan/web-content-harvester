# 平台专用解析模式

---

## 小红书 (xiaohongshu.com)

小红书为 React SPA，搜索结果通过 API 接口返回 JSON，**不需要解析 HTML**，直接调用接口更可靠。

### 搜索 API 接口

```
GET https://www.xiaohongshu.com/api/sns/web/v1/search/notes
参数：
  keyword: 搜索词
  page: 页码（从1开始）
  page_size: 每页数量（建议20）
  sort: 按相关性=general，按最新=time_descending，按最热=popularity_descending
```

### 完整脚本

```python
import requests
import csv
import time
import re
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.xiaohongshu.com/",
    "Origin": "https://www.xiaohongshu.com",
    "Accept": "application/json, text/plain, */*",
    "Cookie": "USER_COOKIE_HERE",  # 必填，需要 a1、web_session 字段
}

def parse_number(text):
    if not text:
        return 0
    text = str(text).strip().replace(",", "").replace("+", "")
    if "万" in text:
        return int(float(text.replace("万", "")) * 10000)
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums else 0

def fetch_xhs_page(keyword: str, page: int) -> list:
    url = "https://www.xiaohongshu.com/api/sns/web/v1/search/notes"
    params = {
        "keyword": keyword,
        "page": page,
        "page_size": 20,
        "sort": "general",
        "note_type": 0,
    }
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)

    if resp.status_code == 461:
        print("⚠️  需要验证码，请在浏览器中完成验证后重新获取 Cookie")
        return []
    if resp.status_code == 401:
        print("⚠️  Cookie 已过期或无效，请重新获取")
        return []

    resp.raise_for_status()
    data = resp.json()

    items = []
    for note in data.get("data", {}).get("items", []):
        note_card = note.get("note_card", {})
        interact = note_card.get("interact_info", {})
        items.append({
            "标题": note_card.get("title", ""),
            "正文": note_card.get("desc", ""),
            "评论数": parse_number(interact.get("comment_count", 0)),
            "点赞数": parse_number(interact.get("liked_count", 0)),
            "转发数": parse_number(interact.get("share_count", 0)),
            "链接": f"https://www.xiaohongshu.com/explore/{note.get('id', '')}",
            "平台": "小红书",
        })
    return items

def harvest_xhs(keyword: str, pages: int, output_file: str = None):
    if not output_file:
        output_file = f"小红书_{keyword}.csv"

    results = []
    for page in range(1, pages + 1):
        page_results = fetch_xhs_page(keyword, page)
        if not page_results:
            print(f"第 {page} 页无数据，停止采集")
            break
        results.extend(page_results)
        print(f"第 {page}/{pages} 页：{len(page_results)} 条，累计 {len(results)} 条")
        time.sleep(2)

    if results:
        import csv
        with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["标题", "正文", "评论数", "点赞数", "转发数", "链接", "平台"])
            writer.writeheader()
            writer.writerows(results)
        print(f"\n✅ 已保存 {len(results)} 条到 {output_file}")
    return results

if __name__ == "__main__":
    harvest_xhs("KEYWORD", PAGES)
```

### Cookie 关键字段
- `a1`：设备指纹，**最重要**
- `web_session`：登录 Session
- `webId`：用户 ID

---

## 闲鱼 (xianyu.taobao.com / 2.taobao.com)

闲鱼搜索通过淘宝的搜索系统，需使用特定的 API 端点。

### 搜索接口

```
POST https://h5api.m.taobao.com/h5/mtop.taobao.idle.pc.search/1.0/
参数（form data）：
  q: 搜索词
  page: 页码
  sortValue: 排序（空=综合, realTime=最新）
  status: 状态（1=在售）
```

### 完整脚本

```python
import requests
import csv
import time
import re
import json
import hashlib

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://2.taobao.com/",
    "Cookie": "USER_COOKIE_HERE",  # 必填，需要 cookie2、_tb_token_、cna
}

def parse_number(text):
    if not text:
        return 0
    text = str(text).strip().replace(",", "").replace("+", "")
    if "万" in text:
        return int(float(text.replace("万", "")) * 10000)
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums else 0

def get_token_from_cookie(cookie_str: str) -> str:
    """从 Cookie 中提取 _tb_token_"""
    for part in cookie_str.split(";"):
        if "_tb_token_" in part:
            return part.split("=", 1)[1].strip()
    return ""

def fetch_xianyu_page(keyword: str, page: int, cookie: str) -> list:
    # 闲鱼需要签名，推荐使用网页版直接抓包 API
    # 方法1：使用搜索页 URL 抓取（静态部分）
    url = f"https://2.taobao.com/search.htm"
    params = {
        "q": keyword,
        "s": (page - 1) * 20,  # 偏移量
    }

    headers = {**HEADERS, "Cookie": cookie}
    resp = requests.get(url, headers=headers, params=params, timeout=15)

    if "请登录" in resp.text or resp.status_code == 401:
        print("⚠️  需要登录，请更新 Cookie")
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    # 尝试解析嵌入的 JSON 数据（闲鱼常将数据嵌入 window.__data__ 或 script 标签）
    for script in soup.find_all("script"):
        text = script.string or ""
        if "itemList" in text or "items" in text:
            try:
                # 提取 JSON 数据
                match = re.search(r'window\.__data__\s*=\s*({.*?});', text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    for item in data.get("itemList", []):
                        items.append({
                            "标题": item.get("title", ""),
                            "正文": item.get("desc", "") or item.get("content", ""),
                            "评论数": parse_number(item.get("wantCount", 0)),
                            "点赞数": parse_number(item.get("collectCount", 0)),
                            "转发数": 0,  # 闲鱼无转发
                            "链接": f"https://2.taobao.com/item.htm?id={item.get('itemId', '')}",
                            "平台": "闲鱼",
                        })
                    break
            except:
                pass

    # 如果没有解析到 JSON，尝试 HTML 解析
    if not items:
        for card in soup.select(".item-list .item, .search-item, [class*='ItemCard']"):
            title_el = card.select_one(".item-title, .title, h3, h4")
            price_el = card.select_one(".price, .item-price")
            want_el = card.select_one(".want-count, [class*='want']")
            link_el = card.select_one("a[href*='item']")

            items.append({
                "标题": title_el.get_text(strip=True) if title_el else "",
                "正文": price_el.get_text(strip=True) if price_el else "",
                "评论数": parse_number(want_el.get_text(strip=True)) if want_el else 0,
                "点赞数": 0,
                "转发数": 0,
                "链接": link_el["href"] if link_el else "",
                "平台": "闲鱼",
            })

    return [i for i in items if i["标题"]]

def harvest_xianyu(keyword: str, pages: int, cookie: str, output_file: str = None):
    if not output_file:
        output_file = f"闲鱼_{keyword}.csv"

    results = []
    for page in range(1, pages + 1):
        page_results = fetch_xianyu_page(keyword, page, cookie)
        if not page_results:
            print(f"第 {page} 页无数据，停止采集")
            break
        results.extend(page_results)
        print(f"第 {page}/{pages} 页：{len(page_results)} 条，累计 {len(results)} 条")
        time.sleep(2.5)

    if results:
        with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["标题", "正文", "评论数", "点赞数", "转发数", "链接", "平台"])
            writer.writeheader()
            writer.writerows(results)
        print(f"\n✅ 已保存 {len(results)} 条到 {output_file}")
    return results

if __name__ == "__main__":
    COOKIE = "YOUR_COOKIE_HERE"
    harvest_xianyu("KEYWORD", PAGES, COOKIE)
```

### Cookie 关键字段
- `cookie2`：设备标识，**最重要**
- `_tb_token_`：请求签名 Token
- `cna`：客户端 ID
- `sgcookie`：安全 Cookie

---

## Playwright 方案（当 requests 被反爬时）

当普通请求被拦截时，改用 Playwright 模拟真实浏览器：

```python
from playwright.sync_api import sync_playwright
import time

def fetch_with_playwright(url: str, cookie_str: str) -> str:
    """用 Playwright 获取动态渲染后的页面内容"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="zh-CN",
        )
        # 注入 Cookie
        if cookie_str:
            cookies = []
            for part in cookie_str.split(";"):
                if "=" in part:
                    name, value = part.strip().split("=", 1)
                    cookies.append({
                        "name": name,
                        "value": value,
                        "domain": ".xiaohongshu.com",  # 根据平台修改
                        "path": "/",
                    })
            context.add_cookies(cookies)

        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)  # 等待 JS 渲染
        content = page.content()
        browser.close()
    return content
```

---

## Cookie 格式说明

用户提供的 Cookie 通常是这样的格式，直接作为字符串传入即可：
```
a1=xxx; web_session=yyy; webId=zzz; ...
```

不需要解析，直接放到 `HEADERS["Cookie"]` 里。
