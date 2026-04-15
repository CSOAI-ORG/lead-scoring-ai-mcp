#!/usr/bin/env python3
"""MEOK AI Labs — lead-scoring-ai-mcp MCP Server. B2B lead scoring with engagement tracking and prioritization."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
import sys, os

sys.path.insert(0, os.path.expanduser("~/clawd/meok-labs-engine/shared"))
from auth_middleware import check_access
from mcp.server.fastmcp import FastMCP
from collections import defaultdict

FREE_DAILY_LIMIT = 15
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now-t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT: return json.dumps({"error": f"Limit {FREE_DAILY_LIMIT}/day"})
    _usage[c].append(now); return None

_store = {"leads": {}, "activities": [], "scoring_history": []}
mcp = FastMCP("lead-scoring-ai", instructions="B2B lead scoring with engagement tracking and prioritization.")


def create_id():
    return str(uuid.uuid4())[:8]


def calculate_lead_score(data: dict) -> dict:
    score = 0
    factors = []

    company_size = data.get("company_size", 0)
    if company_size > 1000:
        score += 30
        factors.append("Enterprise company")
    elif company_size > 100:
        score += 20
        factors.append("Mid-market company")
    elif company_size > 10:
        score += 10
        factors.append("SMB")

    budget = data.get("budget", 0)
    if budget > 100000:
        score += 25
        factors.append("High budget")
    elif budget > 50000:
        score += 15
        factors.append("Medium budget")
    elif budget > 10000:
        score += 5

    engagement = data.get("engagement_score", 0)
    if engagement > 80:
        score += 25
        factors.append("Highly engaged")
    elif engagement > 50:
        score += 15
        factors.append("Moderately engaged")

    if data.get("has_decision_maker_contact"):
        score += 15
        factors.append("Has decision maker")

    if data.get("email_verified"):
        score += 5
        factors.append("Email verified")

    if data.get("website_traffic_monthly", 0) > 10000:
        score += 10
        factors.append("High traffic")

    priority = "hot" if score >= 70 else "warm" if score >= 40 else "cold"

    return {"score": min(100, score), "priority": priority, "factors": factors}


@mcp.tool()
def score_lead(lead_id: str = "", company_size: int = 0, budget: float = 0, engagement_score: float = 0, has_decision_maker_contact: bool = False, email_verified: bool = False, website_traffic_monthly: int = 0, api_key: str = "") -> str:
    """Score a lead based on firmographic data"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    data = {
        "company_size": company_size,
        "budget": budget,
        "engagement_score": engagement_score,
        "has_decision_maker_contact": has_decision_maker_contact,
        "email_verified": email_verified,
        "website_traffic_monthly": website_traffic_monthly,
    }
    result = calculate_lead_score(data)
    if not lead_id:
        lead_id = create_id()

    if lead_id in _store["leads"]:
        _store["leads"]["score"] = result
        _store["leads"]["last_scored"] = datetime.now().isoformat()

    _store["scoring_history"].append(
        {"lead_id": lead_id, "score": result, "timestamp": datetime.now().isoformat()}
    )

    return json.dumps({"lead_id": lead_id, **result}, indent=2)


@mcp.tool()
def add_lead(lead_id: str, company_name: str, contact_name: str = "", contact_email: str = "", company_size: int = 0, industry: str = "", api_key: str = "") -> str:
    """Add a new lead to tracking"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    _store["leads"][lead_id] = {
        "company_name": company_name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "company_size": company_size,
        "industry": industry,
        "score": {"score": 0, "priority": "cold", "factors": []},
        "added_at": datetime.now().isoformat(),
        "last_activity": None,
    }
    return json.dumps({"added": True, "lead_id": lead_id}, indent=2)


@mcp.tool()
def update_lead_activity(lead_id: str, activity_type: str, metadata: dict = None, api_key: str = "") -> str:
    """Record lead activity"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    engagement_boost = {
        "email_open": 5,
        "email_click": 10,
        "website_visit": 8,
        "demo_request": 25,
        "pricing_page": 15,
        "proposal_view": 20,
        "meeting_booked": 30,
    }

    activity = {
        "id": create_id(),
        "lead_id": lead_id,
        "type": activity_type,
        "metadata": metadata or {},
        "timestamp": datetime.now().isoformat(),
        "score_boost": engagement_boost.get(activity_type, 5),
    }
    _store["activities"].append(activity)

    if lead_id in _store["leads"]:
        _store["leads"][lead_id]["last_activity"] = activity["timestamp"]

        current = _store["leads"][lead_id].get("score", {}).get("score", 0)
        new_score = calculate_lead_score(
            {"engagement_score": min(100, current + activity["score_boost"])}
        )
        _store["leads"][lead_id]["score"] = new_score

    return json.dumps(
        {"activity_recorded": True, "score_boost": activity["score_boost"]}, indent=2
    )


