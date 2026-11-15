# NOAH documentation

Index of everything written about NOAH. Start with the [main README](../README.md) for
the overview and the "How it works" diagram.

## Guides

| Document | Read it when you want to… |
|---|---|
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | go from nothing to a running platform: requirements, the six steps, DNS, mail prerequisites, teardown, troubleshooting |
| [Operations Guide](OPERATIONS_GUIDE.md) | run it: GitOps changes, secrets and rotation, Garage, mail, SSO, scaling, DNS, disaster recovery |
| [`Infra/README.md`](../Infra/README.md) | understand the machine layer: OpenTofu on AWS, the `infra-inventory.json` contract, costs, `power_state`, destroy |
| [`Infra/baremetal/README.md`](../Infra/baremetal/README.md) | run Garage on physical machines, and what production needs that development does not |
| [`Infra/aws/launch-templates/`](../Infra/aws/launch-templates/README.md) | see the EC2 launch templates OpenTofu replaced (reference only) |
| [Contributing](CONTRIBUTING.md) | send a change: DCO sign-off, checks, third-party material |
| [`.claude/CLAUDE.md`](../.claude/CLAUDE.md) | work on the code with Claude Code: map, invariants, pitfalls, where versions live |

## Quick links

| I want to… | Go to |
|---|---|
| Deploy on AWS, end to end | [Deployment Guide → Storage tier on AWS](DEPLOYMENT_GUIDE.md#storage-tier-on-aws-steps-1-to-3) |
| Deploy on a host I already have | [Deployment Guide → Cluster](DEPLOYMENT_GUIDE.md#cluster-steps-4-to-6) |
| Understand the secrets model | [Operations Guide → Secrets](OPERATIONS_GUIDE.md#secrets) |
| Rotate a credential | [Operations Guide → Rotating a secret](OPERATIONS_GUIDE.md#rotating-a-secret) |
| Give someone a mailbox | [Operations Guide → Mail](OPERATIONS_GUIDE.md#mail-stalwart) |
| Fix a failing deployment | [Deployment Guide → Troubleshooting](DEPLOYMENT_GUIDE.md#troubleshooting) |
| Stop paying for the AWS target | [Deployment Guide → Tearing down](DEPLOYMENT_GUIDE.md#tearing-down) |
| See the full CLI | [README → CLI reference](../README.md#cli-reference) |

## Diagrams

The diagrams in [`images/`](images/) are hand-written SVG, so they diff and review like
code: `banner.svg`, `how-it-works.svg`, `deployment-flow.svg`, `secrets.svg`. They share
one style (dark card, cyan for the platform, violet for the storage tier and identity,
grey for everything external); keep it when you add one, give it a `<title>` and a
`<desc>`, and update the diagram in the same change as the behaviour it shows.

## Writing conventions

- English, plain sentences, the reason before the rule.
- Commands are run from the repository root as `python3 noah.py …`.
- Placeholders: `your-domain.com` or `<domain>`, `<node-public-ip>`, `<your-ip>/32`.
- A behaviour change updates the guide that describes it in the same commit.

## License

NOAH is licensed under the **GNU Affero General Public License, version 3 or later**;
see [`LICENSE`](../LICENSE).
