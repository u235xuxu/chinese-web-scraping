#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
site_probe.py — 判断一个站点能否被正常抓取 / Check whether a site is scrapable

用法 / Usage:
    python3 site_probe.py https://www.zhihu.com
    python3 site_probe.py https://www.baidu.com https://www.bing.com

输出 / Output:
    每个站点的判定结果 + 建议采用的抓取策略
    Verdict per site + recommended scraping strategy

设计原则 / Design principle:
    不做猜测，只做实测。所有结论来自本次请求的真实响应。
    No guessing — every verdict comes from the actual response.
"""
import sys
import ssl
import socket
import time
import json
import os
import urllib.request
import urllib.error
from urllib.parse import urlparse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")

# 被普遍认为风控较严的中文站点特征
CN_STRICT_MARKERS = [
    "zhihu", "bilibili", "weibo", "xiaohongshu", "douyin", "tieba",
    "baidu", "qq.com", "weixin", "taobao", "tmall", "jd.com",
    "toutiao", "kuaishou", "douban", "csdn", "jianshu",
]

CODE_MEANING = {
    200: "正常访问 / OK",
    301: "永久重定向 / permanent redirect",
    302: "临时重定向 / temporary redirect",
    403: "被拒绝 / forbidden — 通常是反爬或地区限制",
    404: "不存在 / not found",
    429: "限流 / rate limited — 请求过快或 IP 可疑",
    500: "服务端错误 / server error",
    503: "服务不可用 / unavailable — 常出现在区域封禁",
}


def resolve_host(host):
    """解析域名，返回所有 IP / Resolve hostname to all IPs"""
    try:
        infos = socket.getaddrinfo(host, None)
        return sorted({i[4][0] for i in infos})
    except Exception as e:
        return [f"解析失败 / resolve failed: {e}"]


def is_private(ip):
    """粗判是否内网/保留地址 / rough check for private ranges"""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    return (a == 10 or a == 127 or
            (a == 192 and b == 168) or
            (a == 172 and 16 <= b <= 31) or
            (a == 169 and b == 254))


def looks_chinese_strict(host):
    h = host.lower()
    return any(m in h for m in CN_STRICT_MARKERS)


def probe(url, timeout=15):
    """实际请求一次，收集真实响应 / Make one real request, collect the response"""
    result = {
        "url": url,
        "host": "",
        "ips": [],
        "status": None,
        "final_url": None,
        "body_bytes": 0,
        "body_head": "",
        "error": None,
        "elapsed_ms": 0,
    }

    parsed = urlparse(url)
    host = parsed.hostname or ""
    result["host"] = host
    result["ips"] = resolve_host(host) if host else []

    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # 默认绕过系统代理：探测中文站时，代理本身就是失败原因之一
    # Bypass system proxy by default: for Chinese sites, the proxy is often the problem
    use_proxy = os.environ.get("PROBE_USE_PROXY", "") == "1"

    # 显式构造 opener，按需禁用代理
    # Build an explicit opener, disabling proxy when requested
    if use_proxy:
        opener = urllib.request.build_opener()
    else:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    t0 = time.time()
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(200_000)
            result["status"] = resp.status
            result["final_url"] = resp.geturl()
            result["body_bytes"] = len(body)
            result["body_head"] = body[:400].decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        result["status"] = e.code
        try:
            body = e.read(200_000)
            result["body_bytes"] = len(body)
            result["body_head"] = body[:400].decode("utf-8", "ignore")
        except Exception:
            pass
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    result["elapsed_ms"] = int((time.time() - t0) * 1000)
    return result


def judge(r):
    """基于实测结果给出策略建议 / Recommend a strategy from measured results"""
    host = r["host"]
    code = r["status"]
    body = r["body_head"]
    notes = []
    strategy = ""

    if r["error"] and code is None:
        if "timeout" in r["error"].lower() or "timed out" in r["error"].lower():
            strategy = "FAIL — 连接超时。检查网络出口是否为境内 IP"
            notes.append("超时通常意味着 IP 层被阻断 / timeout usually means IP-level blocking")
        elif "Name or service" in r["error"] or "resolve failed" in r["error"]:
            strategy = "FAIL — DNS 解析失败，站点可能不存在或 DNS 被污染"
        else:
            strategy = f"FAIL — {r['error']}"
        return strategy, notes

    if code == 200:
        strategy = "OK — 可直接抓取 / directly scrapable"
        # 判定"空壳"看的是真实响应体大小，不是前400字符
        # Judge SPA-shell by actual body size, not the 400-char preview
        if r["body_bytes"] < 5000:
            strategy = "WARN — 200 但响应体过小，可能是 JS 渲染的空壳 / likely an SPA shell"
            notes.append("需要用真实浏览器执行 JS / needs a real browser to execute JS")
        if "验证" in body or "captcha" in body.lower() or "安全验证" in body:
            strategy = "WARN — 返回了验证页 / returned a verification page"
            notes.append("风控已触发，停止重试 / risk control triggered, stop retrying")

    elif code in (301, 302, 307, 308):
        strategy = f"REDIRECT {code} — 需跟随重定向 / follow redirects"
        if r["final_url"] and r["final_url"] != r["url"]:
            notes.append(f"跳转到 / redirected to: {r['final_url']}")

    elif code == 403:
        strategy = "FAIL — 403 拒绝访问 / forbidden"
        if looks_chinese_strict(host):
            notes.append("中文强风控站点：检查是否用了境外 IP 或无头浏览器 / "
                         "strict Chinese site: check for overseas IP or headless browser")
        else:
            notes.append("可能是 UA / Referer / 地区限制 / may be UA, Referer, or geo restriction")

    elif code == 429:
        strategy = "FAIL — 429 限流 / rate limited"
        notes.append("降低频率并加随机抖动，不要重试 / slow down with jitter, do not retry")

    elif code in (500, 502, 503, 504):
        strategy = f"FAIL — {code} 服务端异常 / server-side failure"
        if code == 503 and looks_chinese_strict(host):
            notes.append("中文站 503 常等于区域封禁 / 503 on Chinese sites often means geo-block")

    else:
        strategy = f"UNKNOWN — HTTP {code}"

    # IP 层提示
    for ip in r["ips"]:
        if isinstance(ip, str) and is_private(ip):
            notes.append(f"解析到内网地址 {ip}，可能是代理/Hosts 劫持 / private IP, possible proxy or hosts hijack")
            break

    return strategy, notes


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    urls = sys.argv[1:]
    print("=" * 66)
    print("站点抓取可行性探测 / Site Scrapability Probe")
    print("=" * 66)

    for url in urls:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        r = probe(url)
        strategy, notes = judge(r)

        print(f"\n站点 / Site: {url}")
        print(f"  主机 / Host: {r['host']}")
        ips_str = ", ".join(str(x) for x in r["ips"][:4])
        print(f"  IP: {ips_str}")
        print(f"  HTTP: {r['status']}  ({CODE_MEANING.get(r['status'], '未知 / unknown')})")
        print(f"  耗时 / elapsed: {r['elapsed_ms']} ms")
        print(f"  响应大小 / size: {r['body_bytes']} bytes")
        if r["error"]:
            print(f"  错误 / error: {r['error']}")
        print(f"  >> 判定 / verdict: {strategy}")
        for n in notes:
            print(f"     - {n}")

    print("\n" + "=" * 66)
    print("提示：判定基于单次实测，不是绝对结论。")
    print("Note: verdicts come from a single request, not absolute truth.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
