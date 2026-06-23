# AgentScope 框架知识总结

> 版本: 2.0.2 | 基于实际安装版本源码分析

---

## 一、框架概览

AgentScope 是一个多智能体（Multi-Agent）框架，核心理念是让每个 Agent 独立执行 **ReAct（推理+行动）循环**，通过消息传递和工具调用来完成复杂任务。

### 核心模块

| 模块 | 路径 | 作用 |
|------|------|------|
| `agent` | `agentscope.agent` | Agent 类和配置（ReAct循环核心） |
| `model` | `agentscope.model` | LLM 聊天模型（8个厂商） |
| `message` | `agentscope.message` | 消息和内容块系统 |
| `formatter` | `agentscope.formatter` | 各厂商 API 格式转换器 |
| `credential` | `agentscope.credential` | API 凭证管理（8个厂商） |
| `tool` | `agentscope.tool` | 工具/Toolkit 系统 |
| `state` | `agentscope.state` | Agent 状态管理 |
| `event` | `agentscope.event` | 流式事件系统 |
| `middleware` | `agentscope.middleware` | 中间件/拦截器 |

---

## 二、Agent 类（最核心）

```python
from agentscope.agent import Agent
```

### 2.1 构造函数

```python
Agent(
    name: str,                              # Agent 唯一标识名
    system_prompt: str,                     # 系统提示词
    model: ChatModelBase,                   # LLM 模型实例
    toolkit: Toolkit | None = None,         # 工具包（Tool/MCP/Skill 注册中心）
    middlewares: list[MiddlewareBase] | None = None,  # 中间件
    state: AgentState | None = None,        # Agent 状态（含上下文）
    offloader: Offloader | None = None,     # 上下文卸载器
    model_config: ModelConfig = ModelConfig(),         # 模型重试/降级配置
    context_config: ContextConfig = ContextConfig(),   # 上下文压缩配置
    react_config: ReActConfig = ReActConfig(),         # ReAct 循环配置
)
```

### 2.2 核心方法

#### `async reply(inputs) -> Msg`

```python
# 描述: 触发 Agent 执行完整的 ReAct 循环并返回最终回复
# 参数:
#   inputs: Msg | list[Msg] | UserConfirmResultEvent | ExternalExecutionResultEvent | None
# 返回: Msg (role="assistant", name=agent.name)

# 示例
response = await agent.reply()
# 或传入外部消息
from agentscope.message import Msg, TextBlock
msg = Msg(name="user", content=[TextBlock(text="你好，请帮我查询天气")], role="user")
response = await agent.reply(msg)
# 获取文本内容
print(response.get_text_content())
```

#### `async reply_stream(inputs) -> AsyncGenerator`

```python
# 描述: 同 reply()，但以流式方式 yield AgentEvent
# 用途: 实时展示思考过程、工具调用、文本生成

# 示例
async for event in agent.reply_stream():
    if isinstance(event, TextBlockDeltaEvent):
        print(event.delta, end="", flush=True)  # 逐字输出
```

#### `async observe(msgs) -> None`

```python
# 描述: 接收外部消息存入上下文，不触发回复
# 参数: msgs: Msg | list[Msg] | None

# 示例: 三国狼人杀中的角色通知
confirm_msg = Msg(
    name="主持人",
    content=[TextBlock(text="你是曹操，扮演狼人。目标是消灭所有好人。")],
    role="user",
)
await agent.observe(confirm_msg)
```

#### `async compress_context(context_config=None) -> None`

```python
# 描述: 当 token 超过阈值（context_size * trigger_ratio）时，自动压缩旧上下文
# 原理: 调用 generate_structured_output 让 LLM 出结构化摘要

# 示例: 通常无需手动调用，reply() 内部会自动触发
```

### 2.3 配置类

```python
# ReAct 循环配置
from agentscope.agent import ReActConfig
ReActConfig(
    max_iters=20,          # 每轮 reply 最多推理-行动迭代次数
    stop_on_reject=False,  # 工具调用被拒绝时是否停止
)

# 上下文配置
from agentscope.agent import ContextConfig
ContextConfig(
    trigger_ratio=0.8,    # Token 达到 context_size 的 80% 时触发压缩
    reserve_ratio=0.1,    # 压缩时保留空间比例
    tool_result_limit=3000,  # 单个工具结果最大 token 数
)

# 模型配置
from agentscope.agent import ModelConfig
ModelConfig(
    max_retries=0,        # 主模型失败后重试次数
    fallback_model=None,  # 降级模型
)
```

---

