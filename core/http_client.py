"""
HTTP 客户端包装器

支持自动使用代理池中的代理
"""

import asyncio
from typing import Optional, Dict, Any
from urllib.parse import urlparse

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from core.print import print_info, print_warning
from core.proxy_pool import proxy_pool, ProxyInfo


class AsyncHttpClient:
    """异步 HTTP 客户端，支持代理池"""
    
    def __init__(
        self,
        use_proxy: bool = True,
        timeout: float = 30.0,
        headers: Optional[Dict] = None,
        **kwargs
    ):
        self.use_proxy = use_proxy
        self.timeout = timeout
        self.default_headers = headers or {}
        self.extra_kwargs = kwargs
        self._current_proxy: Optional[ProxyInfo] = None
    
    def _get_proxies(self) -> Optional[Dict]:
        """获取代理配置"""
        if not self.use_proxy:
            return None
        
        if not proxy_pool.is_enabled():
            return None
        
        proxy_info = proxy_pool.get_proxy()
        if proxy_info:
            self._current_proxy = proxy_info
            return proxy_info.httpx_proxy
        return None
    
    async def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """GET 请求"""
        return await self._request("GET", url, params=params, headers=headers, **kwargs)
    
    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """POST 请求"""
        return await self._request("POST", url, data=data, json=json, headers=headers, **kwargs)
    
    async def put(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """PUT 请求"""
        return await self._request("PUT", url, data=data, json=json, headers=headers, **kwargs)
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """DELETE 请求"""
        return await self._request("DELETE", url, headers=headers, **kwargs)
    
    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """发送请求"""
        if not HAS_HTTPX:
            raise ImportError("httpx 未安装，请运行: pip install httpx")
        
        # 合并请求头
        request_headers = {**self.default_headers, **(headers or {})}
        
        # 获取代理
        proxies = self._get_proxies()
        
        # 合并其他参数
        request_kwargs = {**self.extra_kwargs, **kwargs}
        
        async with httpx.AsyncClient(
            timeout=self.timeout,
            proxies=proxies,
            headers=request_headers if request_headers else None,
            **request_kwargs
        ) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json
                )
                response.raise_for_status()
                
                # 报告代理成功
                self._report_proxy_result(True)
                
                return response
                
            except Exception as e:
                # 报告代理失败
                self._report_proxy_result(False)
                raise
    
    def _report_proxy_result(self, success: bool):
        """报告代理使用结果"""
        if self._current_proxy:
            proxy_pool.report_result(self._current_proxy.url, success)
            self._current_proxy = None


class SyncHttpClient:
    """同步 HTTP 客户端，支持代理池"""
    
    def __init__(
        self,
        use_proxy: bool = True,
        timeout: float = 30.0,
        headers: Optional[Dict] = None,
        **kwargs
    ):
        self.use_proxy = use_proxy
        self.timeout = timeout
        self.default_headers = headers or {}
        self.extra_kwargs = kwargs
        self._current_proxy: Optional[ProxyInfo] = None
    
    def _get_proxies(self) -> Optional[Dict]:
        """获取代理配置"""
        if not self.use_proxy:
            return None
        
        if not proxy_pool.is_enabled():
            return None
        
        proxy_info = proxy_pool.get_proxy()
        if proxy_info:
            self._current_proxy = proxy_info
            return proxy_info.httpx_proxy
        return None
    
    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """GET 请求"""
        return self._request("GET", url, params=params, headers=headers, **kwargs)
    
    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """POST 请求"""
        return self._request("POST", url, data=data, json=json, headers=headers, **kwargs)
    
    def put(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """PUT 请求"""
        return self._request("PUT", url, data=data, json=json, headers=headers, **kwargs)
    
    def delete(
        self,
        url: str,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """DELETE 请求"""
        return self._request("DELETE", url, headers=headers, **kwargs)
    
    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """发送请求"""
        if not HAS_HTTPX:
            raise ImportError("httpx 未安装，请运行: pip install httpx")
        
        # 合并请求头
        request_headers = {**self.default_headers, **(headers or {})}
        
        # 获取代理
        proxies = self._get_proxies()
        
        # 合并其他参数
        request_kwargs = {**self.extra_kwargs, **kwargs}
        
        with httpx.Client(
            timeout=self.timeout,
            proxies=proxies,
            headers=request_headers if request_headers else None,
            **request_kwargs
        ) as client:
            try:
                response = client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json
                )
                response.raise_for_status()
                
                # 报告代理成功
                self._report_proxy_result(True)
                
                return response
                
            except Exception as e:
                # 报告代理失败
                self._report_proxy_result(False)
                raise
    
    def _report_proxy_result(self, success: bool):
        """报告代理使用结果"""
        if self._current_proxy:
            proxy_pool.report_result(self._current_proxy.url, success)
            self._current_proxy = None


# 便捷函数
async def async_get(url: str, use_proxy: bool = True, **kwargs) -> httpx.Response:
    """异步 GET 请求"""
    client = AsyncHttpClient(use_proxy=use_proxy)
    return await client.get(url, **kwargs)


async def async_post(url: str, use_proxy: bool = True, **kwargs) -> httpx.Response:
    """异步 POST 请求"""
    client = AsyncHttpClient(use_proxy=use_proxy)
    return await client.post(url, **kwargs)


def sync_get(url: str, use_proxy: bool = True, **kwargs) -> httpx.Response:
    """同步 GET 请求"""
    client = SyncHttpClient(use_proxy=use_proxy)
    return client.get(url, **kwargs)


def sync_post(url: str, use_proxy: bool = True, **kwargs) -> httpx.Response:
    """同步 POST 请求"""
    client = SyncHttpClient(use_proxy=use_proxy)
    return client.post(url, **kwargs)
