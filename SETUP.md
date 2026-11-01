# 环境搭建 / Setup

## 依赖 / Dependencies

无第三方依赖，Python 3.8+ 即可运行探测脚本。

No third-party dependencies. Python 3.8+ is enough for the probe script.

```bash
python3 --version   # 3.8+
```

## 克隆 / Clone

```bash
# HTTPS（若网络通畅 / if your network allows）
git clone https://github.com/u235xuxu/chinese-web-scraping.git

# SSH（推荐，不受 HTTPS 阻断影响 / recommended, unaffected by HTTPS blocking）
git clone git@github.com:u235xuxu/chinese-web-scraping.git
```

## 运行 / Run

```bash
cd chinese-web-scraping
python3 site_probe.py https://www.zhihu.com
```

## 网络前提 / Network prerequisites

探测脚本默认绕过系统代理。若你的环境必须走代理才能访问国际站点：

```bash
PROBE_USE_PROXY=1 python3 site_probe.py https://www.google.com
```

**注意：探测中文站点时不要走境外代理** —— 详见 README 规则一。

**Note: never route Chinese sites through an overseas proxy** — see Rule 1 in README.