@mcp.tool()
def get_lead_score(lead_id: str, api_key: str = "") -> str:
    """Get current score for a lead"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if lead_id in _store["leads"]:
        return json.dumps(_store["leads"][lead_id].get("score", {}), indent=2)
    return json.dumps({"error": "Lead not found"})


@mcp.tool()
def get_all_leads(priority: str = "all", limit: int = 50, api_key: str = "") -> str:
    """Get all leads with scores"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    leads = list(_store["leads"].values())
    if priority != "all":
        leads = [l for l in leads if l.get("score", {}).get("priority") == priority]

    leads.sort(key=lambda x: x.get("score", {}).get("score", 0), reverse=True)

    return json.dumps({"leads": leads[:limit], "total": len(leads)}, indent=2)


@mcp.tool()
def get_lead_activities(lead_id: str, days: int = 30, api_key: str = "") -> str:
    """Get activity history for a lead"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    cutoff = datetime.now() - timedelta(days=days)
    activities = [
        a
        for a in _store["activities"]
        if a.get("lead_id") == lead_id
        and datetime.fromisoformat(a["timestamp"]) >= cutoff
    ]

    return json.dumps({"activities": activities, "count": len(activities)}, indent=2)


@mcp.tool()
def get_lead_timeline(lead_id: str, api_key: str = "") -> str:
    """Get engagement timeline for a lead"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    activities = [a for a in _store["activities"] if a.get("lead_id") == lead_id]
    activities.sort(key=lambda x: x["timestamp"])
    return json.dumps({"timeline": activities}, indent=2)


@mcp.tool()
def predict_conversion(lead_id: str, api_key: str = "") -> str:
    """Predict conversion probability"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    if lead_id not in _store["leads"]:
        return json.dumps({"error": "Lead not found"})

    lead = _store["leads"][lead_id]
    score = lead.get("score", {}).get("score", 0)

    activities_count = sum(
        1 for a in _store["activities"] if a.get("lead_id") == lead_id
    )

    conversion_prob = min(95, (score * 0.6) + (activities_count * 3))

    return json.dumps(
        {
            "lead_id": lead_id,
            "conversion_probability_percent": round(conversion_prob, 1),
            "recommendation": "prioritize" if conversion_prob > 50 else "nurture",
        },
        indent=2,
    )


@mcp.tool()
def get_priority_leads(min_score: int = 70, limit: int = 20, api_key: str = "") -> str:
    """Get leads by priority threshold"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    leads = [
        l
        for l in _store["leads"].values()
        if l.get("score", {}).get("score", 0) >= min_score
    ]
    leads.sort(key=lambda x: x.get("score", {}).get("score", 0), reverse=True)

    return json.dumps({"priority_leads": leads[:limit], "count": len(leads)}, indent=2)


@mcp.tool()
def track_engagement_trend(lead_id: str, days: int = 30, api_key: str = "") -> str:
    """Get engagement trend over time"""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl(): return err

    cutoff = datetime.now() - timedelta(days=days)
    activities = [
        a
        for a in _store["activities"]
        if a.get("lead_id") == lead_id
        and datetime.fromisoformat(a["timestamp"]) >= cutoff
    ]

    if not activities:
        return json.dumps({"trend": "no_activity", "activities": 0})

    trend = (
        "increasing"
        if activities[-1]["score_boost"] > activities[0]["score_boost"]
        else "decreasing"
    )

    return json.dumps(
        {
            "trend": trend,
            "activities": len(activities),
            "total_engagement": sum(a["score_boost"] for a in activities),
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
