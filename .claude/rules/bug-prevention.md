# Bug Prevention Rules

> 基于 2026-04-23 bug audit 发现的问题制定的预防规则

## 1. Metrics 定义必须使用

**规则**: 所有定义的 Prometheus metrics 必须在代码中实际调用

**检查方法**:
```bash
# 查找所有 metric 定义
rg "Counter\(|Histogram\(|Gauge\(" src/

# 对每个 metric，验证有对应的 .inc()/.observe()/.set() 调用
rg "metric_name\.(inc|observe|set)\(" src/
```

**强制要求**:
- Counter 必须有至少一个 `.inc()` 调用
- Histogram 必须有至少一个 `.observe()` 调用
- Gauge 必须有至少一个 `.set()` 调用

**测试要求**:
- 每个 metric 必须有测试验证其被正确递增/观察/设置
- 测试必须验证 metric 值变化，而不仅仅是验证 metric 被注册

**示例**:
```python
# ❌ 错误：定义但从未使用
api_errors = Counter('api_errors', 'API error count')

def handle_request():
    try:
        process()
    except Exception:
        # BUG: 忘记调用 api_errors.inc()
        raise

# ✅ 正确：定义并使用
api_errors = Counter('api_errors', 'API error count')

def handle_request():
    try:
        process()
    except Exception:
        api_errors.inc()  # 正确递增
        raise
```

---

## 2. 字符串解析必须验证

**规则**: 所有字符串解析操作必须验证输入格式并提供清晰的错误信息

**适用场景**:
- `int()`, `float()` 转换
- `.removeprefix()`, `.removesuffix()`, `.split()` 操作
- 正则表达式匹配
- 版本号、ID、路径解析

**强制要求**:
- 使用 `try-except` 包裹可能失败的转换
- 验证输入格式符合预期（如版本号必须以 "v" 开头）
- 错误信息必须包含实际输入值和期望格式
- 边界条件必须有测试覆盖

**示例**:
```python
# ❌ 错误：隐式假设，无验证
def get_next_version(current):
    num = int(current.removeprefix("v"))  # 遇到 "v001-hotfix" 崩溃
    return f"v{num + 1:03d}"

# ✅ 正确：显式验证，清晰错误
def get_next_version(current):
    if not current.startswith("v"):
        raise ValueError(
            f"Invalid version format: {current} (expected vXXX)"
        )
    
    try:
        num = int(current.removeprefix("v"))
    except ValueError as e:
        raise ValueError(
            f"Cannot parse version number from '{current}'. "
            f"Expected format: v001, v002, etc."
        ) from e
    
    return f"v{num + 1:03d}"
```

**测试要求**:
- 测试标准格式输入（happy path）
- 测试非标准格式输入（如 "v001-hotfix", "version-1", "abc"）
- 测试边界值（空字符串、超长字符串、特殊字符）
- 验证错误信息包含有用的调试信息

---

## 3. 用户输入必须防止路径遍历

**规则**: 所有接受文件路径或 ID 的函数必须验证输入，防止路径遍历攻击

**适用场景**:
- 文件/目录创建
- 文件读写
- 符号链接操作
- 任何基于用户输入构建路径的操作

**强制要求**:
- 拒绝包含 `/` 或 `\` 的输入
- 拒绝 `.` 和 `..`
- 使用 `Path.resolve()` 和 `is_relative_to()` 验证最终路径在预期目录内
- 在文件系统操作前进行验证

**示例**:
```python
# ❌ 错误：无验证，允许路径遍历
def create_version(self, version_id: str):
    version_dir = self.strategies_dir / version_id  # 可以是 "../../../etc/passwd"
    version_dir.mkdir(parents=True)

# ✅ 正确：完整验证
def create_version(self, version_id: str):
    # 1. 基本验证
    if not version_id:
        raise ValueError("version_id cannot be empty")
    
    # 2. 拒绝路径分隔符
    if "/" in version_id or "\\" in version_id:
        raise ValueError(
            f"Invalid version_id: {version_id} "
            f"(cannot contain path separators)"
        )
    
    # 3. 拒绝特殊目录名
    if version_id in (".", ".."):
        raise ValueError(
            f"Invalid version_id: {version_id} "
            f"(cannot be . or ..)"
        )
    
    # 4. 验证解析后的路径在预期目录内
    version_dir = self.strategies_dir / version_id
    try:
        resolved = version_dir.resolve()
        if not resolved.is_relative_to(self.strategies_dir.resolve()):
            raise ValueError(
                f"Invalid version_id: {version_id} "
                f"(path traversal detected)"
            )
    except ValueError:
        raise ValueError(
            f"Invalid version_id: {version_id} "
            f"(path traversal detected)"
        )
    
    # 5. 现在可以安全地创建目录
    version_dir.mkdir(parents=True)
