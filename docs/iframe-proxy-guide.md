# Iframe 跨域代理使用指南

## 概述

本项目已添加了一个代理服务，用于突破 iframe 的跨域限制。该代理服务可以安全地转发外部 URL 的请求，解决浏览器同源策略带来的限制。

## 功能特性

- ✅ **GET/POST 请求代理**：支持代理 GET 和 POST 请求
- ✅ **CORS 处理**：自动添加 CORS 相关响应头
- ✅ **请求头转发**：智能转发客户端请求头
- ✅ **重定向跟随**：自动跟随 HTTP 重定向
- ✅ **超时控制**：30 秒超时保护
- ✅ **域名白名单**：可选的域名白名单功能（默认允许所有域名）
- ✅ **安全响应头**：添加 `X-Frame-Options` 和 `Content-Security-Policy` 允许在 iframe 中显示

## 使用方法

### 1. 在 iframe 中使用（文章详情页）

在 `article_detail.html` 模板中，iframe 的 src 已修改为使用代理：

```html
<iframe src="/proxy/proxy?url={{article.url}}" 
        style="width: 100%; height: 100%; border: none;" 
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups"></iframe>
```

### 2. 直接访问代理 API

#### GET 请求

```
GET /proxy/proxy?url=https://example.com
```

#### POST 请求

```
POST /proxy/proxy?url=https://example.com/api
Content-Type: application/json

{
  "key": "value"
}
```

### 3. 在 JavaScript 中使用

```javascript
// 获取代理 URL
const originalUrl = 'https://mp.weixin.qq.com/s/xxx';
const proxyUrl = `/proxy/proxy?url=${encodeURIComponent(originalUrl)}`;

// 在 iframe 中使用
const iframe = document.createElement('iframe');
iframe.src = proxyUrl;
document.body.appendChild(iframe);

// 或者使用 fetch
fetch(proxyUrl)
  .then(response => response.text())
  .then(data => console.log(data));
```

## API 端点

### GET /proxy/{path:path}

代理 GET 请求到指定的 URL。

**查询参数：**
- `url` (必需): 目标 URL

**示例：**
```bash
curl "http://localhost:8001/proxy/proxy?url=https://mp.weixin.qq.com/s/xxx"
```

### POST /proxy/{path:path}

代理 POST 请求到指定的 URL。

**查询参数：**
- `url` (必需): 目标 URL

**请求体：**
- 任意类型的请求体数据

**示例：**
```bash
curl -X POST "http://localhost:8001/proxy/proxy?url=https://api.example.com/data" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

### OPTIONS /proxy/{path:path}

处理 CORS 预检请求。

## 安全配置

### 域名白名单

为了提高安全性，可以在 `apis/proxy.py` 中配置允许代理的域名白名单：

```python
# 允许代理的域名白名单
ALLOWED_DOMAINS = [
    'mp.weixin.qq.com',
    'weixin.qq.com',
    # 添加更多允许的域名
]
```

设置为 `None` 允许代理所有域名（默认行为）。

### 安全响应头

代理自动添加以下安全响应头：

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: *
X-Frame-Options: ALLOWALL
Content-Security-Policy: frame-ancestors *
```

## 配置建议

### 1. 生产环境

在生产环境中，建议：

1. **启用域名白名单**：限制只允许代理可信的域名
2. **添加认证**：在代理端点添加访问控制
3. **监控日志**：监控代理请求日志，发现异常访问
4. **限流**：添加请求限流防止滥用

### 2. 开发环境

在开发环境中，可以保持默认配置（允许所有域名）以方便测试。

## 常见问题

### Q: 代理请求超时怎么办？

A: 默认超时时间为 30 秒。可以在 `apis/proxy.py` 中修改 `timeout=httpx.Timeout(30.0)` 来调整。

### Q: 如何处理 SSL 证书错误？

A: 代理默认忽略 SSL 证书验证（`verify=False`）。在生产环境中，建议启用证书验证。

### Q: iframe 中的内容无法正常显示？

A: 可能原因：
1. 目标网站有反爬虫机制
2. 需要特定的请求头或 Cookie
3. 目标网站使用了 JavaScript 跳转

可以通过查看浏览器控制台和服务器日志来诊断问题。

### Q: 如何调试代理请求？

A: 检查服务器日志，代理请求会记录以下信息：
- 代理的目标 URL
- 请求状态
- 错误信息（如果有）

## 依赖项

代理服务需要以下依赖项（已包含在 `requirements.txt` 中）：

```
httpx==0.28.1
```

## 文件结构

```
we-mp-rss/
├── apis/
│   └── proxy.py          # 代理服务 API 模块
├── public/
│   └── templates/
│       └── article_detail.html  # 使用代理的文章详情页
├── web.py               # 主应用文件（已注册代理路由）
└── docs/
    └── iframe-proxy-guide.md    # 本文档
```

## 更新日志

- **v1.0.0** (2026-04-02)
  - 添加代理服务 API
  - 支持 GET/POST 请求代理
  - 配置 CORS 和安全响应头
  - 更新文章详情页面使用代理
  - 添加域名白名单功能

## 技术支持

如有问题，请查看：
1. 服务器日志
2. 浏览器控制台错误
3. 本项目的 GitHub Issues
