# EC2 launch templates (reference)

Reference copies of the launch templates used before `Infra/aws/` existed.
**OpenTofu is the source of truth** (`Infra/aws/spot.tf`): nothing in NOAH reads
these files, and they are kept only to document where the instance settings
came from.

| File | Role |
|---|---|
| `Linux_spot_dev_NOAH-v12.json` | compute node as originally created (export of `describe-launch-template-versions`) |
| `Linux_spot_dev_NOAH-v13.json` | compute node, hardened: IMDSv2 required, encrypted EBS, persistent Spot with stop |
| `Linux_spot_garage_NOAH-v1.json` | Garage node: separate SSH key, no instance profile, persistent data volume |

Account-specific identifiers (account ID, security group, AMI, snapshot, key
pair, IAM user) are replaced by `REMPLACER-*` placeholders. Fill them in before
passing a file to `aws ec2 create-launch-template-version`.
