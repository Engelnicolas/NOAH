---
name: external-tools
description: NOAH conventions and safety rules for the gh and aws CLIs — PRs, issues, CI runs, merges, Route53, SSM, CloudFormation. Use for any GitHub or AWS operation.
---

# External tools

Two hard rules across both: **never push, merge, or delete without explicit user
confirmation**, and verify a target exists before acting on it.

## GitHub — `gh`

Use `gh` for all GitHub interactions, in preference to raw `git` or API calls.

```bash
gh pr list
gh pr view <number> --comments
gh pr diff <number>
gh pr checks <number>
gh pr merge <number> --squash          # only when explicitly asked
gh issue list | gh issue view <number>
gh run list --limit 10
gh run view <run-id> --log-failed
```

Create a PR with a HEREDOC body:

```bash
gh pr create --title "..." --body "$(cat <<'EOF'
## Summary
- …
EOF
)"
```

- Merges use `--squash` unless the user specifies otherwise.
- Verify a branch or SHA exists with `gh` or `git` before acting on it.

## AWS — `aws`

Credentials resolve through the standard credential chain. Never hardcode keys, and never
read or write `~/.aws/credentials` directly.

```bash
aws sts get-caller-identity            # before ANY write or delete
aws ec2 describe-instances --query "Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]" --output table
aws route53 list-hosted-zones
aws route53 list-resource-record-sets --hosted-zone-id <zone-id>   # look up before modifying
aws ssm get-parameter --name "/noah/..." --with-decryption
aws cloudformation describe-stacks --stack-name <name>
```

- Run `aws sts get-caller-identity` before any write or delete.
- Never delete a resource without explicit user confirmation and a stated blast-radius
  estimate.
- Prefer `--dry-run` / `--no-execute-changeset` where available.
- Prefer infrastructure-as-code (CDK or CloudFormation) over direct CLI writes.

The AWS MCP servers (`aws-docs`, `aws-eks`, `aws-pricing`) are declared in
`.claude/.mcp.json`. That path is not auto-loaded — start the session with
`claude --mcp-config .claude/.mcp.json` for those tools to be available.
