# CAMEL AI 框架知识总结

> 版本: 0.2.91a4 | 40+ 子包 | 40+ 模型后端 | 100+ 工具包

---

## 一、框架概览

CAMEL 是第一个以 **Role-Playing（角色扮演）** 为核心的 LLM 多智能体框架。核心理念：让 AI Agent 扮演不同角色（助理、用户、评论家），通过角色对话自主完成任务。

```
camel/
  agents/      智能体（ChatAgent + 10 种专用 Agent）
  messages/    消息系统（BaseMessage、FunctionCallingMessage）
  models/      40+ 模型后端 + ModelFactory + ModelManager
  societies/   多 Agent 协作（RolePlaying、BabyAGI、Workforce）
  toolkits/    100+ 内置工具包
  memories/    记忆系统（聊天历史 + 向量数据库）
  embeddings/  9 种嵌入模型
  retrievers/  6 种检索引擎
  loaders/     13 种数据加载器
  prompts/     15+ 提示词模板字典
  tasks/       任务管理
  storages/    KV / 向量 / 图 / 对象存储（15+ 后端）
  verifiers/   代码/数学/物理验证器
  runtime/     执行环境（Docker/Remote/Daytona）
```

---

## 二、智能体 — `camel.agents`

### 2.1 ChatAgent（核心）

```python
from camel.agents import ChatAgent

agent = ChatAgent(
    system_message="你是一个有帮助的助手。",
    model=model_backend,          # BaseModelBackend | ModelManager | str
    memory=ChatHistoryMemory(...), # 记忆系统
    tools=[my_tool],               # 工具列表
    message_window_size=10,        # 消息窗口大小
    max_iteration=5,               # 最大 tool-call 迭代次数
    output_language="中文",
    retry_attempts=3,
)
```

核心方法：

```python
# 同步 step — 发消息，LLM 回复 + 工具调用，循环直到终止
response: ChatAgentResponse = agent.step("帮我搜索天气")
# response.msgs   — List[BaseMessage]
# response.terminated — bool
# response.info   — Dict

# 异步 step（支持结构化输出）
response = await agent.astep("提取用户信息", response_format=UserModel)

# 工具管理
agent.add_tool(my_tool)                    # 添加单个工具
agent.add_tools([tool1, tool2])            # 批量添加
agent.remove_tool("tool_name")              # 移除工具

# 记忆管理
agent.update_memory(msg, RoleType.USER)     # 手动写入记忆
agent.clear_memory()                        # 清除记忆
agent.update_system_message("新提示词")      # 更换系统提示

# 保存/加载
agent.save_memory("memory.json")
agent.load_memory_from_path("memory.json")
```

### 2.2 专用 Agent

| Agent | 用途 |
|-------|------|
| `CriticAgent` | 评估多个选项并选出最佳 |
| `EmbodiedAgent` | 具身 Agent，可使用工具和代码解释器 |
| `KnowledgeGraphAgent` | 从内容构建知识图谱 |
| `RoleAssignmentAgent` | 根据任务生成角色名 |
| `SearchAgent` | 搜索摘要 + 相关性评估 |
| `MCPAgent` | 连接 MCP 服务器获取工具 |
| `DeductiveReasonerAgent` | 演绎推理（A→B 链） |
| `TaskSpecifyAgent` | 细化任务描述 |
| `TaskPlannerAgent` | 将任务分解为子任务 |
| `TaskCreationAgent` | 基于目标创建新任务 |
| `TaskPrioritizationAgent` | 任务优先级排序 |

---

## 三、消息系统 — `camel.messages`

### `BaseMessage`

```python
from camel.messages import BaseMessage

# 创建消息
user_msg = BaseMessage.make_user_message(
    role_name="用户",
    content="你好，请帮我写代码",
)

assistant_msg = BaseMessage.make_assistant_message(
    role_name="助手",
    content="好的，这是代码...",
)

# 转换为 OpenAI 格式
openai_msg = user_msg.to_openai_message(role_at_backend="user")

# 支持图片
msg = BaseMessage.make_user_message(
    role_name="user",
    content="描述这张图",
    image_list=[PIL_image],
    image_detail="high",
)
```

### `FunctionCallingMessage`

```python
from camel.messages import FunctionCallingMessage

# 工具调用消息
tool_call = FunctionCallingMessage(
    role_name="assistant",
    func_name="get_weather",
    args={"city": "北京"},
)
# 转 OpenAI 格式
assistant_msg = tool_call.to_openai_assistant_message()

# 工具结果消息
tool_result = FunctionCallingMessage(
    role_name="tool",
    func_name="get_weather",
    result={"temperature": 22},
    tool_call_id="call_xxx",
)
```

