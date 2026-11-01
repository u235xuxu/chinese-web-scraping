# 中文站点抓取实战指南 / Scraping Chinese Websites

> **一句话原理：中文站点的反爬，本质是"人在不在中国境内"和"是不是真人在用浏览器"这两个问题。**
> **One-line principle: The anti-bot systems of Chinese websites fundamentally ask two questions — "are you inside China?" and "are you a real human in a real browser?"**

[中文](#中文版) | [English](#english-version)

---

## 中文版

### 先跑一下探测脚本

在动手抓之前，先用 `site_probe.py` 确认当前环境能不能访问目标站点：

```bash
python3 site_probe.py https://www.zhihu.com https://www.baidu.com
```

它会实测一次请求，告诉你 HTTP 状态、响应体大小、解析到的 IP，以及**建议采用的策略**。

实测示例（境内网络、绕过代理）：

| 站点 | 结果 | 判定 |
|---|---|---|
| baidu.com | 200 / 200KB | OK，可直接抓取 |
| zhihu.com | 200 / 46KB | OK，可直接抓取 |
| bilibili.com | 200 / 169KB | OK，可直接抓取 |
| google.com | 超时 | FAIL — 境内直连不通，需走代理 |

**最后一行是关键**：Google 在国内直连超时是预期行为。这说明**不能一刀切**——境内站直连、境外站走代理，是两套完全不同的策略。

详见 [USAGE.md](USAGE.md)。

---

### 为什么会有这份文档

给 AI Agent 做中文互联网数据采集时，我踩过几乎所有常见的坑：代理封号、无头浏览器被识别、验证码、页面抓回来是空的。

网上流传的解决方案大多是"技巧合集"——一堆互相矛盾的 tricks。而真正有用的做法是从反爬的第一性原理反推。

这份文档记录的就是那套推导。

---

### 第一性原理：反爬到底在检测什么

中文站点的风控系统（阿里、腾讯、字节、小红书的技术栈高度同质）回答两个问题：

**问题一：你从哪里来？**
- 海外 IP → 直接拒绝或走到验证码队列
- 数据中心 IP（云服务器网段）→ 同样高度可疑
- 家宽/移动网络 IP → 相对可信

**问题二：你是不是真人？**
- 无头浏览器 → `navigator.webdriver`、缺失的插件列表、异常的 Canvas/WebGL 指纹
- 没有交互 → 鼠标轨迹、滚动模式、点击热区分布全是空白
- 请求节奏 → 稳定的固定间隔、无停顿、无停留时间

**这两条是所有规则的根。** 下面每一条规则，都是从这里推导出来的。

---

### 规则一：绝不用境外服务器代理中文站点

**推导链：**

```
中文站封海外 IP
    ↓
VPS（东京/新加坡/美西）的 IP = 海外 IP
    ↓
所有经 VPS 出海的请求，IP 层面就已经出局
    ↓
不是"成功率低"，是"几乎必然失败"
```

**实测结论：**
- 用日本 VPS 访问百度、B站、知乎、贴吧、微博、小红书、抖音 → 限流或直接封禁
- 用日本 VPS 访问 Google、Bing、DuckDuckGo → 正常（那是国际站）

**正确做法：**
- 用境内 IP 出口（你自己的办公网络、家宽、手机热点）
- 如果必须在远程机器上跑，找一个境内节点，而不是境外节点

**唯一例外：** 搜索引擎的**索引层**可以用境外。SearXNG 配置 Google/Bing 引擎走 VPS 完全没问题——那只用来拿 URL，不拿页面内容。

---

### 规则二：真实浏览器 > 无头浏览器

**推导链：**

```
反爬检测无头特征
    ↓
无头浏览器的特征无法完全伪装（即使加了 stealth 插件）
    ↓
真正不可伪装的是：真实用户的历史 cookie、扩展、指纹、行为轨迹
    ↓
所以答案不是"如何伪装无头"，而是"直接用有头的真实浏览器"
```

**常见的无头检测项：**

| 检测点 | 无头浏览器暴露什么 |
|---|---|
| `navigator.webdriver` | 标准化的 `true` |
| `navigator.plugins` | 空列表（真实 Chrome 有 PDF 插件等） |
| Canvas 指纹 | 渲染结果与真实 GPU 不一致 |
| WebGL renderer | `SwiftShader` / `llvmpipe` 等软件渲染器 |
| 窗口尺寸 | `800x600` 默认值，或与屏幕不符 |
| 交互事件 | 没有任何 `mousemove` / `scroll` 序列 |
| 时区/语言 | 与 IP 归属地矛盾 |

**关键认知：** 即使全部伪装成功，你还缺少"历史"。真实用户的浏览器有几个月甚至几年的 cookie、浏览记录、本地存储。这是无头环境最难伪造的东西。

---

### 规则三：复用已登录的浏览器会话

**推导链：**

```
登录态 = 最强的信任凭证（比任何指纹都强）
    ↓
用户自己已经登录过的站点，天然有完整凭证
    ↓
直接驱动用户真实的 Chrome，比任何模拟都有效
```

**实现方式：** 通过浏览器扩展 + WebSocket 桥接，让自动化工具接管真实的 Chrome 窗口。

例如 OpenCLI 的架构：
- Chrome 装一个扩展（Browser Bridge）
- 扩展连本地 WebSocket 服务
- CLI 通过 WebSocket 发指令，扩展在真实窗口执行
- 结果：真实 IP、真实 cookie、真实指纹、真实登录态

**这不是代理。** 代理是伪造来源，这个是直接驾驶真实的浏览器。

---

### 规则四：抓取节奏要像人

**推导链：**

```
反爬系统有行为基线
    ↓
机器特征：固定间隔、24/7 无休、无停留、无鼠标
    ↓
人的特征：间隔波动、有停顿、有滚动、有误点
    ↓
所以要主动引入这些"缺陷"
```

**具体做法：**
- 请求间隔加随机抖动（比如 2-3 秒 ± 1 秒），不要固定 sleep
- 页面打开后停留一会儿再抓，不要立刻提取
- 大批量抓取时分批，模拟"看一会儿、停一会儿"
- 不要并行开十几个请求打同一个站

**这条不是道德建议，是工程必需。** 很多站点的风控就是靠频率和规律性触发的。

---

### 规则五：遇到验证码就停

**推导链：**

```
验证码 = 风控已经判定你可疑
    ↓
继续重试 = 强化这个判定
    ↓
继续硬刚的代价：账号封禁、IP 拉黑（不可逆）
```

**正确做法：**
- 立刻停下，报告给使用者，由人决定
- 换策略（换会话、换时间、降频率），而不是换参数重试
- 如果这个站点的数据不是必需的，就放弃它

**我见过最常见的错误：** 写一个重试循环试图"扛过去"。风控系统就是为此设计的，你扛不过去，只会更快被封。

---

### 规则六：不逆向加密，让浏览器渲染

**推导链：**

```
部分站点用字体映射、JS 加密混淆内容（价格、评论数等）
    ↓
逆向这些加密方案：成本高、站点一更新就失效
    ↓
真实浏览器会正常执行 JS，渲染出明文
    ↓
所以答案是"让它执行"，不是"我来解密"
```

**判断标准：**
- 如果页面在你的真实浏览器里能看到内容 → 让自动化浏览器也执行 JS 再取 DOM
- 如果只在特定条件下才显示 → 先复现那个条件，而不是破解算法

---

### 工具优先级（按有效性排序）

| 优先级 | 方案 | 适用场景 | 为什么 |
|---|---|---|---|
| 1 | 真实浏览器 + 扩展桥接 | 已登录的站点、强风控站点 | 真实 IP + 真实登录态，不可伪造 |
| 2 | 境内机器上的真实 Chrome + CDP | 需要无人值守但仍要真实环境 | 真实环境，可自动化 |
| 3 | 官方/公开 API | 站点提供接口时 | 最稳定，不会被反爬影响 |
| 4 | 境内 IP + 请求库 | 轻量、无风控的小站 | 简单直接 |
| 5 | 境外代理 + 无头浏览器 | **不推荐用于中文站** | 上述所有问题同时出现 |

---

### 验证清单

抓完之后自查：

- [ ] 我用了境外 IP 吗？→ 用了就是错的
- [ ] 我用了无头浏览器吗？→ 用了就是错的
- [ ] 我优先试了浏览器桥接/真实会话吗？→ 应该试
- [ ] 我的请求间隔是固定值吗？→ 应该加抖动
- [ ] 我遇到过验证码还在重试吗？→ 应该停下
- [ ] 抓回来的内容是空壳吗？→ 说明 JS 没执行，不是"站点没数据"

---

### 边界与合规

这份文档是给**合法用途**的工程知识：
- 抓取公开可访问的信息
- 抓取自己的账号数据
- 授权范围内的数据采集

不适用于：
- 绕过付费墙
- 大规模爬取他人隐私数据
- 违反站点服务条款的商业性抓取
- 任何需要破解身份验证的场景

**技术可行性不等于正当性。** 这一条比上面所有规则都重要。

---

## English Version

### Why this document exists

While building AI-agent-driven data collection from the Chinese internet, I hit nearly every trap in the book: proxy bans, headless-browser detection, CAPTCHAs, and pages that came back empty.

Most solutions floating around are collections of "tricks" — often contradictory. What actually works is deriving the approach from the first principles of anti-bot systems.

This document is that derivation.

---

### Run the probe first

Before writing any scraping code, use `site_probe.py` to check whether the current environment can even reach the target:

```bash
python3 site_probe.py https://www.zhihu.com https://www.baidu.com
```

It makes one real request and reports HTTP status, body size, resolved IPs, and a **recommended strategy**.

Measured example (China network, proxy bypassed):

| Site | Result | Verdict |
|---|---|---|
| baidu.com | 200 / 200KB | OK, directly scrapable |
| zhihu.com | 200 / 46KB | OK, directly scrapable |
| bilibili.com | 200 / 169KB | OK, directly scrapable |
| google.com | timeout | FAIL — unreachable from China, needs a proxy |

**The last row is the point:** Google timing out from a China connection is expected. It proves you cannot apply a single policy — China sites run direct, overseas sites run through a proxy. Two entirely different strategies.

See [USAGE.md](USAGE.md) (Chinese) for details.

Chinese site risk-control systems (Alibaba, Tencent, ByteDance, Xiaohongshu — the tech stacks are highly similar) answer two questions:

**Question 1: Where are you coming from?**
- Overseas IP → rejected outright or sent to a CAPTCHA queue
- Datacenter IP (cloud provider ranges) → equally suspect
- Residential / mobile IP → relatively trusted

**Question 2: Are you a real human?**
- Headless browser → `navigator.webdriver`, missing plugin list, anomalous Canvas/WebGL fingerprints
- No interaction → mouse trails, scroll patterns, click heatmaps all blank
- Request rhythm → perfectly uniform intervals, no pauses, no dwell time

**These two questions are the root of everything below.** Every rule is derived from them.

---

### Rule 1: Never proxy Chinese sites through an overseas server

**Derivation:**

```
Chinese sites block overseas IPs
    ↓
Your VPS (Tokyo / Singapore / US West) has an overseas IP
    ↓
Any request egressing through that VPS is already disqualified at the IP layer
    ↓
This isn't "low success rate" — it's near-certain failure
```

**Measured results:**
- Japanese VPS → Baidu, Bilibili, Zhihu, Tieba, Weibo, Xiaohongshu, Douyin: rate-limited or blocked
- Japanese VPS → Google, Bing, DuckDuckGo: fine (those are international sites)

**What to do instead:**
- Egress from a China-based IP (your own office network, home broadband, phone hotspot)
- If you must run remotely, use a China-region node, not an overseas one

**The one exception:** the *search index layer* can run overseas. Pointing SearXNG's Google/Bing engines at a VPS is fine — that's only for getting URLs, not page content.

---

### Rule 2: Real browsers beat headless browsers

**Derivation:**

```
Anti-bot systems detect headless fingerprints
    ↓
Headless fingerprints cannot be fully spoofed (even with stealth plugins)
    ↓
What genuinely cannot be faked: a real user's cookie history, extensions, fingerprint, behavioral trail
    ↓
So the answer isn't "how to disguise headless" — it's "just use a real headed browser"
```

**Common headless detection points:**

| Detection point | What headless exposes |
|---|---|
| `navigator.webdriver` | Standardized `true` |
| `navigator.plugins` | Empty list (real Chrome has PDF plugins, etc.) |
| Canvas fingerprint | Render output inconsistent with real GPU |
| WebGL renderer | `SwiftShader` / `llvmpipe` software renderer |
| Window size | `800x600` default, or mismatched with screen |
| Interaction events | No `mousemove` / `scroll` sequences at all |
| Timezone / language | Contradicts IP geolocation |

**Key insight:** even if you spoof all of the above, you still lack *history*. A real user's browser carries months or years of cookies, browsing records, and local storage. That's the hardest thing to fake in a headless environment.

---

### Rule 3: Reuse an already-authenticated browser session

**Derivation:**

```
Login state = the strongest trust credential (stronger than any fingerprint)
    ↓
Sites the user has already logged into natively carry full credentials
    ↓
Driving the user's real Chrome beats any simulation
```

**Implementation:** a browser extension plus a WebSocket bridge, letting automation take over a real Chrome window.

For example, OpenCLI's architecture:
- A Chrome extension (Browser Bridge) is installed
- The extension connects to a local WebSocket server
- The CLI sends commands over WebSocket; the extension executes them in the real window
- Result: real IP, real cookies, real fingerprint, real login state

**This is not a proxy.** A proxy forges the origin; this drives the actual browser.

---

### Rule 4: Scrape at human pace

**Derivation:**

```
Risk-control systems maintain a behavioral baseline
    ↓
Machine signature: uniform intervals, 24/7 without rest, no dwell, no mouse
    ↓
Human signature: fluctuating intervals, pauses, scrolling, occasional misclicks
    ↓
So deliberately introduce those "flaws"
```

**In practice:**
- Add random jitter to intervals (e.g. 2–3 seconds ± 1 second), don't use fixed sleeps
- Dwell on the page before extracting, don't scrape immediately on load
- Batch large jobs — simulate "browse a while, rest a while"
- Don't fire a dozen parallel requests at the same site

**This isn't etiquette; it's an engineering requirement.** Many sites' risk control triggers on frequency and regularity alone.

---

### Rule 5: Stop when you hit a CAPTCHA

**Derivation:**

```
A CAPTCHA means risk control has already flagged you
    ↓
Retrying reinforces that flag
    ↓
The cost of pushing through: account ban, IP blacklist (irreversible)
```

**What to do:**
- Stop immediately, report to the user, let a human decide
- Change strategy (different session, different time, lower rate) — not parameters in a retry loop
- If the data isn't essential, drop the site

**The most common mistake I see:** writing a retry loop hoping to "power through." Risk-control systems are designed for exactly that. You won't outlast them — you'll just get banned faster.

---

### Rule 6: Don't reverse-engineer encryption; let the browser render

**Derivation:**

```
Some sites obfuscate content via font mapping or JS encryption (prices, comment counts)
    ↓
Reversing those schemes: high cost, breaks the moment the site updates
    ↓
A real browser executes the JS normally and renders plaintext
    ↓
So the answer is "let it run," not "let me decrypt"
```

**How to decide:**
- If the content is visible in your real browser → have the automated browser execute JS, then read the DOM
- If it only appears under specific conditions → reproduce those conditions first, don't crack the algorithm

---

### Tool priority (by effectiveness)

| Priority | Approach | Use case | Why |
|---|---|---|---|
| 1 | Real browser + extension bridge | Sites you're logged into, heavily protected sites | Real IP + real login state, unforgeable |
| 2 | Real Chrome + CDP on a China host | Unattended but still needs a real environment | Real environment, automatable |
| 3 | Official / public APIs | When the site offers one | Most stable, immune to anti-bot |
| 4 | China IP + HTTP client | Lightweight sites without protection | Simple and direct |
| 5 | Overseas proxy + headless | **Not recommended for Chinese sites** | Every problem above at once |

---

### Verification checklist

Self-check after scraping:

- [ ] Did I use an overseas IP? → If yes, wrong
- [ ] Did I use a headless browser? → If yes, wrong
- [ ] Did I try a browser bridge / real session first? → I should have
- [ ] Are my request intervals fixed? → Add jitter
- [ ] Did I keep retrying past a CAPTCHA? → Should have stopped
- [ ] Is the scraped content an empty shell? → That means JS didn't execute, not that the site has no data

---

### Scope and compliance

This is engineering knowledge for **legitimate use**:
- Scraping publicly accessible information
- Exporting your own account data
- Data collection within an authorized scope

It does not cover:
- Bypassing paywalls
- Large-scale scraping of others' private data
- Commercial scraping that violates a site's terms of service
- Any scenario requiring circumvention of authentication

**Technical feasibility is not justification.** This matters more than every rule above.

---

## License

MIT — see [LICENSE](LICENSE)

## Contributing

Corrections and additional real-world cases are welcome. If you've hit a detection vector not listed here, open an issue with:
1. The site (or its general category)
2. The symptom
3. What you tried
4. What actually worked
