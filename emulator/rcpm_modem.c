/* RCP/M virtual modem. Included by simio.c; also compiled alone by tests.
 * Project-authored hardware interface, independent of BYE5 source.
 */
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define RM_CAP 8192
static int rm_mode, rm_listener = -1, rm_peer = -1, rm_connecting;
static unsigned char rm_control, rm_dcd, rm_ri, rm_escape;
static unsigned char rm_rx[RM_CAP], rm_tx[RM_CAP];
static size_t rm_nr, rm_nt;
static struct sockaddr_in rm_address;
static time_t rm_retry;
static uint64_t rm_idle_origin;
static unsigned short rm_idle_snapshot;
static unsigned char rm_idle_phase, rm_idle_armed;

#ifndef RM_CLOCK_NOW
static uint64_t rm_clock_now(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) < 0) {
        perror("RCP/M monotonic clock");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)now.tv_sec * UINT64_C(1000000000) + (uint64_t)now.tv_nsec;
}
#define RM_CLOCK_NOW rm_clock_now
#endif

/* Port 74 is an inactivity stopwatch, independent of the emulated CPU.
 * OUT resets it. Paired INs return elapsed whole minutes, low then high;
 * the first read latches both bytes. Saturation cannot wrap away a timeout.
 */
static void rcpm_idle_reset(unsigned char unused)
{
    (void)unused;
    rm_idle_origin = RM_CLOCK_NOW();
    rm_idle_snapshot = 0;
    rm_idle_phase = 0;
    rm_idle_armed = rm_mode != 0;
}

static unsigned char rcpm_idle_read(void)
{
    if (!rm_idle_phase) {
        uint64_t elapsed = 0;
        if (rm_idle_armed) {
            uint64_t now = RM_CLOCK_NOW();
            if (now >= rm_idle_origin)
                elapsed = (now - rm_idle_origin) / UINT64_C(60000000000);
        }
        rm_idle_snapshot = elapsed > 65535 ? 65535 : (unsigned short)elapsed;
        rm_idle_phase = 1;
        return (unsigned char)rm_idle_snapshot;
    }
    rm_idle_phase = 0;
    return (unsigned char)(rm_idle_snapshot >> 8);
}

static void rm_disconnect(void)
{
    if (rm_peer >= 0) close(rm_peer);
    rm_peer = -1;
    rm_connecting = 0;
    rm_dcd = rm_ri = rm_escape = 0;
    rm_nr = rm_nt = 0;
    rm_idle_armed = rm_idle_phase = 0;
    rm_retry = time(NULL) + 1;
}

static void rcpm_modem_close(void)
{
    rm_disconnect();
    if (rm_listener >= 0) close(rm_listener);
    rm_listener = -1;
    rm_mode = 0;
}

static int rm_socket(void)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    if (fcntl(fd, F_SETFL, O_NONBLOCK) < 0 ||
        fcntl(fd, F_SETFD, FD_CLOEXEC) < 0) {
        close(fd);
        return -1;
    }
#ifdef SO_NOSIGPIPE
    {
        int one = 1;
        if (setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one)) < 0) {
            close(fd);
            return -1;
        }
    }
#endif
    return fd;
}

static void rm_dtr(void)
{
    rm_tx[rm_nt++] = 255;
    rm_tx[rm_nt++] = rm_control & 1;
}

/* Disabled unless explicitly selected. IPv4 only, matching current cpmsim. */
static int rcpm_modem_init(void)
{
    const char *mode = getenv("RCPM_MODEM");
    const char *host = getenv("RCPM_MODEM_HOST");
    const char *port = getenv("RCPM_MODEM_PORT");
    char *end;
    long number;
    int one = 1;
    rcpm_modem_close();
    rm_control = 0;
    rm_retry = 0;
    if (!mode || !*mode) return 0;
    if (!strcmp(mode, "direct")) rm_mode = 1;
    else if (!strcmp(mode, "ip232")) rm_mode = 2;
    else goto bad;
    if (!port || !*port) goto bad;
    errno = 0;
    number = strtol(port, &end, 10);
    if (errno || *end || number < 1 || number > 65535) goto bad;
    memset(&rm_address, 0, sizeof(rm_address));
    rm_address.sin_family = AF_INET;
    rm_address.sin_port = htons((unsigned short)number);
    if (inet_pton(AF_INET, host ? host : "127.0.0.1", &rm_address.sin_addr) != 1)
        goto bad;
    if (rm_mode == 1) {
        rm_listener = rm_socket();
        if (rm_listener < 0) goto bad;
        if (setsockopt(rm_listener, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)) < 0 ||
            bind(rm_listener, (struct sockaddr *)&rm_address, sizeof(rm_address)) < 0 ||
            listen(rm_listener, 4) < 0) goto bad;
    }
    /* Release launchers opt in; print locally only after listen succeeds. */
    if (getenv("RCPM_ANNOUNCE") && !strcmp(getenv("RCPM_ANNOUNCE"), "1")) {
        if (rm_mode == 1) {
            printf("RCP/M is now running on port %ld.\r\n", number);
            printf("Listening address: %s (direct raw TCP).\r\n", host ? host : "127.0.0.1");
            printf("See INSTALLATION.DOC for information on how to connect\r\n"
                   "from your system (Windows, Linux, macOS).\r\n");
        } else {
            printf("RCP/M is using the virtual modem endpoint %s:%ld (IP232).\r\n",
                   host ? host : "127.0.0.1", number);
            printf("Callers connect to the virtual modem's caller port; see INSTALLATION.DOC.\r\n");
        }
        fflush(stdout);
    }
    return 0;
