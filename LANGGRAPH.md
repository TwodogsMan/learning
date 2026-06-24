# LangGraph 框架知识总结

> 版本: 1.2.5 | 完整的 Stateful Agent/Workflow 框架

---

## 一、框架概览

LangGraph 是 LangChain 生态中专门用于构建 **带状态的 Agent 和工作流** 的框架。核心思想：**图（Graph）= 节点（Node）+ 边（Edge）+ 状态（State）**。

```
langgraph/
  graph/         StateGraph 构建器 + 编译引擎
  prebuilt/      create_react_agent、ToolNode 等预置组件
  channels/      14 种通道（状态存储模式）
  checkpoint/    检查点/持久化系统
  pregel/        Pregel (BSP) 运行时引擎
  managed/       托管值（IsLastStep / RemainingSteps）
  func/          函数式 API（@entrypoint / @task）
  store/         跨会话持久化存储
  types/         核心类型（Command / Send / Interrupt / StreamMode）
```

**核心公式：**
```
StateGraph(schema).add_node().add_edge().compile()
→ CompiledStateGraph (本质是 LangChain Runnable)
→ invoke() / stream() / astream()
```

---

## 二、StateGraph — 图构建器

### 2.1 快速开始

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

# 1. 定义状态 Schema
class State(TypedDict):
    messages: Annotated[list, add_messages]  # add_messages = 追加合并
    step_count: int                           # LastValue = 覆盖

# 2. 定义节点函数
def my_node(state: State) -> dict:
    """节点函数：接收 state，返回 state 的部分更新"""
    return {"step_count": state["step_count"] + 1}

# 3. 构建图
builder = StateGraph(State)
builder.add_node("node_a", my_node)
builder.add_node("node_b", lambda s: {"messages": [("assistant", "done")]})

builder.add_edge(START, "node_a")           # 入口
builder.add_conditional_edges("node_a",     # 条件边
    lambda s: "node_b" if s["step_count"] > 3 else END,
)

# 4. 编译 → 可执行
graph = builder.compile()

# 5. 运行
result = graph.invoke({"messages": [("user", "hello")], "step_count": 0})
```

### 2.2 状态 Schema 的三种写法

```python
# 写法1: TypedDict（最常用）
class State(TypedDict):
    messages: Annotated[list, add_messages]  # 追加合并
    count: int                                # 默认 LastValue（覆盖）

# 写法2: Pydantic BaseModel
class State(BaseModel):
    messages: list = Field(default_factory=list)
    count: int = 0

# 写法3: dataclass
@dataclass
class State:
    messages: list = field(default_factory=list)
    count: int = 0
```

### 2.3 `Annotated[type, reducer]` — 状态合并规则

```python
from operator import add
from langgraph.graph.message import add_messages

class State(TypedDict):
    # add_messages: 按 ID 去重合并，同名消息覆盖
    messages: Annotated[list, add_messages]

    # operator.add: 列表拼接
    items: Annotated[list, add]

    # 自定义 reducer
    total: Annotated[int, lambda left, right: left + right]

    # 无 Annotated = LastValue: 新值覆盖旧值
    name: str
```

### 2.4 核心方法

```python
builder = StateGraph(StateSchema)

# 添加节点
builder.add_node("name", function)                     # 基本节点
builder.add_node("name", function, retry_policy=...)   # 带重试策略

# 添加边
builder.add_edge("A", "B")                    # 固定边 A→B
builder.add_edge(["A", "B"], "C")            # 等 A 和 B 都完成 → C（并行汇聚）
builder.add_edge(START, "start_node")         # 入口
builder.add_edge("final_node", END)           # 出口

# 条件边
builder.add_conditional_edges(
    "source",
    lambda state: "branch_a" if condition else "branch_b",
    path_map={"branch_a": "node_a", "branch_b": "node_b", END: END},
)

# 快速添加序列
builder.add_sequence([node1, node2, node3])  # 自动连边

# 编译
graph = builder.compile(
    checkpointer=MemorySaver(),           # 持久化
    interrupt_before=["human_review"],    # 节点前中断
    interrupt_after=["critical_node"],    # 节点后中断
    debug=True,                           # 调试模式
)
```

---

## 三、编译后的 Graph — 核心 API

```python
graph: CompiledStateGraph = builder.compile(checkpointer=...)

# ===== 运行 =====

# 同步
result = graph.invoke(input, config={"configurable": {"thread_id": "1"}})

# 异步
result = await graph.ainvoke(input, config)

# 流式（单模式）
for event in graph.stream(input, stream_mode="values"):
    print(event)

