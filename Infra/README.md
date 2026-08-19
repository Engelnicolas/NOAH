# `Infra/` — machine provisioning

Infrastructure as code for the machines NOAH runs on. Engine: **OpenTofu**
(decision G10). Specification: [`Specs/To-do/Garage.md`](../../Specs/To-do/Garage.md) §16.

```
Infra/
  aws/         ← default target: development, Spot, eu-west-3     (written)
  baremetal/   ← production A.2: inventory written by hand, no IaC (written)
  scaleway/    ← second target, Europe                             (not written — see below)
  ovh/         ← second target, subject to V8                      (not written — see below)
```

`Infra/scaleway/` and `Infra/ovh/` are deliberately absent. §16.8 is explicit:
*`Infra/aws/` first and alone* — the European target is written once the §16.3
contract has actually carried a complete AWS deployment. Writing it in parallel
would generalise a contract that has carried nothing yet. The gap is estimated
at ~0.5 day once `Infra/aws/` is delivered, precisely because the contract
absorbs the difference.

---

## What this layer does, and where it stops

| | Owner | Contents |
|---|---|---|
| **Machine lifecycle** | OpenTofu, `Infra/` | instance, disks, network, security groups, public SSH keys, power state |
| **Machine contents** | Ansible, `Ansible/roles/garage-*` | ZFS, the Garage binary, `garage.toml`, cluster formation, TLS proxy |

**No `remote-exec`, no `local-exec` calling `ansible-playbook`.** OpenTofu never
connects over SSH to the machines it creates. The handover is a file, not a
call — which is what makes the `baremetal/` target achievable without a line of
code, and what stops a fourth secret domain from appearing.

Four things the IaC never does (§16.7):

1. **Generate a Garage secret.** No `random_password`, no `tls_private_key`.
   Secrets are born in `_service_generators()` and nowhere else — a secret born
   in OpenTofu lives in the OpenTofu state, i.e. in an undeclared, untested
   fourth domain.
2. **Create provider object storage.** Garage *is* the object tier.
3. **Connect to the machines.**
4. **Hold the private administration SSH key.** OpenTofu publishes the public
   half; the private half stays in secret domain 3.

Two refusals, before any resource is created:

| Input | Verdict |
|---|---|
| `operator_cidr = 0.0.0.0/0` | **refused** — the compute node is the only exposed machine *and* the jump host to the storage tier |
| `node_count` outside {2, 3} | **refused** — G8 moved one layer earlier, so the mistake falls before anything is paid for |
| `state_passphrase` unset | **refused** — no default, so the run fails instead of writing the state in the clear |

---

## The output contract — `infra-inventory.json` (§16.3)

Each target produces **one** file, with a schema identical across targets:

```json
{
  "provider": "aws",
  "compute_node": { "name": "noah-compute-dev", "public_ip": "…", "private_ip": "…" },
  "bastion": "noah-compute-dev",
  "garage_cidr": "10.0.2.0/24",
  "garage_nodes": [
    { "name": "garage-a", "public_ip": null, "private_ip": "…", "zone": "site-a",
      "capacity": "20G",
      "data_device": "/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol0123…" }
  ]
}
```

Rules that are not obvious from the shape:

- **The file contains no secret.** No private key, no `rpc_secret`, no S3
  credential, no provider token. Only public infrastructure facts. That is what
  allows it to sit on disk in the clear, and it is why the contract is a file
  rather than a call: a call would sooner or later have carried a secret. A
  test enforces it (T12), symmetrically with T3.
- **One null field is admitted, never a missing one.** `public_ip: null` on a
  Garage node is a topology decision (G19: they are in a private subnet);
  an absent field would read as an oversight of the generator.
- **`bastion`** names the machine through which the Garage nodes are reached.
  A target that gave each machine a public address would fill `public_ip` and
  set `bastion` to `null`, without changing the contract.
- **`garage_cidr`** has no consumer in `Garage.md`. It is produced here because
  this layer creates the subnet, so it is the only one that knows the exact
  prefix. Its consumer is `cilium_sso.md` §6.6, which founds every Garage
  egress rule on it. A prefix entered wider than the real subnet widens the
  cluster's S3 egress rules and **no test sees it**.
- **`data_device` is never a short device name.** On Nitro instances the NVMe
  enumeration order is not guaranteed: `/dev/nvme1n1` may be the root disk, and
  `garage-zfs` would create the pool on it. The deterministic `by-id` path is
  the only safe form; `/dev/vdb` is proscribed for the same reason.

---

## Using `Infra/aws/`

Everything below goes through `noah garage infra`, which reads the state
passphrase and the cloud credentials from secret domain 3 and never puts them
in a file:

