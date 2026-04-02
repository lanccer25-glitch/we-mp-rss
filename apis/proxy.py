"""
代理服务模块 - 用于突破 iframe 跨域限制
"""
from fastapi import APIRouter, Request, Response
import httpx
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy", tags=["代理服务"])

# 允许代理的域名白名单（可选，为了安全可以限制）
ALLOWED_DOMAINS = None  # None 表示允许所有域名，或者设置列表如 ['mp.weixin.qq.com', 'weixin.qq.com']

def is_domain_allowed(url: str) -> bool:
    """
    检查域名是否在允许列表中
    
    Args:
        url: 目标URL
        
    Returns:
        bool: 是否允许代理
    """
    if ALLOWED_DOMAINS is None:
        return True
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # 移除端口号
        domain = domain.split(':')[0]
        return domain in ALLOWED_DOMAINS
    except Exception:
        return False


@router.get("/{path:path}")
async def proxy_get_request(path: str, request: Request):
    """
    代理 GET 请求
    
    代理外部 URL 的请求，解决 iframe 跨域限制
    
    Args:
        path: 代理的路径
        request: FastAPI 请求对象
        
    Returns:
        Response: 代理的响应内容
    """
    # 从查询参数中获取目标 URL
    target_url = request.query_params.get("url")
    
    if not target_url:
        return Response(
            content="Missing 'url' parameter",
            status_code=400,
            media_type="text/plain"
        )
    
    # 检查域名白名单
    if not is_domain_allowed(target_url):
        logger.warning(f"尝试代理不允许的域名: {target_url}")
        return Response(
            content="Domain not allowed",
            status_code=403,
            media_type="text/plain"
        )
    
    try:
        # 获取客户端请求头
        headers = dict(request.headers)
        
        # 移除不应该转发的头
        headers.pop('host', None)
        headers.pop('content-length', None)
        headers.pop('content-encoding', None)
        headers.pop('transfer-encoding', None)
        
        # 添加用户代理（避免被反爬虫拦截）
        headers['User-Agent'] = headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 获取查询参数（除了 url 参数）
        query_params = dict(request.query_params)
        query_params.pop('url', None)
        
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=False  # 忽略 SSL 证书验证
        ) as client:
            # 发起代理请求
            response = await client.get(
                target_url,
                headers=headers,
                params=query_params if query_params else None
            )
            
            # 构建响应
            content = response.content
            response_headers = dict(response.headers)
            
            # 移除不应该返回的头
            response_headers.pop('content-encoding', None)
            response_headers.pop('transfer-encoding', None)
            response_headers.pop('content-length', None)
            
            # 添加 CORS 相关头
            response_headers['Access-Control-Allow-Origin'] = '*'
            response_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response_headers['Access-Control-Allow-Headers'] = '*'
            
            # 针对微信公众号文章的特殊处理
            # 添加一些安全相关的头，允许在 iframe 中显示
            response_headers['X-Frame-Options'] = 'ALLOWALL'
            response_headers['Content-Security-Policy'] = "frame-ancestors *"
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type', 'text/html')
            )
            
    except httpx.TimeoutException:
        logger.error(f"代理请求超时: {target_url}")
        return Response(
            content="Request timeout",
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"代理请求失败: {target_url}, 错误: {str(e)}")
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )


@router.options("/{path:path}")
async def proxy_options_request(path: str, request: Request):
    """
    处理 OPTIONS 请求（CORS 预检请求）
    """
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Max-Age': '86400',
    }
    return Response(headers=headers, status_code=200)


@router.post("/{path:path}")
async def proxy_post_request(path: str, request: Request):
    """
    代理 POST 请求
    
    Args:
        path: 代理的路径
        request: FastAPI 请求对象
        
    Returns:
        Response: 代理的响应内容
    """
    # 从查询参数中获取目标 URL
    target_url = request.query_params.get("url")
    
    if not target_url:
        return Response(
            content="Missing 'url' parameter",
            status_code=400,
            media_type="text/plain"
        )
    
    # 检查域名白名单
    if not is_domain_allowed(target_url):
        logger.warning(f"尝试代理不允许的域名: {target_url}")
        return Response(
            content="Domain not allowed",
            status_code=403,
            media_type="text/plain"
        )
    
    try:
        # 获取请求体
        body = await request.body()
        
        # 获取客户端请求头
        headers = dict(request.headers)
        
        # 移除不应该转发的头
        headers.pop('host', None)
        headers.pop('content-length', None)
        headers.pop('content-encoding', None)
        headers.pop('transfer-encoding', None)
        
        # 添加用户代理
        headers['User-Agent'] = headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 获取查询参数（除了 url 参数）
        query_params = dict(request.query_params)
        query_params.pop('url', None)
        
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=False
        ) as client:
            # 发起代理请求
            response = await client.post(
                target_url,
                content=body,
                headers=headers,
                params=query_params if query_params else None
            )
            
            # 构建响应
            content = response.content
            response_headers = dict(response.headers)
            
            # 移除不应该返回的头
            response_headers.pop('content-encoding', None)
            response_headers.pop('transfer-encoding', None)
            response_headers.pop('content-length', None)
            
            # 添加 CORS 相关头
            response_headers['Access-Control-Allow-Origin'] = '*'
            response_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response_headers['Access-Control-Allow-Headers'] = '*'
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type', 'text/html')
            )
            
    except httpx.TimeoutException:
        logger.error(f"代理请求超时: {target_url}")
        return Response(
            content="Request timeout",
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"代理请求失败: {target_url}, 错误: {str(e)}")
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )
