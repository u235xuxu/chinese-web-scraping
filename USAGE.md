# 用法 / Usage

## 基本探测

```bash
python3 site_probe.py https://www.zhihu.com
python3 site_probe.py https://www.baidu.com https://www.bilibili.com https://www.xiaohongshu.com
```

## 通过代理探测（默认不走代理）

脚本**默认绕过系统代理**——因为探测中文站时，代理本身就是最常见的问题来源。

需要走代理时：

```bash
PROBE_USE_PROXY=1 python3 site_probe.py https://www.google.com
```

## 实测输出示例

以下是在**境内网络、绕过代理**条件下跑出来的真实结果：

```
站点 / Site: https://www.baidu.com
  主机 / Host: www.baidu.com
  IP: 2409:8c20:6:123c:0:ff:b0f6:b2d, 36.152.44.132, 36.152.44.93
  HTTP: 200  (正常访问 / OK)
  耗时 / elapsed: 1011 ms
  响应大小 / size: 200000 bytes
  >> 判定 / verdict: OK — 可直接抓取 / directly scrapable

站点 / Site: https://www.zhihu.com
  HTTP: 200  (正常访问 / OK)
  响应大小 / size: 46566 bytes
  >> 判定 / verdict: OK — 可直接抓取 / directly scrapable

站点 / Site: https://www.bilibili.com
  HTTP: 200  (正常访问 / OK)
  响应大小 / size: 169131 bytes
  >> 判定 / verdict: OK — 可直接抓取 / directly scrapable

站点 / Site: https://www.google.com
  HTTP: None  (未知 / unknown)
  耗时 / elapsed: 30005 ms
  错误 / error: URLError: <urlopen error timed out>
  >> 判定 / verdict: FAIL — 连接超时。检查网络出口是否为境内 IP
     - 超时通常意味着 IP 层被阻断 / timeout usually means IP-level blocking
```

**注意最后一例**：Google 在国内直连超时是**预期行为**，不是脚本错误。
这恰好印证了核心原则——**境内站直连、境外站走代理，不能一刀切。**

---

## 同样的站点，走代理会怎样

```bash
PROBE_USE_PROXY=1 python3 site_probe.py https://www.baidu.com
```

在代理节点质量不佳或被分流规则拦截时，会看到：

```
HTTP: None
错误 / error: URLError: <urlopen error timed out>
>> 判定 / verdict: FAIL — 连接超时
```

**同一个站点，直连 200、走代理超时** —— 这就是"代理害的"最直接的证据。

---

## 判定的局限

这个脚本做的是**单次 HTTP 探测**，不是完整诊断。它不会：

- 执行 JavaScript（所以 SPA 站点的真实内容它看不到）
- 模拟登录态
- 规避任何风控

它只回答一个问题：**从当前网络环境、用当前配置，这个站点能不能正常拿到内容。**

答案是"能"——说明可以直接抓；答案是"不能"——说明要先修网络出口或换策略，而不是急着写解析代码。
