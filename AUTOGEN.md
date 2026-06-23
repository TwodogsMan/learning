# AutoGen 框架知识总结

> 版本: 0.7.5 | 基于实际安装版本源码分析

---

## 一、框架概览

AutoGen 是微软开源的多智能体框架，分为三层：

| 层级 | 包名 | 定位 |
|------|------|------|
| **高层** | `autogen_agentchat` | 开箱即用的 Agent / Team / UI |
| **核心** | `autogen_core` | 运行时、消息路由、工具、模型抽象 |
| **扩展** | `autogen_ext` | 模型客户端、代码执行器、MCP |

### 核心理念

- Agent = 状态机：`on_messages()` 接收输入 → `Response` 输出
- Team = 多个 Agent 的协调器：内置 Publish/Subscribe 消息路由
- 一切皆 `Component`：可通过 JSON 声明式配置

---

## 二、autogen_agentchat — 高层 API

### 2.1 Agent 类型

#### `AssistantAgent` ⭐ 最核心

LLM 驱动的智能体，支持工具调用、handoff、结构化输出。

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key="sk-xxx")

agent = AssistantAgent(
    name="assistant",                    # 必须，Python 合法标识符
    model_client=model_client,           # 必须，LLM 客户端
    system_message="你是一个有用的助手",  # None = 无系统提示
    description="提供帮助的智能体",       # 用于 Speaker 选择
    tools=[my_tool],                      # 工具列表（FunctionTool 或 callable）
    handoffs=["other_agent"],             # Handoff 目标
    model_context=UnboundedChatCompletionContext(),  # 上下文管理
    reflect_on_tool_use=True,             # 工具执行后是否再调 LLM
    max_tool_iterations=3,                # 最大工具迭代次数
    output_content_type=MyPydanticModel,  # 结构化输出类型
    model_client_stream=True,             # 启用流式输出
    memory=[ListMemory()],                # 记忆存储
)
```

常用方法：

```python
# 独立运行
result = await agent.run(task="帮我找两个北美城市")

# 流式运行
async for msg in agent.run_stream(task="你好"):
    if isinstance(msg, TextMessage):
        print(msg.content)

# 作为 Team 成员时的输入处理
response = await agent.on_messages(
    [TextMessage(content="Hello", source="user")],
    cancellation_token=cancellation_token,
)
# response.chat_message 是最终的回复消息
# response.inner_messages 是中间过程（工具调用等）

# 重置和状态
await agent.on_reset(CancellationToken())
state = await agent.save_state()
await agent.load_state(state)
```

#### `CodeExecutorAgent`

```python
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

executor = DockerCommandLineCodeExecutor(work_dir="coding")
await executor.start()

agent = CodeExecutorAgent(
    name="coder",
    code_executor=executor,
    model_client=model_client,          # 可选，用于生成代码
    sources=["assistant"],               # 只执行来自指定 Agent 的代码
    approval_func=my_approval,           # 代码审批函数
)

# 审批函数
def my_approval(request: ApprovalRequest) -> ApprovalResponse:
    print(f"是否执行: {request.code[:100]}")
    return ApprovalResponse(approved=True, reason="OK")
```

#### `UserProxyAgent`

```python
# 代表人类用户
from autogen_agentchat.agents import UserProxyAgent

agent = UserProxyAgent("human", description="人类用户")
```

#### `SocietyOfMindAgent`

```python
# 内部运行一个 Team，然后把结果交给 LLM 综合成一封回复
agent = SocietyOfMindAgent(
    name="thinker",
    team=inner_team,         # 内部的 Team
    model_client=model_client,
    instruction="分析以下讨论并给出最终答案",
)
```

---

### 2.2 消息类型

```python
from autogen_agentchat.messages import (
    TextMessage,                # content: str — 纯文本
    MultiModalMessage,          # content: str|Image — 图片+文本
    StopMessage,                # content: str — 终止信号
    HandoffMessage,             # content: str, target: str — 交接
    ToolCallSummaryMessage,     # content: str — 工具调用摘要
    StructuredMessage,          # content: BaseModel — 结构化输出（泛型）
    # 事件类（流程内通知）
    ToolCallRequestEvent,       # 请求工具调用
    ToolCallExecutionEvent,     # 工具执行结果
    ThoughtEvent,               # 思考过程
    ModelClientStreamingChunkEvent,  # 流式文本增量
)
```

示例：

```python
# 创建文本消息
msg = TextMessage(content="Hello", source="Alice")

