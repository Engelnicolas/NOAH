---
name: github
description: NOAH conventions for GitHub work with the gh CLI — PRs, issues, CI runs, merges. Use for any GitHub operation.
---

Use `gh` (GitHub CLI) for all GitHub interactions. Prefer it over raw `git` or API calls.

```bash
# View open PRs
gh pr list

# Review PR details and diff
gh pr view <number> --comments
gh pr diff <number>

# Create a PR (always use HEREDOC for body)
gh pr create --title "..." --body "$(cat <<'EOF'
## Summary
- …
EOF
)"

# Check CI status
gh pr checks <number>

# Merge a PR (only when explicitly asked)
gh pr merge <number> --squash

# View and create issues
gh issue list
gh issue view <number>
gh issue create --title "..." --body "..."

# Fetch workflow run logs
gh run list --limit 10
gh run view <run-id> --log-failed
```

**Rules:**
- Never push or merge without explicit user confirmation.
- Always use `--squash` for merges unless the user specifies otherwise.
- When referencing a branch or SHA, verify it exists with `gh` or `git` before acting.
