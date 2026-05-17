# NOAH ServiceLB Technical Specification

**Status**: Draft
**Version**: 0.1.0
**Last Updated**: May 2026
**Target NOAH release**: v0.0.10

This document specifies the integration of **ServiceLB** (also known as
[Klipper LB](https://github.com/k3s-io/klipper-lb), the load balancer
that ships with K3s) as the default `Service type: LoadBalancer`
implementation for NOAH deployments. ServiceLB replaces the current
"no load balancer" posture (`--disable servicelb` in the K3s install
flags) and works uniformly on **single-node** and **multi-node**
clusters, including bare AWS EC2 instances behind a Security Group.

It also describes how ports **80** and **443** are exposed at the node
level and forwarded to the cluster's ingress controller (Cilium
Ingress) so that any `Service` of type `LoadBalancer` requesting those
ports works out of the box, on both single-node and multi-node
topologies.

---

## 1. Goals & Non-Goals

### 1.1 Goals

1. Provide a working `Service type: LoadBalancer` implementation by
   default in every NOAH cluster, without requiring an external cloud
   load balancer (no ELB, no NLB, no MetalLB BGP peering).
2. Default behavior on a **single-node** cluster: the node's primary
   IP becomes the `EXTERNAL-IP` of every `LoadBalancer` service.
3. Compatibility with a **multi-node** cluster: every node exposes the
   service ports, and the `EXTERNAL-IP` field lists every node IP
   (round-robin via DNS or a future external L4 balancer).
4. Compatibility with **AWS EC2** bare-instance deployments: the
   advertised IP must be reachable from the public internet, ports
   80/443 must traverse the Security Group, and the Public IP (Elastic
   IP) must be surfaced to `external-dns` so DNS records resolve to
   the correct address.
5. **Port 80 / 443 ingress path**: ServiceLB binds 80 and 443 on the
   host network and forwards to the Cilium Ingress `LoadBalancer`
   service, which terminates TLS and routes by `Host:` header.
6. Zero-touch upgrade path from the current Cilium-only posture: the
   same `Ingress` objects keep working, only the underlying
   `EXTERNAL-IP` becomes populated.

### 1.2 Non-Goals

- Replacing Cilium's L7 ingress controller. ServiceLB is L4 only; L7
  routing remains the responsibility of the Cilium Ingress.
- Implementing BGP/ARP/EVPN-based IP advertisement. Use MetalLB or
  Cilium's `LoadBalancer IPAM` if you need a virtual IP that floats
  across nodes — out of scope for v0.0.10.
- Providing native AWS ELB/NLB integration via the AWS cloud
  controller manager. NOAH explicitly targets *bare* EC2 instances
  managed by Ansible, not EKS.
- Multi-AZ public IP failover. A single EC2 instance's Elastic IP is
  pinned to one AZ; HA across AZs requires Route53 health checks or a
  managed NLB (future work, see §10).

---

## 2. Background

### 2.1 What ServiceLB is

ServiceLB is a tiny LoadBalancer controller that ships in-tree with
K3s. For every `Service` of `type: LoadBalancer`, it:

1. Creates a `DaemonSet` named `svclb-<service-name>-<hash>` in the
   `kube-system` namespace.
2. Each pod in that DaemonSet binds the service's port(s) on the
   **host network** (via `hostPort`) and `iptables`/`nftables`-DNATs
   incoming traffic to the underlying ClusterIP.
3. Patches the `Service.status.loadBalancer.ingress[]` field with the
   IPs of every node hosting an `svclb-*` pod.

The result: a service requesting port 80 on a 3-node cluster will have
three host:80 listeners (one per node) and three IPs in its
`EXTERNAL-IP` column. On a single-node cluster, you get one IP and one
listener — exactly what users expect.

### 2.2 Why NOAH currently disables it

`Ansible/roles/k3s-server-init/tasks/main.yml:32` and
`Ansible/roles/k3s-server-join/tasks/main.yml:31` both pass
`--disable servicelb` to the K3s installer. This was a defensible
default while the project used `nginx-ingress` with
`hostNetwork: true` (the README architecture diagram still references
this older layout), because that ingress was binding 80/443 directly
and ServiceLB would have collided on those ports.