# 创建结构化消息
class WeatherInfo(BaseModel):
    city: str
    temperature: float

structured_msg = StructuredMessage[WeatherInfo](
    content=WeatherInfo(city="北京", temperature=22.0),
    source="weather_agent",
)
```

---

### 2.3 Team 类型 — 多 Agent 协调

#### `RoundRobinGroupChat` — 轮询发言

```python
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination

team = RoundRobinGroupChat(
    participants=[agent1, agent2, agent3],
    termination_condition=MaxMessageTermination(10) | TextMentionTermination("TERMINATE"),
    max_turns=20,          # 最多 20 轮
)

# 运行
result = await team.run(task="请协作完成以下任务...")

# 流式 + 控制台渲染
from autogen_agentchat.ui import Console
await Console(team.run_stream(task="你好"))
```

#### `SelectorGroupChat` ⭐ — LLM 选择发言人

```python
from autogen_agentchat.teams import SelectorGroupChat

team = SelectorGroupChat(
    participants=[travel_advisor, hotel_agent, flight_agent],
    model_client=model_client,           # 用于选择下一发言人
    selector_prompt="""根据对话历史，选择最合适的下一个发言人。
可选角色: {roles}
参与者: {participants}
对话历史: {history}""",
    allow_repeated_speaker=False,        # 是否允许连续发言
    max_selector_attempts=3,             # 选择重试次数
)

await Console(team.run_stream(task="帮我规划东京三日游"))
```

#### `Swarm` — 基于 Handoff 的发言顺序

```python
from autogen_agentchat.teams import Swarm

agent1 = AssistantAgent("Alice", model_client=model_client, handoffs=["Bob"])
agent2 = AssistantAgent("Bob", model_client=model_client)

team = Swarm(
    participants=[agent1, agent2],
    termination_condition=MaxMessageTermination(5),
)
```

#### `GraphFlow` — 有向图执行流

```python
from autogen_agentchat.teams._group_chat._graph import DiGraphBuilder

builder = DiGraphBuilder()
builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
builder.add_edge(agent_a, agent_b)
builder.add_edge(agent_b, agent_c, condition="approve")  # 条件边
builder.add_edge(agent_b, agent_a)       # 回环
g = builder.build()

team = GraphFlow(participants=..., graph=g, termination_condition=...)
```

---

### 2.4 终止条件

| 条件 | 参数 | 行为 |
|------|------|------|
| `MaxMessageTermination` | `max_messages: int` | N 条消息后终止 |
| `TextMentionTermination` | `text: str` | 消息中出现指定文本时终止 |
| `StopMessageTermination` | 无 | 收到 StopMessage 时终止 |
| `HandoffTermination` | `target: str` | 收到指定目标的 Handoff 时终止 |
| `TokenUsageTermination` | `max_total_token` 等 | Token 超限时终止 |
| `TimeoutTermination` | `timeout_seconds` | 超时终止 |
| `ExternalTermination` | 无 | 外部调用 `.set()` 终止 |
| `FunctionCallTermination` | `function_name` | 特定函数被调用时终止 |

**组合条件**：

```python
# OR: 任一满足
cond = MaxMessageTermination(10) | TextMentionTermination("TERMINATE")

# AND: 全部满足
cond = MaxMessageTermination(10) & TextMentionTermination("TERMINATE")
```

---

### 2.5 Console UI

```python
from autogen_agentchat.ui import Console

# 流式渲染 Team 的执行过程到终端
await Console(
    team.run_stream(task="你好"),
    output_stats=True,        # 最后打印 token 统计
)

# 输出示例:
# ---------- user ----------
# 你好
# ---------- assistant ----------
# 你好！有什么可以帮你的吗？
# [Stats] Total tokens: 234 | Time: 1.2s
```

---

### 2.6 状态持久化

```python
# Team 级别
state = await team.save_state()
# state 是 dict: {"agent_states": {"agent1": ..., "agent2": ...}}
await team.load_state(state)

# Agent 级别
agent_state = await assistant_agent.save_state()
await assistant_agent.load_state(agent_state)

