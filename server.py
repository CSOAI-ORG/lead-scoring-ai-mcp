#!/usr/bin/env python3
"""MEOK AI Labs — lead-scoring-ai-mcp MCP Server. B2B lead scoring with engagement tracking and prioritization."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any
import uuid
import sys, os

sys.path.insert(0, os.path.expanduser("~/clawd/meok-labs-engine/shared"))
from auth_middleware import check_access

from datetime import datetime, timezone
from collections import defaultdict

FREE_DAILY_LIMIT = 15
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now-t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT: return json.dumps({"error": f"Limit {FREE_DAILY_LIMIT}/day"})
    _usage[c].append(now); return None

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
import mcp.types as types

_store = {"leads": {}, "activities": [], "scoring_history": []}
server = Server("lead-scoring-ai")


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


@server.list_resources()
def handle_list_resources():
    return [Resource(uri="leads://all", name="All Leads", mimeType="application/json")]


@server.list_tools()
def handle_list_tools():
    return [
        Tool(
            name="score_lead",
            description="Score a lead based on firmographic data",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string"},
                    "company_size": {"type": "number"},
                    "budget": {"type": "number"},
                    "engagement_score": {"type": "number"},
                    "has_decision_maker_contact": {"type": "boolean"},
                    "email_verified": {"type": "boolean"},
                    "website_traffic_monthly": {"type": "number"},
                    "api_key": {"type": "string"},
                },
            },
        ),
        Tool(
            name="add_lead",
            description="Add a new lead to tracking",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string"},
                    "company_name": {"type": "string"},
                    "contact_name": {"type": "string"},
                    "contact_email": {"type": "string"},
                    "company_size": {"type": "number"},
                    "industry": {"type": "string"},
                },
                "required": ["lead_id", "company_name"],
            },
        ),
        Tool(
            name="update_lead_activity",
            description="Record lead activity",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string"},
                    "activity_type": {
                        "type": "string",
                        "enum": [
                            "email_open",
                            "email_click",
                            "website_visit",
                            "demo_request",
                            "pricing_page",
                            "proposal_view",
                            "meeting_booked",
                        ],
                    },
                    "metadata": {"type": "object"},
                },
                "required": ["lead_id", "activity_type"],
            },
        ),
        Tool(
            name="get_lead_score",
            description="Get current score for a lead",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string"},
                    "api_key": {"type": "string"},
                },
            },
        ),
        Tool(
            name="get_all_leads",
            description="Get all leads with scores",
            inputSchema={
                "type": "object",
                "properties": {
                    "priority": {
                        "type": "string",
                        "enum": ["hot", "warm", "cold", "all"],
                    },
                    "limit": {"type": "number"},
                },
            },
        ),
        Tool(
            name="get_lead_activities",
            description="Get activity history for a lead",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string"},
                    "days": {"type": "number"},
                },
            },
        ),
        Tool(
            name="get_lead_timeline",
            description="Get engagement timeline for a lead",
            inputSchema={
                "type": "object",
                "properties": {"lead_id": {"type": "string"}},
            },
        ),
        Tool(
            name="predict_conversion",
            description="Predict conversion probability",
            inputSchema={
                "type": "object",
                "properties": {"lead_id": {"type": "string"}},
                "required": ["lead_id"],
            },
        ),
        Tool(
            name="get_priority_leads",
            description="Get leads by priority threshold",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_score": {"type": "number"},
                    "limit": {"type": "number"},
                },
            },
        ),
        Tool(
            name="track_engagement_trend",
            description="Get engagement trend over time",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string"},
                    "days": {"type": "number"},
                },
            },
        ),
    ]


@server.call_tool()
def handle_call_tool(name: str, arguments: Any = None) -> list[types.TextContent]:
    args = arguments or {}
    api_key = args.get("api_key", "")
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
                ),
            )
        ]
    if err := _rl():
        return [TextContent(type="text", text=err)]

    if name == "score_lead":
        result = calculate_lead_score(args)
        lead_id = args.get("lead_id", create_id())

        if lead_id in _store["leads"]:
            _store["leads"]["score"] = result
            _store["leads"]["last_scored"] = datetime.now().isoformat()

        _store["scoring_history"].append(
            {
                "lead_id": lead_id,
                "score": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return [
            TextContent(
                type="text", text=json.dumps({"lead_id": lead_id, **result}, indent=2)
            )
        ]

    elif name == "add_lead":
        lead_id = args["lead_id"]
        _store["leads"][lead_id] = {
            "company_name": args["company_name"],
            "contact_name": args.get("contact_name", ""),
            "contact_email": args.get("contact_email", ""),
            "company_size": args.get("company_size", 0),
            "industry": args.get("industry", ""),
            "score": {"score": 0, "priority": "cold", "factors": []},
            "added_at": datetime.now().isoformat(),
            "last_activity": None,
        }
        return [
            TextContent(
                type="text",
                text=json.dumps({"added": True, "lead_id": lead_id}, indent=2),
            )
        ]

    elif name == "update_lead_activity":
        lead_id = args["lead_id"]
        activity_type = args["activity_type"]

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
            "metadata": args.get("metadata", {}),
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

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"activity_recorded": True, "score_boost": activity["score_boost"]},
                    indent=2,
                ),
            )
        ]

    elif name == "get_lead_score":
        lead_id = args.get("lead_id")
        if lead_id in _store["leads"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        _store["leads"][lead_id].get("score", {}), indent=2
                    ),
                )
            ]
        return [TextContent(type="text", text=json.dumps({"error": "Lead not found"}))]

    elif name == "get_all_leads":
        priority = args.get("priority", "all")
        limit = args.get("limit", 50)

        leads = list(_store["leads"].values())
        if priority != "all":
            leads = [l for l in leads if l.get("score", {}).get("priority") == priority]

        leads.sort(key=lambda x: x.get("score", {}).get("score", 0), reverse=True)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"leads": leads[:limit], "total": len(leads)}, indent=2
                ),
            )
        ]

    elif name == "get_lead_activities":
        lead_id = args.get("lead_id")
        days = args.get("days", 30)

        cutoff = datetime.now() - timedelta(days=days)
        activities = [
            a
            for a in _store["activities"]
            if a.get("lead_id") == lead_id
            and datetime.fromisoformat(a["timestamp"]) >= cutoff
        ]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"activities": activities, "count": len(activities)}, indent=2
                ),
            )
        ]

    elif name == "get_lead_timeline":
        lead_id = args.get("lead_id")
        activities = [a for a in _store["activities"] if a.get("lead_id") == lead_id]
        activities.sort(key=lambda x: x["timestamp"])

        return [
            TextContent(
                type="text", text=json.dumps({"timeline": activities}, indent=2)
            )
        ]

    elif name == "predict_conversion":
        lead_id = args["lead_id"]

        if lead_id not in _store["leads"]:
            return [
                TextContent(type="text", text=json.dumps({"error": "Lead not found"}))
            ]

        lead = _store["leads"][lead_id]
        score = lead.get("score", {}).get("score", 0)

        activities_count = sum(
            1 for a in _store["activities"] if a.get("lead_id") == lead_id
        )

        conversion_prob = min(95, (score * 0.6) + (activities_count * 3))

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "lead_id": lead_id,
                        "conversion_probability_percent": round(conversion_prob, 1),
                        "recommendation": "prioritize"
                        if conversion_prob > 50
                        else "nurture",
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "get_priority_leads":
        min_score = args.get("min_score", 70)
        limit = args.get("limit", 20)

        leads = [
            l
            for l in _store["leads"].values()
            if l.get("score", {}).get("score", 0) >= min_score
        ]
        leads.sort(key=lambda x: x.get("score", {}).get("score", 0), reverse=True)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"priority_leads": leads[:limit], "count": len(leads)}, indent=2
                ),
            )
        ]

    elif name == "track_engagement_trend":
        lead_id = args.get("lead_id")
        days = args.get("days", 30)

        cutoff = datetime.now() - timedelta(days=days)
        activities = [
            a
            for a in _store["activities"]
            if a.get("lead_id") == lead_id
            and datetime.fromisoformat(a["timestamp"]) >= cutoff
        ]

        if not activities:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"trend": "no_activity", "activities": 0}),
                )
            ]

        trend = (
            "increasing"
            if activities[-1]["score_boost"] > activities[0]["score_boost"]
            else "decreasing"
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "trend": trend,
                        "activities": len(activities),
                        "total_engagement": sum(a["score_boost"] for a in activities),
                    },
                    indent=2,
                ),
            )
        ]

    return [TextContent(type="text", text=json.dumps({"error": "Unknown tool"}))]


async def main():
    async with stdio_server(server._read_stream, server._write_stream) as (
        read_stream,
        write_stream,
    ):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="lead-scoring-ai-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