---

## 四、模型系统 — `camel.models`

### 4.1 ModelFactory

```python
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# 创建模型后端
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    # 或直接用字符串: model_type="gpt-4o"
)

# 也可以用简写
model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type="qwen-max",
)
```

### 4.2 ModelManager（多模型调度）

```python
from camel.models import ModelManager

manager = ModelManager(
    models=[model1, model2, model3],
    scheduling_strategy="round_robin",  # 或 "random"
)

agent = ChatAgent(model=manager, ...)
# 每次调用自动轮转模型
```

### 4.3 支持的厂商（40+）

| 厂商 | 类名 |
|------|------|
| OpenAI | `OpenAIModel` |
| Azure OpenAI | `AzureOpenAIModel` |
| Anthropic Claude | `AnthropicModel` |
| Google Gemini | `GeminiModel` |
| 阿里百炼 Qwen | `QwenModel` |
| DeepSeek | `DeepSeekModel` |
| Moonshot/Kimi | `MoonshotModel` |
| 智谱 GLM | `ZhipuAIModel` |
| Ollama | `OllamaModel` |
| vLLM | `VLLMModel` |
| 百度千帆 | `QianfanModel` |
| 字节火山 | `VolcanoModel` |
| ... | 还有 28+ 个 |

---

## 五、多智能体协作 — `camel.societies`

### 5.1 RolePlaying（经典角色扮演）

```python
from camel.societies import RolePlaying

role_playing = RolePlaying(
    assistant_role_name="Python 程序员",
    user_role_name="产品经理",
    task_prompt="开发一个 Web 爬虫",
    with_task_specify=True,        # 自动细化任务
    with_task_planner=True,        # 自动分解任务
    with_critic_in_the_loop=True,  # 加入评论家
    output_language="中文",
)

# 初始化聊天
role_playing.init_chat()

# 逐步推进
assistant_msg = ...
assistant_resp, user_resp = role_playing.step(assistant_msg)
```

### 5.2 Workforce（层次化工作组）⭐

```python
from camel.societies import Workforce

# 创建 Workforce
workforce = Workforce(
    name="软件开发团队",
    description="完成一个软件项目",
    process_simultaneously=True,  # 可并行执行的子任务并行跑
)

# 添加单 Agent 工人
coder = workforce.add_single_agent_worker(
    name="后端开发",
    role="Python 后端开发者",
    worker_config={"model": model, "tools": [sql_tool]},
)

# 添加角色扮演工人（双 Agent 对话）
pair = workforce.add_role_playing_worker(
    name="需求分析",
    role="需求分析师",
    worker_config={"model": model},
)

# 嵌套 Workforce
sub_team = Workforce("前端团队", "负责前端开发")
sub_team.add_single_agent_worker(...)
workforce.add_workforce(sub_team)

# 处理任务
task = Task(content="开发一个电商网站", id="task-1")
result = workforce.process_task(task)
```

### 5.3 BabyAGI（任务自主循环）

```python
from camel.societies import BabyAGI

# 基于 babyagi 的自主任务执行循环
# 创建 → 优先级排序 → 执行 → 创建新任务 → 循环
```

---

## 六、工具系统 — `camel.toolkits`

### 6.1 自定义工具

```python
from camel.toolkits import FunctionTool, tool

# 方式1: 包装函数
def search(query: str) -> str:
    """搜索互联网。参数 query: 搜索关键词"""
    return f"搜索结果: {query}"

search_tool = FunctionTool(search)

# 方式2: 装饰器
@tool
def calculate(expression: str) -> float:
    """计算数学表达式。参数 expression: 数学表达式"""
    return eval(expression)

# 获取 OpenAI 格式的 schema
schema = search_tool.get_openai_tool_schema()
```

### 6.2 自定义 Toolkit

```python
from camel.toolkits import BaseToolkit

class MyToolkit(BaseToolkit):
    def my_search(self, query: str) -> str:
        """搜索"""
        return f"结果: {query}"

    def my_calc(self, expr: str) -> float:
        """计算"""
        return eval(expr)

toolkit = MyToolkit(timeout=30.0)
tools = toolkit.get_tools()  # 自动生成 FunctionTool 列表
```

### 6.3 常用内置 Toolkit