```

**测试要求**:
- 测试标准输入（如 "v001"）
- 测试路径遍历尝试（如 "../escape", "../../etc/passwd"）
- 测试特殊字符（如 ".", "..", "version/../other"）
- 验证错误信息清晰且不泄露敏感信息

---

## 4. 重试逻辑必须测试

**规则**: 所有使用 `@retry` 装饰器的函数必须有测试验证重试行为

**强制要求**:
- 测试重试触发（前 N 次失败，第 N+1 次成功）
- 测试重试耗尽（所有尝试都失败）
- 测试非重试异常不触发重试
- 测试指数退避时间（如果配置了）

**示例**:
```python
# 实现
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(APIError)
)
async def call_api():
    return await client.request()

# ✅ 必须的测试
@pytest.mark.asyncio
async def test_retry_triggers_on_api_error():
    """验证 APIError 触发重试，第 3 次成功"""
    mock_client.request = AsyncMock(side_effect=[
        APIError("error"),
        APIError("error"),
        {"status": "ok"}  # 第 3 次成功
    ])
    
    result = await call_api()
    assert result == {"status": "ok"}
    assert mock_client.request.call_count == 3

@pytest.mark.asyncio
async def test_retry_exhausts_and_raises():
    """验证重试耗尽后抛出最后的异常"""
    mock_client.request = AsyncMock(side_effect=APIError("error"))
    
    with pytest.raises(APIError):
        await call_api()
    
    assert mock_client.request.call_count == 3

@pytest.mark.asyncio
async def test_non_retryable_exception_not_retried():
    """验证非 APIError 异常不触发重试"""
    mock_client.request = AsyncMock(side_effect=ValueError("bad input"))
    
    with pytest.raises(ValueError):
        await call_api()
    
    assert mock_client.request.call_count == 1  # 只调用一次
```

---

## 5. Circuit Breaker 状态必须完整测试

**规则**: Circuit breaker 的所有状态转换必须有测试覆盖

**强制要求**:
- 测试 CLOSED → OPEN（失败阈值）
- 测试 OPEN → HALF_OPEN（超时后）
- 测试 HALF_OPEN → CLOSED（成功恢复）
- 测试 HALF_OPEN → OPEN（恢复失败）
- 测试排除的异常类型不触发 circuit breaker

**示例**:
```python
@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """验证 circuit breaker 从 OPEN 恢复到 CLOSED"""
    provider = ClaudeProvider(fail_max=3, reset_timeout=1)
    
    # 1. 触发 circuit 开路
    for _ in range(3):
        with pytest.raises(ProviderError):
            await provider.generate(request)
    
    assert provider._breaker.current_state == "open"
    
    # 2. 等待 reset_timeout
    await asyncio.sleep(1.1)
    
    # 3. 下一次调用应该进入 HALF_OPEN 状态
    mock_client.messages.create = AsyncMock(return_value=success_response)
    result = await provider.generate(request)
    
    # 4. 成功后应该恢复到 CLOSED
    assert provider._breaker.current_state == "closed"
    assert result[0] == "success"
```

---

## 6. 格式转换器必须测试

**规则**: 所有数据格式转换函数必须有完整的测试覆盖

**适用场景**:
- `to_openai()`, `to_anthropic()` 等格式转换
- JSON/YAML/CSV 导出
- API 响应格式化
- 数据序列化/反序列化

**强制要求**:
- 测试输出结构符合规范
- 测试所有输入类型/枚举值
- 测试 Unicode 和特殊字符保留
- 测试边界条件（空字符串、None、超长文本）

**示例**:
```python
def test_to_openai_format_structure():
    """验证 OpenAI 格式结构正确"""
    record = EvaluationRecord(
        question="What is Docker?",
        answer="Docker is a containerization platform.",
        question_type=QuestionType.FACTUAL,
        auto_score=0.9
    )
    
    result = DatasetConverter().to_openai(record)
    data = json.loads(result)
    
    # 验证结构
    assert "messages" in data
    assert len(data["messages"]) == 3
    
    # 验证角色
    assert data["messages"][0]["role"] == "system"
    assert data["messages"][1]["role"] == "user"
    assert data["messages"][2]["role"] == "assistant"
    
    # 验证内容
    assert data["messages"][1]["content"] == "What is Docker?"
    assert data["messages"][2]["content"] == "Docker is a containerization platform."

def test_to_openai_unicode_preserved():
    """验证 Unicode 字符正确保留"""
    record = EvaluationRecord(
        question="什么是 Docker？",
        answer="Docker 是容器化平台。",
        question_type=QuestionType.FACTUAL,
        auto_score=0.9
    )
    
    result = DatasetConverter().to_openai(record)
    data = json.loads(result)
    
    # 验证中文字符未被转义
    assert "什么是 Docker" in result
    assert "\\u" not in result  # 确保没有 Unicode 转义
