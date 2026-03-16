---
name: web-content-harvester
description: >
  批量爬取指定网站的搜索结果并提取结构化内容，输出 CSV 文件。当用户给出网址（URL）、搜索关键词和页数 N，
  在该网站搜索关键词，翻取前 N 页结果，提取每条内容的标题、正文、评论数、点赞数和转发数。
  主要支持小红书、闲鱼，也支持通用网站。会引导用户获取并填写 Cookie。
  触发词：搜索网站内容、批量采集、爬取、抓取帖子/笔记/商品/评论、提取点赞转发、内容采集、小红书采集、闲鱼采集。
  即使用户只说"帮我抓取小红书的 XX"或"爬一下闲鱼 XX"，也要立即使用此 skill。
---

# Web Content Harvester

批量采集网站搜索结果，提取标题、正文、评论数、点赞数、转发数，输出 CSV。

## 执行流程

### 第一步：识别平台并检查 Cookie

根据 URL 或用户描述判断平台：

| 平台 | 识别关键词 | 是否需要 Cookie |
|------|-----------|--------------|
| 小红书 | xiaohongshu.com、小红书、红书、xhs | **必须** |
| 闲鱼 | xianyu.taobao.com、闲鱼 | **必须** |
| 通用网站 | 其他 URL | 视情况 |

**如果需要 Cookie，立即引导用户获取**（见"Cookie 获取指南"章节），不要跳过这一步直接运行脚本。

---

### 第二步：Cookie 获取指南

当平台需要登录时，向用户说明以下步骤，并等待他们提供：

```
这个平台需要你的登录 Cookie 才能正常采集。请按以下步骤操作：

1. 用 Chrome/Edge 浏览器打开对应网站，确保你已登录
2. 按 F12 打开开发者工具
3. 点击顶部的「Network（网络）」选项卡
4. 在网站上随便点一下（触发一个请求）
5. 在请求列表里点击任意一条（选 document 或 xhr 类型的）
6. 在右侧找到「Request Headers（请求标头）」
7. 找到「Cookie:」那一行，把它后面的内容全部复制给我

【小红书重点关注的字段】：a1、web_session、webId
【闲鱼重点关注的字段】：cookie2、_tb_token_、cna、sgcookie
```

获取到 Cookie 后，将其存入脚本的 `HEADERS["Cookie"]` 字段。

---

### 第三步：编写采集脚本

根据平台选择对应的专用脚本（详见 `references/platform-patterns.md`）。

**通用脚本结构**（所有平台都基于此）：

```python
import requests
import csv
import json
import time
import re
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cookie": "USER_COOKIE_HERE",  # 替换为用户提供的 Cookie
}

def parse_number(text: str) -> int:
    """处理 '1.2万'、'3k'、'999+' 等格式"""
    if not text:
        return 0
    text = str(text).strip().replace(",", "").replace("+", "").replace("万", "0000")
    if "k" in text.lower():
        return int(float(text.lower().replace("k", "")) * 1000)
    nums = re.sub(r"[^\d.]", "", text)
    try:
        return int(float(nums)) if nums else 0
    except:
        return 0

def save_csv(results: list, filename: str):
    if not results:
        print("没有采集到数据")
        return
    fieldnames = ["标题", "正文", "评论数", "点赞数", "转发数", "链接", "平台"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig 确保 Excel 正确显示中文
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"已保存 {len(results)} 条数据到 {filename}")

def harvest(keyword: str, pages: int, platform: str) -> list:
    results = []
    for page in range(1, pages + 1):
        page_results = fetch_page(keyword, page)
        results.extend(page_results)
        print(f"第 {page}/{pages} 页：获取 {len(page_results)} 条，累计 {len(results)} 条")
        time.sleep(2)  # 礼貌延迟
    return results
```

---

### 第四步：执行脚本

将脚本保存为 `harvest_script.py`，填入用户的 Cookie，然后执行：

```bash
pip install requests beautifulsoup4 playwright -q
python harvest_script.py
```

如需 Playwright（动态渲染页面）：
```bash
pip install playwright -q
playwright install chromium
python harvest_script.py
```

---

### 第五步：输出 CSV 结果

脚本执行成功后，汇报采集摘要：

```
采集完成！
━━━━━━━━━━━━━━━━━━━━
平台：小红书
关键词：{keyword}
共采集：{total} 条
文件：harvest_{keyword}.csv
━━━━━━━━━━━━━━━━━━━━
前3条预览：
1. 标题: xxx | 点赞: 1234 | 评论: 56
2. 标题: yyy | 点赞: 890 | 评论: 12
3. 标题: zzz | 点赞: 567 | 评论: 34
```

---

## 常见问题处理

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 返回空结果 | Cookie 过期 | 重新获取 Cookie |
| 返回登录页 | Cookie 字段不完整 | 确认复制了完整的 Cookie 行 |
| 403/429 错误 | 请求过快/被封 | 增大 `time.sleep(5)`，减少页数 |
| 数据全为 0 | 选择器变化 | 用 F12 重新分析页面结构 |
| JS 未渲染 | 动态页面 | 改用 Playwright 方案 |
| Excel 显示乱码 | 编码问题 | 确认使用 `utf-8-sig` 编码 |