| Toolkit | 功能 |
|---------|------|
| `SearchToolkit` | 网页搜索（Google/DuckDuckGo/Wikipedia） |
| `CodeExecutionToolkit` | Python 代码执行 |
| `GithubToolkit` | GitHub API（仓库/Issue/PR） |
| `SQLToolkit` | SQL 数据库操作 |
| `ExcelToolkit` | Excel 文件操作 |
| `BrowserToolkit` | 浏览器自动化（Playwright） |
| `ArxivToolkit` | ArXiv 论文搜索 |
| `GoogleMapsToolkit` | Google 地图 |
| `GmailToolkit` | Gmail 邮件 |
| `SlackToolkit` | Slack 消息 |
| `TwitterToolkit` | Twitter/X API |
| `StripeToolkit` | Stripe 支付 |
| `RetrievalToolkit` | RAG 检索 |
| `MemoryToolkit` | Agent 记忆操作 |
| `HumanToolkit` | 人类介入 |
| `MCPToolkit` | MCP 协议 |
| `DingtalkToolkit` | 钉钉消息 |
| `LarkToolkit` | 飞书消息 |
| `WeChatOfficialToolkit` | 微信公众号 |

---

## 七、记忆系统 — `camel.memories`

```python
from camel.memories import ChatHistoryMemory, VectorDBMemory, LongtermAgentMemory
from camel.memories import ScoreBasedContextCreator

# 聊天历史记忆
memory = ChatHistoryMemory(
    context_creator=ScoreBasedContextCreator(...),
    window_size=20,  # 最近 N 条消息
)

# 向量数据库记忆（语义检索）
vectordb_memory = VectorDBMemory(
    context_creator=...,
    vector_storage=QdrantStorage(...),
)

# 长期记忆 = 聊天历史 + 向量数据库
long_memory = LongtermAgentMemory(
    chat_history_block=...,
    vector_db_block=...,
)

# 用于 Agent
agent = ChatAgent(
    system_message="...",
    model=model,
    memory=memory,
)
```

---

## 八、嵌入 & 检索 — RAG 流水线

```python
from camel.embeddings import OpenAIEmbedding
from camel.retrievers import AutoRetriever
from camel.storages import QdrantStorage

# 嵌入模型
embedding = OpenAIEmbedding()
vectors = embedding.embed_list(["文本1", "文本2"])

# 向量存储
storage = QdrantStorage(
    vector_dim=1536,
    collection_name="my_docs",
)

# 自动检索器（嵌入 + 存储 + 查询）
retriever = AutoRetriever(
    embedding_model=embedding,
    vector_storage=storage,
)
retriever.process(content="长文档内容...")
results = retriever.query(query="关键问题?")
```

---

## 九、完整示例

```python
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool, SearchToolkit
from camel.societies import RolePlaying

# 1. 创建模型
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

# 2. 创建工具
toolkit = SearchToolkit()
tools = toolkit.get_tools()

# 3. 创建 Agent
agent = ChatAgent(
    system_message="你是一个研究助手，擅长搜索和分析。",
    model=model,
    tools=tools,
    output_language="中文",
)

# 4. 运行
response = agent.step("搜索最新的大语言模型发展趋势")
for msg in response.msgs:
    print(f"[{msg.role_name}]: {msg.content}")

# 5. 多 Agent 角色扮演
society = RolePlaying(
    assistant_role_name="AI 研究员",
    user_role_name="项目经理",
    task_prompt="撰写一份关于 Agent 框架的对比报告",
    model=model,
    output_language="中文",
)
```

---

## 十、CAMEL vs 其他框架对比

| 维度 | CAMEL | AgentScope | AutoGen |
|------|-------|-----------|---------|
| **核心理念** | Role-Playing 角色扮演 | ReAct 循环 | Publish/Subscribe 消息路由 |
| **Agent 类型** | ChatAgent (step 循环) | Agent (reply/observe) | AssistantAgent (RoutedAgent) |
| **多 Agent** | RolePlaying / Workforce | 手动编排 | RoundRobin / Selector / Swarm |
| **模型后端** | 40+（ModelFactory + ModelManager） | 8（各厂商独立实现） | 多种（autogen_ext） |
| **工具** | 100+ Toolkit + FunctionTool | Toolkit + FunctionTool | FunctionTool + Workbench |
| **记忆** | ChatHistory / VectorDB / Longterm | AgentState 上下文 | ChatCompletionContext |
| **RAG** | 嵌入 + 检索 + 存储全栈 | 无内置 | 无内置 |
| **人工介入** | Human + HumanToolkit | 无专门支持 | UserProxyAgent |
| **角色系统** | RoleType + SystemMessageGenerator | 手动编写系统提示 | 手动编写系统提示 |
| **适合场景** | 角色扮演对话、复杂工作流 | 灵活编排、游戏模拟 | 团队协作、微软生态 |
