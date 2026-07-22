import pytest

from src.metrics_engine.campaign_targets import CAMPAIGN_TYPES, TARGET_CONFIGS
from src.metrics_engine.cycle_data import build_cycle_data
from src.metrics_engine.cycle_report import generate_cycle_report


def _completed_cycle_payloads():
    campaign_id = "campaign-1"
    meta_data = {
        "campaigns": [
            {
                "id": campaign_id,
                "name": "Completed Promotion",
                "objective": "OUTCOME_SALES",
                "campaign_type": "promotional",
                "start_date": "2026-01-01",
                "end_date": "2026-01-07",
                "status": "COMPLETED",
                "effective_status": "COMPLETED",
            }
        ],
        "adsets": [
            {
                "id": "adset-winner",
                "name": "Winning audience",
                "campaign_id": campaign_id,
                "audience_type": "lookalike",
                "optimization_goal": "CONVERSATIONS",
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "daily_budget": "10000",
                "status": "COMPLETED",
                "effective_status": "COMPLETED",
            },
            {
                "id": "adset-loser",
                "name": "Losing audience",
                "campaign_id": campaign_id,
                "audience_type": "broad",
                "optimization_goal": "CONVERSATIONS",
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "daily_budget": "10000",
                "status": "COMPLETED",
                "effective_status": "COMPLETED",
            },
        ],
        "creatives": [
            {
                "id": "creative-winner",
                "name": "Winning creative",
                "theme": "proof",
                "angle": "social_proof",
                "status": "ACTIVE",
            },
            {
                "id": "creative-loser",
                "name": "Losing creative",
                "theme": "discount",
                "angle": "urgency",
                "status": "ACTIVE",
            },
        ],
        "ads": [
            {
                "id": "ad-winner",
                "name": "Winning ad",
                "adset_id": "adset-winner",
                "campaign_id": campaign_id,
                "creative": {"id": "creative-winner"},
                "start_date": "2026-01-01",
                "end_date": "2026-01-07",
                "status": "COMPLETED",
                "effective_status": "COMPLETED",
            },
            {
                "id": "ad-loser",
                "name": "Losing ad",
                "adset_id": "adset-loser",
                "campaign_id": campaign_id,
                "creative": {"id": "creative-loser"},
                "start_date": "2026-01-01",
                "end_date": "2026-01-07",
                "status": "COMPLETED",
                "effective_status": "COMPLETED",
            },
        ],
        "insights": [
            {
                "ad_id": "ad-winner",
                "adset_id": "adset-winner",
                "campaign_id": campaign_id,
                "date_start": "2026-01-07",
                "date_stop": "2026-01-07",
                "impressions": "1000",
                "reach": "900",
                "frequency": "1.11",
                "clicks": "1",
                "link_clicks": "1",
                "ctr": "0.1",
                "spend": "100",
                "cpm": "100",
                "actions": [
                    {
                        "action_type": "onsite_conversion.messaging_conversation_started_7d",
                        "value": "10",
                    }
                ],
            },
            {
                "ad_id": "ad-loser",
                "adset_id": "adset-loser",
                "campaign_id": campaign_id,
                "date_start": "2026-01-07",
                "date_stop": "2026-01-07",
                "impressions": "1000",
                "reach": "900",
                "frequency": "1.11",
                "clicks": "900",
                "link_clicks": "850",
                "ctr": "90",
                "spend": "100",
                "cpm": "100",
                "actions": [
                    {
                        "action_type": "onsite_conversion.messaging_conversation_started_7d",
                        "value": "10",
                    }
                ],
            },
        ],
    }

    conversations = []
    for index in range(10):
        delivered = index < 6
        conversations.append(
            {
                "id": f"winner-conversation-{index}",
                "started_at": "2026-01-07T10:00:00",
                "last_message_at": "2026-01-07T10:10:00",
                "language": "en",
                "cycle": 1,
                "customer": {"id": f"winner-customer-{index}"},
                "source": {
                    "platform": "meta_ctwa",
                    "campaign_id": campaign_id,
                    "ad_id": "ad-winner",
                    "creative_id": "creative-winner",
                },
                "messages": [],
                "outcome": {
                    "type": "delivered" if delivered else "ghosted",
                    "order_id": f"order-{index}" if delivered else None,
                    "total": 100 if delivered else 0,
                    "line_items": (
                        [{"product_id": "product-1", "quantity": 1, "unit_price": 100}]
                        if delivered
                        else []
                    ),
                },
            }
        )
        conversations.append(
            {
                "id": f"loser-conversation-{index}",
                "started_at": "2026-01-07T10:00:00",
                "last_message_at": "2026-01-07T10:05:00",
                "language": "en",
                "cycle": 1,
                "customer": {"id": f"loser-customer-{index}"},
                "source": {
                    "platform": "meta_ctwa",
                    "campaign_id": campaign_id,
                    "ad_id": "ad-loser",
                    "creative_id": "creative-loser",
                },
                "messages": [],
                "outcome": {"type": "ghosted"},
            }
        )

    products = [
        {
            "id": "product-1",
            "name": "Test product",
            "category": "test",
            "price": 100,
            "tags": [],
        }
    ]
    return meta_data, conversations, products


def test_all_notebook_campaign_types_have_primary_and_allocation_kpis():
    assert set(CAMPAIGN_TYPES) == {
        "awareness",
        "always_on",
        "promotional",
        "seasonal",
        "experimental",
        "launch",
        "scale",
        "retention",
    }
    for config in TARGET_CONFIGS.values():
        assert config["primary_kpis"]
        assert config["recommended_kpis"]
        assert config["allocation_kpis"]


def test_next_cycle_winner_and_loser_are_driven_by_whatsapp_outcomes_not_clicks():
    data = build_cycle_data(*_completed_cycle_payloads())
    report = generate_cycle_report(data)
    ads = report.ad_scorecard.set_index("ad_id")

    assert ads.loc["ad-winner", "delivered_orders"] == 6
    assert ads.loc["ad-winner", "next_cycle_action"] == "SCALE_NEXT_CYCLE"
    assert ads.loc["ad-winner", "recommended_budget_share_pct"] == pytest.approx(100)

    # The losing ad has 850 link clicks but no delivered order. Click volume
    # cannot rescue it because next-cycle allocation is outcome-based.
    assert ads.loc["ad-loser", "link_clicks"] == 850
    assert ads.loc["ad-loser", "next_cycle_action"] == "DO_NOT_FUND_NEXT_CYCLE"
    assert ads.loc["ad-loser", "recommended_budget_share_pct"] == 0


def test_report_contains_all_three_decision_levels_and_compact_llm_context():
    data = build_cycle_data(*_completed_cycle_payloads())
    report = generate_cycle_report(data)

    assert len(report.campaign_scorecard) == 1
    assert len(report.adset_scorecard) == 2
    assert len(report.ad_scorecard) == 2
    assert report.campaign_scorecard.loc[0, "campaign_type"] == "promotional"
    assert report.campaign_scorecard.loc[0, "primary_kpis"]

    context = report.to_llm_context()
    assert set(context) == {
        "report_purpose",
        "decision_basis",
        "data_quality",
        "campaigns",
        "adsets",
        "ads",
    }
    assert "messages" not in str(context)