# 流式（多模式）
async for mode, data in graph.astream(input, stream_mode=["updates", "messages"]):
    if mode == "updates":
        print(f"节点输出: {data}")   # {node_name: output}
    elif mode == "messages":
        msg, meta = data
        print(f"[{msg.type}]: {msg.content}")

# ===== 状态管理 =====
state: StateSnapshot = graph.get_state(config)
# state.values       — 当前状态值
# state.next         — 下一步要执行的节点
# state.tasks        — 当前执行中的任务
# state.interrupts   — 中断信息

# 更新状态（外部干预）
graph.update_state(config, values={"approved": True})

# ===== 历史 =====
for snapshot in graph.get_state_history(config, limit=10):
    print(snapshot.values)

# ===== 可视化 =====
print(graph.get_graph().draw_ascii())
```

---

## 四、Stream Modes（流式模式）

```python
# values — 每步后输出完整状态
graph.stream(input, stream_mode="values")

# updates — 只输出增量变化 {node_name: output}
graph.stream(input, stream_mode="updates")

# messages — 实时输出 LLM token
graph.stream(input, stream_mode="messages")

# custom — 用户自定义流式输出
graph.stream(input, stream_mode="custom")

# debug — 调试详情
graph.stream(input, stream_mode="debug")

# 多模式同时
graph.stream(input, stream_mode=["updates", "messages", "custom"])
```

---

## 五、Prebuilt 预置组件

### 5.1 `create_react_agent` ⭐（已废弃，推荐 langchain.agents.create_agent）

```python
from langgraph.prebuilt import create_react_agent, ToolNode

# 一行创建 ReAct Agent
agent = create_react_agent(
    model="gpt-4o",                    # str | BaseChatModel | callable
    tools=[tool1, tool2],              # 工具列表
    prompt="你是一个有用的助手",         # 系统提示
    checkpointer=MemorySaver(),        # 持久化
)

result = await agent.ainvoke(
    {"messages": [("user", "帮忙搜索天气")]},
    config={"configurable": {"thread_id": "1"}},
)
```

内部结构：
```
START → agent_node → (条件判断)
                      ├─ 有 tool_calls → tools_node → agent_node
                      └─ 无 → END
```

### 5.2 `ToolNode`

```python
from langgraph.prebuilt import ToolNode, tools_condition

tool_node = ToolNode(
    tools=[tool1, tool2],
    handle_tool_errors=True,  # True/"continue"=忽略错误 / "raise"=抛异常 / callable
)

# 条件路由函数
builder.add_conditional_edges("agent", tools_condition)
# → 返回 "tools" 或 "__end__"
```

工具参数注入：

```python
from langgraph.prebuilt import InjectedState, InjectedStore, ToolRuntime

def my_tool(
    query: str,                          # LLM 传入
    state: Annotated[dict, InjectedState()],  # 自动注入全部状态
    store: Annotated[BaseStore, InjectedStore()],  # 自动注入 Store
    runtime: ToolRuntime,                 # 自动注入运行时
):
    # runtime.stream_writer()    — 自定义流式输出
    # runtime.context            — 不可变上下文
    # runtime.config             — RunnableConfig
    return f"结果: {query}"
```

---

## 六、Interrupt — 人机协作（Human-in-the-Loop）

```python
from langgraph.types import interrupt, Command

# 在节点中使用 interrupt
def approval_node(state):
    result = process(state)
    response = interrupt(f"请确认: {result}")  # 暂停执行
    # 恢复后 response = Command(resume=...) 的值
    return {"approved": response}

# 编译时设置中断点
graph = builder.compile(
    checkpointer=MemorySaver(),    # 必须有 checkpointer
    interrupt_before=["approval"],  # 进入节点前中断
    interrupt_after=["agent"],      # 执行节点后中断
)

# 运行 → 遇到中断暂停
result = graph.invoke(input, config)  # 可能返回 GraphInterrupt

# 查看中断状态
state = graph.get_state(config)
for interrupt in state.interrupts:
    print(interrupt.value)  # "请确认: ..."

# 恢复执行
graph.invoke(
    Command(resume={"approved": True}),  # 批准
    config,
)
```

---

## 七、Pregel 运行时 — BSP 执行模型

LangGraph 底层采用 **BSP (Bulk Synchronous Parallel)** 模型：

```
Step 1: Plan    → 确定哪些节点需要执行（哪些 channel 被更新了）
Step 2: Execute → 并行执行所有选中的节点
Step 3: Update  → 将节点输出写入 channel
Step N: 重复直到无节点可执行 或 达到 recursion_limit
```

### Channel 类型（14 种状态存储模式）

| Channel | 行为 |
|---------|------|
| `LastValue` | 存储最后一个值（最常用） |
| `BinaryOperatorAggregate` | 用二元操作符合并（如 `add_messages`） |
| `Topic` | 发布/订阅，`accumulate=True` 累积 |
| `EphemeralValue` | 只保留上一步的值，下一步清除 |
| `AnyValue` | 存储最后值，假设并发值相等 |
| `NamedBarrierValue` | 等待所有命名值到达后可用 |
| `DeltaChannel` | 增量通道，只存标记，重建时回放 |
| `UntrackedValue` | 存储但不写入 checkpoint |
| `LastValueAfterFinish` | 存储最后值，仅 finish() 后可用 |

---

## 八、函数式 API（`@entrypoint` / `@task`）

```python
from langgraph.func import entrypoint, task

