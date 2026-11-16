#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Static checks on the network baseline (gitops/network-policies/ and the
Stalwart policies shipped with gitops/apps-extra/stalwart/).

No cluster needed: these guard the failure modes that raise no error on a
cluster and only show up as a silent drop, or as a baseline that enforces
nothing.
"""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
BASELINE = REPO_ROOT / 'gitops/network-policies'
STALWART = REPO_ROOT / 'gitops/apps-extra/stalwart/networkpolicy.yaml'
POLICY_KINDS = {'CiliumNetworkPolicy', 'CiliumClusterwideNetworkPolicy'}

# Ports of Kubernetes SERVICES that front a pod listening elsewhere. A policy
# is evaluated on the pod port: one of these as a destination towards the
# matching backend is an allow that matches nothing.
SERVICE_PORT_TRAPS = {
    # (destination label, value): pod port that must be used instead of 80
    ('k8s-app', 'hubble-ui'): '8081',
    ('app', 'cilium-auth-proxy'): '8080',
    ('app', 'stalwart'): '8080',
}


def _docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _baseline_files():
    listed = yaml.safe_load((BASELINE / 'kustomization.yaml').read_text())['resources']
    return [BASELINE / name for name in listed]


def _all_policies():
    docs = []
    for path in _baseline_files() + [STALWART]:
        docs += [d for d in _docs(path) if d.get('kind') in POLICY_KINDS]
    return docs


def _rules(policy):
    spec = policy['spec']
    return [('ingress', r) for r in spec.get('ingress', [])] + \
           [('egress', r) for r in spec.get('egress', [])]


def _ports(rule):
    return [p['port'] for tp in rule.get('toPorts', []) for p in tp.get('ports', [])]


class TestKustomizationWiring:
    def test_every_policy_file_is_listed(self):
        on_disk = {p.name for p in BASELINE.glob('*.yaml')} - {'kustomization.yaml'}
        listed = {p.name for p in _baseline_files()}
        assert on_disk == listed

    def test_flux_applies_the_baseline_last(self):
        k = yaml.safe_load(
            (REPO_ROOT / 'clusters/production/network-policies.yaml').read_text())
        assert k['spec']['path'] == './gitops/network-policies'
        assert k['spec']['prune'] is True, 'prune is the rollback'
        depends = {d['name'] for d in k['spec']['dependsOn']}
        assert depends == {'infrastructure', 'cert-manager-issuers', 'apps', 'apps-extra'}

    def test_baseline_is_in_the_cluster_kustomization(self):
        k = yaml.safe_load(
            (REPO_ROOT / 'clusters/production/kustomization.yaml').read_text())
        assert 'network-policies.yaml' in k['resources']

    def test_baseline_is_not_under_infrastructure(self):
        """It would be reconciled by `infrastructure` and cut its own convergence."""
        assert not (REPO_ROOT / 'gitops/infrastructure/network-policies').exists()

    def test_stalwart_policies_ship_with_stalwart(self):
        listed = yaml.safe_load(
            (STALWART.parent / 'kustomization.yaml').read_text())['resources']
        assert STALWART.name in listed
        # A policy in the (optional) stalwart namespace would fail the baseline.
        for path in _baseline_files():
            for doc in _docs(path):
                assert doc['metadata'].get('namespace') != 'stalwart', path.name


class TestDefaultDeny:
    @pytest.fixture
    def policy(self):
        (doc,) = _docs(BASELINE / 'default-deny.yaml')
        return doc

    def test_selects_every_endpoint(self, policy):
        assert policy['kind'] == 'CiliumClusterwideNetworkPolicy'
        assert policy['spec']['endpointSelector'] == {}

    def test_is_not_inert(self, policy):
        """`ingress: []` has no rule: Cilium then enables no default-deny at all."""
        assert policy['spec']['ingress'] == [{}]
        assert policy['spec']['egress'] == [{}]
        assert policy['spec']['enableDefaultDeny'] == {'ingress': True, 'egress': True}


class TestAllowRules:
    def test_no_rule_is_empty(self):
        """Outside default-deny, an empty rule is a mistake, not an allow."""
        for policy in _all_policies():
            if policy['metadata']['name'] == 'default-deny-all':
                continue
            for direction, rule in _rules(policy):
                assert rule, f"{policy['metadata']['name']}: empty {direction} rule"
                assert _ports(rule), f"{policy['metadata']['name']}: {direction} rule without port"

    def test_no_unsubstituted_variable(self):
        """Flux substitutes ${VAR}; a variable missing from cluster-vars breaks the apply."""
        for path in _baseline_files() + [STALWART]:
            assert '${' not in path.read_text(), path.name

    def test_cloud_metadata_is_never_allowed(self):
        for path in _baseline_files() + [STALWART]:
            text = '\n'.join(l for l in path.read_text().splitlines()
                             if not l.lstrip().startswith('#'))
            assert '169.254.169.254' not in text, path.name

    def test_garage_admin_ports_are_never_allowed(self):
        """SSH, Garage RPC and admin API: the absence of an allow is the measure."""
        for policy in _all_policies():
            for _, rule in _rules(policy):
                if 'toCIDR' in rule or 'toCIDRSet' in rule:
                    assert not {'22', '3901', '3903'} & set(_ports(rule)), \
                        policy['metadata']['name']

    def test_policies_target_pod_ports_not_service_ports(self):
        for policy in _all_policies():
            for _, rule in _rules(policy):
                for selector in rule.get('toEndpoints', []):
                    labels = selector.get('matchLabels', {})
                    for (key, value), pod_port in SERVICE_PORT_TRAPS.items():
                        if labels.get(key) == value:
                            assert _ports(rule) == [pod_port], policy['metadata']['name']
            subject = policy['spec'].get('endpointSelector', {}).get('matchLabels', {})
            for (key, value), pod_port in SERVICE_PORT_TRAPS.items():
                if subject.get(key) == value:
                    for rule in policy['spec'].get('ingress', []):
                        assert '80' not in _ports(rule), policy['metadata']['name']

    def test_no_http_rule_towards_external_storage(self):
        """An http rule on S3 egress would put object names in Hubble flows."""
        for policy in _all_policies():
            for rule in policy['spec'].get('egress', []):
                if 'toCIDR' in rule or 'toCIDRSet' in rule:
                    for tp in rule.get('toPorts', []):
                        assert 'http' not in tp.get('rules', {}), policy['metadata']['name']


class TestStalwartRelay:
    def test_unauthenticated_relay_is_open_to_exactly_two_senders(self):
        policies = [d for d in _docs(STALWART)
                    if d['metadata']['namespace'] == 'stalwart'
                    and d['spec'].get('endpointSelector', {}).get('matchLabels') == {'app': 'stalwart'}]
        (policy,) = policies
        relay_rules = [r for r in policy['spec']['ingress'] if '2525' in _ports(r)]
        (rule,) = relay_rules
        assert _ports(rule) == ['2525']
        assert 'fromEntities' not in rule
        senders = {s['matchLabels']['k8s:io.kubernetes.pod.namespace']: s['matchLabels']
                   for s in rule['fromEndpoints']}
        assert set(senders) == {'authentik', 'nextcloud'}
        for labels in senders.values():
            assert len(labels) == 2, 'a namespace-wide sender would include any Job or sidecar pod'


class TestCiliumHelmRelease:
    @pytest.fixture
    def values(self):
        hr = yaml.safe_load(
            (REPO_ROOT / 'gitops/infrastructure/cilium/helmrelease.yaml').read_text())
        return hr['spec']['values']

    def test_audit_mode_is_a_committed_value(self, values):
        """Posed with `cilium config`, Flux would revert it mid-audit."""
        assert 'policyAuditMode' in values

    def test_l7_visibility_is_enabled(self, values):
        assert values['l7Proxy'] is True
        metrics = values['hubble']['metrics']['enabled']
        assert any(m.startswith('http') for m in metrics)
        assert any(m.startswith('dns') for m in metrics)

    def test_bpf_masquerade_is_not_enabled(self, values):
        """With kubeProxyReplacement it enables eBPF host routing, which bypasses
        the netfilter NAT rule the Garage nodes egress through."""
        assert values.get('bpf', {}).get('masquerade') is not True

    def test_pod_range_is_explicit_and_matches_the_preflight(self, values):
        """Allocated once by the preflight: a HelmRelease stating another range
        would be silently ignored for the nodes already there."""
        (pod_cidr,) = values['ipam']['operator']['clusterPoolIPv4PodCIDRList']
        preflight = (REPO_ROOT / 'Ansible/roles/cilium-preflight/tasks/main.yml').read_text()
        assert f"ipam.operator.clusterPoolIPv4PodCIDRList={{{pod_cidr}}}" in preflight

    def test_pod_range_overlaps_no_infrastructure_prefix(self, values):
        """Egress to Garage is a toCIDR rule: it only means something if that
        prefix is outside the pod range."""
        import ipaddress
        import json
        import re
        (pod_cidr,) = values['ipam']['operator']['clusterPoolIPv4PodCIDRList']
        pods = ipaddress.ip_network(pod_cidr)
        tf = (REPO_ROOT / 'Infra/aws/variables.tf').read_text()
        prefixes = re.findall(r'default\s*=\s*"(\d+\.\d+\.\d+\.\d+/\d+)"', tf)
        assert prefixes, 'no CIDR default found in Infra/aws/variables.tf'
        example = json.loads(
            (REPO_ROOT / 'Infra/baremetal/infra-inventory.example.json').read_text())
        prefixes.append(example['garage_cidr'])
        for prefix in prefixes:
            assert not pods.overlaps(ipaddress.ip_network(prefix)), prefix

    def test_gui_is_only_exposed_through_the_auth_proxy(self, values):
        assert values['hubble']['ui']['ingress']['enabled'] is False
        ingress = yaml.safe_load(
            (REPO_ROOT / 'gitops/apps/cilium-auth/cilium-ingress.yaml').read_text())
        assert ingress['spec']['rules'][0]['host'] == 'cilium.${DOMAIN}'
        assert 'nginx.ingress.kubernetes.io/auth-url' in ingress['metadata']['annotations']
        # The backend stays the chart-managed Service: only the exposure is renamed.
        backend = ingress['spec']['rules'][0]['http']['paths'][0]['backend']['service']
        assert backend['name'] == 'hubble-ui'
