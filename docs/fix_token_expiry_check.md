# 微信授权过期检查修复

## 问题描述

在微信登录授权未到期的情况下，系统仍然显示"等待扫码登录"。

## 问题原因

通过代码分析，发现系统**没有检查微信 token 的实际过期时间**。具体问题如下：

1. **`getStatus()` 函数** 只从 Redis 或全局变量读取登录状态，没有检查 token 是否过期
2. **`_get_token_data()` 函数** 只是读取 token 数据，没有验证过期时间
3. **`CanGetToken()` 函数** 只检查 `getStatus() && getLockStatus() == False`，也没有检查过期时间

这导致即使 token 实际上已经过期，只要 Redis 中的状态没有被更新，系统仍然认为已经登录。

## 解决方案

修改了 `driver/success.py` 文件中的两个关键函数：

### 1. 修改 `getStatus()` 函数

增加了 token 过期时间检查逻辑：

```python
def getStatus():
    """获取登录状态，优先从Redis读取，失败则使用全局变量，并检查token是否过期"""
    global WX_LOGIN_ED
    import time

    # 尝试从Redis读取
    if redis_client.is_connected:
        try:
            val = redis_client._client.get(REDIS_KEY_STATUS)
            if val is not None and val == "1":
                # 检查token是否过期
                token_data = getLoginInfo()
                if token_data and 'expiry' in token_data and token_data['expiry']:
                    expiry = token_data['expiry']
                    # 检查剩余秒数
                    if 'remaining_seconds' in expiry:
                        remaining = expiry['remaining_seconds']
                        if remaining is not None and remaining > 0:
                            return True
                        else:
                            # token已过期，更新状态
                            print_warning("Token已过期，需要重新登录")
                            setStatus(False)
                            return False
                    # 检查过期时间戳
                    elif 'expiry_timestamp' in expiry:
                        expiry_timestamp = expiry['expiry_timestamp']
                        if expiry_timestamp and expiry_timestamp > time.time():
                            return True
                        else:
                            # token已过期，更新状态
                            print_warning("Token已过期，需要重新登录")
                            setStatus(False)
                            return False
                # 没有过期信息，但状态为True，暂时返回True
                return True
        except Exception as e:
            print_warning(f"检查登录状态失败: {e}")
            pass
    # 回退到全局变量
    with login_lock:
        return WX_LOGIN_ED
```

### 2. 修改 `CanGetToken()` 函数

增加了更详细的 token 过期时间检查和错误提示：

```python
def CanGetToken():
    """检查是否可以获取Token，包括检查登录状态、锁定状态和token过期时间"""
    import time

    # 检查锁定状态
    if getLockStatus():
        print_warning("正在切换账号，请等待切换完成")
        return False

    # 检查登录状态
    if not getStatus():
        print_warning("当前未登录，请先扫码登录")
        return False

    # 检查token过期时间
    token_data = getLoginInfo()
    if not token_data or not token_data.get('token'):
        print_warning("Token不存在，请重新登录")
        setStatus(False)
        return False

    # 检查过期信息
    expiry = token_data.get('expiry')
    if expiry:
        # 检查剩余秒数
        if 'remaining_seconds' in expiry:
            remaining = expiry['remaining_seconds']
            if remaining is not None and remaining <= 0:
                print_warning("Token已过期，请重新扫码登录")
                setStatus(False)
                return False
        # 检查过期时间戳
        elif 'expiry_timestamp' in expiry:
            expiry_timestamp = expiry['expiry_timestamp']
            if expiry_timestamp and expiry_timestamp <= time.time():
                print_warning("Token已过期，请重新扫码登录")
                setStatus(False)
                return False

    return True
```

## 修复效果

1. **自动检测 token 过期**：系统会自动检查 token 的过期时间
2. **自动更新状态**：当检测到 token 过期时，会自动更新登录状态为 False
3. **清晰的错误提示**：提供明确的错误信息，帮助用户理解问题
4. **防止误判**：避免在 token 未过期时错误地提示需要重新登录

## 使用说明

修复后，系统会：

1. 在每次检查登录状态时，自动验证 token 是否过期
2. 如果 token 已过期，自动更新登录状态，并提示用户重新登录
3. 前端会正确显示登录状态，避免误判

## 注意事项

1. 此修复会修改 `driver/success.py` 文件
2. 修复后，系统会自动检查 token 过期时间
3. 如果 token 已过期，系统会自动更新登录状态
4. 用户需要重新扫码登录以获取新的 token

## 测试建议

1. 测试 token 未过期时，系统正确显示已登录状态
2. 测试 token 已过期时，系统正确提示需要重新登录
3. 测试 token 不存在时，系统正确提示需要重新登录
4. 测试 Redis 不可用时，系统能正常回退到全局变量
