from hello_agents.tools import MCPTool
from hello_agents import SimpleAgent
from 搭建框架.my_llm import MyLLM

agent = SimpleAgent(name="助手", llm=MyLLM(provider="dashscope"))

# 无需任何配置，自动使用内置演示服务器
mcp_tool = MCPTool(name='calculator')
agent.add_tool(mcp_tool)
# ✅ MCP工具 'calculator' 已展开为 6 个独立工具

# 智能体可以直接使用展开后的工具
response = agent.run("计算 25 乘以 16")
print(response)