```

---

## 7. 并发场景必须测试

**规则**: 共享状态的代码必须测试并发安全性

**适用场景**:
- 缓存（如 `_prompt_cache`）
- 全局状态
- 文件系统操作（如符号链接）
- 数据库连接池

**强制要求**:
- 使用锁保护共享状态
- 测试并发读写
- 测试竞态条件
- 使用原子操作（如 `Path.replace()` 而非 `unlink() + symlink()`）

**示例**:
```python
# ❌ 错误：无锁保护
class VersionManager:
    def __init__(self):
        self._prompt_cache = {}  # 共享状态
    
    def load_prompt_config(self, version_id):
        if version_id in self._prompt_cache:
            return self._prompt_cache[version_id]  # 竞态条件
        
        config = self._load_from_disk(version_id)
        self._prompt_cache[version_id] = config  # 竞态条件
        return config

# ✅ 正确：使用锁保护
import threading

class VersionManager:
    def __init__(self):
        self._prompt_cache = {}
        self._cache_lock = threading.Lock()
    
    def load_prompt_config(self, version_id):
        with self._cache_lock:
            if version_id in self._prompt_cache:
                return self._prompt_cache[version_id]
        
        config = self._load_from_disk(version_id)
        
        with self._cache_lock:
            self._prompt_cache[version_id] = config
        
        return config

# ✅ 必须的测试
def test_prompt_cache_thread_safe():
    """验证缓存在并发访问时线程安全"""
    manager = VersionManager(tmp_path)
    manager.create_version("v001", None, {"system_prompt": "test"})
    
    results = []
    errors = []
    
    def load_config():
        try:
            config = manager.load_prompt_config("v001")
            results.append(config)
        except Exception as e:
            errors.append(e)
    
    # 启动 10 个并发线程
    threads = [threading.Thread(target=load_config) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # 验证无错误，所有结果一致
    assert len(errors) == 0
    assert len(results) == 10
    assert all(r == results[0] for r in results)
```

---

## 8. 错误信息必须清晰

**规则**: 所有异常必须包含足够的上下文信息用于调试

**强制要求**:
- 包含实际输入值
- 包含期望格式/范围
- 包含操作失败的具体原因
- 不泄露敏感信息（如完整路径、密钥）

**示例**:
```python
# ❌ 错误：信息不足
if not version_id.startswith("v"):
    raise ValueError("Invalid version")

# ✅ 正确：清晰的错误信息
if not version_id.startswith("v"):
    raise ValueError(
        f"Invalid version format: '{version_id}'. "
        f"Expected format: vXXX (e.g., v001, v002)"
    )

# ❌ 错误：泄露敏感信息
raise ValueError(f"Cannot access {full_path}")

# ✅ 正确：隐藏敏感路径
raise ValueError(
    f"Cannot access version directory for '{version_id}'. "
    f"Check permissions and disk space."
)
```

---

## 检查清单

在提交代码前，使用此清单验证：

### Metrics
- [ ] 所有定义的 metrics 都有对应的 `.inc()`/`.observe()`/`.set()` 调用
- [ ] 每个 metric 都有测试验证其被正确使用

### 字符串解析
- [ ] 所有 `int()`/`float()` 转换都有 try-except
- [ ] 所有解析操作都验证输入格式
- [ ] 错误信息包含实际输入值和期望格式
- [ ] 边界条件有测试覆盖

### 安全
- [ ] 所有文件路径输入都验证了路径遍历
- [ ] 使用 `is_relative_to()` 验证最终路径
- [ ] 测试覆盖路径遍历尝试

### 重试逻辑
- [ ] 所有 `@retry` 装饰器都有测试验证重试触发
- [ ] 测试覆盖重试耗尽场景
- [ ] 测试覆盖非重试异常

### Circuit Breaker
- [ ] 测试所有状态转换（CLOSED/OPEN/HALF_OPEN）
- [ ] 测试排除的异常类型

### 格式转换
- [ ] 所有格式转换函数都有测试
- [ ] 测试覆盖所有输入类型
- [ ] 测试 Unicode 保留

### 并发
- [ ] 共享状态使用锁保护
- [ ] 测试并发访问场景

### 错误信息
- [ ] 所有异常包含清晰的上下文
- [ ] 不泄露敏感信息

---

## CI 集成

将这些检查集成到 CI 流水线：

```yaml
# .github/workflows/bug-prevention.yml
name: Bug Prevention Checks
on: [push, pull_request]

jobs:
  check-metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check metrics usage
        run: python scripts/check_metrics_usage.py
  
  check-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security scan
        run: |
          pip install bandit
          bandit -r src/ -ll
  
  check-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          pip install -e ".[dev]"
          pytest tests/ -v --cov=src --cov-report=term-missing
          # 验证覆盖率 >= 90%
          coverage report --fail-under=90
```

---

## 版本历史

- **1.0.0** (2026-04-23): 基于 bug audit 发现的 3 个 Critical 和 4 个 Warning 问题制定初始规则
