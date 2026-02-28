"""
代理池管理模块

功能：
1. 支持从配置文件加载代理列表
2. 支持多种代理协议 (HTTP, HTTPS, SOCKS5)
3. 支持轮询、随机、加权等策略
4. 支持代理健康检查
5. 提供 Playwright 和 HTTP 客户端使用的统一接口
"""

import random
import time
import asyncio
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from core.print import print_info, print_warning, print_error, print_success
from core.config import cfg


class ProxyProtocol(Enum):
    """代理协议类型"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyStrategy(Enum):
    """代理选择策略"""
    ROUND_ROBIN = "round_robin"  # 轮询
    RANDOM = "random"            # 随机
    WEIGHTED = "weighted"        # 加权
    LEAST_USED = "least_used"    # 最少使用


@dataclass
class ProxyInfo:
    """代理信息"""
    host: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    weight: int = 1            # 权重
    max_failures: int = 3      # 最大失败次数
    
    # 运行时状态
    failures: int = field(default=0, repr=False)
    successes: int = field(default=0, repr=False)
    last_used: float = field(default=0, repr=False)
    last_check: float = field(default=0, repr=False)
    is_available: bool = field(default=True, repr=False)
    
    @property
    def url(self) -> str:
        """获取代理URL"""
        if self.username and self.password:
            return f"{self.protocol.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol.value}://{self.host}:{self.port}"
    
    @property
    def playwright_proxy(self) -> Dict:
        """获取 Playwright 代理配置"""
        proxy_config = {
            "server": f"{self.protocol.value}://{self.host}:{self.port}"
        }
        if self.username and self.password:
            proxy_config["username"] = self.username
            proxy_config["password"] = self.password
        return proxy_config
    
    @property
    def httpx_proxy(self) -> Dict:
        """获取 httpx 代理配置"""
        # httpx 使用 all:// 或指定协议
        return {
            "http://": self.url,
            "https://": self.url
        }
    
    def mark_success(self):
        """标记成功"""
        self.successes += 1
        self.failures = 0
        self.is_available = True
        self.last_used = time.time()
    
    def mark_failure(self):
        """标记失败"""
        self.failures += 1
        if self.failures >= self.max_failures:
            self.is_available = False
            print_warning(f"代理 {self.host}:{self.port} 已标记为不可用")
    
    def reset(self):
        """重置状态"""
        self.failures = 0
        self.successes = 0
        self.is_available = True


class ProxyPool:
    """代理池管理器"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, strategy: ProxyStrategy = ProxyStrategy.ROUND_ROBIN):
        if self._initialized:
            return
        
        self._proxies: List[ProxyInfo] = []
        self._strategy = strategy
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._initialized = True
        self._check_interval = 300  # 健康检查间隔（秒）
        
        # 从配置加载代理
        self._load_from_config()
    
    def _load_from_config(self):
        """从配置文件加载代理列表"""
        proxy_config = cfg.get("proxy", {})
        
        if not proxy_config.get("enabled", False):
            print_info("代理未启用")
            return
        
        proxies = proxy_config.get("list", [])
        for p in proxies:
            try:
                proxy = self._parse_proxy(p)
                if proxy:
                    self._proxies.append(proxy)
            except Exception as e:
                print_error(f"解析代理配置失败: {p} - {e}")
        
        # 设置策略
        strategy_name = proxy_config.get("strategy", "round_robin")
        self._strategy = ProxyStrategy(strategy_name)
        
        print_success(f"代理池加载完成，共 {len(self._proxies)} 个代理，策略: {strategy_name}")
    
    def _parse_proxy(self, config: dict) -> Optional[ProxyInfo]:
        """解析代理配置"""
        # 支持多种配置格式
        # 格式1: {"url": "http://user:pass@host:port"}
        # 格式2: {"host": "host", "port": 8080, "protocol": "http", "username": "user", "password": "pass"}
        # 格式3: 直接字符串 "http://user:pass@host:port"
        
        if isinstance(config, str):
            return self._parse_proxy_url(config)
        
        if "url" in config:
            proxy = self._parse_proxy_url(config["url"])
            if proxy and "weight" in config:
                proxy.weight = config["weight"]
            if proxy and "max_failures" in config:
                proxy.max_failures = config["max_failures"]
            return proxy
        
        return ProxyInfo(
            host=config["host"],
            port=int(config["port"]),
            protocol=ProxyProtocol(config.get("protocol", "http")),
            username=config.get("username"),
            password=config.get("password"),
            weight=config.get("weight", 1),
            max_failures=config.get("max_failures", 3)
        )
    
    def _parse_proxy_url(self, url: str) -> Optional[ProxyInfo]:
        """解析代理URL"""
        try:
            parsed = urlparse(url)
            protocol = ProxyProtocol(parsed.scheme or "http")
            
            return ProxyInfo(
                host=parsed.hostname,
                port=parsed.port or (1080 if protocol == ProxyProtocol.SOCKS5 else 8080),
                protocol=protocol,
                username=parsed.username,
                password=parsed.password
            )
        except Exception as e:
            print_error(f"解析代理URL失败: {url} - {e}")
            return None
    
    def add_proxy(self, proxy: ProxyInfo):
        """添加代理"""
        self._proxies.append(proxy)
    
    def remove_proxy(self, host: str, port: int):
        """移除代理"""
        self._proxies = [p for p in self._proxies if not (p.host == host and p.port == port)]
    
    def get_proxy(self) -> Optional[ProxyInfo]:
        """获取一个可用代理"""
        available = [p for p in self._proxies if p.is_available]
        
        if not available:
            print_warning("没有可用的代理")
            return None
        
        if self._strategy == ProxyStrategy.RANDOM:
            return random.choice(available)
        
        elif self._strategy == ProxyStrategy.ROUND_ROBIN:
            proxy = available[self._current_index % len(available)]
            self._current_index += 1
            return proxy
        
        elif self._strategy == ProxyStrategy.WEIGHTED:
            # 加权随机
            weights = [p.weight for p in available]
            return random.choices(available, weights=weights, k=1)[0]
        
        elif self._strategy == ProxyStrategy.LEAST_USED:
            # 最少使用
            return min(available, key=lambda p: p.successes + p.failures)
        
        return available[0]
    
    def get_all_proxies(self) -> List[ProxyInfo]:
        """获取所有代理"""
        return self._proxies.copy()
    
    def get_available_count(self) -> int:
        """获取可用代理数量"""
        return sum(1 for p in self._proxies if p.is_available)
    
    def is_enabled(self) -> bool:
        """检查代理是否启用"""
        return len(self._proxies) > 0
    
    async def check_proxy(self, proxy: ProxyInfo, test_url: str = "https://httpbin.org/ip") -> bool:
        """检查代理是否可用"""
        if not HAS_HTTPX:
            print_warning("httpx 未安装，跳过代理检查")
            return True
        
        try:
            async with httpx.AsyncClient(
                proxy=proxy.url,
                timeout=10.0
            ) as client:
                response = await client.get(test_url)
                if response.status_code == 200:
                    proxy.mark_success()
                    proxy.last_check = time.time()
                    return True
        except Exception as e:
            print_warning(f"代理 {proxy.host}:{proxy.port} 检查失败: {e}")
            proxy.mark_failure()
        
        return False
    
    async def check_all_proxies(self):
        """检查所有代理"""
        tasks = [self.check_proxy(p) for p in self._proxies]
        await asyncio.gather(*tasks)
        print_info(f"代理检查完成，可用: {self.get_available_count()}/{len(self._proxies)}")
    
    def get_playwright_proxy(self) -> Optional[Dict]:
        """获取 Playwright 代理配置"""
        proxy = self.get_proxy()
        if proxy:
            return proxy.playwright_proxy
        return None
    
    def get_httpx_proxy(self) -> Optional[Dict]:
        """获取 httpx 代理配置"""
        proxy = self.get_proxy()
        if proxy:
            return proxy.httpx_proxy
        return None
    
    def get_proxy_url(self) -> Optional[str]:
        """获取代理URL"""
        proxy = self.get_proxy()
        if proxy:
            return proxy.url
        return None
    
    def report_result(self, proxy_url: str, success: bool):
        """报告代理使用结果"""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                if success:
                    proxy.mark_success()
                else:
                    proxy.mark_failure()
                break


# 全局代理池实例
proxy_pool = ProxyPool()


def get_proxy_pool() -> ProxyPool:
    """获取代理池实例"""
    return proxy_pool
