# `Infra/baremetal/` — production A.2, no code

**This target contains no code, and that is the demonstration that the §16.3
contract is the right cut.** Production runs on the client's physical machines;
they are not created by anything. All that is needed is the handover file,
written by hand:

```bash
cp Infra/baremetal/infra-inventory.example.json Infra/baremetal/infra-inventory.json
$EDITOR Infra/baremetal/infra-inventory.json
python3 noah.py garage deploy --from-infra Infra/baremetal/infra-inventory.json
```

Production consumes the same chain as development, with no cloud provider at
all.

## Filling the file

| Field | On physical machines |
|---|---|
| `provider` | `baremetal` |
| `compute_node.public_ip` | the node's real address |
| `bastion` | **`null`** — the Garage nodes are reachable directly, so no ProxyJump is produced |
| `garage_nodes[].public_ip` | the node's address on the administration segment |
| `garage_cidr` | the prefix of the Garage segment, **no wider than it really is** — it is what the cluster egress policies are founded on |
| `capacity` | the usable capacity of the ZFS pool, e.g. `2T` |
| `data_device` | a **deterministic** path: `/dev/disk/by-id/…`. Never `/dev/sdb` or `/dev/nvme1n1` — enumeration order is not guaranteed, and `garage-zfs` would create the pool on the root disk |

`bastion: null` and `public_ip: null` are both valid; a **missing** field is
not. One null field is admitted, never an absent one: a missing field reads as
an oversight of the generator, a null one as a topology decision.

The file must contain **no secret** — `noah garage deploy` refuses it if it
does (T12).

## What production requires that development does not

- **Three nodes**, replication factor 3 (D13, G7). Two nodes give a write
  quorum of 2: losing one node stops writes. Acceptable while validating a
  mechanism, unacceptable in production.
- **Two disks per Garage node**, ZFS mirror. Snapshots are local and are not
  replicated by Garage; the development single-disk shortcut (§5.1) would
  destroy the point of the mirror if carried over.
- **GA kernel, not HWE.** A kernel upgrade running ahead of OpenZFS support
  makes the pool unreachable at the next reboot.
