/* Foreground ownership of an optional bundled modem, not a system service. */
#include <signal.h>
#include <time.h>

static volatile sig_atomic_t modem_stop_signal;
static void modem_signal(int sig) { modem_stop_signal = sig; }

static int launch_guest(char *const guest[], int owned_modem,
                        const char *address, const char *port, int lease) {
    if (!owned_modem) { execv(guest[0], guest); io_fail("cpmsim"); }
    int reservation = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in endpoint; memset(&endpoint, 0, sizeof(endpoint));
    endpoint.sin_family = AF_INET; endpoint.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (reservation < 0 || bind(reservation, (struct sockaddr *)&endpoint, sizeof(endpoint)))
        io_fail("private modem endpoint");
    socklen_t size = sizeof(endpoint);
    if (getsockname(reservation, (struct sockaddr *)&endpoint, &size)) io_fail("private modem port");
    char serial[40], callers[96], internal_port[16];
    snprintf(internal_port, sizeof(internal_port), "%u", ntohs(endpoint.sin_port));
    snprintf(serial, sizeof(serial), "127.0.0.1:%s", internal_port);
    snprintf(callers, sizeof(callers), "%s:%s", address, port);
    if (access("runtime/tcpser", X_OK)) fail("Bundled runtime/tcpser is missing or not executable");
    close(reservation);
    struct sigaction action, oldterm, oldint, oldhup;
    memset(&action, 0, sizeof(action)); action.sa_handler = modem_signal;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTERM, &action, &oldterm) || sigaction(SIGINT, &action, &oldint) ||
        sigaction(SIGHUP, &action, &oldhup)) io_fail("launcher signals");
    fflush(NULL);
    pid_t modem = fork();
    if (modem < 0) io_fail("start modem");
    if (!modem) {
        close(lease);
        signal(SIGTERM, SIG_DFL); signal(SIGINT, SIG_DFL); signal(SIGHUP, SIG_DFL);
        int log = open("state/tcpser.log", O_WRONLY|O_CREAT|O_TRUNC, 0600);
        int input = open("/dev/null", O_RDONLY);
        if (log < 0 || input < 0 || dup2(input, 0) < 0 || dup2(log, 1) < 0 || dup2(log, 2) < 0) _exit(126);
        close(log); close(input);
        execl("runtime/tcpser", "tcpser", "-v", serial, "-p", callers,
              "-s", "2400", "-S", "2400", "-i", "e0v1&c1&d2", "-l", "0", (char *)NULL);
        _exit(127);
    }
    if (setenv("RCPM_MODEM_HOST", "127.0.0.1", 1) || setenv("RCPM_MODEM_PORT", internal_port, 1)) {
        kill(modem, SIGTERM); waitpid(modem, NULL, 0); io_fail("modem environment");
    }
    printf("RCP/M virtual modem caller address: %s:%s\n", address, port); fflush(NULL);
    pid_t child = fork();
    if (child < 0) { kill(modem, SIGTERM); waitpid(modem, NULL, 0); io_fail("start CP/M"); }
    if (!child) {
        sigaction(SIGTERM, &oldterm, NULL); sigaction(SIGINT, &oldint, NULL); sigaction(SIGHUP, &oldhup, NULL);
        execv(guest[0], guest); _exit(127);
    }
    int status = 0, modem_dead = 0;
    const struct timespec pause = {0, 100000000};
    for (;;) {
        pid_t result = waitpid(child, &status, WNOHANG);
        if (result == child) break;
        if (result < 0 && errno != EINTR) io_fail("wait for CP/M");
        if (modem_stop_signal) { kill(child, modem_stop_signal); modem_stop_signal = 0; }
        if (!modem_dead && waitpid(modem, NULL, WNOHANG) == modem) {
            modem_dead = 1;
            fprintf(stderr, "RCP/M: virtual modem exited; stopping CP/M. See state/tcpser.log.\n");
            kill(child, SIGTERM);
        }
        nanosleep(&pause, NULL);
    }
    if (!modem_dead) {
        kill(modem, SIGTERM);
        while (waitpid(modem, NULL, 0) < 0 && errno == EINTR) {}
    }
    return !modem_dead && WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
