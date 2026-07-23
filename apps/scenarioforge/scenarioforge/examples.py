"""Two reproducible walkthroughs and their explicitly offline outputs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

EXAMPLES: dict[str, dict[str, Any]] = {
    "campus-night-market": {
        "id": "campus-night-market",
        "label": "校园夜市",
        "title": "雨季校园公益夜市",
        "goal": "在周五晚为 800 名师生举办安全、低浪费且不超预算的公益夜市。",
        "plan": (
            "活动计划周五 17:30 到 21:30 在图书馆前广场举行，设 24 个学生摊位和一处舞台。"
            "志愿者 18 人，预算 12000 元，已预订帐篷但没有室内备选场地。天气预报存在降雨可能。"
            "现场使用两个临时配电箱，食品摊位由社团自行采购。18:40 有十五分钟乐队演出，"
            "预计 19:00 达到客流峰值。主办方准备在闭场后 30 分钟内完成垃圾分类和场地恢复。"
        ),
        "constraints": [
            "总预算不得超过 12000 元",
            "不得阻塞图书馆消防通道",
            "食品安全问题必须有明确责任人",
            "降雨时必须在 30 分钟内完成取消或转场决策",
        ],
        "analysis": {
            "brief": {
                "objective": (
                    "在固定预算和安全边界内，为约 800 名师生交付一场可及时应对降雨的"
                    "公益夜市。"
                ),
                "non_negotiables": [
                    "总支出不超过 12000 元",
                    "消防通道始终畅通",
                    "食品安全责任可追溯",
                    "降雨决策窗口不超过 30 分钟",
                ],
                "assumptions": [
                    "24 个摊位能够使用已预订帐篷",
                    "18 名志愿者需要同时承担客流、舞台和清场职责",
                    "当前没有已确认的室内备选场地",
                ],
            },
            "perspectives": [
                {
                    "name": "安全负责人",
                    "concern": "高峰客流、临时配电与消防通道缺少统一布点和巡检机制。",
                    "evidence_from_plan": (
                        "计划包含 24 个摊位、舞台和两个临时配电箱，但未写明安全布点。"
                    ),
                    "severity": "critical",
                },
                {
                    "name": "食品摊主",
                    "concern": "社团自行采购导致温控、过敏原标识和留样责任不清。",
                    "evidence_from_plan": "食品摊位由社团自行采购，计划未列食品安全责任人。",
                    "severity": "high",
                },
                {
                    "name": "现场总协调",
                    "concern": "18 名志愿者在客流峰值与舞台演出重叠时可能无法覆盖全部岗位。",
                    "evidence_from_plan": "18:40 演出，19:00 客流峰值，志愿者总数只有 18 人。",
                    "severity": "high",
                },
            ],
            "scenarios": [
                {
                    "title": "开场前突发中雨",
                    "trigger": "16:45 雷达显示未来一小时持续降雨。",
                    "early_signal": "气象预警升级且广场出现积水。",
                    "impact": "电气和滑倒风险上升，帐篷无法替代室内备选场地。",
                    "response": "由总协调在 17:00 前执行取消门槛，并通过统一渠道通知摊主和参与者。",
                },
                {
                    "title": "峰值客流挤占消防通道",
                    "trigger": "19:00 入口排队超过预设缓冲区。",
                    "early_signal": "巡场人员发现通道宽度低于安全标线。",
                    "impact": "疏散能力下降，活动需要立即限流。",
                    "response": "暂停入口、单向分流并移除通道附近两个机动摊位。",
                },
                {
                    "title": "摊位出现疑似食物过敏",
                    "trigger": "参与者报告呼吸不适且无法确认食材。",
                    "early_signal": "摊位没有完整过敏原卡片。",
                    "impact": "产生健康风险且责任链不清。",
                    "response": "立即停摊、启动校医联络并由食品安全负责人封存采购与配料记录。",
                },
            ],
        },
        "decision": {
            "recommendation": "CONDITIONAL_GO",
            "rationale": "目标可实现，但室内备选、食品责任和高峰限流三个关键控制目前没有闭环。",
            "gates": [
                {
                    "condition": "确认书面降雨取消阈值和唯一发布渠道",
                    "owner": "现场总协调",
                    "deadline": "周四 18:00",
                    "fallback": "未完成则取消活动并启动退款通知",
                },
                {
                    "condition": "24 个摊位全部提交过敏原卡和采购联系人",
                    "owner": "食品安全负责人",
                    "deadline": "周五 12:00",
                    "fallback": "资料不全的摊位不得售卖食品",
                },
                {
                    "condition": "完成消防通道、配电箱和机动摊位的现场标线",
                    "owner": "安全负责人",
                    "deadline": "周五 15:30",
                    "fallback": "缩减摊位数量并取消舞台用电",
                },
            ],
            "next_48h": [
                "绘制摊位与消防通道平面图并现场走查",
                "指定食品安全负责人并收齐摊位资料",
                "建立天气监测时点、取消阈值和通知模板",
                "为 18:40 至 19:15 高峰时段重新排志愿者岗位",
            ],
            "stop_conditions": [
                "17:00 前降雨达到预设取消阈值",
                "消防通道无法保持标定宽度",
                "临时配电未通过校方安全检查",
            ],
        },
    },
    "saas-release": {
        "id": "saas-release",
        "label": "SaaS 发布",
        "title": "企业账单引擎周五发布",
        "goal": "在不影响现有客户结算的前提下，为首批 20 家企业启用新版账单引擎。",
        "plan": (
            "团队计划周五 20:00 将新版账单引擎开放给 20 家试点客户。新引擎已经通过单元测试，"
            "但只使用脱敏样本做过一次全量回放。数据库迁移不可逆，预计耗时 12 分钟。值班团队由"
            "两名后端和一名客服组成，发布后观察 30 分钟。若错误率上升，当前方案是关闭新请求，"
            "但没有旧引擎的数据回填脚本。下周一是月度出账日。"
        ),
        "constraints": [
            "不得产生重复账单",
            "任何客户数据不得离开现有生产区域",
            "错误率超过 0.5% 必须停止扩量",
            "必须在下周一出账前完成对账",
        ],
        "analysis": {
            "brief": {
                "objective": (
                    "在月度出账前，以可观测且可止损的方式向 20 家试点客户启用新版账单引擎。"
                ),
                "non_negotiables": [
                    "不产生重复账单",
                    "客户数据留在现有生产区域",
                    "错误率超过 0.5% 时停止扩量",
                    "下周一前完成对账",
                ],
                "assumptions": [
                    "一次脱敏样本回放能够覆盖主要计费路径",
                    "三人值班可以同时处理发布、监控和客户沟通",
                    "关闭新请求足以控制不可逆迁移后的影响",
                ],
            },
            "perspectives": [
                {
                    "name": "SRE",
                    "concern": "不可逆迁移没有等价回滚路径，30 分钟观察窗口也可能漏掉延迟任务。",
                    "evidence_from_plan": "迁移不可逆，且没有旧引擎的数据回填脚本。",
                    "severity": "critical",
                },
                {
                    "name": "财务运营",
                    "concern": "发布距离月度出账过近，异常对账时间不足。",
                    "evidence_from_plan": "周五晚发布，下周一即月度出账。",
                    "severity": "high",
                },
                {
                    "name": "客户支持",
                    "concern": "一名客服无法覆盖 20 家试点客户的异常通知和证据收集。",
                    "evidence_from_plan": "值班团队只有一名客服且未说明客户分级。",
                    "severity": "medium",
                },
            ],
            "scenarios": [
                {
                    "title": "延迟任务产生重复账单",
                    "trigger": "旧引擎队列在迁移后继续消费。",
                    "early_signal": "同一账单键出现两个任务来源。",
                    "impact": "违反零重复账单约束并引发客户投诉。",
                    "response": "启用幂等门禁，冻结受影响租户并用账单键执行逐笔对账。",
                },
                {
                    "title": "观察窗口后错误率上升",
                    "trigger": "批处理在发布 45 分钟后开始运行。",
                    "early_signal": "异步任务失败率与待处理队列同步增长。",
                    "impact": "30 分钟观察结束后无人及时止损。",
                    "response": "把观察覆盖到首轮批任务结束，并保留两名后端持续值班。",
                },
                {
                    "title": "不可逆字段需要回填",
                    "trigger": "新旧引擎对税率舍入规则不一致。",
                    "early_signal": "影子对账差异超过 0.1%。",
                    "impact": "无法简单切回旧引擎，周一出账受阻。",
                    "response": "发布前实现按租户回填脚本并在生产区域内演练恢复。",
                },
            ],
        },
        "decision": {
            "recommendation": "NO_GO",
            "rationale": (
                "不可逆迁移缺少回填与并行对账能力，当前发布会把技术异常直接放大为账务风险。"
            ),
            "gates": [
                {
                    "condition": "实现并演练按租户回填脚本",
                    "owner": "后端负责人",
                    "deadline": "重新排期前 24 小时",
                    "fallback": "保持旧引擎，不执行迁移",
                },
                {
                    "condition": "完成生产区域内的影子全量回放且差异低于 0.1%",
                    "owner": "财务运营与 SRE",
                    "deadline": "重新排期前 12 小时",
                    "fallback": "缩减到内部测试租户",
                },
                {
                    "condition": "监控覆盖首轮异步批任务并配置 0.5% 自动停止门槛",
                    "owner": "SRE",
                    "deadline": "发布审批前",
                    "fallback": "禁用新版账单写入",
                },
            ],
            "next_48h": [
                "取消本周五面向 20 家客户的发布窗口",
                "实现账单键幂等检查与旧引擎回填脚本",
                "用生产区域内快照执行一次影子全量回放",
                "将观察窗口延长到首轮异步任务结束",
            ],
            "stop_conditions": [
                "影子对账差异达到或超过 0.1%",
                "回填演练无法在约定恢复时限内完成",
                "值班覆盖不足以持续到首轮批任务结束",
            ],
        },
    },
}


def public_examples() -> list[dict[str, Any]]:
    keys = ("id", "label", "title", "goal", "plan", "constraints")
    return [{key: deepcopy(item[key]) for key in keys} for item in EXAMPLES.values()]


class DemoClient:
    """Returns bundled outputs only; never claims to be a live Hy3 request."""

    def __init__(self, example_id: str) -> None:
        if example_id not in EXAMPLES:
            raise ValueError("demo mode only accepts a bundled example_id")
        self.example = EXAMPLES[example_id]
        self.call_index = 0

    def complete_json(
        self, *, system: str, user: str, max_tokens: int = 2_800
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del system, user, max_tokens
        key = "analysis" if self.call_index == 0 else "decision"
        self.call_index += 1
        return deepcopy(self.example[key]), {"model": "offline-fixture", "usage": {}}
