#!/bin/bash
# Script to start/stop Odoo 19.0
# Usage: ./run_odoo.sh start|stop|restart

ODOO_DIR="/Users/trung/projects/odoo"
CONFIG="$ODOO_DIR/odoo.conf"
PIDFILE="$ODOO_DIR/odoo.pid"

start() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Odoo is already running (PID: $(cat $PIDFILE))"
        exit 1
    fi
    echo "Starting Odoo..."
    cd "$ODOO_DIR"
    python3 odoo-bin -c "$CONFIG" --http-port=8069 -d odoo_dev &
    echo $! > "$PIDFILE"
    sleep 2
    echo "Odoo started at http://localhost:8069"
    echo "Login with admin / admin"
}

stop() {
    if [ ! -f "$PIDFILE" ]; then
        echo "Odoo is not running (no PID file)"
        exit 1
    fi
    PID=$(cat "$PIDFILE")
    echo "Stopping Odoo (PID: $PID)..."
    kill $PID 2>/dev/null
    rm -f "$PIDFILE"
    echo "Odoo stopped"
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Odoo is running (PID: $(cat $PIDFILE))"
        echo "Access at http://localhost:8069"
    else
        echo "Odoo is not running"
    fi
}

case "${1:-}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 1; start ;;
    status)  status ;;
    *)       echo "Usage: $0 {start|stop|restart|status}" ;;
esac