---
name: external-tools
description: NOAH conventions and safety rules for the gh and aws CLIs — PRs, issues, checks, merges, EC2/Spot inspection, teardown checks. Use for any GitHub or AWS operation.
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
gh pr checks <number>                  # CodeQL + GitGuardian; there is no other CI
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

Credentials resolve through the standard credential chain. Prefer `aws login`
(short-lived); never hardcode keys, and never read or write `~/.aws/credentials` directly.
NOAH's own AWS resources are created by **OpenTofu** (`Infra/aws/`, through
`noah garage infra`), never by direct CLI writes, CDK or CloudFormation (decision G10).
Use the CLI to look, not to change.

```bash
aws sts get-caller-identity            # before ANY write or delete
aws ec2 describe-instances --region eu-west-3 \
    --query "Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key=='Name']|[0].Value]" --output table
aws ec2 describe-spot-instance-requests --region eu-west-3 \
    --filters Name=state,Values=open,active            # must be empty after a destroy
aws ec2 describe-addresses --region eu-west-3           # Elastic IPs bill even when idle
aws ec2 describe-spot-price-history --region eu-west-3 \
    --instance-types m6a.2xlarge t3a.medium --product-descriptions Linux/UNIX \
    --start-time "$(date -u +%Y-%m-%dT%H:%M:%S)"
```

- Run `aws sts get-caller-identity` before any write or delete.
- Never delete a resource without explicit user confirmation and a stated blast-radius
  estimate. Prefer `tofu plan` / `tofu plan -destroy` to preview.
- DNS is on **Cloudflare**, not Route 53. Records are written by external-dns; after a
  teardown, check the zone for records left pointing at a released Elastic IP.

The AWS MCP servers (`aws-docs`, `aws-eks`, `aws-pricing`) are declared in
`.claude/.mcp.json`. That path is not auto-loaded — start the session with
`claude --mcp-config .claude/.mcp.json` for those tools to be available.
