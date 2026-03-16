# web-content-harvester

批量采集小红书、闲鱼搜索结果，提取标题、正文、评论数、点赞数、转发数，输出 CSV 文件。

提供两种使用方式：
- **Claude Code Skill**：在 Claude Code CLI 中自然语言触发
- **独立命令行工具**（`harvest.py`）：在 Trae、VS Code 等任意终端中直接运行

---

## 安装

```bash
npx skills add genezhangyan/web-content-harvester@web-content-harvester
```

或全局安装：

```bash
npx skills add genezhangyan/web-content-harvester@web-content-harvester -g
```

---

## 使用方法

安装后，在 Claude Code 中直接用自然语言触发：

```
帮我抓取小红书上关于露营装备的笔记，前5页
爬一下闲鱼上"复古相机"的商品，要3页
批量采集 xiaohongshu.com 的"健身食谱"内容
```

Claude 会自动识别平台、引导你获取 Cookie、生成并执行采集脚本，最终输出 CSV 文件。

---

## 功能说明

### 支持平台

| 平台 | 采集内容 | 是否需要 Cookie |
|------|---------|--------------|
| 小红书 | 标题、正文、评论数、点赞数、转发数、链接 | **必须** |
| 闲鱼 | 标题、价格/描述、想要数、链接 | **必须** |
| 通用网站 | 标题、正文、数字类字段 | 视情况 |

### 输出格式

CSV 文件（`utf-8-sig` 编码，Excel 可直接打开）：

| 字段 | 说明 |
|------|------|
| 标题 | 帖子/笔记/商品标题 |
| 正文 | 正文内容或描述 |
| 评论数 | 评论/回复数量 |
| 点赞数 | 点赞/收藏数量 |
| 转发数 | 转发/分享数量 |
| 链接 | 原文链接 |
| 平台 | 来源平台名称 |

---

## Cookie 获取方法

小红书和闲鱼需要登录 Cookie，触发 skill 后 Claude 会自动给出以下引导：

1. 用 Chrome/Edge 打开对应网站，确保已登录
2. 按 `F12` 打开开发者工具
3. 点击顶部 **Network（网络）** 选项卡
4. 在网站上随便操作一下（触发请求）
5. 点击左侧任意一条 `fetch` 或 `xhr` 类型的请求
6. 在右侧 **Request Headers** 中找到 `cookie:` 行
7. 复制完整内容粘贴给 Claude

**小红书重点字段**：`a1`、`web_session`、`webId`

**闲鱼重点字段**：`cookie2`、`_tb_token_`、`cna`

---

## 常见问题

**Q: 返回空结果怎么办？**
Cookie 可能已过期，重新获取即可。

**Q: 报 403/429 错误？**
请求频率过高，Claude 会自动调大间隔时间（默认 2 秒/页）。

**Q: Excel 打开 CSV 显示乱码？**
文件已使用 `utf-8-sig` 编码，如果仍乱码，在 Excel 中导入时选择 UTF-8 编码。

**Q: 页面是动态渲染的，抓不到内容？**
Skill 内置 Playwright 备用方案，Claude 会在检测到动态页面时自动切换。

---

## 文件结构

```
web-content-harvester/
├── SKILL.md                        # 主流程说明（Claude 读取）
├── README.md                       # 本文档
└── references/
    └── platform-patterns.md       # 各平台专用解析脚本
```

---

## 在 Trae / VS Code 等 IDE 中使用

不需要 Claude Code，直接在终端运行 `harvest.py`：

```bash
# 1. 安装依赖
pip install requests beautifulsoup4

# 2. 下载脚本
curl -O https://raw.githubusercontent.com/genezhangyan/web-content-harvester/main/harvest.py

# 3. 运行
python harvest.py --platform xhs --keyword 露营装备 --pages 5
python harvest.py --platform xianyu --keyword 复古相机 --pages 3

# 直接传 Cookie（省略交互引导）
python harvest.py --platform xhs --keyword 健身食谱 --pages 2 --cookie "a1=xxx; web_session=yyy"
```

**参数说明：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `--platform` | `-p` | 平台：`xhs`（小红书）或 `xianyu`（闲鱼） |
| `--keyword` | `-k` | 搜索关键词 |
| `--pages` | `-n` | 采集页数（默认3） |
| `--cookie` | `-c` | 登录 Cookie（不填则交互式引导） |
| `--output` | `-o` | 输出文件名（默认自动生成） |

---

## 注意事项

- 本工具仅供个人学习和研究使用
- 采集时会自动加入请求延迟，避免对服务器造成压力
- 请遵守目标网站的使用条款和 robots.txt
- Cookie 属于个人隐私信息，请勿泄露给他人
