# Watchdog lifecycle: framework adapters

The scope discipline in SKILL.md (§1–§4) is runtime-agnostic. This is the
exact call shape per scheduler primitive for pausing/resuming/deleting the
job itself, wired to `scripts/watchdog_scope.py` as the in-body gate.

## Hermes `cronjob_manage`

Hermes cron jobs support pause/resume natively — prefer that over deleting
and recreating.

```
# create paused, nothing fires yet
cronjob_manage(action="create", schedule="*/5 * * * *", command="...", paused=true)

# at dispatch time: resume the job AND activate the scope marker
cronjob_manage(action="resume", job_id="build-check-142")
python3 scripts/watchdog_scope.py activate build-check-142 --ttl-minutes 180

# inside the job's command, before the real check:
python3 scripts/watchdog_scope.py check build-check-142 || exit 0

# once resolved:
cronjob_manage(action="pause", job_id="build-check-142")
python3 scripts/watchdog_scope.py deactivate build-check-142
# or, for a genuinely one-off watchdog:
cronjob_manage(action="delete", job_id="build-check-142")
```

Use the *same* ID string for the cron job and the scope marker so `list`
output and cron state never drift apart.

## macOS launchd

launchd has no native pause; use `bootout`/`bootstrap` (or `load -w`/
`unload -w`) to toggle a LaunchAgent, and let the plist's script call the
scope gate.

```bash
# create the plist, disabled
launchctl bootout gui/$(id -u)/com.example.watchdog.build-check-142 2>/dev/null || true

# at dispatch time
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.watchdog.build-check-142.plist
python3 scripts/watchdog_scope.py activate build-check-142 --ttl-minutes 180

# inside the plist's ProgramArguments script:
python3 scripts/watchdog_scope.py check build-check-142 || exit 0

# once resolved
launchctl bootout gui/$(id -u)/com.example.watchdog.build-check-142
python3 scripts/watchdog_scope.py deactivate build-check-142
rm ~/Library/LaunchAgents/com.example.watchdog.build-check-142.plist   # one-off jobs
```

## Linux systemd timers

Timers support `systemctl stop`/`start` on the `.timer` unit without
touching the unit file.

```bash
systemctl --user start build-check-142.timer
python3 scripts/watchdog_scope.py activate build-check-142 --ttl-minutes 180

# inside the paired .service's ExecStart script:
python3 scripts/watchdog_scope.py check build-check-142 || exit 0

systemctl --user stop build-check-142.timer
python3 scripts/watchdog_scope.py deactivate build-check-142
```

## GitHub Actions scheduled workflows

Actions has no per-run pause — `schedule:` triggers fire regardless. Use the
scope gate as the FIRST step so unwanted runs exit immediately (near-zero
billed minutes) instead of skipping the workflow definition itself:

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'
jobs:
  watch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: scope gate
        run: python3 scripts/watchdog_scope.py check build-check-142 || exit 0
      - name: real poll logic
        run: ./poll_build.sh
```

Activate/deactivate the marker from whatever process dispatches/resolves the
watched target (a separate workflow_dispatch call, or a step in the job
that kicks off the build), since the scheduled workflow itself can't opt out
of being triggered — only out of doing anything once triggered.

## Cloud schedulers (AWS EventBridge / GCP Cloud Scheduler)

Both support enable/disable/delete on the rule or job itself:

```bash
# AWS EventBridge
aws events enable-rule  --name build-check-142
aws events disable-rule --name build-check-142

# GCP Cloud Scheduler
gcloud scheduler jobs resume build-check-142
gcloud scheduler jobs pause  build-check-142
```

Pair each enable/resume with `watchdog_scope.py activate` and each
disable/pause with `deactivate`, same pattern as above — the cloud
scheduler's own state and the local scope marker should always agree, and
the in-body `check` call is what protects you on the runs between "target
resolved" and "you remembered to actually disable the rule."