bad:
    fprintf(stderr, "Invalid/unavailable RCPM_MODEM endpoint (mode, IPv4 host, port)\n");
    rcpm_modem_close();
    return -1;
}

static void rm_poll(void)
{
    unsigned char wire[1024];
    ssize_t n;
    size_t i;
    if (!rm_mode) return;
    if (rm_mode == 1) {
        /* One accept per poll bounds time even under a connection flood. */
        int fd = accept(rm_listener, NULL, NULL);
        if (fd >= 0) {
            if (rm_peer >= 0 || (rm_control & 3) != 3) close(fd);
            else {
                rm_peer = fd;
                if (fcntl(fd, F_SETFL, O_NONBLOCK) < 0 ||
                    fcntl(fd, F_SETFD, FD_CLOEXEC) < 0) rm_disconnect();
#ifdef SO_NOSIGPIPE
                else {
                    int one = 1;
                    if (setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one)) < 0)
                        rm_disconnect();
                }
#endif
                if (rm_peer >= 0) rm_dcd = 1;
            }
        }
    } else if (rm_peer < 0 && time(NULL) >= rm_retry) {
        rm_peer = rm_socket();
        if (rm_peer < 0) { rm_retry = time(NULL) + 1; return; }
        if (connect(rm_peer, (struct sockaddr *)&rm_address, sizeof(rm_address)) == 0)
            rm_dtr();
        else if (errno == EINPROGRESS) rm_connecting = 1;
        else rm_disconnect();
    }
    if (rm_peer < 0) return;
    if (rm_connecting) {
        struct pollfd p = {rm_peer, POLLOUT, 0};
        if (poll(&p, 1, 0) <= 0) return;
        if (p.revents) {
            int error = 0;
            socklen_t length = sizeof(error);
            if (getsockopt(rm_peer, SOL_SOCKET, SO_ERROR, &error, &length) < 0 || error) {
                rm_disconnect(); return;
            }
            rm_connecting = 0;
            rm_dtr();
        }
    }
    if (rm_nt) {
#ifdef MSG_NOSIGNAL
        n = send(rm_peer, rm_tx, rm_nt, MSG_NOSIGNAL);
#else
        n = send(rm_peer, rm_tx, rm_nt, 0);
#endif
        if (n > 0) {
            rm_nt -= (size_t)n;
            memmove(rm_tx, rm_tx + n, rm_nt);
        } else if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
            rm_disconnect(); return;
        }
    }
    /* Worst case is one decoded byte per wire byte. Never drop data on overflow. */
    i = RM_CAP - rm_nr;
    if (!i) return;
    if (i > sizeof(wire)) i = sizeof(wire);
    n = recv(rm_peer, wire, i, 0);
    if (!n) { rm_disconnect(); return; }
    if (n < 0) {
        if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) rm_disconnect();
        return;
    }
    for (i = 0; i < (size_t)n; i++) {
        unsigned char c = wire[i];
        if (rm_mode == 1) rm_rx[rm_nr++] = c;
        else if (rm_escape) {
            rm_escape = 0;
            if (c == 255) rm_rx[rm_nr++] = 255;
            else if (c <= 3) {
                rm_dcd = c & 1;
                rm_ri = (c >> 1) & 1;
            }
        } else if (c == 255) rm_escape = 1;
        else rm_rx[rm_nr++] = c;
    }
}

/* IN 70: RX-ready, TX-ready, carrier, transport-link, answer-enabled, DTR, RI. */
static unsigned char rcpm_modem_status(void)
{
    unsigned char status = 0;
    rm_poll();
    if (rm_nr) status |= 1;
    if (rm_peer >= 0 && !rm_connecting) {
        status |= 8;
        if (rm_nt <= RM_CAP - 4) status |= 2;
    }
    if (rm_dcd) status |= 4;
    if (rm_control & 2) status |= 16;
    if (rm_control & 1) status |= 32;
    if (rm_ri) status |= 64;
    return status;
}

static unsigned char rcpm_modem_read(void)
{
    unsigned char c = 0;
    rm_poll();
    if (rm_nr) {
        c = rm_rx[0];
        --rm_nr;
        memmove(rm_rx, rm_rx + 1, rm_nr);
    }
    return c;
}

static void rcpm_modem_write(unsigned char c)
{
    rm_poll();
    if (rm_peer < 0 || rm_connecting || rm_nt > RM_CAP - 4) return;
    rm_tx[rm_nt++] = c;
    if (rm_mode == 2 && c == 255) rm_tx[rm_nt++] = c;
    rm_poll();
}

static unsigned char rcpm_modem_control_read(void)
{
    return rm_control;
}

/* OUT 72: persistent DTR/answer in bits 0/1; bit 2 pulses direct hangup.
 * IP232 hangup uses DTR low (&D2 at tcpser); answering uses Hayes commands.
 */
static void rcpm_modem_control(unsigned char value)
{
    unsigned char previous = rm_control;
    rm_control = value & 3;
    if (rm_mode == 1) {
        if (!(value & 1) || (value & 4)) rm_disconnect();
    } else if (rm_mode == 2 && ((previous ^ value) & 1)) {
        rm_poll();
        if (rm_peer >= 0 && !rm_connecting) {
            /* Preserve IP232 framing even after a partial socket write. */
            if (rm_nt <= RM_CAP - 2) rm_dtr();
            else { rm_disconnect(); return; }
            rm_poll();
        }
    }
}