# @task — 可重试、可缓存的子任务
@task(retry_policy=RetryPolicy(max_attempts=3))
def fetch_data(query: str) -> dict:
    return api_call(query)

# @entrypoint — 将函数编译为 Pregel 图
@entrypoint(checkpointer=MemorySaver())
def my_workflow(user_query: str, config) -> str:
    data = fetch_data(user_query).result()     # 调用 @task
    analysis = analyze(data).result()
    return analysis
```

---

## 九、Checkpoint — 持久化

```python
from langgraph.checkpoint.memory import MemorySaver

# 内存检查点（开发用）
checkpointer = MemorySaver()

# 编译时注入
graph = builder.compile(checkpointer=checkpointer)

# 每次 invoke 指定 thread_id 自动保存
config = {"configurable": {"thread_id": "user-session-123"}}
result = graph.invoke(input, config)

# 下次同 thread_id 自动加载历史
result = graph.invoke(next_input, config)  # 延续之前的对话

# 查看历史
for snapshot in graph.get_state_history(config, limit=5):
    print(f"Step {snapshot.metadata['step']}")
    print(snapshot.values)
    print(snapshot.next)  # 下一个要执行的节点
```

---

## 十、Store — 跨会话持久化

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# 在节点中使用
def my_node(state, config, *, store: BaseStore):
    # 存储跨会话数据
    store.put(("users", "preferences"), "theme", {"color": "dark"})

    # 读取
    item = store.get(("users", "preferences"), "theme")
    return state

graph = builder.compile(checkpointer=..., store=store)
```

---

## 十一、完整示例

```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# 1. State
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 2. 工具
def search(query: str) -> str:
    """搜索网络"""
    return f"搜索结果: {query}"

tools = [search]
tool_node = ToolNode(tools)

# 3. Agent 节点
def agent(state: State):
    from langchain_openai import ChatOpenAI
    model = ChatOpenAI(model="gpt-4o")
    model_with_tools = model.bind_tools(tools)
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# 4. 构建图
builder = StateGraph(State)
builder.add_node("agent", agent)
builder.add_node("tools", tool_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

# 5. 编译（带持久化）
graph = builder.compile(checkpointer=MemorySaver())

# 6. 运行
config = {"configurable": {"thread_id": "conv-1"}}
result = graph.invoke(
    {"messages": [("user", "搜索 LangGraph 的最新特性")]},
    config,
)
for msg in result["messages"]:
    if hasattr(msg, "content"):
        print(f"[{msg.type}]: {msg.content}")
```

---

## 十二、LangGraph vs 其他框架对比

| 维度 | LangGraph | AgentScope | AutoGen | CAMEL |
|------|-----------|-----------|---------|-------|
| **核心抽象** | 有向图（StateGraph） | Agent ReAct 循环 | Team + Pub/Sub | Role-Playing |
| **状态管理** | State Schema + Reducer + Channel | AgentState (Pydantic) | 无内置（手动） | Memory (ChatHistory + VectorDB) |
| **持久化** | Checkpoint (内存/Postgres/SQLite) | AgentState 序列化 | save_state() → dict | memory.save/load |
| **人机协作** | interrupt() + Command(resume=) | 无专门支持 | UserProxyAgent | Human + HumanToolkit |
| **流式** | 7 种 stream mode | reply_stream() → AgentEvent | run_stream() → Message | step() with stream=True |
| **并行执行** | BSP (自动并行) | 手动 asyncio | 内部 Pub/Sub | Workforce 自动并行 |
| **条件路由** | add_conditional_edges | 手动 if/else | SelectorGroupChat | 手动 |
| **学曲线** | 中（图思维） | 中（ReAct 思维） | 低（Team 开箱即用） | 低（ChatAgent.step） |
| **生态** | LangChain 全生态 | 独立 | 微软生态 | 独立，工具包最丰富 |
| **最适合** | 复杂多步 Workflow、审批流、Agent 编排 | 游戏模拟、灵活编排 | 团队聊天协作 | 角色扮演对话、工具密集型 |
