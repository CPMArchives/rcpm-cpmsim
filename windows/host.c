#define RCPM_WINDOWS_HOST_IMPLEMENTATION
#include "host.h"
#include <stdarg.h>
#include <string.h>
#include <limits.h>

#define SOCKET_BASE 65536
#define SOCKET_COUNT 32
static SOCKET sockets[SOCKET_COUNT];
static int sockets_initialized, console_initialized;
static DWORD input_mode, output_mode;
static unsigned char keys[32];
static size_t key_count, key_offset;
static unsigned key_repeat;
static void (*alarm_handler)(int);
static void (*interrupt_handler)(int), (*termination_handler)(int);
static uint64_t timer_due, timer_interval;
static volatile LONG break_pending;

static int socket_error(void) {
    switch (WSAGetLastError()) {
    case WSAEWOULDBLOCK: errno = EAGAIN; break;
    case WSAEINPROGRESS: case WSAEALREADY: errno = EINPROGRESS; break;
    case WSAEINTR: errno = EINTR; break;
    case WSAECONNRESET: errno = ECONNRESET; break;
    case WSAECONNREFUSED: errno = ECONNREFUSED; break;
    case WSAEADDRINUSE: errno = EADDRINUSE; break;
    default: errno = EIO; break;
    }
    return -1;
}
static int start_sockets(void) {
    if (!sockets_initialized) {
        WSADATA data;
        if (WSAStartup(MAKEWORD(2, 2), &data)) { errno = EIO; return -1; }
        for (size_t k = 0; k < SOCKET_COUNT; k++) sockets[k] = INVALID_SOCKET;
        sockets_initialized = 1;
    }
    return 0;
}
static SOCKET native_socket(int fd) {
    if (!sockets_initialized || fd < SOCKET_BASE || fd >= SOCKET_BASE + SOCKET_COUNT)
        return INVALID_SOCKET;
    return sockets[fd - SOCKET_BASE];
}
static int save_socket(SOCKET value) {
    if (value == INVALID_SOCKET) return socket_error();
    /* Never leak the listener or caller into a child utility. */
    if (!SetHandleInformation((HANDLE)value, HANDLE_FLAG_INHERIT, 0)) {
        closesocket(value); errno = EIO; return -1;
    }
    for (int k = 0; k < SOCKET_COUNT; k++) if (sockets[k] == INVALID_SOCKET) {
        sockets[k] = value; return k + SOCKET_BASE;
    }
    closesocket(value); errno = EMFILE; return -1;
}
int rcpm_socket(int family, int type, int protocol) {
    if (start_sockets()) return -1;
    return save_socket(socket(family, type, protocol));
}
int rcpm_accept(int fd, struct sockaddr *address, socklen_t *length) {
    return save_socket(accept(native_socket(fd), address, length));
}
int rcpm_connect(int fd, const struct sockaddr *address, socklen_t length) {
    int n = connect(native_socket(fd), address, length);
    if (n == SOCKET_ERROR) {
        if (WSAGetLastError() == WSAEWOULDBLOCK) { errno = EINPROGRESS; return -1; }
        return socket_error();
    }
    return n;
}
int rcpm_bind(int fd, const struct sockaddr *address, socklen_t length) {
    return bind(native_socket(fd), address, length) == SOCKET_ERROR ? socket_error() : 0;
}
int rcpm_getsockname(int fd, struct sockaddr *address, socklen_t *length) {
    return getsockname(native_socket(fd), address, length) == SOCKET_ERROR ? socket_error() : 0;
}
int rcpm_listen(int fd, int backlog) {
    return listen(native_socket(fd), backlog) == SOCKET_ERROR ? socket_error() : 0;
}
int rcpm_setsockopt(int fd, int level, int option, const void *value, socklen_t length) {
    /* Windows SO_REUSEADDR can admit a competing listener. Preserve exclusive
     * endpoint ownership instead; POSIX reuse exists only for safe restarts. */
    if (level == SOL_SOCKET && option == SO_REUSEADDR) option = SO_EXCLUSIVEADDRUSE;
    return setsockopt(native_socket(fd), level, option, value, length) == SOCKET_ERROR ? socket_error() : 0;
}
int rcpm_getsockopt(int fd, int level, int option, void *value, socklen_t *length) {
    return getsockopt(native_socket(fd), level, option, value, length) == SOCKET_ERROR ? socket_error() : 0;
}
ssize_t rcpm_send(int fd, const void *data, size_t size, int flags) {
    int n = send(native_socket(fd), data, size > INT_MAX ? INT_MAX : (int)size, flags);
    return n == SOCKET_ERROR ? socket_error() : n;
}
ssize_t rcpm_recv(int fd, void *data, size_t size, int flags) {
    int n = recv(native_socket(fd), data, size > INT_MAX ? INT_MAX : (int)size, flags);
    return n == SOCKET_ERROR ? socket_error() : n;
}
int rcpm_fcntl(int fd, int operation, ...) {
    va_list args;
    va_start(args, operation);
    int value = va_arg(args, int);
    va_end(args);
    SOCKET s = native_socket(fd);
    if (s == INVALID_SOCKET) { errno = EBADF; return -1; }
    if (operation == F_SETFL) {
        u_long on = (value & O_NONBLOCK) != 0;
        return ioctlsocket(s, FIONBIO, &on) == SOCKET_ERROR ? socket_error() : 0;
    }
    if (operation == F_SETFD && value == FD_CLOEXEC)
        return SetHandleInformation((HANDLE)s, HANDLE_FLAG_INHERIT, 0) ? 0 : -1;
    errno = EINVAL; return -1;
}
int rcpm_open(const char *path, int flags, ...) {
    int mode = 0600;
    if (flags & O_CREAT) {
        va_list args; va_start(args, flags); mode = va_arg(args, int); va_end(args);
    }
    return _open(path, (flags & ~O_NONBLOCK) | _O_BINARY | _O_NOINHERIT, mode);
}
int rcpm_link(const char *existing, const char *created) {
    if (CreateHardLinkA(created, existing, NULL)) return 0;
    errno = GetLastError() == ERROR_ALREADY_EXISTS ? EEXIST : EIO; return -1;
}
int rcpm_close(int fd) {
    SOCKET s = native_socket(fd);
    if (s != INVALID_SOCKET) {
        sockets[fd - SOCKET_BASE] = INVALID_SOCKET;
        return closesocket(s) == SOCKET_ERROR ? socket_error() : 0;
    }
    if (fd >= SOCKET_BASE) { errno = EBADF; return -1; }
    return _close(fd);
}
static void pump_keys(void) {
    if (key_count || key_repeat) return;
    HANDLE input = GetStdHandle(STD_INPUT_HANDLE);
    DWORD mode, count;
    INPUT_RECORD record;
    if (!GetConsoleMode(input, &mode)) return;
    while (PeekConsoleInputW(input, &record, 1, &count) && count) {
        if (!ReadConsoleInputW(input, &record, 1, &count) || !count) return;
        if (record.EventType != KEY_EVENT || !record.Event.KeyEvent.bKeyDown) continue;
        KEY_EVENT_RECORD *key = &record.Event.KeyEvent;
        const char *sequence = NULL;
        switch (key->wVirtualKeyCode) {
        case VK_UP: sequence = "\033[A"; break;
        case VK_DOWN: sequence = "\033[B"; break;
        case VK_RIGHT: sequence = "\033[C"; break;
        case VK_LEFT: sequence = "\033[D"; break;
        case VK_HOME: sequence = "\033[H"; break;
        case VK_END: sequence = "\033[F"; break;
        case VK_DELETE: sequence = "\177"; break;
        default: break;
        }
        if (sequence) { key_count = strlen(sequence); memcpy(keys, sequence, key_count); }
        else if (key->uChar.UnicodeChar && key->uChar.UnicodeChar <= 255) {
            keys[0] = (unsigned char)key->uChar.UnicodeChar; key_count = 1;
        }
        if (key_count) { key_repeat = key->wRepeatCount ? key->wRepeatCount : 1; return; }
    }
}
ssize_t rcpm_read(int fd, void *buffer, size_t size) {
    if (!size) return 0;
    if (native_socket(fd) != INVALID_SOCKET) return rcpm_recv(fd, buffer, size, 0);
    if (fd >= SOCKET_BASE) { errno = EBADF; return -1; }
    DWORD mode;
    if (fd == 0 && GetConsoleMode(GetStdHandle(STD_INPUT_HANDLE), &mode)) {
        while (!key_count) { pump_keys(); if (!key_count) Sleep(1); }
        /* Drain a whole key sequence without losing repeat counts. */
        size_t available = key_count - key_offset;
        size_t n = size < available ? size : available;
        memcpy(buffer, keys + key_offset, n);
        key_offset += n;
        if (key_offset == key_count) {
            key_offset = 0;
            if (--key_repeat == 0) key_count = 0;
        }
        return (ssize_t)n;
    }
    return _read(fd, buffer, size > INT_MAX ? INT_MAX : (unsigned)size);
}
ssize_t rcpm_write(int fd, const void *buffer, size_t size) {
    if (native_socket(fd) != INVALID_SOCKET) return rcpm_send(fd, buffer, size, 0);
    if (fd >= SOCKET_BASE) { errno = EBADF; return -1; }
    return _write(fd, buffer, size > INT_MAX ? INT_MAX : (unsigned)size);
}
static int descriptor_ready(int fd, short events) {
    if (fd < 0) return 0;
    if (fd >= SOCKET_BASE) return POLLNVAL;
    if (events & POLLOUT) return POLLOUT;
    if (!(events & POLLIN)) return 0;
    HANDLE handle = (HANDLE)_get_osfhandle(fd);
    DWORD mode, count;
    if (GetConsoleMode(handle, &mode)) { pump_keys(); return key_count ? POLLIN : 0; }
    if (GetFileType(handle) == FILE_TYPE_PIPE) {
        if (!PeekNamedPipe(handle, NULL, 0, NULL, &count, NULL))
            return GetLastError() == ERROR_BROKEN_PIPE ? POLLHUP : POLLERR;
        return count ? POLLIN : 0;
    }
    return GetFileType(handle) == FILE_TYPE_DISK ? POLLIN : POLLERR;
}
int rcpm_poll(struct pollfd *fds, nfds_t count, int timeout) {
    uint64_t start = GetTickCount64();
    for (;;) {
        int ready = 0;
        int interrupted = InterlockedCompareExchange(&break_pending, 0, 0) != 0;
        (void)rcpm_monotonic_us();
        if (interrupted) { errno = EINTR; return -1; }
        for (nfds_t k = 0; k < count; k++) {
            int fd = (int)fds[k].fd;
            SOCKET s = native_socket(fd);
            fds[k].revents = 0;
            if (s != INVALID_SOCKET) {
                WSAPOLLFD p = {s, fds[k].events, 0};
                int n = WSAPoll(&p, 1, 0);
                if (n == SOCKET_ERROR) return socket_error();
                fds[k].revents = p.revents;
            } else fds[k].revents = (short)descriptor_ready(fd, fds[k].events);
            if (fds[k].revents) ready++;
        }
        if (ready || timeout == 0) return ready;
        if (timeout > 0 && GetTickCount64() - start >= (uint64_t)timeout) return 0;
        Sleep(1);
    }
}
static uint64_t raw_clock_us(void) {
    LARGE_INTEGER count, frequency;
    if (!QueryPerformanceCounter(&count) || !QueryPerformanceFrequency(&frequency)) abort();
    return (uint64_t)(count.QuadPart / frequency.QuadPart) * 1000000 +
        (uint64_t)(count.QuadPart % frequency.QuadPart) * 1000000 / (uint64_t)frequency.QuadPart;
}
uint64_t rcpm_monotonic_us(void) {
    uint64_t now = raw_clock_us();
    if (timer_due && now >= timer_due) {
        timer_due = timer_interval ? now + timer_interval : 0;
        if (alarm_handler && alarm_handler != SIG_IGN && alarm_handler != SIG_DFL) alarm_handler(SIGALRM);
    }
    if (InterlockedExchange(&break_pending, 0) && interrupt_handler &&
        interrupt_handler != SIG_IGN && interrupt_handler != SIG_DFL) interrupt_handler(SIGINT);
    return now;
}
int rcpm_clock_gettime(int clock_id, struct timespec *out) {
    if (clock_id != CLOCK_MONOTONIC) { errno = EINVAL; return -1; }
    uint64_t t = rcpm_monotonic_us();
    out->tv_sec = (time_t)(t / 1000000); out->tv_nsec = (long)(t % 1000000) * 1000;
    return 0;
}
int rcpm_nanosleep(const struct timespec *duration, struct timespec *remaining) {
    if (duration->tv_sec < 0 || duration->tv_nsec < 0 || duration->tv_nsec >= 1000000000) {
        errno = EINVAL; return -1;
    }
    /* A native waitable timer avoids rounding every short CPU delay to 16 ms. */
    HANDLE timer = CreateWaitableTimerExW(NULL, NULL, CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, TIMER_ALL_ACCESS);
    if (!timer) timer = CreateWaitableTimerW(NULL, TRUE, NULL);
    if (!timer) { errno = EIO; return -1; }
    LARGE_INTEGER due;
    due.QuadPart = -((LONGLONG)duration->tv_sec * 10000000 + (duration->tv_nsec + 99) / 100);
    if (!due.QuadPart) due.QuadPart = -1;
    BOOL ok = SetWaitableTimer(timer, &due, 0, NULL, NULL, FALSE);
    DWORD result = ok ? WaitForSingleObject(timer, INFINITE) : WAIT_FAILED;
    CloseHandle(timer);
    if (result != WAIT_OBJECT_0) { errno = EIO; return -1; }
    if (remaining) memset(remaining, 0, sizeof(*remaining));
    return 0;
}
int rcpm_sigaction(int sig, const struct rcpm_sigaction *action, struct rcpm_sigaction *old) {
    if (sig == SIGALRM) {
        if (old) { memset(old, 0, sizeof(*old)); old->sa_handler = alarm_handler; }
        if (action) alarm_handler = action->sa_handler;
        return 0;
    }
    if (sig == SIGQUIT) return 0; /* Ctrl-Break is dispatched as SIGINT on the CPU thread. */
    void (**handler)(int) = sig == SIGINT ? &interrupt_handler :
                           sig == SIGTERM ? &termination_handler : NULL;
    if (!handler) { errno = EINVAL; return -1; }
    if (old) { memset(old, 0, sizeof(*old)); old->sa_handler = *handler; }
    if (action) *handler = action->sa_handler;
    return 0;
}
int rcpm_setitimer(int kind, const struct itimerval *value, struct itimerval *old) {
    if (kind != ITIMER_REAL || !value || old) { errno = EINVAL; return -1; }
    timer_interval = (uint64_t)value->it_interval.tv_sec * 1000000 + value->it_interval.tv_usec;
    uint64_t delay = (uint64_t)value->it_value.tv_sec * 1000000 + value->it_value.tv_usec;
    timer_due = delay ? raw_clock_us() + delay : 0;
    return 0;
}
static BOOL WINAPI console_control(DWORD event) {
    if (event != CTRL_BREAK_EVENT && event != CTRL_C_EVENT) return FALSE;
    InterlockedExchange(&break_pending, 1); return TRUE;
}
void set_unix_terminal(void) {
    if (console_initialized) return;
    HANDLE input = GetStdHandle(STD_INPUT_HANDLE), output = GetStdHandle(STD_OUTPUT_HANDLE);
    _setmode(0, _O_BINARY); _setmode(1, _O_BINARY);
    if (!GetConsoleMode(input, &input_mode)) return; /* Headless qualification may use pipes. */
    if (!GetConsoleMode(output, &output_mode)) return;
    DWORD raw = input_mode & ~(ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_PROCESSED_INPUT | ENABLE_QUICK_EDIT_MODE);
    raw |= ENABLE_EXTENDED_FLAGS;
    if (!SetConsoleMode(input, raw) ||
        !SetConsoleMode(output, output_mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING)) {
        SetConsoleMode(input, input_mode); SetConsoleMode(output, output_mode);
        fputs("Cannot initialize Windows console\n", stderr); exit(1);
    }
    SetConsoleCtrlHandler(console_control, TRUE);
    console_initialized = 1;
    atexit(reset_unix_terminal);
}
void reset_unix_terminal(void) {
    if (!console_initialized) return;
    SetConsoleMode(GetStdHandle(STD_INPUT_HANDLE), input_mode);
    SetConsoleMode(GetStdHandle(STD_OUTPUT_HANDLE), output_mode);
    SetConsoleCtrlHandler(console_control, FALSE);
    console_initialized = 0;
}