The current GitOps state (see `gitops/infrastructure/cilium/helmrelease.yaml`)
enables Cilium's built-in Ingress controller with
`loadbalancerMode: dedicated`, which creates a `Service` of
`type: LoadBalancer` per `Ingress`. Without a LoadBalancer provider in
the cluster, those services sit in `<pending>` forever and the only
way to reach them is `kubectl port-forward` or manual `hostPort`
patches. ServiceLB closes that gap.

### 2.3 ServiceLB vs alternatives

| Solution | Single-node | Multi-node bare EC2 | L7 needed? | Operational cost |
|---|---|---|---|---|
| **ServiceLB**                    | ✅ trivial   | ✅ per-node `hostPort` | No  | Built into K3s |
| MetalLB (L2/ARP)                  | ✅           | ⚠️ needs gratuitous ARP, blocked on EC2 | No  | Extra controller, IP pool config |
| MetalLB (BGP)                     | ✅           | ✅ but needs BGP-capable ToR | No  | BGP peering, not available on EC2 |
| Cilium LB-IPAM + L2 announcements | ✅           | ⚠️ ARP again, EC2 broken | No  | Cilium-version-coupled |
| AWS NLB via cloud-controller      | ❌ overkill  | ✅                       | No  | Requires EKS / cloud-controller-manager |
| External nginx on host            | ✅           | ❌ no per-node fan-out   | Yes | Manual config drift |

ServiceLB is the only option that is (a) built in, (b) works on
single-node, and (c) functions on bare EC2 without ARP gymnastics.

---

## 3. Architecture

### 3.1 Single-node topology (default)

```
┌─────────────────── EC2 instance (Elastic IP: 203.0.113.10) ───────────────────┐
│                                                                               │
│  Security Group: allow tcp/80, tcp/443, tcp/22, tcp/6443 from 0.0.0.0/0       │
│                                                                               │
│   :80, :443  ┌──────────────────────────────────────────────────────────┐     │
│  ─────────► │ svclb-cilium-ingress-xxxx (DaemonSet pod, hostNetwork)   │     │
│              │   hostPort 80  → cilium-ingress ClusterIP :80           │     │
│              │   hostPort 443 → cilium-ingress ClusterIP :443          │     │
│              └────────────────────────┬─────────────────────────────────┘     │
│                                       │                                       │
│                                       ▼                                       │
│              ┌──────────────────────────────────────────────────────────┐     │
│              │ cilium-ingress (Service, type: LoadBalancer)             │     │
│              │   EXTERNAL-IP: 203.0.113.10  (set by ServiceLB)         │     │
│              │   forwards by Host: header → authentik / headlamp / …   │     │
│              └──────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────────────┘
```

`external-dns` reads `EXTERNAL-IP = 203.0.113.10`, writes the A
records `auth.example.com → 203.0.113.10`, etc.

### 3.2 Multi-node topology

```
                       ┌─── *.example.com → DNS round-robin ───┐
                       │                                        │
                       ▼                                        ▼
   ┌────── EC2 node1 ──────┐  ┌────── EC2 node2 ──────┐  ┌────── EC2 node3 ──────┐
   │ EIP 203.0.113.10      │  │ EIP 203.0.113.11      │  │ EIP 203.0.113.12      │
   │ svclb-* :80, :443     │  │ svclb-* :80, :443     │  │ svclb-* :80, :443     │
   └──────────┬────────────┘  └──────────┬────────────┘  └──────────┬────────────┘
              │                          │                          │
              └─── cilium-ingress ClusterIP (Cilium kube-proxy ──────┘
                       replacement DNATs to the right backend pod)
```

`Service.status.loadBalancer.ingress` lists all three IPs. `external-dns`
publishes three A records per hostname. Failure of one node removes
that node's `svclb-*` pod and (via Cilium's health-check) the matching
A record on the next reconcile.

### 3.3 EC2 specifics

EC2 instances have a **private VPC IP** on the primary ENI and a
**Public IP / Elastic IP** that is NAT-mapped externally. The instance
itself never sees the public IP on its interfaces — `ip addr` only
shows the private one. Three consequences for ServiceLB:

