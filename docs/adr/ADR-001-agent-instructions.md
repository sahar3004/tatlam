# ADR-001: Agent Instructions File Structure

## Status
Accepted

## Date
2025-12-31

## Context

The project had two instruction files for AI coding agents:
- `AGENTS.md` (263 lines) - general instructions with template noise
- `CLAUDE.md` (206 lines) - Claude-specific instructions with overlapping content

This created issues:
1. **Redundancy**: Same information repeated across files
2. **Maintenance burden**: Updates needed in multiple places
3. **Context waste**: Long files consume valuable LLM context window
4. **Inconsistency**: Different instructions in different files could conflict

## Decision

Adopt the [AGENTS.md standard](https://agents.md) as the primary instruction format with the following structure:

```
tatlam/
├── AGENTS.md                    # Primary (universal for all agents) - ~85 lines
├── CLAUDE.md → symlink          # Symlink to AGENTS.md for backward compatibility
├── .github/
│   └── copilot-instructions.md  # GitHub Copilot-specific additions
└── docs/adr/
    └── ADR-001-agent-instructions.md  # This document
```

## Rationale

1. **Single source of truth**: One file to maintain
2. **Industry standard**: AGENTS.md is used by 60K+ open-source projects
3. **Tool compatibility**: Works with Cursor, Windsurf, VS Code, Codex, Jules, and more
4. **Conciseness**: Reduced from ~470 lines to ~130 lines total (>70% reduction)
5. **Backward compatibility**: Symlink preserves any tooling that looks for `CLAUDE.md`

## Consequences

### Positive
- Less maintenance overhead
- Faster context loading for AI agents
- Consistent instructions across all AI tools
- Easier onboarding for contributors

### Negative
- Claude-specific features may need to go in `.claude/` config instead
- Initial migration effort required

## Notes

- GitHub Copilot has its own instruction file format (`.github/copilot-instructions.md`)
- Cursor uses `.cursor/rules/` but also supports `AGENTS.md`
- Windsurf uses `.windsurf/rules/` but also supports `AGENTS.md`
