#!/bin/zsh
# Keep a caller listener in the background and open the persistent local console.
set -eu
setopt PIPE_FAIL

script_path=${0:A}
repository=${script_path:h}
project=${repository:h}
export PATH="$repository/build/cpmtools/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export RCPM_INSTANCE=${RCPM_INSTANCE:-$project/rcpm-cpm3}
export RCPM_CPMSIM=${RCPM_CPMSIM:-$project/rcpm-cpm3-trial/runtime/cpmsim-console}
export RCPM_CALLER_INSTANCE=${RCPM_CALLER_INSTANCE:-$project/rcpm-cpm3-trial}
export RCPM_CALLER_CPMSIM=${RCPM_CALLER_CPMSIM:-$project/rcpm-cpm3-trial/runtime/cpmsim}
export RCPM_BIND_ADDRESS=${RCPM_BIND_ADDRESS:-0.0.0.0}
export RCPM_PORT=${RCPM_PORT:-4000}
console_session=rcpm-console
listener_session=rcpm-listener
listener_log="$RCPM_CALLER_INSTANCE/listener.log"

fail() {
    print -u2 -r -- "$*"
    exit 1
}

port_in_use() {
    # A bind probe avoids connecting to the listener and booting a guest.
    python3 - "$RCPM_BIND_ADDRESS" "$RCPM_PORT" <<'PY'
import errno
import socket
import sys
with socket.socket() as probe:
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind((sys.argv[1], int(sys.argv[2])))
    except OSError as error:
        if error.errno == errno.EADDRINUSE:
            sys.exit(0)
        raise
sys.exit(1)
PY
}

command -v tmux >/dev/null || fail 'tmux is unavailable. Install it with brew install tmux.'
command -v python3 >/dev/null || fail 'python3 is unavailable.'
[[ "$RCPM_PORT" == <-> && $RCPM_PORT -ge 1 && $RCPM_PORT -le 65535 ]] || fail 'RCPM_PORT must be between 1 and 65535.'

for simulator in "$RCPM_CPMSIM" "$RCPM_CALLER_CPMSIM"; do
    [[ -x "$simulator" ]] || fail "cpmsim executable unavailable at $simulator"
done
for instance in "$RCPM_INSTANCE" "$RCPM_CALLER_INSTANCE"; do
    for drive in a b i j p; do
        [[ -r "$instance/disks/drive$drive.dsk" ]] || fail "Missing readable drive $drive in $instance"
    done
done
[[ -r "$RCPM_INSTANCE/conf/net_server.conf" && -r "$RCPM_INSTANCE/conf/net_client.conf" ]] ||
    fail "Missing local network configuration in $RCPM_INSTANCE/conf"

case ${1:-} in
    --setup-sysop)
        [[ $# == 1 ]] || fail 'Usage: launch_rcpm.zsh [--check|--setup-sysop|--publish|--archive-status]'
        exec python3 "$repository/archive_admin.py" setup \
            --console "$RCPM_INSTANCE" --callers "$RCPM_CALLER_INSTANCE" \
            --mount-command "${RCPM_CPMSIM:h}/mount-sysop.com"
        ;;
    --publish)
        [[ $# == 1 ]] || fail 'Usage: launch_rcpm.zsh [--check|--setup-sysop|--publish|--archive-status]'
        exec python3 "$repository/archive_admin.py" publish --console "$RCPM_INSTANCE"
        ;;
    --archive-status)
        [[ $# == 1 ]] || fail 'Usage: launch_rcpm.zsh [--check|--setup-sysop|--publish|--archive-status]'
        exec python3 "$repository/archive_admin.py" status --console "$RCPM_INSTANCE"
        ;;
    --check)
        [[ $# == 1 ]] || fail 'Usage: launch_rcpm.zsh [--check]'
        print -r -- 'Console and listener prerequisites verified.'
        exit 0
        ;;
    --listener)
        exec python3 "$repository/serve_rcpm.py" \
            --instance "$RCPM_CALLER_INSTANCE" --cpmsim "$RCPM_CALLER_CPMSIM" \
            --inbox "$RCPM_CALLER_INSTANCE/inbox" \
            --bind-address "$RCPM_BIND_ADDRESS" --port "$RCPM_PORT" \
            >> "$listener_log" 2>&1
        ;;
    --console)
        [[ -n ${TMUX:-} ]] || fail 'Run this launcher without arguments to open the console in tmux.'
        exec python3 "$repository/launch_rcpm_cpm3.py" \
            --instance "$RCPM_INSTANCE" --cpmsim "$RCPM_CPMSIM"
        ;;
esac

[[ $# == 0 ]] || fail 'Usage: launch_rcpm.zsh [--check|--setup-sysop|--publish|--archive-status]'
[[ -t 0 && -t 1 ]] || fail 'Run this launcher in an interactive Terminal window.'
if [[ -n ${TMUX:-} ]]; then
    tmux display-message -p '#{session_name}' >/dev/null 2>&1 ||
        fail 'TMUX is set, but its tmux server is unavailable. Open a fresh Terminal tab.'
fi

# tmux servers can retain older environment values. Pass this launch's settings.
typeset -a launch_environment
launch_environment=(
    -e "RCPM_INSTANCE=$RCPM_INSTANCE" -e "RCPM_CPMSIM=$RCPM_CPMSIM"
    -e "RCPM_CALLER_INSTANCE=$RCPM_CALLER_INSTANCE"
    -e "RCPM_CALLER_CPMSIM=$RCPM_CALLER_CPMSIM" -e "RCPM_PORT=$RCPM_PORT"
    -e "RCPM_BIND_ADDRESS=$RCPM_BIND_ADDRESS"
)

if ! port_in_use; then
    if ! tmux has-session -t "=$listener_session" 2>/dev/null; then
        if ! tmux new-session -d -s "$listener_session" -n Listener \
                "${launch_environment[@]}" /bin/zsh "$script_path" --listener; then
            tmux has-session -t "=$listener_session" 2>/dev/null || fail 'Could not start the listener session.'
        fi
    fi
    for attempt in {1..50}; do
        port_in_use && break
        if ! tmux has-session -t "=$listener_session" 2>/dev/null; then
            [[ ! -f "$listener_log" ]] || tail -n 10 "$listener_log" >&2
            fail "Listener exited. See $listener_log"
        fi
        sleep 0.1
    done
    port_in_use || fail "Listener did not become ready. See $listener_log"
fi

if [[ -n ${TMUX:-} ]]; then
    if ! tmux has-session -t "=$console_session" 2>/dev/null; then
        if ! tmux new-session -d -s "$console_session" -n CP-M -x 80 -y 24 \
                "${launch_environment[@]}" /bin/zsh "$script_path" --console; then
            tmux has-session -t "=$console_session" 2>/dev/null || fail 'Could not start the console session.'
        fi
    fi
    exec tmux switch-client -t "=$console_session"
fi

exec tmux new-session -A -s "$console_session" -n CP-M -x 80 -y 24 \
    "${launch_environment[@]}" /bin/zsh "$script_path" --console
