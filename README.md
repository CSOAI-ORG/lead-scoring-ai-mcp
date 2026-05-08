<div align="center">

# Lead Scoring Ai MCP

**MCP server for lead scoring ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-lead-scoring-ai-mcp)](https://pypi.org/project/meok-lead-scoring-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Lead Scoring Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `score_lead` | Score a lead based on firmographic data |
| `add_lead` | Add a new lead to tracking |
| `update_lead_activity` | Record lead activity |
| `get_lead_score` | Get current score for a lead |
| `get_all_leads` | Get all leads with scores |
| `get_lead_activities` | Get activity history for a lead |
| `get_lead_timeline` | Get engagement timeline for a lead |
| `predict_conversion` | Predict conversion probability |
| `get_priority_leads` | Get leads by priority threshold |
| `track_engagement_trend` | Get engagement trend over time |

## Installation

```bash
pip install meok-lead-scoring-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "lead-scoring-ai": {
      "command": "python",
      "args": ["-m", "meok_lead_scoring_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 10 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