1. K3s started without `--node-external-ip` will report the private IP
   in `Node.status.addresses[type=InternalIP]` only. ServiceLB
   defaults to using `ExternalIP` if present, else `InternalIP`, which
   would publish the unreachable private IP.
2. The Ansible role must therefore detect the public IP via the EC2
   IMDSv2 metadata service and pass `--node-external-ip <public-ip>`
   to K3s on EC2 hosts.
3. The Security Group must allow TCP 80 and 443 inbound from
   `0.0.0.0/0` (or the operator's chosen CIDR). This is **out-of-band
   configuration** — NOAH documents it but does not manage it (no AWS
   SDK dependency).

---

## 4. Detailed Design

### 4.1 K3s install-flag changes

**File**: `Ansible/roles/k3s-server-init/tasks/main.yml`

Remove `--disable servicelb`. Keep `--disable traefik`,
`--disable-network-policy`, `--disable-kube-proxy`,
`--flannel-backend=none`. Add `--node-external-ip` when the node is
detected as EC2.

```diff
   curl -sfL https://get.k3s.io | \
     INSTALL_K3S_VERSION="{{ k3s_version }}" \
     K3S_TOKEN="{{ k3s_token }}" \
     INSTALL_K3S_EXEC="server" \
     sh -s - \
       --cluster-init \
       --disable traefik \
-      --disable servicelb \
       --disable-network-policy \
       --disable-kube-proxy \
       --flannel-backend=none \
       --tls-san "{{ node1_ip }}" \
       --node-ip "{{ ansible_default_ipv4.address }}" \
+      {% if ec2_public_ip is defined and ec2_public_ip %}--node-external-ip "{{ ec2_public_ip }}"{% endif %} \
       --write-kubeconfig-mode 644
```

Apply the same change in `Ansible/roles/k3s-server-join/tasks/main.yml`.

### 4.2 EC2 public-IP detection

Add a new task in `Ansible/roles/common/tasks/main.yml` (runs on all
nodes before K3s install):

```yaml
- name: Detect EC2 environment via IMDSv2 token
  uri:
    url: http://169.254.169.254/latest/api/token
    method: PUT
    headers:
      X-aws-ec2-metadata-token-ttl-seconds: "60"
    return_content: yes
    timeout: 2
  register: ec2_imds_token
  failed_when: false
  changed_when: false

- name: Fetch EC2 public IPv4 (when on EC2)
  uri:
    url: http://169.254.169.254/latest/meta-data/public-ipv4
    headers:
      X-aws-ec2-metadata-token: "{{ ec2_imds_token.content }}"
    return_content: yes
    timeout: 2
  register: ec2_public_ipv4_raw
  failed_when: false
  changed_when: false
  when: ec2_imds_token.status == 200

- name: Set ec2_public_ip fact
  set_fact:
    ec2_public_ip: "{{ ec2_public_ipv4_raw.content | trim }}"
  when:
    - ec2_imds_token.status == 200
    - ec2_public_ipv4_raw.status == 200
    - ec2_public_ipv4_raw.content | trim | length > 0
```

Hosts that are not on EC2 simply skip these tasks and `ec2_public_ip`
remains undefined — the K3s install line then omits
`--node-external-ip` and ServiceLB falls back to the node's
`InternalIP`, which is the correct behavior for on-prem / dev
deployments.

### 4.3 Cilium configuration changes

The current Cilium HelmRelease enables the L7 ingress controller in
`loadbalancerMode: dedicated`, which creates one `Service` of
`type: LoadBalancer` per `Ingress`. That is wasteful — every Ingress
spawns its own `svclb-*` DaemonSet and competes for port 80/443.

**Switch to `loadbalancerMode: shared`** so that a single
`cilium-ingress` Service (in `kube-system`) handles every Ingress:

```diff
   ingressController:
     enabled: true
-    loadbalancerMode: dedicated
+    loadbalancerMode: shared
     default: true
+    service:
+      type: LoadBalancer
+      # Let ServiceLB allocate the EXTERNAL-IP from the node addresses
+      # by leaving externalTrafficPolicy at Cluster.
+      ports:
+        - 80
+        - 443
```

This guarantees that exactly one DaemonSet (`svclb-cilium-ingress-*`)
binds 80/443 on each node.

### 4.4 Port 80 → 443 redirect

HTTPS redirect is an **L7 concern** and lives at the Cilium Ingress
layer, not at ServiceLB. ServiceLB is L4: it does not understand HTTP
and cannot rewrite `Location:` headers. The redirect is declared per
`Ingress` via the standard annotation:

```yaml
metadata:
  annotations:
    ingress.cilium.io/force-https: "true"
```

For NOAH's bundled apps (Authentik, Headlamp, Hubble), add the
annotation in their respective HelmRelease values / Ingress manifests
under `gitops/apps/*/`. A cluster-wide default can be configured in
the Cilium HelmRelease:

```yaml
   ingressController:
     enabled: true
     loadbalancerMode: shared
+    enforceHttps: true   # global HTTP→HTTPS 301 for every Ingress
```

Operators who need to opt **out** for a specific service set
`ingress.cilium.io/force-https: "false"` on that Ingress.

### 4.5 ServiceLB DaemonSet scheduling

By default ServiceLB schedules `svclb-*` pods on every node that
doesn't carry a `NoSchedule` taint. In NOAH that means every server
node (we have no dedicated worker nodes today). No changes required.

If, in the future, operators add **edge nodes** that should not
terminate public traffic, tag them with:

```bash
kubectl label node <edge-node> svccontroller.k3s.cattle.io/lbpool=internal
```

and set `metadata.annotations.svccontroller.k3s.cattle.io/lbpool=public`
on the `cilium-ingress` Service. The K3s ServiceLB controller honors
this label selector. This is documented in §6.3 of this spec but **not
wired by default**.

### 4.6 Conflict handling: priority class & port allocation

- Every `svclb-*` pod requests `priorityClassName: system-node-critical`
  (K3s sets this automatically) so it is not evicted under memory
  pressure ahead of application workloads.
- If two `LoadBalancer` services request the same port on the same
  node, the second one's DaemonSet pods will `CrashLoopBackOff` with
  `bind: address already in use`. NOAH avoids this by funneling all
  public HTTP/S traffic through the single `cilium-ingress` Service
  (§4.3). The `validate` step (§7) checks for port collisions and
  fails fast.

### 4.7 Source IP preservation

`externalTrafficPolicy: Cluster` (the default) NATs the client IP to
the node IP. To preserve the real client IP for Authentik's audit log
and rate limiting:

```yaml
   ingressController:
     enabled: true
     loadbalancerMode: shared
     service:
       type: LoadBalancer
+      externalTrafficPolicy: Local
```

Trade-off: `Local` only routes traffic to a node if a backend pod is
running there. On a single-node cluster, this is always true. On
multi-node, Cilium Ingress runs as a Deployment (default 2 replicas),
so 1 or 2 of N nodes will *not* have a backend — ServiceLB will still
publish that node's IP but connections to it will black-hole until
the operator pins Cilium Ingress as a DaemonSet (out of scope) or
relies on Cilium's healthCheckNodePort to remove unhealthy nodes from
DNS via `external-dns`.

**Decision**: default to `Cluster` (works on every topology), document
`Local` as an opt-in for operators who need client IPs and accept the
HA caveat.

---

## 5. Interaction with `external-dns`

`external-dns` (configured at `gitops/infrastructure/external-dns/helmrelease.yaml`)
watches `Service.status.loadBalancer.ingress[].ip` and `Ingress`
hostnames. With ServiceLB enabled:

- **Single node**: each `Ingress` resolves to a single A record
  pointing at the EC2 Public IP.
- **Multi node**: each `Ingress` resolves to N A records (round-robin
  DNS). External-DNS publishes them all by default.

No external-dns config change is required. The TXT-registry
`txtOwnerId` continues to scope records per cluster, and the existing
`policy: upsert-only` default is preserved.

---

## 6. Operator-facing changes

### 6.1 `noah.py` CLI

No new flags. The change is invisible to the operator on the existing
command:

```bash
python3 noah.py cluster bootstrap \
  --node 203.0.113.10 \
  --domain example.com \
  --flux-repo https://github.com/Engelnicolas/NOAH.git \
  --git-token $GITHUB_TOKEN
```

Add a new `--lb-external-ip <ip>` override on `cluster bootstrap` for
the rare case where IMDSv2 is disabled (operators who run a hardened
AMI with IMDS blocked). When supplied, this value is passed through to
the Ansible playbook as `ec2_public_ip` and overrides metadata
detection.

### 6.2 `noah.py cluster status`

Extend the status output to include the LB summary:

```
LoadBalancer (ServiceLB)
  cilium-ingress (kube-system): EXTERNAL-IP 203.0.113.10  ports 80/TCP, 443/TCP
    svclb-cilium-ingress-abc12  node1  Running
```

### 6.3 Documentation updates

- `docs/DEPLOYMENT_GUIDE.md` — replace the "nginx-ingress (hostNetwork)"
  row in the reconciliation table with "ServiceLB + Cilium Ingress
  (hostPort 80/443)".
- `docs/DNS_MANAGEMENT_GUIDE.md` — remove the manual "Get Node Public
  IP" step; the LoadBalancer IP is now auto-published.
- `docs/README.md` — refresh the architecture ASCII diagram (currently
  references nginx-ingress, which has not existed in `gitops/` for
  several releases).

### 6.4 AWS prerequisites (new section in DEPLOYMENT_GUIDE)

Required for EC2 deployment:

| Resource           | Setting                                                              |
|--------------------|----------------------------------------------------------------------|
| EC2 instance       | Ubuntu 22.04+, `t3.xlarge` minimum (8 GB RAM, 4 vCPU)                |
| EBS volume         | gp3, 50 GB+, mounted at `/var/lib/rancher`                          |
| Elastic IP         | One per node, attached to the primary ENI                            |
| Security Group     | Inbound: `tcp/22` (SSH), `tcp/80`, `tcp/443`, `tcp/6443` (K8s API). HA only: `tcp/2379-2380` (etcd), `tcp/10250` (kubelet), `udp/8472` (VXLAN if not Cilium) |
| IMDSv2             | Enabled (`HttpTokens=required`). NOAH uses IMDSv2 to discover the public IP. |
| Route53 / Cloudflare | Domain delegated; `external-dns` token configured                  |

Operators using a different cloud (Hetzner, OVH, Scaleway) follow the
same rules — substitute "Elastic IP" with "Floating IP" or
"Reverse-DNS-mapped IP".

---

## 7. Validation

Extend `Ansible/roles/k3s-validate/tasks/main.yml` with three checks:

1. **ServiceLB DaemonSet is healthy**: every `svclb-cilium-ingress-*`
   pod is `Running` and `Ready` on every node.
2. **Ports 80 and 443 are bound on every node**:
   `ss -tlnp | grep -E ':(80|443)\b'` returns a row per node.
3. **`cilium-ingress` Service has an EXTERNAL-IP**: poll
   `kubectl get svc -n kube-system cilium-ingress -o jsonpath=...`
   until `loadBalancer.ingress[0].ip` is set (timeout 120 s).
4. **End-to-end HTTP**: from the Ansible control host,
   `curl -kI https://<public-ip>/` returns a `200` or `301` (proves
   TLS termination + ingress routing).

Failure of any check aborts the bootstrap and prints the offending
node + diagnostic command.

---

## 8. Migration & rollback

### 8.1 Forward migration (v0.0.9 → v0.0.10)

There is no in-place migration. ServiceLB is enabled at K3s install
time via a startup flag, which K3s reads from
`/etc/systemd/system/k3s.service` and which cannot be toggled without
re-installing K3s. For an existing v0.0.9 cluster:

```bash
# 1. Pull v0.0.10
git pull --rebase

# 2. Re-run cluster bootstrap with --force-reset
python3 noah.py cluster bootstrap --force-reset --node <ip> --domain example.com ...
```

`--force-reset` is destructive (already documented). Workloads are
GitOps-reconciled, so re-bootstrap is the supported pattern.

### 8.2 Rollback

Revert the Ansible role changes (add `--disable servicelb` back, drop
`--node-external-ip`) and re-run bootstrap with `--force-reset`. The
Cilium HelmRelease change is forward-compatible: `loadbalancerMode:
shared` works without ServiceLB (the Service simply stays `<pending>`,
same as today).

---

## 9. Security considerations

1. **Host port binding**: ServiceLB pods run with
   `securityContext.capabilities: NET_ADMIN, NET_RAW, SYS_MODULE`
   (required by Klipper to manage iptables rules). This is no
   broader than the existing Cilium agent privileges.
2. **Bypassing NetworkPolicy**: `hostPort`-exposed traffic enters the
   node network namespace and is **not** subject to Cilium
   `NetworkPolicy` selectors that target pod IPs. The Cilium Ingress
   pod still applies its own L7 filters; do not rely on
   `NetworkPolicy` to firewall public HTTP/S traffic — use the
   Security Group instead.
3. **IMDSv1**: must remain disabled. The Ansible playbook uses IMDSv2
   exclusively (PUT + token header).
4. **Public IP exposure**: ServiceLB advertises every node IP. If any
   node holds a public IP and the operator does *not* want it to
   serve traffic, taint it with
   `node.kubernetes.io/exclude-from-external-load-balancers=:NoSchedule`
   — K3s respects this taint for `svclb-*` scheduling.

---

## 10. Open questions & future work

1. **Multi-AZ HA**: Elastic IPs are AZ-pinned. For a true multi-AZ
   active-active cluster we need either Route53 health checks (NOAH
   would emit health-check CRs via external-dns) or an AWS NLB in
   front of the cluster (defeats the "no cloud LB" goal). Track in a
   follow-up RFC.
2. **IPv6**: ServiceLB supports dual-stack since K3s v1.27, but
   external-dns AAAA support and Cilium dual-stack on EC2 need
   end-to-end testing.
3. **Wildcard certificates**: Today cert-manager issues one cert per
   `Ingress`. With ServiceLB, the same node serves every hostname —
   a single wildcard cert would cut issuance/renewal volume on
   Let's Encrypt. Out of scope; opens the door to a future
   `*.example.com` ClusterIssuer.
4. **Cilium LB-IPAM coexistence**: Cilium 1.16+ ships its own
   LoadBalancer IPAM. If we ever want a virtual IP that survives node
   loss without DNS-level failover, that path replaces ServiceLB.
   For now, ServiceLB is simpler and matches the "one node = one IP"
   mental model.

---

## 11. Test plan

| # | Scenario                                  | Expected result                                                                              |
|---|-------------------------------------------|----------------------------------------------------------------------------------------------|
| 1 | Fresh single-node bootstrap on EC2        | `kubectl get svc -A` shows `cilium-ingress` with `EXTERNAL-IP = <EIP>`. `curl https://auth.example.com/` returns the Authentik login page. |
| 2 | Fresh single-node bootstrap on local VM   | `EXTERNAL-IP` = VM's IP. Same curl test against `/etc/hosts`-resolved hostname succeeds.     |
| 3 | Bootstrap with `--ha --nodes n1,n2,n3` on EC2 | `EXTERNAL-IP` lists 3 IPs. `dig auth.example.com +short` returns 3 A records. Curl against each succeeds. |
| 4 | Kill one node in the 3-node HA cluster    | External-DNS removes the dead node's A record within `<txtCacheInterval>` (default 1 h, configurable). |
| 5 | Disable IMDSv2 on EC2 instance            | Bootstrap fails fast with "Could not determine EC2 public IP; pass --lb-external-ip explicitly". |
| 6 | Two Ingresses, same hostname, different paths | Both reachable via the same `cilium-ingress` (no port collision; shared mode).            |
| 7 | `curl -I http://auth.example.com/`        | Returns `301 → https://auth.example.com/` (enforceHttps).                                    |
| 8 | Security Group blocks port 443             | Validation step 4 fails with a clear "TCP 443 unreachable on 203.0.113.10" error.            |

---

## 12. References

- K3s ServiceLB (Klipper LB) source — https://github.com/k3s-io/klipper-lb
- K3s networking docs — https://docs.k3s.io/networking#service-load-balancer
- Cilium Ingress shared vs dedicated mode — https://docs.cilium.io/en/stable/network/servicemesh/ingress/
- AWS IMDSv2 spec — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-IMDS-new-instances.html
- NOAH Deployment Guide — `docs/DEPLOYMENT_GUIDE.md`
- NOAH DNS Management Guide — `docs/DNS_MANAGEMENT_GUIDE.md`
- NOAH Migration Guide — `docs/MIGRATION_GUIDE.md`
