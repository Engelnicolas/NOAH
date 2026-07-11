---
name: aws
description: NOAH conventions for AWS operations — Route53, SSM, CloudFormation, plus safety rules for writes and deletes. Use for any aws CLI operation.
---

Use the `aws` CLI. Assume credentials are configured via environment variables or `~/.aws/credentials`. Never hardcode keys.

```bash
# Confirm active identity before any write operation
aws sts get-caller-identity

# List resources (common services used by NOAH's infra)
aws ec2 describe-instances --query "Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]" --output table
aws route53 list-hosted-zones
aws s3 ls

# Route53 — look up a zone before modifying records
aws route53 list-resource-record-sets --hosted-zone-id <zone-id>

# SSM Parameter Store (secrets alternative to SOPS in cloud context)
aws ssm get-parameter --name "/noah/..." --with-decryption

# CloudFormation / CDK stack status
aws cloudformation describe-stacks --stack-name <name>
```

**Rules:**
- Run `aws sts get-caller-identity` before any write or delete operation.
- Never delete resources without explicit user confirmation and a stated blast-radius estimate.
- Prefer `--dry-run` or `--no-execute-changeset` flags where available.
- Never read or write `~/.aws/credentials` directly; rely on the CLI's credential chain.

MCP servers `aws-docs`, `aws-eks`, and `aws-pricing` are configured in `.claude/settings.json` for documentation lookup, EKS operations, and pricing queries.
