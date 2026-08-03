# Contributing to NOAH

Thank you for considering a contribution. Issues, bug reports and pull requests
are all welcome.

---

## 1. Sign off your commits

NOAH uses the [Developer Certificate of Origin](DCO) (DCO) — the same mechanism
as the Linux kernel. **There is no Contributor License Agreement to sign, and no
paperwork.**

Add `-s` when you commit:

```bash
git commit -s -m "fix: handle empty canonical store"
```

That appends one line to the commit message:

```
Signed-off-by: Your Name <you@example.com>
```

By adding it you certify the four points in the [`DCO`](DCO) file: that you wrote
the code, or took it from somewhere under a compatible licence, or received it
from someone who certified the same — and that you understand the contribution
and its record are public and kept indefinitely.

### What it means, and what it does not

|  | |
|---|---|
| You keep your copyright | **yes** — nothing is assigned or transferred |
| Your contribution is licensed to the project | under **AGPL-3.0-or-later**, the project's own licence, and nothing beyond it |
| You can reuse your own code elsewhere | **yes**, on any terms you like |
| You owe support or maintenance | **no** |
| You are obliged to keep contributing | **no** |
| Anyone can relicense your contribution | **no** — it stays under the AGPL |

### Set your identity first

The sign-off must carry a real name and a working email address — it is a
certification, so it needs to identify someone. Pseudonymous accounts are fine
for the forge; the sign-off is not the place for one.

```bash
git config user.name  "Your Name"
git config user.email "you@example.com"
```

### If you forget

Last commit:

```bash
git commit --amend -s --no-edit
```

Several commits in a branch:

```bash
git rebase --signoff main
```

Then force-push your branch. A pull request whose commits are not all signed off
cannot be merged — the check is mechanical, not a judgement of the change.

---

## 2. Before you open a pull request

Install the dependencies:

```bash
pip install -r Scripts/utils/requirements.txt
```

Run the checks:

```bash
# Tests
pytest Tests/ -v                          # unit tests (integration excluded)
pytest Tests/ -v -m integration           # include integration (needs a real sops)
NOAH_SKIP_ANSIBLE=true pytest Tests/ -q   # skip Ansible

# Lint and security scan
ruff check Scripts/ noah.py
bandit -r Scripts/ noah.py -ll
ansible-lint Ansible/
```

`noah.py` re-execs itself under `.venv/bin/python3` when the venv exists, so
`python3 noah.py` always runs with the right interpreter.

---

## 3. Third-party material

This is clause **(b)** of the DCO, and it is the one that actually needs your
attention. If your contribution includes code, assets, datasets or documentation
you did not write, **say so explicitly** in the pull request:

```
Third-party material : <name and description>
Source              : <URL or reference>
Author              : <rights holder>
Licence             : <SPDX identifier or full title>
Restrictions        : <attribution, reciprocity obligations, or "none">
```

The licence must be compatible with AGPL-3.0-or-later. Permissive licences (MIT,
BSD, Apache-2.0) and GPL-family licences generally are; proprietary code, code
under a non-commercial or "source available" licence, and code with no licence
at all are not.

Undeclared third-party material is the most common way a codebase's licensing
gets quietly broken. Declaring it costs nothing and is exactly what your
sign-off certifies.

---

## 4. Secrets

Never commit secrets. NOAH keeps them in a SOPS/Age-encrypted canonical store,
applied out-of-band — see the README.

If you believe you have committed a secret, say so immediately rather than
force-pushing over it; the value has to be rotated either way.

---

## 5. Reporting a security issue

Do not open a public issue for a security vulnerability. Email
contact@nicolasengel.fr instead, and allow reasonable time for a fix before
disclosure.

---

## 6. Pull request expectations

- One logical change per pull request.
- Explain **why**, not only what — the diff already shows what.
- Match the surrounding code's style; `ruff` is the arbiter for Python.
- Update documentation affected by your change.
- Tests for behaviour changes, where the existing suite gives you a place to
  put them.
- All commits signed off (section 1).

Maintainers may decline a contribution, or remove it later, for reasons of
scope, direction or maintenance cost. That is not a judgement of the work.
