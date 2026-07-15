from hello_agents.protocols import A2AClient

# 创建客户端连接到研究员Agent
client = A2AClient("http://localhost:5000")
# 发送研究请求
response = client.execute_skill("research", "research AI在医疗领域的应用")
print(f"收到响应:{response.get("result")}")