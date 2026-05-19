---
name: mathbattle-write-spec
description: Use when creating or updating a spec document for a MathBattle-BE sub-function (SF)
---

# MathBattle Spec Writing Guide

## Overview

Rules and template for spec docs in `docs/01_Design/BE/sub_functions/`. Use `G01_F01_SF01.md` as the canonical example.

## File Naming

`G{group:02d}_F{feature:02d}_SF{subfunction:02d}.md`  
Example: `G01_F02_SF03.md`

## Frontmatter

```yaml
---
id: G01_F02_SF03
name: View Profile
group: G01 - User Management
feature: F02 - Profile
mvp_scope: true
---
```

## Required Sections (in order)

1. `## 📝 Change History` — **FIRST, before any other heading**
2. `# Title: ID: Name`
3. Status block (MVP scope, Function, Status, Priority, Difficulty)
4. `## 📋 Description`
5. `## 🎯 Detailed Requirements` (Input Parameters + Validation Rules + Output Schemas)
6. `## 🗏️ Business Logic` (numbered steps)
7. `## 🔄 Flow Diagram` (Mermaid flowchart)
8. `## 💻 Backend Implementation`
9. `## 📊 Security Considerations`
10. `## ✅ Test Coverage`
11. `## 🚀 API Endpoint`
12. `## 📋 Implementation Checklist`
13. `## 🔗 Related Documentation` — **LAST section**

## Change History Rules

```markdown
## 📝 Change History
| Date | Version | Changes | Status |
|------|---------|---------|--------|
| 2026-05-19 | 1.0.0 | Initial spec | 📝 Draft |
```

- Date: `YYYY-MM-DD` only
- Version: `1.0.0` initial → `1.1.0` minor → `2.0.0` major redesign
- Status: `✅ Complete` / `📝 Draft` / `🔄 In Progress` / `❌ Deprecated`
- Add new row for every change; never overwrite history

## Implementation Highlights Format

```markdown
✅ **Feature**: description   ← already implemented
⬜ **Feature**: description   ← planned, not yet done
```

## Related Documentation Format

```markdown
## 🔗 Related Documentation
- **Database Models**: `app/models/xxx.py`
- **Test Suite**: `tests/test_xxx.py`
- **API Router**: `app/api/v1/xxx.py`
- **Service Logic**: `app/services/xxx_service.py`
- **Related Specs**: G0X_FXX_SFXX
```

Point to **actual or planned code file paths**, not just spec IDs.

## Language Rules

- All text in **English** — no inline Vietnamese
- Variable names, error codes, API fields in English

## Common Mistakes

- Change History not first → move it before all other headings
- TBD / placeholder left in any section → fill or remove before committing
- Related Documentation pointing to non-existent files → use planned paths with a note
- Sections out of order → follow the numbered list above exactly

## Commit and Push

After spec is complete and self-reviewed:

```bash
git add docs/01_Design/BE/sub_functions/<filename>.md
git commit -m "docs: add spec <G0X_FXX_SFXX> <SF name>"
git push origin main
```

Commit message examples:
- `docs: add spec G01_F02_SF01 view profile`
- `docs: update spec G02_F04_SF03 submit answer — add timeout handling`