## 三、模型系统

### 3.1 支持的厂商

| 类名 | 凭证类 | 特点 |
|------|--------|------|
| `OpenAIChatModel` | `OpenAICredential` | OpenAI / 兼容 API |
| `DashScopeChatModel` | `DashScopeCredential` | 阿里百炼（qwen系列） |
| `AnthropicChatModel` | `AnthropicCredential` | Claude 系列，支持 extended thinking |
| `GeminiChatModel` | `GeminiCredential` | Google Gemini |
| `DeepSeekChatModel` | `DeepSeekCredential` | DeepSeek |
| `OllamaChatModel` | `OllamaCredential` | 本地模型（无需 API Key） |
| `MoonshotChatModel` | `MoonshotCredential` | Moonshot AI (Kimi) |
| `XAIChatModel` | `XAICredential` | xAI Grok |

### 3.2 使用方法

```python
# DashScope（阿里百炼）— 三国狼人杀实际使用
from agentscope.credential import DashScopeCredential
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeMultiAgentFormatter

credential = DashScopeCredential(
    api_key="sk-xxx",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
model = DashScopeChatModel(
    credential=credential,
    model="qwen3.6-plus",
    stream=True,
    formatter=DashScopeMultiAgentFormatter(),
)
```

```python
# OpenAI 风格
from agentscope.credential import OpenAICredential
from agentscope.model import OpenAIChatModel

credential = OpenAICredential(api_key="sk-xxx")
model = OpenAIChatModel(
    credential=credential,
    model="gpt-4.1",
    parameters=OpenAIChatModel.Parameters(temperature=0.7)
)
```

### 3.3 结构化输出

```python
# generate_structured_output(messages, structured_model) -> StructuredResponse
# 用 Pydantic 模型约束 LLM 返回格式

from pydantic import BaseModel, Field

class VoteModel(BaseModel):
    vote: str = Field(description="投票目标姓名")
    reason: str = Field(description="投票理由")
    suspicion_level: int = Field(description="怀疑程度 1-10", ge=1, le=10)

# 使用（在 Agent 中）
result = await agent.model.generate_structured_output(
    messages,      # list[Msg]: 上下文消息
    VoteModel,     # Pydantic 模型类
)
# result.content 是一个 dict
print(result.content["vote"])    # "曹操"
print(result.content["reason"])  # "他发言可疑"
```

在三国狼人杀中的实际用法：
```python
async def _structured_reply(agent, model_cls):
    messages = (await agent._prepare_model_input())["messages"]
    result = await agent.model.generate_structured_output(messages, model_cls)
    return result.content  # 返回 dict
```

---

## 四、消息系统

### 4.1 Msg 类和工厂函数

```python
from agentscope.message import Msg, TextBlock
from agentscope.message import UserMsg, AssistantMsg, SystemMsg

# 方式一: 直接创建 Msg
msg = Msg(
    name="用户",
    content=[TextBlock(text="你好")],
    role="user",
)

# 方式二: 工厂函数
user_msg = UserMsg(name="user", content=[TextBlock(text="hello")])
assistant_msg = AssistantMsg(name="bot", content=[TextBlock(text="hi")])
system_msg = SystemMsg(name="system", content=[TextBlock(text="指令")])

# 重要: content 必须是 list[ContentBlock]，不是纯字符串！
# 字符串会被 pydantic 拒绝
```

### 4.2 内容块类型

```python
from agentscope.message import (
    TextBlock,        # 文本块: TextBlock(text="...")
    ThinkingBlock,    # 思考块: ThinkingBlock(thinking="...")
    ToolCallBlock,    # 工具调用: 包含 name, input (JSON string)
    ToolResultBlock,  # 工具结果: 包含 name, output
    DataBlock,        # 二进制数据: 图片、音频等
    HintBlock,         # 提示块
)

# 创建一个简单文本消息的完整写法
msg = Msg(
    name="助手",
    content=[TextBlock(text="这是一段回复")],
    role="assistant",
)

# Msg 常用方法
msg.get_text_content()   # 拼接所有文本块内容
msg.has_content_blocks(["tool_call"])  # 检查含特定块类型
```

### 4.3 消息角色限制

- `role="user"` — 只能包含 `TextBlock` 和 `DataBlock`
- `role="assistant"` — 可以包含任意 ContentBlock
- `role="system"` — 只能包含 `TextBlock`

---

## 五、工具系统

### 5.1 FunctionTool — 包装 Python 函数

