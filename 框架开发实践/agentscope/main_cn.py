# -*- coding: utf-8 -*-
"""
三国狼人杀 - 基于AgentScope 2.0.2的中文版狼人杀游戏
融合三国演义角色和传统狼人杀玩法
"""
import asyncio
import os
import random
from typing import List, Dict, Optional, Any

from dotenv import load_dotenv
load_dotenv(override=True)

from agentscope.agent import Agent
from agentscope.model import DashScopeChatModel
from agentscope.credential import DashScopeCredential
from agentscope.formatter import DashScopeMultiAgentFormatter
from agentscope.message import Msg, TextBlock

from prompt_cn import ChinesePrompts
from game_roles import GameRoles
from structured_output_cn import (
    DiscussionModelCN,
    get_vote_model_cn,
    WitchActionModelCN,
    get_seer_model_cn,
    get_hunter_model_cn,
    WerewolfKillModelCN,
)
from utils_cn import (
    check_winning_cn,
    majority_vote_cn,
    get_chinese_name,
    format_player_list,
    GameModerator,
    MAX_GAME_ROUND,
    MAX_DISCUSSION_ROUND,
)


# ============================================================
# 辅助函数
# ============================================================

async def _get_agent_messages(agent: Agent) -> list:
    """获取 Agent 当前的上下文消息列表，用于结构化输出调用"""
    return (await agent._prepare_model_input())["messages"]


async def _structured_reply(agent: Agent, model_cls: type) -> dict:
    """让 Agent 以指定结构化模型生成回复，返回解析后的 dict"""
    messages = await _get_agent_messages(agent)
    result = await agent.model.generate_structured_output(messages, model_cls)
    return result.content


def _make_announcement(name: str, text: str) -> Msg:
    """创建一个用户消息（模拟主持人的公告）"""
    return Msg(
        name=name,
        content=[TextBlock(text=text)],
        role="user",
    )


# ============================================================
# 游戏主类
# ============================================================

