# Lead Scoring AI

> By [MEOK AI Labs](https://meok.ai) — B2B lead scoring with engagement tracking and prioritization

## Installation

```bash
pip install lead-scoring-ai-mcp
```

## Usage

```bash
python server.py
```

## Tools

### `score_lead`
Score a lead based on firmographic data (company size, budget, engagement, decision maker contact).

**Parameters:**
- `lead_id` (str): Lead identifier
- `company_size` (int): Number of employees
- `budget` (float): Budget amount
- `engagement_score` (float): Engagement score 0-100
- `has_decision_maker_contact` (bool): Whether decision maker is known
- `email_verified` (bool): Whether email is verified
- `website_traffic_monthly` (int): Monthly website visitors

### `add_lead`
Add a new lead to tracking.

**Parameters:**
- `lead_id` (str): Lead identifier
- `company_name` (str): Company name
- `contact_name` (str): Contact person name
- `contact_email` (str): Contact email
- `company_size` (int): Number of employees
- `industry` (str): Industry sector

### `update_lead_activity`
Record lead activity (email_open, email_click, website_visit, demo_request, pricing_page, proposal_view, meeting_booked).

**Parameters:**
- `lead_id` (str): Lead identifier
- `activity_type` (str): Type of activity
- `metadata` (dict): Additional activity metadata

### `get_lead_score`
Get current score for a lead.

### `get_all_leads`
Get all leads with scores, optionally filtered by priority (hot, warm, cold).

### `get_lead_activities`
Get activity history for a lead within a date range.

### `get_lead_timeline`
Get engagement timeline for a lead.

### `predict_conversion`
Predict conversion probability based on score and activity history.

### `get_priority_leads`
Get leads above a minimum score threshold.

### `track_engagement_trend`
Get engagement trend over time (increasing, decreasing, no_activity).

## Authentication

Free tier: 15 calls/day. Upgrade at [meok.ai/pricing](https://meok.ai/pricing) for unlimited access.

## License

MIT — MEOK AI Labs
