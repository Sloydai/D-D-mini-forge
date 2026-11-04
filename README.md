# D&D Mini Forge

Claude skills for tabletop players and GMs, powered by the [Sloyd API](https://www.sloyd.ai/api).
Describe your character, or paste your whole party, and get a print-ready 28mm/32mm miniature STL
on a round base. GMs also get bestiary minis on the right base for their size category, modular
scatter terrain, gridded battle maps and 360 skyboxes.

The plugin lives in [`teams/dnd-mini-forge/`](teams/dnd-mini-forge/). Its README has the skills,
folder tree, examples and costs.

## Install

```bash
export SLOYD_CLIENT_ID=sok_live_...   # from https://api-dashboard.sloyd.ai
export SLOYD_CLIENT_SECRET=...
claude plugin marketplace add Sloydai/D-D-mini-forge
claude plugin install dnd-mini-forge@sloyd-dnd-mini-forge
```

Or in one step inside Claude Code: `/plugin install dnd-mini-forge --marketplace Sloydai/D-D-mini-forge`
