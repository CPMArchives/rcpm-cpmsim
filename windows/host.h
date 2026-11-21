/* Native Win32 host services for the unchanged cpmsim guest devices.
 * Socket descriptors are table indices, never truncated SOCKET handles. */
#ifndef RCPM_WINDOWS_HOST_H
#define RCPM_WINDOWS_HOST_H
#define WIN32_LEAN_AND_MEAN
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <errno.h>
#include <fcntl.h>
#include <io.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#ifndef O_NONBLOCK
#define O_NONBLOCK 0x40000000
#endif
#define F_SETFL 1
#define F_SETFD 2
#define FD_CLOEXEC 1
#define SIGQUIT 3
#define SIGALRM 14
#define ITIMER_REAL 0
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 1
#endif
/* winsock provides struct pollfd, but fd must remain a full SOCKET-sized field. */
typedef unsigned long nfds_t;
struct rcpm_sigaction { void (*sa_handler)(int); int sa_mask; int sa_flags; };
struct itimerval { struct timeval it_interval, it_value; };
int rcpm_sigaction(int, const struct rcpm_sigaction *, struct rcpm_sigaction *);
int rcpm_setitimer(int, const struct itimerval *, struct itimerval *);
uint64_t rcpm_monotonic_us(void);
int rcpm_clock_gettime(int, struct timespec *);
int rcpm_nanosleep(const struct timespec *, struct timespec *);
int rcpm_open(const char *, int, ...);
ssize_t rcpm_read(int, void *, size_t);
ssize_t rcpm_write(int, const void *, size_t);
int rcpm_close(int);
int rcpm_link(const char *, const char *);
int rcpm_poll(struct pollfd *, nfds_t, int);
int rcpm_fcntl(int, int, ...);
int rcpm_socket(int, int, int);
int rcpm_accept(int, struct sockaddr *, socklen_t *);
int rcpm_connect(int, const struct sockaddr *, socklen_t);
int rcpm_bind(int, const struct sockaddr *, socklen_t);
int rcpm_listen(int, int);
int rcpm_getsockname(int, struct sockaddr *, socklen_t *);
int rcpm_setsockopt(int, int, int, const void *, socklen_t);
int rcpm_getsockopt(int, int, int, void *, socklen_t *);
ssize_t rcpm_send(int, const void *, size_t, int);
ssize_t rcpm_recv(int, void *, size_t, int);
void set_unix_terminal(void);
void reset_unix_terminal(void);
#ifndef RCPM_WINDOWS_HOST_IMPLEMENTATION
#define open rcpm_open
#define read rcpm_read
#define write rcpm_write
#define close rcpm_close
#define fsync _commit
#define link rcpm_link
#define poll rcpm_poll
#define fcntl rcpm_fcntl
#define socket rcpm_socket
#define accept rcpm_accept
#define connect rcpm_connect
#define bind rcpm_bind
#define listen rcpm_listen
#define setsockopt rcpm_setsockopt
#define getsockopt rcpm_getsockopt
#define send rcpm_send
#define recv rcpm_recv
#define sigaction rcpm_sigaction
#define sigemptyset(p) (*(p) = 0)
#define setitimer rcpm_setitimer
#define clock_gettime rcpm_clock_gettime
#define nanosleep rcpm_nanosleep
#endif
#endif