# 重置
await team.reset()
```

---

## 三、autogen_core — 核心运行时

### 3.1 Agent 标识

```python
from autogen_core import AgentId, TopicId, AgentType

# AgentId = "type/key"
agent_id = AgentId(type="assistant_agent", key="instance_1")
agent_id_str = str(agent_id)  # "assistant_agent/instance_1"

# TopicId = "type/source"
topic = TopicId(type="chat_message", source="assistant_agent/instance_1")

# AgentType 用于工厂注册
agent_type = AgentType(type="assistant_agent")
```

### 3.2 CancellationToken

```python
from autogen_core import CancellationToken

token = CancellationToken()

# 在后台任务中使用
task = asyncio.create_task(team.run(task="...", cancellation_token=token))

# 5 秒后取消
await asyncio.sleep(5)
token.cancel()
```

### 3.3 MessageContext

每个消息处理都会携带的上下文：

```python
@dataclass
class MessageContext:
    sender: AgentId | None         # 发送者
    topic_id: TopicId | None       # 主题
    is_rpc: bool                   # 是否 RPC 调用
    cancellation_token: CancellationToken
    message_id: str                # 消息唯一 ID
```

### 3.4 RoutedAgent — 消息路由基类

```python
from autogen_core import RoutedAgent, MessageContext, event, rpc

class MyAgent(RoutedAgent):
    def __init__(self):
        super().__init__("我的智能体")

    # 事件处理器（ctx.is_rpc == False）
    @event
    async def on_notification(self, message: MyNotification, ctx: MessageContext) -> None:
        print(f"收到通知: {message}")

    # RPC 处理器（ctx.is_rpc == True）- 有返回值
    @rpc(match=lambda msg, ctx: msg.priority > 5)  # 可选的二次路由
    async def handle_query(self, message: MyQuery, ctx: MessageContext) -> QueryResult:
        return QueryResult(answer="处理完成")

    # 未匹配消息的处理
    async def on_unhandled_message(self, message, ctx):
        print(f"未处理的消息: {message}")
```

### 3.5 SingleThreadedAgentRuntime

```python
from autogen_core import SingleThreadedAgentRuntime

runtime = SingleThreadedAgentRuntime()

# 注册 Agent 工厂
await MyAgent.register(runtime, "my_agent_type", lambda: MyAgent())

# 启动
runtime.start()

# 发送消息
await runtime.send_message(
    message=MyQuery(question="你好"),
    recipient=AgentId("my_agent_type", "instance_1"),
    sender=AgentId("caller", "main"),
    cancellation_token=CancellationToken(),
)

# 优雅停止
await runtime.stop_when_idle()
```

---

### 3.6 模型抽象

#### LLM 消息类型

```python
from autogen_core.models import (
    SystemMessage,       # content: str
    UserMessage,         # content: str | list[str|Image], source: str
    AssistantMessage,    # content: str | list[FunctionCall], thought: str|None
    FunctionExecutionResultMessage,  # content: list[FunctionExecutionResult]
)

# 构建对话
messages = [
    SystemMessage(content="你是助手"),
    UserMessage(content="你好", source="user"),
]
```

#### ChatCompletionClient

```python
# 核心抽象方法
class ChatCompletionClient:
    async def create(
        self,
        messages: Sequence[LLMMessage],      # 必须
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: "auto" | "required" | "none" | Tool = "auto",
        json_output: bool | type[BaseModel] | None = None,  # 结构化输出
        extra_create_args: Mapping = {},
        cancellation_token: CancellationToken | None = None,
    ) -> CreateResult

    async def create_stream(...) -> AsyncGenerator[str | CreateResult]:
        # 流式版本：先 yield 文本块，最后 yield CreateResult

    # Token 统计
    def actual_usage() -> RequestUsage   # 上次调用的消耗
    def total_usage() -> RequestUsage    # 累计消耗
    def count_tokens(messages, tools) -> int
    def remaining_tokens(messages, tools) -> int
```

---

## 四、autogen_ext — 扩展

### 4.1 模型客户端

#### OpenAIChatCompletionClient  ⭐ 最常用

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient

client = OpenAIChatCompletionClient(
    model="gpt-4o",
    api_key="sk-xxx",
    temperature=0.7,
    max_tokens=4096,
    # 支持所有 OpenAI 兼容参数
)

# 也支持结构化输出
class Person(BaseModel):
    name: str
    age: int

result = await client.create(
    messages=[UserMessage(content="提取: 张三今年25岁", source="user")],
    json_output=Person,
)
person: Person = result.content  # Person(name="张三", age=25)
```