class ThreeKingdomsWerewolfGame:
    """三国狼人杀游戏主类"""

    def __init__(self):
        self.players: Dict[str, Agent] = {}
        self.roles: Dict[str, str] = {}
        self.moderator = GameModerator()
        self.alive_players: List[Agent] = []
        self.werewolves: List[Agent] = []
        self.villagers: List[Agent] = []
        self.seer: List[Agent] = []
        self.witch: List[Agent] = []
        self.hunter: List[Agent] = []

        # 女巫道具状态
        self.witch_has_antidote = True
        self.witch_has_poison = True

    async def create_player(self, role: str, character: str) -> Agent:
        """创建具有三国背景的玩家"""
        name = get_chinese_name(character)
        self.roles[name] = role

        # 仅从 .env 文件读取配置
        api_key = os.environ["api_key"]
        model_name = os.environ.get("model_name", "qwen-max")
        base_url = os.environ.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")

        agent = Agent(
            name=name,
            system_prompt=ChinesePrompts.get_role_prompt(role, character),
            model=DashScopeChatModel(
                credential=DashScopeCredential(
                    api_key=api_key,
                    base_url=base_url,
                ),
                model=model_name,
                stream=True,
                formatter=DashScopeMultiAgentFormatter(),
            ),
        )

        # 角色身份确认
        confirm_msg = _make_announcement(
            self.moderator.name,
            f"【{name}】你在这场三国狼人杀中扮演{GameRoles.get_role_desc(role)}，"
            f"你的角色是{character}。{GameRoles.get_role_ability(role)}"
        )
        await agent.observe(confirm_msg)

        self.players[name] = agent
        return agent

    async def setup_game(self, player_count: int = 6):
        """设置游戏"""
        print("🎮 开始设置三国狼人杀游戏...")

        # 获取角色配置
        roles = GameRoles.get_standard_setup(player_count)
        characters = random.sample([
            "刘备", "关羽", "张飞", "诸葛亮", "赵云",
            "曹操", "司马懿", "周瑜", "孙权"
        ], player_count)

        # 创建玩家
        for i, (role, character) in enumerate(zip(roles, characters)):
            agent = await self.create_player(role, character)
            self.alive_players.append(agent)

            # 分配到对应阵营
            if role == "狼人":
                self.werewolves.append(agent)
            elif role == "预言家":
                self.seer.append(agent)
            elif role == "女巫":
                self.witch.append(agent)
            elif role == "猎人":
                self.hunter.append(agent)
            else:
                self.villagers.append(agent)

        print(f"✅ 游戏设置完成，共{len(self.alive_players)}名玩家")
        print(f"   存活玩家：{format_player_list(self.alive_players)}")

    # ============================================================
    # 夜晚阶段
    # ============================================================

    async def werewolf_phase(self, round_num: int):
        """狼人阶段"""
        if not self.werewolves:
            return None

        print(f"\n🐺 狼人请睁眼，选择今晚要击杀的目标...")

        # 初始公告
        init_msg = _make_announcement(
            self.moderator.name,
            f"狼人们，请讨论今晚的击杀目标。存活玩家：{format_player_list(self.alive_players)}"
        )

        # 先让所有狼人收到初始公告
        for wolf in self.werewolves:
            await wolf.observe(init_msg)

        # 讨论阶段
        for round_idx in range(MAX_DISCUSSION_ROUND):
            for wolf in self.werewolves:
                try:
                    response = await wolf.reply()
                    # 广播给其他狼人
                    for other in self.werewolves:
                        if other != wolf:
                            await other.observe(response)
                except Exception as e:
                    print(f"⚠️ {wolf.name} 讨论出错：{e}")

        # 投票击杀
        votes = {}
        for wolf in self.werewolves:
            try:
                result = await _structured_reply(wolf, WerewolfKillModelCN)
                target = result.get("target")
                votes[wolf.name] = target
                print(f"  {wolf.name} 投票击杀：{target}")
            except Exception as e:
                print(f"⚠️ {wolf.name} 的击杀投票失败：{e}")
                # 随机选择一个非狼人目标
                valid_targets = [p.name for p in self.alive_players
                                 if p.name not in [w.name for w in self.werewolves]]
                votes[wolf.name] = random.choice(valid_targets) if valid_targets else None

        killed_player, vote_count = majority_vote_cn(votes)
        print(f"  狼人投票结果：击杀 {killed_player}（{vote_count}票）")
        return killed_player

    async def seer_phase(self):
        """预言家阶段"""
        if not self.seer:
            return

        seer_agent = self.seer[0]
        print(f"\n🔮 预言家 {seer_agent.name} 请睁眼，选择要查验的玩家...")

        try:
            # 提醒预言家当前存活玩家（避免查验已死亡玩家）
            alive_names = [p.name for p in self.alive_players]
            hint = _make_announcement(
                self.moderator.name,
                f"当前存活玩家：{'、'.join(alive_names)}。请从中选择一人查验。"
            )
            await seer_agent.observe(hint)

            result = await _structured_reply(
                seer_agent,
                get_seer_model_cn(self.alive_players),
            )
            target_name = result.get("target")
            if not target_name:
                print(f"⚠️ 预言家未选择查验目标")
                return

            target_role = self.roles.get(target_name, "村民")
            result_msg = f"查验结果：{target_name}是{'狼人' if target_role == '狼人' else '好人'}"
            print(f"  {result_msg}")

            await seer_agent.observe(_make_announcement(
                self.moderator.name, result_msg,
            ))
        except Exception as e:
            print(f"⚠️ 预言家查验失败：{e}")

    async def witch_phase(self, killed_player: str):
        """女巫阶段"""
        if not self.witch:
            return killed_player, None

        witch_agent = self.witch[0]
        print(f"\n🧙‍♀️ 女巫 {witch_agent.name} 请睁眼...")

        # 告知女巫死亡信息
        death_info = f"今晚{killed_player}被狼人击杀" if killed_player else "今晚平安无事"
        await witch_agent.observe(_make_announcement(self.moderator.name, death_info))

        saved_player = None
        poisoned_player = None

        try:
            result = await _structured_reply(witch_agent, WitchActionModelCN)

            if result.get("use_antidote") and self.witch_has_antidote:
                if killed_player:
                    saved_player = killed_player
                    self.witch_has_antidote = False
                    print(f"  女巫使用解药救了 {killed_player}")
                    await witch_agent.observe(_make_announcement(
                        self.moderator.name, f"你使用解药救了{killed_player}"
                    ))

            if result.get("use_poison") and self.witch_has_poison:
                poisoned_player = result.get("target_name")
                if poisoned_player:
                    self.witch_has_poison = False
                    print(f"  女巫使用毒药毒杀了 {poisoned_player}")
                    await witch_agent.observe(_make_announcement(
                        self.moderator.name, f"你使用毒药毒杀了{poisoned_player}"
                    ))
        except Exception as e:
            print(f"⚠️ 女巫行动失败：{e}，视为不使用技能")

        # 确定最终死亡玩家
        final_killed = killed_player if not saved_player else None
        return final_killed, poisoned_player

    async def hunter_phase(self, shot_by_hunter: str):
        """猎人阶段"""
        if not self.hunter:
            return None

        hunter_agent = self.hunter[0]
        if hunter_agent.name != shot_by_hunter:
            return None

        print(f"\n🏹 猎人 {hunter_agent.name} 发动技能，可以带走一名玩家...")

        try:
            result = await _structured_reply(
                hunter_agent,
                get_hunter_model_cn(self.alive_players),
            )

            if result.get("shoot"):
                target = result.get("target")
                if target:
                    print(f"  猎人 {hunter_agent.name} 开枪带走了 {target}")
                    return target
                else:
                    print(f"⚠️ 猎人选择开枪但未指定目标，视为放弃")
        except Exception as e:
            print(f"⚠️ 猎人技能使用失败：{e}，视为放弃开枪")

        return None

    def update_alive_players(self, dead_players: List[str]):
        """更新存活玩家列表"""
        for dead_name in dead_players:
            if dead_name:
                print(f"💀 {dead_name} 已死亡")
                self.alive_players = [p for p in self.alive_players if p.name != dead_name]
                self.werewolves = [p for p in self.werewolves if p.name != dead_name]
                self.villagers = [p for p in self.villagers if p.name != dead_name]
                self.seer = [p for p in self.seer if p.name != dead_name]
                self.witch = [p for p in self.witch if p.name != dead_name]
                self.hunter = [p for p in self.hunter if p.name != dead_name]

    # ============================================================
    # 白天阶段
    # ============================================================

    async def day_phase(self, round_num: int):
        """白天阶段"""
        await self.moderator.day_announcement(round_num)

        # 讨论公告
        discuss_msg = _make_announcement(
            self.moderator.name,
            f"现在开始自由讨论。存活玩家：{format_player_list(self.alive_players)}"
        )

        # 所有存活玩家收到讨论公告
        for player in self.alive_players:
            await player.observe(discuss_msg)

        # 每人发言一轮（顺序发言）
        for player in self.alive_players:
            try:
                response = await player.reply()
                print(f"  💬 {player.name}：{_extract_text(response)}")
                # 广播给其他玩家
                for other in self.alive_players:
                    if other != player:
                        await other.observe(response)
            except Exception as e:
                print(f"⚠️ {player.name} 发言出错：{e}")

        # 投票阶段
        print(f"\n  🗳️ 开始投票...")
        VoteModelCN = get_vote_model_cn(self.alive_players)
        votes = {}

        for player in self.alive_players:
            try:
                result = await _structured_reply(player, VoteModelCN)
                vote_target = result.get("vote")
                votes[player.name] = vote_target
                print(f"  {player.name} 投票淘汰：{vote_target}")
            except Exception as e:
                print(f"⚠️ {player.name} 的投票无效：{e}，视为弃票")
                votes[player.name] = None

        voted_out, vote_count = majority_vote_cn(votes)
        await self.moderator.vote_result_announcement(voted_out, vote_count)

        return voted_out

    # ============================================================
    # 游戏主循环
    # ============================================================

    async def run_game(self):
        """运行游戏主循环"""
        try:
            await self.setup_game()

            for round_num in range(1, MAX_GAME_ROUND + 1):
                print(f"\n{'='*50}")
                print(f"🌙 === 第{round_num}轮游戏开始 ===")
                print(f"{'='*50}")

                # ---- 夜晚阶段 ----
                await self.moderator.night_announcement(round_num)

                # 狼人击杀
                killed_player = await self.werewolf_phase(round_num)

                # 预言家查验
                await self.seer_phase()

                # 女巫行动
                final_killed, poisoned_player = await self.witch_phase(killed_player)

                # 更新死亡玩家
                night_deaths = [p for p in [final_killed, poisoned_player] if p]
                self.update_alive_players(night_deaths)

                # 死亡公告
                await self.moderator.death_announcement(night_deaths)

                # 检查胜利条件
                winner = check_winning_cn(self.alive_players, self.roles)
                if winner:
                    await self.moderator.game_over_announcement(winner)
                    return

                # ---- 白天阶段 ----
                voted_out = await self.day_phase(round_num)

                # 猎人技能
                hunter_shot = await self.hunter_phase(voted_out)

                # 更新死亡玩家
                day_deaths = [p for p in [voted_out, hunter_shot] if p]
                self.update_alive_players(day_deaths)

                # 检查胜利条件
                winner = check_winning_cn(self.alive_players, self.roles)
                if winner:
                    await self.moderator.game_over_announcement(winner)
                    return

                print(f"第{round_num}轮结束，存活玩家：{format_player_list(self.alive_players)}")

        except Exception as e:
            print(f"❌ 游戏运行出错：{e}")
            import traceback
            traceback.print_exc()


# ============================================================
# 辅助函数
# ============================================================

def _extract_text(msg: Msg) -> str:
    """从 Msg 中提取纯文本内容"""
    if msg.content:
        for block in msg.content:
            if hasattr(block, 'text'):
                return block.text[:100]  # 截断显示
    return "..."


async def main():
    """主函数 — 所有配置仅从 .env 文件读取"""
    if "api_key" not in os.environ:
        print("❌ 请在 .env 文件中配置 api_key")
        return

    print("🎮 欢迎来到三国狼人杀！")
    game = ThreeKingdomsWerewolfGame()
    await game.run_game()


if __name__ == "__main__":
    asyncio.run(main())
