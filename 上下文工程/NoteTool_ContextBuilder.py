from typing import List, Dict, Optional

from hello_agents import SimpleAgent
from hello_agents.context import ContextBuilder, ContextConfig, ContextPacket
from hello_agents.tools import MemoryTool, RAGTool, NoteTool
from datetime import datetime
from 搭建框架.my_llm import MyLLM
from dotenv import load_dotenv
load_dotenv()

class ProjectAssistant(SimpleAgent):
    """长期项目助手,集成 NoteTool 和 ContextBuilder"""

    def __init__(self, name: str, project_name: str, **kwargs):
        super().__init__(name=name, llm=MyLLM(provider="dashscope"), **kwargs)

        self.project_name = project_name

        # 初始化工具
        self.memory_tool = MemoryTool(user_id=project_name)
        self.rag_tool = RAGTool(knowledge_base_path=f"./{project_name}_kb")
        self.note_tool = NoteTool(workspace=f"./{project_name}_notes")

        # 初始化上下文构建器
        self.context_builder = ContextBuilder(
            memory_tool=self.memory_tool,
            rag_tool=self.rag_tool,
            config=ContextConfig(max_tokens=4000)
        )

        self.conversation_history = []

    def run(self, user_input: str, note_as_action: bool = False) -> str:
        """运行助手,自动集成笔记"""

        # 1. 从 NoteTool 检索相关笔记
        relevant_notes = self._retrieve_relevant_notes(user_input)

        # 2. 将笔记转换为 ContextPacket
        note_packets = self._notes_to_packets(relevant_notes)

        # 3. 构建优化的上下文
        context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.conversation_history,
            system_instructions=self._build_system_instructions(),
            additional_packets=note_packets
        )

        # 4. 调用 LLM（ContextBuilder 返回字符串，需包装为消息格式）
        response = self.llm.invoke([{"role": "user", "content": context}])

        # 5. 如果需要,将交互记录为笔记
        if note_as_action:
            self._save_as_note(user_input, response)

        # 6. 更新对话历史
        self._update_history(user_input, response)

        return response

    def _retrieve_relevant_notes(self, query: str, limit: int = 3) -> List[Dict]:
        """检索相关笔记（直接读取 NoteTool 内部索引和文件）"""
        try:
            all_notes: List[Dict] = []

            # 1) 优先取 blocker 类型的笔记
            for idx_note in self.note_tool.notes_index.get("notes", []):
                if idx_note.get("type") == "blocker":
                    note = self._read_note_file(idx_note["id"])
                    if note:
                        all_notes.append(note)

            # 2) 关键词搜索（匹配标题/标签）
            query_lower = query.lower()
            for idx_note in self.note_tool.notes_index.get("notes", []):
                if idx_note.get("type") == "blocker":
                    continue  # 已添加
                if query_lower in idx_note.get("title", "").lower():
                    note = self._read_note_file(idx_note["id"])
                    if note:
                        all_notes.append(note)
                elif any(query_lower in t.lower() for t in idx_note.get("tags", [])):
                    note = self._read_note_file(idx_note["id"])
                    if note:
                        all_notes.append(note)

            # 3) 内容级搜索（读文件内容匹配，数量少时补位）
            if len(all_notes) < limit:
                for idx_note in self.note_tool.notes_index.get("notes", []):
                    if any(n.get("id") == idx_note["id"] for n in all_notes):
                        continue
                    note = self._read_note_file(idx_note["id"])
                    if note and query_lower in note.get("content", "").lower():
                        all_notes.append(note)
                        if len(all_notes) >= limit:
                            break

            return all_notes[:limit]

        except Exception as e:
            print(f"[WARNING] 笔记检索失败: {e}")
            return []

    def _read_note_file(self, note_id: str) -> Optional[Dict]:
        """读取单个笔记文件，返回结构化 dict"""
        note_path = self.note_tool.workspace / f"{note_id}.md"
        if not note_path.exists():
            return None
        try:
            note = self.note_tool._markdown_to_note(note_path.read_text(encoding="utf-8"))
            return note
        except Exception:
            return None

    def _notes_to_packets(self, notes: List[Dict]) -> List[ContextPacket]:
        """将笔记转换为上下文包"""
        packets = []

        for note in notes:
            content = f"[笔记:{note['title']}]\n{note['content']}"

            packets.append(ContextPacket(
                content=content,
                timestamp=datetime.fromisoformat(note['updated_at']),
                token_count=len(content) // 4,  # 简单估算
                relevance_score=0.75,  # 笔记具有较高相关性
                metadata={
                    "type": "note",
                    "note_type": note['type'],
                    "note_id": note['id']
                }
            ))

        return packets

    def _save_as_note(self, user_input: str, response: str):
        """将交互保存为笔记"""
        try:
            # 判断应该保存为什么类型的笔记
            if "问题" in user_input or "阻塞" in user_input:
                note_type = "blocker"
            elif "计划" in user_input or "下一步" in user_input:
                note_type = "action"
            else:
                note_type = "conclusion"

            self.note_tool.run({
                "action": "create",
                "title": f"{user_input[:30]}...",
                "content": f"## 问题\n{user_input}\n\n## 分析\n{response}",
                "note_type": note_type,
                "tags": [self.project_name, "auto_generated"]
            })

        except Exception as e:
            print(f"[WARNING] 保存笔记失败: {e}")

    def _build_system_instructions(self) -> str:
        """构建系统指令"""
        return f"""你是 {self.project_name} 项目的长期助手。

你的职责:
1. 基于历史笔记提供连贯的建议
2. 追踪项目进展和待解决问题
3. 在回答时引用相关的历史笔记
4. 提供具体、可操作的下一步建议

注意:
- 优先关注标记为 blocker 的问题
- 在建议中说明依据来源(笔记、记忆或知识库)
- 保持对项目整体进度的认识"""

    def _update_history(self, user_input: str, response: str):
        """更新对话历史"""
        from hello_agents.core.message import Message

        self.conversation_history.append(
            Message(content=user_input, role="user", timestamp=datetime.now())
        )
        self.conversation_history.append(
            Message(content=response, role="assistant", timestamp=datetime.now())
        )

        # 限制历史长度
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

# 使用示例
assistant = ProjectAssistant(
    name="项目助手",
    project_name="data_pipeline_refactoring"
)

# 第一次交互:记录项目状态
print("=" * 60)
print("第一次交互:")
print("=" * 60)
response = assistant.run(
    "我们已经完成了数据模型层的重构,测试覆盖率达到85%。下一步计划重构业务逻辑层。",
    note_as_action=True
)
print(response)

# 第二次交互:提出问题
print("\n" + "=" * 60)
print("第二次交互:")
print("=" * 60)
response = assistant.run(
    "在重构业务逻辑层时,我遇到了依赖版本冲突的问题,该如何解决?"
)
print(response)

# 查看笔记摘要
print("\n" + "=" * 60)
summary = assistant.note_tool.run({"action": "summary"})
print(summary)