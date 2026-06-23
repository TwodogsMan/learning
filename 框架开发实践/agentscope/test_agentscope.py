# -*- coding: utf-8 -*-
"""agentscope 三国狼人杀 - 综合单元测试

测试 agentscope 2.0.2 适配版的所有纯逻辑模块。
"""
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest


# ============================================================
# 辅助函数
# ============================================================

def make_mock_agent(name: str):
    """创建一个带有 name 属性的 Mock Agent / 对象"""
    agent = MagicMock()
    agent.name = name
    return agent


# ============================================================
# 1. 测试 game_roles.py（纯逻辑，无外部依赖）
# ============================================================

class TestGameRoles:
    """测试 GameRoles 类"""

    def test_get_role_desc_known(self):
        from game_roles import GameRoles
        assert GameRoles.get_role_desc("狼人") == "狼人"
        assert GameRoles.get_role_desc("预言家") == "预言家"
        assert GameRoles.get_role_desc("女巫") == "女巫"
        assert GameRoles.get_role_desc("猎人") == "猎人"
        assert GameRoles.get_role_desc("村民") == "村民"
        assert GameRoles.get_role_desc("守护者") == "守护者"

    def test_get_role_desc_unknown(self):
        from game_roles import GameRoles
        assert GameRoles.get_role_desc("皇帝") == "未知角色"
        assert GameRoles.get_role_desc("") == "未知角色"

    def test_get_role_ability_known(self):
        from game_roles import GameRoles
        assert "击杀" in GameRoles.get_role_ability("狼人")
        assert "查验" in GameRoles.get_role_ability("预言家")
        assert "解药" in GameRoles.get_role_ability("女巫")
        assert "开枪" in GameRoles.get_role_ability("猎人")
        assert "推理" in GameRoles.get_role_ability("村民")

    def test_get_role_ability_unknown(self):
        from game_roles import GameRoles
        assert GameRoles.get_role_ability("外星人") == "无特殊技能"

    def test_get_character_trait_known(self):
        from game_roles import GameRoles
        assert "仁德" in GameRoles.get_character_trait("刘备")
        assert "智慧" in GameRoles.get_character_trait("诸葛亮")
        assert "雄才" in GameRoles.get_character_trait("曹操")

    def test_get_character_trait_unknown(self):
        from game_roles import GameRoles
        assert GameRoles.get_character_trait("路人甲") == "性格温和，说话得体"

    def test_is_werewolf_true(self):
        from game_roles import GameRoles
        assert GameRoles.is_werewolf("狼人") is True

    def test_is_werewolf_false(self):
        from game_roles import GameRoles
        assert GameRoles.is_werewolf("预言家") is False
        assert GameRoles.is_werewolf("女巫") is False
        assert GameRoles.is_werewolf("村民") is False
        assert GameRoles.is_werewolf("猎人") is False

    def test_is_villager_team(self):
        from game_roles import GameRoles
        assert GameRoles.is_villager_team("预言家") is True
        assert GameRoles.is_villager_team("女巫") is True
        assert GameRoles.is_villager_team("猎人") is True
        assert GameRoles.is_villager_team("村民") is True
        assert GameRoles.is_villager_team("守护者") is True
        assert GameRoles.is_villager_team("狼人") is False

    def test_get_standard_setup_6_players(self):
        from game_roles import GameRoles
        roles = GameRoles.get_standard_setup(6)
        assert len(roles) == 6
        assert roles.count("狼人") == 2
        assert "预言家" in roles
        assert "女巫" in roles
        assert "村民" in roles

    def test_get_standard_setup_8_players(self):
        from game_roles import GameRoles
        roles = GameRoles.get_standard_setup(8)
        assert len(roles) == 8
        assert roles.count("狼人") == 3
        assert "预言家" in roles
        assert "女巫" in roles
        assert "猎人" in roles

    def test_get_standard_setup_9_players(self):
        from game_roles import GameRoles
        roles = GameRoles.get_standard_setup(9)
        assert len(roles) == 9
        assert "守护者" in roles

    def test_get_standard_setup_custom_count(self):
        from game_roles import GameRoles
        for count in [7, 10, 12, 15]:
            roles = GameRoles.get_standard_setup(count)
            assert len(roles) == count
            expected_wolves = max(1, count // 3)
            assert roles.count("狼人") == expected_wolves

    def test_standard_setup_12_players_has_all_specials(self):
        from game_roles import GameRoles
        roles = GameRoles.get_standard_setup(12)
        assert "预言家" in roles
        assert "女巫" in roles
        assert "猎人" in roles
        assert roles.count("狼人") == 4
        villager_count = roles.count("村民")
        assert villager_count == 12 - 4 - 3  # 3 神职


# ============================================================
# 2. 测试 prompt_cn.py（纯字符串生成逻辑）
# ============================================================

class TestChinesePrompts:
    """测试 ChinesePrompts 类"""

    def test_werewolf_prompt(self):
        from prompt_cn import ChinesePrompts
        prompt = ChinesePrompts.get_role_prompt("狼人", "曹操")
        assert "曹操" in prompt
        assert "狼人" in prompt
        assert "狼人阵营" in prompt
        assert "伪装" in prompt or "误导" in prompt
        # 新 prompt 不应包含 JSON 格式要求
        assert "reach_agreement" not in prompt
        assert "JSON" not in prompt

    def test_seer_prompt(self):
        from prompt_cn import ChinesePrompts
        prompt = ChinesePrompts.get_role_prompt("预言家", "诸葛亮")
        assert "诸葛亮" in prompt
        assert "预言家" in prompt
        assert "好人阵营" in prompt
        assert "查验" in prompt
        assert "reach_agreement" not in prompt

    def test_witch_prompt(self):
        from prompt_cn import ChinesePrompts
        prompt = ChinesePrompts.get_role_prompt("女巫", "周瑜")
        assert "周瑜" in prompt
        assert "女巫" in prompt
        assert "解药" in prompt
        assert "毒药" in prompt

    def test_hunter_prompt(self):
        from prompt_cn import ChinesePrompts
        prompt = ChinesePrompts.get_role_prompt("猎人", "张飞")
        assert "张飞" in prompt
        assert "猎人" in prompt
        assert "开枪" in prompt

    def test_villager_prompt(self):
        from prompt_cn import ChinesePrompts
        prompt = ChinesePrompts.get_role_prompt("村民", "刘备")
        assert "刘备" in prompt
        assert "村民" in prompt
        assert "推理" in prompt

    def test_no_json_format_in_prompts(self):
        """新 prompt 不应包含 JSON 格式要求——自然语言讨论"""
        from prompt_cn import ChinesePrompts
        for role in ["狼人", "预言家", "女巫", "猎人", "村民"]:
            prompt = ChinesePrompts.get_role_prompt(role, "测试角色")
            assert "json" not in prompt.lower()
            assert "JSON" not in prompt
            assert "reach_agreement" not in prompt

    def test_all_prompts_are_non_empty(self):
        from prompt_cn import ChinesePrompts
        for role in ["狼人", "预言家", "女巫", "猎人", "村民"]:
            prompt = ChinesePrompts.get_role_prompt(role, "任意角色")
            assert len(prompt) > 50
            assert "任意角色" in prompt
            assert role in prompt

    def test_prompts_encourage_natural_speech(self):
        """提示词应引导自然中文对话而非机器输出"""
        from prompt_cn import ChinesePrompts
        for role in ["狼人", "预言家", "女巫", "猎人", "村民"]:
            prompt = ChinesePrompts.get_role_prompt(role, "测试角色")
            # 应包含自然语言引导
            assert any(kw in prompt for kw in ["自然", "对话", "口吻"])


# ============================================================
# 3. 测试 structured_output_cn.py（Pydantic 模型验证）
# ============================================================

class TestStructuredOutputCN:
    """测试 Pydantic 结构化输出模型"""

    # === DiscussionModelCN ===

    def test_discussion_model_valid(self):
        from structured_output_cn import DiscussionModelCN
        data = DiscussionModelCN(
            reach_agreement=True,
            confidence_level=7,
            key_evidence="我觉得张飞说话很可疑"
        )
        assert data.reach_agreement is True
        assert data.confidence_level == 7
        assert data.key_evidence == "我觉得张飞说话很可疑"

    def test_discussion_model_min_confidence(self):
        from structured_output_cn import DiscussionModelCN
        data = DiscussionModelCN(reach_agreement=False, confidence_level=1)
        assert data.confidence_level == 1

    def test_discussion_model_max_confidence(self):
        from structured_output_cn import DiscussionModelCN
        data = DiscussionModelCN(reach_agreement=True, confidence_level=10)
        assert data.confidence_level == 10

    def test_discussion_model_invalid_confidence_low(self):
        from pydantic import ValidationError
        from structured_output_cn import DiscussionModelCN
        with pytest.raises(ValidationError):
            DiscussionModelCN(reach_agreement=True, confidence_level=0)

    def test_discussion_model_invalid_confidence_high(self):
        from pydantic import ValidationError
        from structured_output_cn import DiscussionModelCN
        with pytest.raises(ValidationError):
            DiscussionModelCN(reach_agreement=True, confidence_level=11)

    def test_discussion_model_no_evidence(self):
        from structured_output_cn import DiscussionModelCN
        data = DiscussionModelCN(reach_agreement=False, confidence_level=5)
        assert data.key_evidence is None

    # === VoteModelCN ===

    def test_vote_model_valid(self):
        from structured_output_cn import get_vote_model_cn
        agents = [make_mock_agent("刘备"), make_mock_agent("关羽"), make_mock_agent("张飞")]
        VoteModelCN = get_vote_model_cn(agents)
        data = VoteModelCN(vote="张飞", reason="他发言前后矛盾", suspicion_level=8)
        assert data.vote == "张飞"
        assert data.reason == "他发言前后矛盾"
        assert data.suspicion_level == 8

    def test_vote_model_invalid_target(self):
        from pydantic import ValidationError
        from structured_output_cn import get_vote_model_cn
        agents = [make_mock_agent("刘备"), make_mock_agent("关羽")]
        VoteModelCN = get_vote_model_cn(agents)
        with pytest.raises(ValidationError):
            VoteModelCN(vote="曹操", reason="不是候选人", suspicion_level=5)

    def test_vote_model_all_valid_targets(self):
        from structured_output_cn import get_vote_model_cn
        agents = [make_mock_agent("刘备"), make_mock_agent("关羽"), make_mock_agent("张飞")]
        VoteModelCN = get_vote_model_cn(agents)
        for name in ["刘备", "关羽", "张飞"]:
            data = VoteModelCN(vote=name, reason="测试", suspicion_level=5)
            assert data.vote == name

    # === WitchActionModelCN ===

    def test_witch_action_model_use_antidote(self):
        from structured_output_cn import WitchActionModelCN
        data = WitchActionModelCN(
            use_antidote=True, use_poison=False,
            target_name="刘备", action_reason="他是预言家，必须救"
        )
        assert data.use_antidote is True
        assert data.use_poison is False
        assert data.target_name == "刘备"

    def test_witch_action_model_use_poison(self):
        from structured_output_cn import WitchActionModelCN
        data = WitchActionModelCN(
            use_antidote=False, use_poison=True,
            target_name="曹操", action_reason="他很可疑"
        )
        assert data.use_poison is True

    def test_witch_action_model_no_action(self):
        from structured_output_cn import WitchActionModelCN
        data = WitchActionModelCN(use_antidote=False, use_poison=False)
        assert data.target_name is None
        assert data.action_reason is None

    def test_witch_action_model_both_actions(self):
        from structured_output_cn import WitchActionModelCN
        data = WitchActionModelCN(
            use_antidote=True, use_poison=True,
            target_name="赵云", action_reason="救预言家，毒狼人"
        )
        assert data.use_antidote is True
        assert data.use_poison is True

    # === SeerModelCN ===

    def test_seer_model_valid(self):
        from structured_output_cn import get_seer_model_cn
        agents = [make_mock_agent("关羽"), make_mock_agent("曹操")]
        SeerModelCN = get_seer_model_cn(agents)
        data = SeerModelCN(target="曹操", check_reason="他行为可疑", priority_level=9)
        assert data.target == "曹操"
        assert data.check_reason == "他行为可疑"
        assert data.priority_level == 9

    def test_seer_model_invalid_target(self):
        from pydantic import ValidationError
        from structured_output_cn import get_seer_model_cn
        agents = [make_mock_agent("关羽"), make_mock_agent("张飞")]
        SeerModelCN = get_seer_model_cn(agents)
        with pytest.raises(ValidationError):
            SeerModelCN(target="刘备", check_reason="他不在游戏中", priority_level=5)

    # === HunterModelCN ===

    def test_hunter_model_shoot(self):
        from structured_output_cn import get_hunter_model_cn
        agents = [make_mock_agent("曹操"), make_mock_agent("张飞")]
        HunterModelCN = get_hunter_model_cn(agents)
        data = HunterModelCN(shoot=True, target="曹操", shoot_reason="我怀疑他是狼人")
        assert data.shoot is True
        assert data.target == "曹操"

    def test_hunter_model_no_shoot(self):
        from structured_output_cn import get_hunter_model_cn
        agents = [make_mock_agent("曹操")]
        HunterModelCN = get_hunter_model_cn(agents)
        data = HunterModelCN(shoot=False)
        assert data.shoot is False
        assert data.target is None
        assert data.shoot_reason is None

    # === WerewolfKillModelCN ===

    def test_werewolf_kill_model_valid(self):
        from structured_output_cn import WerewolfKillModelCN
        data = WerewolfKillModelCN(
            target="诸葛亮",
            kill_strategy="先杀预言家，他威胁最大",
            team_coordination="我负责投票，你负责掩护"
        )
        assert data.target == "诸葛亮"
        assert "预言家" in data.kill_strategy

    def test_werewolf_kill_model_no_coordination(self):
        from structured_output_cn import WerewolfKillModelCN
        data = WerewolfKillModelCN(target="刘备", kill_strategy="看起来像预言家")
        assert data.target == "刘备"
        assert data.team_coordination is None

    # === GameAnalysisModelCN ===

    def test_game_analysis_model(self):
        from structured_output_cn import GameAnalysisModelCN
        data = GameAnalysisModelCN(
            suspected_werewolves=["曹操", "司马懿"],
            trusted_players=["刘备", "关羽"],
            key_clues=["曹操昨晚没有发言", "司马懿投票时犹豫"],
            next_strategy="建议预言家查验曹操"
        )
        assert len(data.suspected_werewolves) == 2
        assert len(data.trusted_players) == 2
        assert len(data.key_clues) == 2
        assert data.next_strategy == "建议预言家查验曹操"

    def test_game_analysis_model_empty_lists(self):
        from structured_output_cn import GameAnalysisModelCN
        data = GameAnalysisModelCN(
            suspected_werewolves=[], trusted_players=[],
            key_clues=[], next_strategy="继续观察"
        )
        assert data.suspected_werewolves == []
        assert data.trusted_players == []
        assert data.key_clues == []
        assert data.next_strategy == "继续观察"


# ============================================================
# 4. 测试 utils_cn.py（工具函数）
# ============================================================

class TestUtilsCN:
    """测试工具函数"""

    # === get_chinese_name ===

    def test_get_chinese_name_known(self):
        from utils_cn import get_chinese_name
        assert get_chinese_name("刘备") == "刘备"
        assert get_chinese_name("曹操") == "曹操"
        assert get_chinese_name("诸葛亮") == "诸葛亮"
        assert get_chinese_name("吕布") == "吕布"

    def test_get_chinese_name_none(self):
        from utils_cn import get_chinese_name, CHINESE_NAMES
        for _ in range(20):
            name = get_chinese_name(None)
            assert name in CHINESE_NAMES

    def test_get_chinese_name_unknown(self):
        from utils_cn import get_chinese_name, CHINESE_NAMES
        for _ in range(20):
            name = get_chinese_name("路人甲")
            assert name in CHINESE_NAMES

    # === format_player_list ===

    def test_format_player_list_empty(self):
        from utils_cn import format_player_list
        assert format_player_list([]) == "无玩家"

    def test_format_player_list_single(self):
        from utils_cn import format_player_list
        agent = make_mock_agent("刘备")
        assert format_player_list([agent]) == "刘备"

    def test_format_player_list_multiple(self):
        from utils_cn import format_player_list
        agents = [make_mock_agent("刘备"), make_mock_agent("关羽"), make_mock_agent("张飞")]
        result = format_player_list(agents)
        assert result == "刘备、关羽、张飞"

    def test_format_player_list_with_roles(self):
        from utils_cn import format_player_list
        agent1 = make_mock_agent("刘备")
        agent1.role = "村民"
        agent2 = make_mock_agent("曹操")
        agent2.role = "狼人"
        result = format_player_list([agent1, agent2], show_roles=True)
        assert "村民" in result
        assert "狼人" in result

    # === majority_vote_cn ===

    def test_majority_vote_clear_winner(self):
        from utils_cn import majority_vote_cn
        votes = {"刘备": "曹操", "关羽": "曹操", "张飞": "刘备"}
        winner, count = majority_vote_cn(votes)
        assert winner == "曹操"
        assert count == 2

    def test_majority_vote_tie(self):
        from utils_cn import majority_vote_cn
        votes = {"刘备": "曹操", "关羽": "张飞"}
        winner, count = majority_vote_cn(votes)
        assert count == 1
        assert winner in ["曹操", "张飞"]

    def test_majority_vote_empty(self):
        from utils_cn import majority_vote_cn
        winner, count = majority_vote_cn({})
        assert winner == "无人"
        assert count == 0

    def test_majority_vote_unanimous(self):
        from utils_cn import majority_vote_cn
        votes = {"刘备": "曹操", "关羽": "曹操", "张飞": "曹操", "诸葛亮": "曹操"}
        winner, count = majority_vote_cn(votes)
        assert winner == "曹操"
        assert count == 4

    def test_majority_vote_all_none(self):
        """所有人弃票（值为None）时返回 None"""
        from utils_cn import majority_vote_cn
        votes = {"刘备": None, "关羽": None}
        winner, count = majority_vote_cn(votes)
        assert count == 0
        assert winner is None

    # === check_winning_cn ===

    def test_check_winning_villager_win(self):
        from utils_cn import check_winning_cn
        agents = [make_mock_agent("刘备"), make_mock_agent("关羽"), make_mock_agent("张飞")]
        roles = {"刘备": "村民", "关羽": "预言家", "张飞": "女巫"}
        result = check_winning_cn(agents, roles)
        assert result is not None
        assert "好人阵营" in result

    def test_check_winning_werewolf_win(self):
        from utils_cn import check_winning_cn
        agents = [make_mock_agent("曹操"), make_mock_agent("司马懿"), make_mock_agent("刘备")]
        roles = {"曹操": "狼人", "司马懿": "狼人", "刘备": "村民"}
        result = check_winning_cn(agents, roles)
        assert result is not None
        assert "狼人阵营" in result

    def test_check_winning_continue(self):
        from utils_cn import check_winning_cn
        agents = [
            make_mock_agent("刘备"), make_mock_agent("关羽"),
            make_mock_agent("张飞"), make_mock_agent("曹操")
        ]
        roles = {"刘备": "村民", "关羽": "预言家", "张飞": "女巫", "曹操": "狼人"}
        result = check_winning_cn(agents, roles)
        assert result is None

    def test_check_winning_equal_numbers(self):
        from utils_cn import check_winning_cn
        agents = [make_mock_agent("曹操"), make_mock_agent("刘备")]
        roles = {"曹操": "狼人", "刘备": "村民"}
        result = check_winning_cn(agents, roles)
        assert result is not None
        assert "狼人阵营" in result

    def test_check_winning_all_dead(self):
        from utils_cn import check_winning_cn
        result = check_winning_cn([], {})
        assert result is not None
        assert "好人阵营" in result

    # === format_player_list_str ===

    def test_format_player_list_str_empty(self):
        from utils_cn import format_player_list_str
        assert format_player_list_str([]) == "无人"

    def test_format_player_list_str_single(self):
        from utils_cn import format_player_list_str
        assert format_player_list_str(["刘备"]) == "刘备"

    def test_format_player_list_str_multiple(self):
        from utils_cn import format_player_list_str
        result = format_player_list_str(["刘备", "关羽", "张飞"])
        assert result == "刘备、关羽、张飞"

    # === analyze_speech_pattern ===

    def test_analyze_speech_pattern_empty(self):
        from utils_cn import analyze_speech_pattern
        result = analyze_speech_pattern("")
        assert result["word_count"] == 0
        assert result["confidence_keywords"] == 0
        assert result["doubt_keywords"] == 0
        assert result["emotion_score"] == 0

    def test_analyze_speech_pattern_confident(self):
        from utils_cn import analyze_speech_pattern
        speech = "我确定张飞一定是狼人，必须投票淘汰他！"
        result = analyze_speech_pattern(speech)
        assert result["confidence_keywords"] >= 2
        assert result["word_count"] > 0

    def test_analyze_speech_pattern_doubtful(self):
        from utils_cn import analyze_speech_pattern
        speech = "我可能感觉怀疑不确定，也许是曹操"
        result = analyze_speech_pattern(speech)
        assert result["doubt_keywords"] >= 3

    def test_analyze_speech_pattern_positive(self):
        from utils_cn import analyze_speech_pattern
        speech = "这个推理好棒！我支持赞成你的观点"
        result = analyze_speech_pattern(speech)
        assert result["emotion_score"] > 0

    def test_analyze_speech_pattern_negative(self):
        from utils_cn import analyze_speech_pattern
        speech = "这个推理太差了，我反对不行，这是错误的"
        result = analyze_speech_pattern(speech)
        assert result["emotion_score"] < 0

    def test_analyze_speech_pattern_mixed(self):
        from utils_cn import analyze_speech_pattern
        speech = "这个推理好，但是有些地方错了"
        result = analyze_speech_pattern(speech)
        assert -1 <= result["emotion_score"] <= 1

    # === calculate_suspicion_score ===

    def test_calculate_suspicion_score_empty_history(self):
        from utils_cn import calculate_suspicion_score
        assert calculate_suspicion_score("刘备", []) == 0.0

    def test_calculate_suspicion_score_voted(self):
        from utils_cn import calculate_suspicion_score
        history = [{"type": "vote", "target": "刘备"}, {"type": "vote", "target": "刘备"}]
        assert calculate_suspicion_score("刘备", history) == 0.6

    def test_calculate_suspicion_score_accused(self):
        from utils_cn import calculate_suspicion_score
        assert calculate_suspicion_score("曹操", [{"type": "accusation", "target": "曹操"}]) == 0.2

    def test_calculate_suspicion_score_defended(self):
        from utils_cn import calculate_suspicion_score
        history = [{"type": "defense", "player": "关羽"}] * 3
        assert calculate_suspicion_score("关羽", history) == 0.0

    def test_calculate_suspicion_score_mixed(self):
        from utils_cn import calculate_suspicion_score
        history = [
            {"type": "vote", "target": "张飞"},
            {"type": "vote", "target": "张飞"},
            {"type": "accusation", "target": "张飞"},
            {"type": "defense", "player": "张飞"},
        ]
        assert calculate_suspicion_score("张飞", history) == pytest.approx(0.7)

    def test_calculate_suspicion_score_capped_at_1(self):
        from utils_cn import calculate_suspicion_score
        history = [{"type": "vote", "target": "刘备"}] * 5
        assert calculate_suspicion_score("刘备", history) == 1.0

    def test_calculate_suspicion_score_unrelated(self):
        from utils_cn import calculate_suspicion_score
        history = [{"type": "vote", "target": "曹操"}, {"type": "accusation", "target": "曹操"}]
        assert calculate_suspicion_score("刘备", history) == 0.0

    def test_calculate_suspicion_score_lower_bound(self):
        from utils_cn import calculate_suspicion_score
        history = [{"type": "defense", "player": "赵云"}] * 5
        assert calculate_suspicion_score("赵云", history) == 0.0


# ============================================================
# 5. 测试 GameModerator（不需要真实的 Agent）
# ============================================================

class TestGameModerator:
    """测试 GameModerator 类"""

    def test_moderator_init(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        assert moderator.name == "游戏主持人"
        assert moderator.game_log == []

    @pytest.mark.asyncio
    async def test_moderator_announce(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        msg = await moderator.announce("测试公告")
        assert msg.name == "游戏主持人"
        assert "测试公告" in str(msg.content)
        assert "测试公告" in moderator.game_log

    @pytest.mark.asyncio
    async def test_moderator_night_announcement(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        msg = await moderator.night_announcement(3)
        text = str(msg.content)
        assert "3" in text
        assert ("🌙" in text or "夜" in text or "天黑" in text)

    @pytest.mark.asyncio
    async def test_moderator_day_announcement(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        msg = await moderator.day_announcement(2)
        text = str(msg.content)
        assert "2" in text
        assert ("☀️" in text or "天亮" in text)

    @pytest.mark.asyncio
    async def test_moderator_death_announcement_no_deaths(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        msg = await moderator.death_announcement([])
        text = str(msg.content)
        assert "平安" in text

    @pytest.mark.asyncio
    async def test_moderator_death_announcement_with_deaths(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        msg = await moderator.death_announcement(["曹操", "刘备"])
        text = str(msg.content)
        assert "曹操" in text
        assert "刘备" in text

    @pytest.mark.asyncio
    async def test_moderator_vote_result(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        msg = await moderator.vote_result_announcement("张飞", 5)
        text = str(msg.content)
        assert "张飞" in text
        assert "5" in text

    @pytest.mark.asyncio
    async def test_moderator_game_over(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        msg = await moderator.game_over_announcement("好人阵营胜利！")
        text = str(msg.content)
        assert "好人阵营胜利" in text
        assert "🎉" in text

    @pytest.mark.asyncio
    async def test_moderator_game_log_accumulates(self):
        from utils_cn import GameModerator
        moderator = GameModerator()
        await moderator.announce("第一条")
        await moderator.announce("第二条")
        await moderator.announce("第三条")
        assert len(moderator.game_log) == 3
        assert moderator.game_log == ["第一条", "第二条", "第三条"]

    @pytest.mark.asyncio
    async def test_moderator_returns_msg(self):
        from utils_cn import GameModerator
        from agentscope.message import Msg
        moderator = GameModerator()
        msg = await moderator.announce("测试")
        assert isinstance(msg, Msg)
        assert msg.role == "user"  # observer 只能接收 user 或 assistant 消息


# ============================================================
# 6. 跨模块集成测试
# ============================================================

class TestCrossModuleIntegration:
    """测试跨模块交互"""

    def test_all_standard_roles_have_prompts(self):
        from prompt_cn import ChinesePrompts
        from game_roles import GameRoles
        all_roles = set()
        for count in [6, 8, 9]:
            all_roles.update(GameRoles.get_standard_setup(count))
        for role in all_roles:
            prompt = ChinesePrompts.get_role_prompt(role, "测试角色")
            assert len(prompt) > 50
            # 守护者没有专属分支，会走村民(else)分支
            if role == "守护者":
                assert "村民" in prompt
            else:
                assert role in prompt

    def test_all_small_list_characters_have_traits(self):
        from game_roles import GameRoles
        small_list = ["刘备", "关羽", "张飞", "诸葛亮", "赵云",
                      "曹操", "司马懿", "周瑜", "孙权"]
        for char in small_list:
            trait = GameRoles.get_character_trait(char)
            assert trait != "性格温和，说话得体"

    def test_all_chinese_names_in_traits(self):
        from game_roles import GameRoles
        from utils_cn import CHINESE_NAMES
        for name in CHINESE_NAMES:
            trait = GameRoles.get_character_trait(name)
            assert trait is not None

    def test_game_constants_are_reasonable(self):
        from utils_cn import MAX_GAME_ROUND, MAX_DISCUSSION_ROUND
        assert MAX_GAME_ROUND == 10
        assert MAX_DISCUSSION_ROUND == 3
        assert MAX_GAME_ROUND > MAX_DISCUSSION_ROUND

    def test_role_setup_character_count_matches(self):
        from game_roles import GameRoles
        setup = GameRoles.get_standard_setup(9)
        main_characters = ["刘备", "关羽", "张飞", "诸葛亮", "赵云",
                           "曹操", "司马懿", "周瑜", "孙权"]
        assert len(setup) == len(main_characters)

    def test_werewolf_role_team_consistency(self):
        from game_roles import GameRoles
        assert GameRoles.is_werewolf("狼人") is True
        assert GameRoles.is_villager_team("狼人") is False
        for role in ["预言家", "女巫", "猎人", "村民", "守护者"]:
            assert GameRoles.is_werewolf(role) is False
            assert GameRoles.is_villager_team(role) is True

    def test_majority_vote_with_game_roles(self):
        """集成测试：多数投票 + 角色判定"""
        from utils_cn import majority_vote_cn, check_winning_cn
        from game_roles import GameRoles
        # 模拟一天的投票结果
        votes = {"刘备": "曹操", "关羽": "曹操", "张飞": "曹操", "曹操": "刘备"}
        target, count = majority_vote_cn(votes)
        assert target == "曹操"
        assert count == 3
        # 验证曹操的确是狼人
        assert GameRoles.is_werewolf("狼人") is True

    def test_prompt_character_consistency(self):
        """提示词中的角色姓名与性格一致"""
        from prompt_cn import ChinesePrompts
        from game_roles import GameRoles
        for char in ["刘备", "关羽", "张飞", "诸葛亮", "赵云",
                      "曹操", "司马懿", "周瑜", "孙权"]:
            prompt = ChinesePrompts.get_role_prompt("村民", char)
            assert char in prompt
            trait = GameRoles.get_character_trait(char)
            assert trait != "性格温和，说话得体"


# ============================================================
# 7. 测试 main_cn.py 的辅助函数（不涉及真实 API 调用）
# ============================================================

class TestMainCNHelpers:
    """测试 main_cn.py 中的辅助函数"""

    def test_make_announcement(self):
        from main_cn import _make_announcement
        from agentscope.message import Msg
        msg = _make_announcement("主持人", "游戏开始")
        assert isinstance(msg, Msg)
        assert msg.name == "主持人"
        assert msg.role == "user"

    def test_extract_text(self):
        from main_cn import _extract_text
        from agentscope.message import Msg, TextBlock
        msg = Msg(
            name="test",
            content=[TextBlock(text="这是一条测试消息")],
            role="assistant",
        )
        text = _extract_text(msg)
        assert "测试消息" in text

    def test_extract_text_empty(self):
        from main_cn import _extract_text
        from agentscope.message import Msg, TextBlock
        msg = Msg(name="test", content=[], role="assistant")
        text = _extract_text(msg)
        assert text == "..."


# ============================================================
# 运行入口
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
