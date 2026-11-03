#!/usr/bin/env bash
# Usage: bash ~/.codex/scripts/virtuoso-batch.sh [--project DIR] [--diagnostic] [job.il]
# Default project: invocation directory. Relative jobs resolve from the project.
# A custom job should return normally; this driver handles completion and exit.
set -eo pipefail
umask 077

usage() {
    printf 'Usage on ECE: bash ~/.codex/scripts/virtuoso-batch.sh [--project DIR] [--diagnostic] [job.il]\n'
}
project=$(pwd -P)
diagnostic=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --diagnostic) diagnostic=true; shift ;;
        --project)
            if [[ $# -lt 2 ]]; then usage >&2; exit 64; fi
            project=$(cd -- "$2" && pwd -P) || exit 66
            shift 2 ;;
        --) shift; break ;;
        -*) usage >&2; exit 64 ;;
        *) break ;;
    esac
done
if [[ $# -gt 1 || $(uname -s) != Linux ]]; then
    usage >&2
    exit 64
fi
if [[ ! -f "$project/cds.lib" || ! -r "$project/cds.lib" ]]; then
    printf 'ERROR: No readable cds.lib in Cadence project root: %s\nRun from your project directory or pass --project DIR. Setup was not run.\n' "$project" >&2
    exit 66
fi
job=
if [[ $# == 1 ]]; then
    job=$(cd -- "$project" && readlink -f -- "$1") || exit 66
    if [[ ! -f "$job" || ! -r "$job" ]]; then
        printf 'ERROR: Job is not a readable file: %s (project: %s)\n' "$1" "$project" >&2
        exit 66
    fi
fi
duration=${VIRTUOSO_TIMEOUT_SECONDS:-90}
[[ "$duration" =~ ^[1-9][0-9]*$ ]] || {
    printf 'VIRTUOSO_TIMEOUT_SECONDS must be a positive integer\n' >&2
    exit 64
}
run_root="$project/runs"
if [[ -z "$job" || "$diagnostic" == true ]]; then
    run_root="$HOME/.local/state/codex/virtuoso"
fi
mkdir -p "$run_root"
run=$(mktemp -d "$run_root/virtuoso_batch_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")
printf 'RUN=%s\n' "$run"

# The site setup copies cds.lib/.cdsinit into its current directory. Run it in
# scratch, then return to the normal project so its mappings/init still apply.
mkdir "$run/setup"
cd "$run/setup"
set +e
if declare -F cadence_env >/dev/null; then
    cadence_env > "$run/setup.stdout.log" 2> "$run/setup.stderr.log"
    setup_status=$?
else
    source /apps/settings > "$run/setup.stdout.log" 2> "$run/setup.stderr.log"
    setup_status=$?
fi
set -e
printf '%s\n' "$setup_status" > "$run/setup.status"
if [[ "$setup_status" != 0 ]]; then
    cat "$run/setup.stderr.log" >&2
    exit "$setup_status"
fi
export PATH=/apps/cds/xcelium2309/tools.lnx86/bin:/apps/cds/xcelium2309/tools/bin:$PATH
cd "$project"
virtuoso=$(type -P virtuoso)

# Private, authenticated Xvfb is managed by the installed -nograph wrapper.
# Do not reuse an interactive display or let its cleanup scan other sessions.
unset DISPLAY CDS_NOGRAPH_DISPLAY CDS_XVFB_UD CDS_XVFB_OPTIONS CDS_XVFB_SERVER_OPTIONS CDS_XVFB_DEBUG
export CDS_XVFB_AUTOCLEAN=none CDS_XVFB_MONITOR=0
export CODEX_VIRTUOSO_RUN="$run" CODEX_VIRTUOSO_JOB="$job"
{
    printf 'host=%s\nuser=%s\nproject=%s\njob=%s\n' "$(hostname)" "$(id -un)" "$project" "${job:-<generic-smoke>}"
    printf 'bash=%s\nvirtuoso=%s\n' "$BASH_VERSION" "$virtuoso"
    "$virtuoso" -W
    command -v xrun
    xrun -version
} > "$run/context.log" 2>&1
if [[ -n "$job" ]]; then
    cp -- "$job" "$run/job.il"
else
    cat > "$run/job.il" <<'IL'
let((out)
  out=outfile(strcat(getShellEnvVar("CODEX_VIRTUOSO_RUN") "/smoke.txt"))
  unless(out error("Cannot write smoke result"))
  fprintf(out "CODEX_VIRTUOSO_SMOKE_OK\nLIBRARY_COUNT %d\n" length(ddGetLibList()))
  close(out)
)
IL
fi
export CODEX_VIRTUOSO_JOB="$run/job.il"
cat > "$run/driver.il" <<'IL'
let((result marker)
  result=errset(load(getShellEnvVar("CODEX_VIRTUOSO_JOB")) t)
  unless(result exit(1))
  marker=outfile(strcat(getShellEnvVar("CODEX_VIRTUOSO_RUN") "/completion.ok"))
  unless(marker exit(2))
  fprintf(marker "CODEX_VIRTUOSO_COMPLETE %s\n" getShellEnvVar("CODEX_VIRTUOSO_RUN"))
  close(marker)
  exit(0)
)
IL
command=(timeout --kill-after=10s "${duration}s" "$virtuoso"
    -nograph -replay "$run/driver.il" -log "$run/CDS.log")
printf '%q ' "${command[@]}" > "$run/command.txt"
printf '\n' >> "$run/command.txt"
set +e
"${command[@]}" > "$run/stdout.log" 2> "$run/stderr.log"
status=$?
set -e
printf '%s\n' "$status" > "$run/virtuoso.status"
if [[ "$status" == 0 ]] && ! grep -Fxq "CODEX_VIRTUOSO_COMPLETE $run" "$run/completion.ok"; then
    printf 'Missing completion marker; see %s\n' "$run/CDS.log" >&2
    status=65
fi
printf '%s\n' "$status" > "$run/status"
printf 'STATUS=%s\n' "$status"
if [[ "$status" != 0 ]]; then
    cat "$run/stderr.log" >&2
else
    cat "$run/completion.ok"
    if [[ -f "$run/smoke.txt" ]]; then cat "$run/smoke.txt"; fi
    if [[ -f "$run/cellview.txt" ]]; then cat "$run/cellview.txt"; fi
fi
exit "$status"
