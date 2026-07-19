"""在 Agent 中使用天气 MCP 服务器"""
from hello_agents import SimpleAgent
from hello_agents.tools import MCPTool
import os
from dotenv import load_dotenv
from 搭建框架.my_llm import HelloAgentsLLM, MyLLM

load_dotenv()

def create_weather_assistant():
    """创建天气助手"""
    llm = MyLLM(provider="dashscope")

    assistant = SimpleAgent(
        name="天气助手",
        llm=llm,
        system_prompt="你是天气助手，可以查询城市天气。使用get_weather工具查询天气，支持中文城市名。"
    )

    server_script = os.path.join(os.path.dirname(__file__), "weather_mcp_server.py")
    weather_tool = MCPTool(server_command=["python", server_script])
    assistant.add_tool(weather_tool)

    return assistant

def demo():
    """演示"""
    assistant = create_weather_assistant()
    print("\n查询北京天气：")
    response = assistant.run("北京今天天气怎么样？")
    print(f"回答：{response}\n")

def interactive():
    """交互模式"""
    assistant = create_weather_assistant()

    while True:
        user_input = input("\n你:").strip()
        if user_input.lower() in ["quit", "exit"]:
            break
        response= assistant.run(user_input)
        print(f"助手：{response}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        interactive()