```bash
python3 noah.py garage admin init          # once: creates Age/garage-admin.txt
python3 noah.py garage admin set-cloud --provider aws \
        --access-key-id … --secret-access-key …
python3 noah.py garage infra init
python3 noah.py garage infra plan  --operator-cidr 203.0.113.4/32
python3 noah.py garage infra apply --operator-cidr 203.0.113.4/32
```

Raw `tofu` works too, provided the passphrase is exported by hand:

```bash
export TF_VAR_state_passphrase="$(python3 noah.py garage admin show --field tofu_state_passphrase)"
cd Infra/aws && tofu init && tofu plan -var operator_cidr=203.0.113.4/32
```

### `power_state` — the daily lever

**Stopping the instances is not enough.** Most of the monthly cost runs with
the machines off:

| Item | Billed when | Order of magnitude |
|---|---|---|
| Spot instances | **only while running** | ~0.12 $/h for all three |
| **gp3 EBS volumes** | **always, stopped machines included** | ~14 $/month, incompressible |
| **Public IPv4** | **always**, attached or not | 1 Elastic IP → ~3.65 $/month |

A platform left in place "just in case" costs **~17.65 $/month doing nothing** —
roughly 106 $ over the six-month window, more than half the credits, without a
machine having run. These are orders of magnitude to be confirmed on the
account before any budget arbitration; check the real Spot prices with
`aws ec2 describe-spot-price-history --instance-types m6a.2xlarge t3a.medium
--product-descriptions Linux/UNIX --start-time <now>`.

```bash
python3 noah.py garage infra power stopped    # tofu apply -var power_state=stopped
python3 noah.py garage infra power running
```

If AWS has stopped an instance and the configuration asks for `running`, the
next apply attempts a start that may fail for want of capacity. That is
expected, and informative: it signals a shortage on the chosen instance type,
not a platform failure.

### Recovering after `tofu destroy`

`destroy` is the end-of-campaign lever, and it is **safe because everything is
reconstructible** — the topology comes from `Infra/`, the configuration from
the Ansible roles, and the S3 credentials from the canonical store via
`garage key import` (§6.2, G2). It is §6.2 that makes `destroy` acceptable:
without it, destroying the nodes would lose secrets that cannot be read back.

```bash
python3 noah.py garage infra destroy
# … later, same credentials, same buckets:
python3 noah.py garage infra apply --operator-cidr <cidr>
python3 noah.py garage deploy   --from-infra Infra/aws/infra-inventory.json
python3 noah.py garage provision --from-infra Infra/aws/infra-inventory.json
```

**Check afterwards that no Spot request survived:**

```bash
aws ec2 describe-spot-instance-requests \
    --filters Name=state,Values=open,active --region eu-west-3
```

It must return nothing. A `persistent` Spot request outlives the destruction of
its instance; if it is not cancelled it relaunches an instance **outside the
state** that bills until somebody notices. The provider cancels it from version
**5.86.0** onward (issue #38142, PR #41206) — which is why `required_providers`
pins `aws >= 5.86.0` and why `.terraform.lock.hcl` must be committed. Below
that floor, `tofu destroy` reports success and leaks money in silence.

### Bootstrap order — the step that does not show

The Garage nodes are in a **private subnet**: they have **no egress at all**
until the compute node routes for them. Installing ZFS, downloading the Garage
binary, fetching Ubuntu packages — all of it fails until then, and it fails by
**hanging**, not by refusing.

```
1. tofu apply                       machines exist
2. noah garage nat                  ip_forward + masquerading on the compute node
3. noah garage deploy               ZFS, install, config, cluster
4. noah garage provision            layout, buckets, keys
```

Step 2 is a **bootstrap prerequisite**, not a day-2 operation. It also has a
dependency nobody guesses: **`bpf.masquerade` must stay `false` on the Cilium
side** (`cilium_sso.md` N9). eBPF host routing bypasses netfilter in the host
namespace; enabling it would stop the masquerading rule from running and cut
the Garage nodes' egress **with no message at all**. It is an ordinary
performance setting — exactly the kind of change made without relating it to a
storage specification.

On physical machines step 2 is moot and is skipped.

---

## Files kept out of Git

`.gitignore` covers `Infra/**/*.tfstate*`, `Infra/**/.terraform/`,
`Infra/**/*.tfvars` and `Infra/**/infra-inventory.json`. The state is encrypted
(G14) but has no business in the repository, and a `tfvars` would carry the
operator's CIDR. `.terraform.lock.hcl` **is** committed — it is what pins the
provider version floor.
