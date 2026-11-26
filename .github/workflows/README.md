# GitHub Actions is intentionally disabled on this repository

CI was stopped deliberately. Both workflows that existed here (`.github/workflows/probe.yml` and `.github/workflows/test.yml`) are **disabled at the repository level**, and no workflow file is committed to this tree.

Verified state:

```
$ gh api repos/isiddharthsarkar/Clyra-Vendor/actions/workflows
427765060  probe  disabled_manually
427770712  test   disabled_manually
active workflows: 0
```

## Why

1. **The account cannot run Actions at all.** Every run fails at dispatch with:

   > The job was not started because recent account payments have failed or
   > your spending limit needs to be increased.

   No step ever executes (`runner_id: 0`). A red check therefore says nothing
   about the code and only creates noise.

2. **Verification does not need CI.** The full suite runs locally in about a
   second and requires no network, no device and no root:

   ```bash
   ./scripts/tests/run-tests.sh
   ```

   plus the standalone auditors:

   ```bash
   python3 scripts/tests/check_arch.py .
   python3 scripts/tests/check_blobs.py . --strict
   python3 scripts/tests/check_rules_resolve.py vendor.mk .
   python3 scripts/generate_build_files.py --check
   ```

## If you want CI back

Resolve the billing block in **Settings → Billing & plans**, then restore
`test.yml` from git history (`git log --all -- .github/workflows/test.yml`).
Re-adding a workflow while billing is blocked only produces a permanently red
check.