#### AzureOpenAIChatCompletionClient

```python
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

client = AzureOpenAIChatCompletionClient(
    model="gpt-4o",
    azure_endpoint="https://xxx.openai.azure.com",
    api_key="xxx",
    api_version="2024-08-01-preview",
)
```

### 4.2 代码执行器

```python
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

executor = DockerCommandLineCodeExecutor(
    work_dir="coding",
    timeout=60,           # 超时秒数
)

await executor.start()
result = await executor.execute_code_blocks([
    CodeBlock(code="print('hello world')", language="python"),
])
print(result.output)  # "hello world"
await executor.stop()
```

### 4.3 MCP 集成

```python
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

# 连接 MCP 服务器
params = StdioServerParams(command="python", args=["my_mcp_server.py"])
workbench = McpWorkbench(params)

# 将 MCP 工具注册给 Agent
agent = AssistantAgent(
    name="assistant",
    model_client=model_client,
    workbench=[workbench],
)
```

---

## 五、AgentScope vs AutoGen 对比

| 维度 | AgentScope | AutoGen |
|------|-----------|---------|
| **运行模型** | 每个 Agent 独立 ReAct 循环 | Publish/Subscribe 消息路由 |
| **Agent 基类** | `Agent` (ReAct 循环内置) | `AssistantAgent` (基于 `BaseChatAgent`) |
| **多 Agent** | 手动 `observe()` + `reply()` | `RoundRobinGroupChat` / `SelectorGroupChat` / `Swarm` |
| **工具调用** | `Toolkit` + `FunctionTool` | `FunctionTool` / `Workbench` / MCP |
| **结构化输出** | `generate_structured_output(PydanticModel)` | `json_output=PydanticModel` or `output_content_type` |
| **流式** | `reply_stream()` → `AgentEvent` | `run_stream()` → `BaseChatMessage | AgentEvent` |
| **消息** | `Msg(name, content=[TextBlock], role)` | `TextMessage(content, source)` |
| **状态序列化** | `AgentState` Pydantic 模型 | `save_state()` → dict |
| **终止条件** | 需自定义（检查游戏规则） | 内置 10+ 种 `TerminationCondition` |
| **LLM 厂商** | 8 种（OpenAI/百炼/Claude/Gemini/DeepSeek/Ollama/Moonshot/xAI） | 多种（通过 autogen_ext 扩展） |
| **中间件** | 5 个洋葱钩子 + 1 个转换器钩子 | 通过 `RoutedAgent` handler 装饰器 |
| **学习曲线** | 灵活但需手动编排 | 高层抽象多，Team 开箱即用 |

---

## 六、典型模式

### AutoGen: 单 Agent

```python
agent = AssistantAgent("assistant", model_client=client)
result = await agent.run(task="计算 1+1")
```

### AutoGen: 多 Agent 协作

```python
team = SelectorGroupChat(
    [researcher, writer, critic],
    model_client=client,
    termination_condition=TextMentionTermination("TERMINATE"),
)
await Console(team.run_stream(task="写一篇关于AI的文章"))
```

### AutoGen: Handoff / Swarm 模式

```python
agent = AssistantAgent("Alice", model_client=client, handoffs=["Bob", "Charlie"])
team = Swarm([agent, agent_bob, agent_charlie], ...)
```

### AgentScope: 手动编排模式（三国狼人杀）

```python
# 创建所有 Agent
for role in roles:
    agent = Agent(name=name, system_prompt=prompt, model=model)
    self.players[name] = agent

# 第一天: 狼人讨论
for wolf in werewolves:
    await wolf.observe(announcement)
for round in range(3):  # 讨论轮次
    for wolf in werewolves:
        resp = await wolf.reply()
        for other in werewolves:
            if other != wolf:
                await other.observe(resp)

# 投票（结构化输出）
for wolf in werewolves:
    result = await _structured_reply(wolf, KillVoteModel)
    votes[wolf.name] = result["target"]

# 白天讨论 + 投票
for player in alive_players:
    resp = await player.reply()
    for other in alive_players:
        await other.observe(resp)
# ...投票...
```

---