```python
from agentscope.tool import Toolkit, FunctionTool

def search(query: str) -> str:
    """搜索信息。Args: query: 搜索关键词"""
    return f"搜索结果: {query}"

toolkit = Toolkit(tools=[FunctionTool(search)])
# 传入 Agent
agent = Agent(name="assistant", system_prompt="...", model=model, toolkit=toolkit)
```

### 5.2 内置工具

AgentScope 内置了一组文件操作工具：
- `Read` — 读取文件
- `Write` — 写入文件
- `Edit` — 编辑文件（精确字符串替换）
- `Bash` — 执行命令
- `Grep` — 内容搜索
- `Glob` — 文件匹配

### 5.3 MCP 集成

```python
from agentscope.mcp import MCPClient
from agentscope.tool import MCPTool

# 连接 MCP 服务器并注册工具
mcp_client = MCPClient(...)
toolkit = Toolkit(mcps=[mcp_client])
```

---

## 六、状态管理

```python
from agentscope.state import AgentState

# AgentState 字段
state = AgentState()
state.session_id     # str: 会话唯一标识
state.context        # list[Msg]: 对话上下文
state.summary        # str|list: 压缩后的摘要
state.cur_iter       # int: 当前 ReAct 迭代计数
state.reply_id       # str: 当前回复 ID
state.tool_context   # ToolContext: 工具缓存和激活状态
state.tasks_context  # TaskContext: 任务记录
```

---

## 七、事件系统

`reply_stream()` 会产出以下事件：

| 事件 | 含义 |
|------|------|
| `ReplyStartEvent` | 回复开始 |
| `ModelCallStartEvent` | LLM 调用开始 |
| `TextBlockDeltaEvent` | 文本增量（逐字输出） |
| `ThinkingBlockDeltaEvent` | 思考增量 |
| `ToolCallStartEvent` | 工具调用开始 |
| `ToolCallDeltaEvent` | 工具调用参数增量 |
| `ToolCallEndEvent` | 工具调用结束 |
| `ToolResultEndEvent` | 工具结果 |
| `ModelCallEndEvent` | LLM 调用结束（含 token 统计） |
| `ReplyEndEvent` | 回复结束 |

---

## 八、中间件系统

中间件通过 **洋葱模式** 在 Agent 执行流程的关键点插入自定义逻辑：

```python
from agentscope.middleware import MiddlewareBase

class MyMiddleware(MiddlewareBase):
    # 可选钩子（重写需要的方法即可）
    async def on_reply(self, agent, input_kwargs, next_handler):
        # 包裹整个 reply 流程
        async for event in next_handler():
            yield event

    async def on_reasoning(self, agent, input_kwargs, next_handler):
        # 包裹推理/模型调用阶段
        async for event in next_handler():
            yield event

    def on_system_prompt(self, agent, current_prompt) -> str:
        # 转换器模式：修改 system prompt
        return current_prompt + "\n你是一个诚实的助手。"

    def list_tools(self) -> list:
        # 中间件可提供工具
        return [my_extra_tool]

# 使用
agent = Agent(
    name="assistant",
    system_prompt="...",
    model=model,
    middlewares=[MyMiddleware()],
)
```

---

## 九、完整实战示例：三国狼人杀

### 创建 Agent

```python
agent = Agent(
    name="曹操",
    system_prompt="""你是曹操，在这场三国狼人杀中扮演【狼人】。
你的目标是消灭所有好人。白天要伪装成好人，用曹操的性格说话。""",
    model=DashScopeChatModel(
        credential=DashScopeCredential(api_key="sk-xxx"),
        model="qwen3.6-plus",
        stream=True,
        formatter=DashScopeMultiAgentFormatter(),
    ),
)
```

### Agent 间通信模式

```python
# 1. 发送公告给所有玩家（单播）
for player in self.alive_players:
    await player.observe(announcement_msg)

# 2. 狼人讨论（广播）
for wolf in self.werewolves:
    response = await wolf.reply()         # 狼人发言
    for other in self.werewolves:
        if other != wolf:
            await other.observe(response)  # 广播给其他狼人

# 3. 白天讨论（顺序发言）
for player in self.alive_players:
    response = await player.reply()
    print(f"  {player.name}: {response.get_text_content()}")
    for other in self.alive_players:
        if other != player:
            await other.observe(response)
```

### 结构化投票

```python
from structured_output_cn import get_vote_model_cn

VoteModel = get_vote_model_cn(self.alive_players)  # 动态约束可选目标
result = await _structured_reply(player, VoteModel)
vote_target = result["vote"]  # 例: "诸葛亮"
```

---
