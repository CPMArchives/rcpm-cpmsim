/* Native qualification probes. A successful compile is not a test pass. */
#define RCPM_WINDOWS_HOST_IMPLEMENTATION
#include "host.h"
#include "launcher_host.h"
static void fail(const char *message) { fprintf(stderr, "PROBE FAILED: %s\n", message); exit(1); }
static void io_fail(const char *message) { fail(message); }
#define CHECK(value) do { if (!(value)) fail(#value); } while (0)

static void private_file(const char *name) {
    wchar_t *path = win_wide(name);
    PACL acl = NULL; PSECURITY_DESCRIPTOR descriptor = NULL;
    CHECK(GetNamedSecurityInfoW(path, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
                                NULL, NULL, &acl, NULL, &descriptor) == ERROR_SUCCESS);
    SECURITY_DESCRIPTOR_CONTROL control; DWORD revision;
    CHECK(GetSecurityDescriptorControl(descriptor, &control, &revision));
    CHECK(control & SE_DACL_PROTECTED);
    CHECK(acl && acl->AceCount == 1);
    ACCESS_ALLOWED_ACE *ace;
    CHECK(GetAce(acl, 0, (void **)&ace));
    CHECK(ace->Header.AceType == ACCESS_ALLOWED_ACE_TYPE);
    HANDLE token; DWORD size = 0;
    CHECK(OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token));
    GetTokenInformation(token, TokenUser, NULL, 0, &size);
    TOKEN_USER *user = malloc(size);
    CHECK(user && GetTokenInformation(token, TokenUser, user, size, &size));
    CHECK(EqualSid(user->User.Sid, &ace->SidStart));
    free(user); CloseHandle(token); LocalFree(descriptor); free(path);
}
static unsigned alarms;
static void timer_alarm(int sig) { CHECK(sig == SIGALRM); alarms++; }
static void test_host(void) {
    unsigned char body[] = {0, 13, 10, 26, 128, 255}, readback[sizeof(body)];
    int file = win_open("binary-probe", O_RDWR | O_CREAT | O_TRUNC, 0600);
    CHECK(file >= 0 && win_permissions(file, 0600) == 0);
    CHECK(rcpm_write(file, body, sizeof(body)) == sizeof(body));
    CHECK(_lseek(file, 0, SEEK_SET) == 0);
    CHECK(rcpm_read(file, readback, sizeof(readback)) == sizeof(readback));
    CHECK(!memcmp(body, readback, sizeof(body)));
    _close(file); private_file("binary-probe");
    CHECK(rcpm_link("binary-probe", "published-probe") == 0);
    CHECK(rcpm_link("binary-probe", "published-probe") != 0);
    CHECK(_unlink("published-probe") == 0 && _unlink("binary-probe") == 0);
    uint64_t first = rcpm_monotonic_us(); Sleep(5);
    CHECK(rcpm_monotonic_us() > first);
    struct rcpm_sigaction action = {timer_alarm, 0, 0};
    CHECK(rcpm_sigaction(SIGALRM, &action, NULL) == 0);
    struct itimerval interval = {{0, 10000}, {0, 10000}};
    CHECK(rcpm_setitimer(ITIMER_REAL, &interval, NULL) == 0);
    Sleep(30); (void)rcpm_monotonic_us(); CHECK(alarms == 1);
    interval.it_value.tv_usec = 0;
    CHECK(rcpm_setitimer(ITIMER_REAL, &interval, NULL) == 0);
    Sleep(20); (void)rcpm_monotonic_us(); CHECK(alarms == 1);
    int server = rcpm_socket(AF_INET, SOCK_STREAM, 0);
    CHECK(server >= 0);
    int one = 1;
    CHECK(rcpm_setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)) == 0);
    struct sockaddr_in address; memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET; address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    CHECK(rcpm_bind(server, (struct sockaddr *)&address, sizeof(address)) == 0);
    socklen_t size = sizeof(address);
    CHECK(rcpm_getsockname(server, (struct sockaddr *)&address, &size) == 0);
    CHECK(rcpm_listen(server, 4) == 0);
    int duplicate = rcpm_socket(AF_INET, SOCK_STREAM, 0);
    CHECK(duplicate >= 0);
    CHECK(rcpm_setsockopt(duplicate, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)) == 0);
    CHECK(rcpm_bind(duplicate, (struct sockaddr *)&address, sizeof(address)) != 0);
    CHECK(rcpm_close(duplicate) == 0);
    int caller = rcpm_socket(AF_INET, SOCK_STREAM, 0);
    CHECK(caller >= 0 && rcpm_fcntl(caller, F_SETFL, O_NONBLOCK) == 0);
    int connected = rcpm_connect(caller, (struct sockaddr *)&address, sizeof(address));
    CHECK(connected == 0 || errno == EINPROGRESS);
    struct pollfd ready = {(SOCKET)caller, POLLOUT, 0};
    CHECK(rcpm_poll(&ready, 1, 5000) == 1 && (ready.revents & POLLOUT));
    int error = -1; size = sizeof(error);
    CHECK(rcpm_getsockopt(caller, SOL_SOCKET, SO_ERROR, &error, &size) == 0 && error == 0);
    int peer = rcpm_accept(server, NULL, NULL); CHECK(peer >= 0);
    CHECK(rcpm_write(caller, body, sizeof(body)) == sizeof(body));
    ready.fd = (SOCKET)peer; ready.events = POLLIN;
    CHECK(rcpm_poll(&ready, 1, 5000) == 1 && (ready.revents & POLLIN));
    size_t received = 0;
    while (received < sizeof(readback)) {
        CHECK(rcpm_poll(&ready, 1, 5000) == 1 && (ready.revents & POLLIN));
        ssize_t n = rcpm_read(peer, readback + received, sizeof(readback) - received);
        CHECK(n > 0); received += (size_t)n;
    }
    CHECK(!memcmp(body, readback, sizeof(body)));
    CHECK(rcpm_close(peer) == 0 && rcpm_close(caller) == 0 && rcpm_close(server) == 0);
}
struct close_after_ready { int fd; HANDLE ready, go; };
static DWORD WINAPI release_parent_lease(void *argument) {
    struct close_after_ready *context = argument;
    CHECK(WaitForSingleObject(context->ready, 10000) == WAIT_OBJECT_0);
    CHECK(_close(context->fd) == 0);
    CHECK(SetEvent(context->go));
    return 0;
}
static void test_lease(const char *program) {
    int fd = win_open(".console.lock", O_RDWR | O_CREAT, 0600); CHECK(fd >= 0);
    CHECK(win_open(".console.lock", O_RDWR | O_CREAT, 0600) < 0);
    SECURITY_ATTRIBUTES attributes = {sizeof(attributes), NULL, TRUE};
    HANDLE ready = CreateEventW(&attributes, TRUE, FALSE, NULL);
    HANDLE go = CreateEventW(&attributes, TRUE, FALSE, NULL);
    CHECK(ready && go);
    struct close_after_ready context = {fd, ready, go};
    HANDLE thread = CreateThread(NULL, 0, release_parent_lease, &context, 0, NULL);
    CHECK(thread);
    char lease_arg[40], ready_arg[40], go_arg[40];
    snprintf(lease_arg, sizeof(lease_arg), "%llu", (unsigned long long)_get_osfhandle(fd));
    snprintf(ready_arg, sizeof(ready_arg), "%llu", (unsigned long long)(uintptr_t)ready);
    snprintf(go_arg, sizeof(go_arg), "%llu", (unsigned long long)(uintptr_t)go);
    char *command[] = {(char *)program, "--lease-child", lease_arg, ready_arg, go_arg, NULL};
    CHECK(win_process(command, 0) == 0);
    CHECK(WaitForSingleObject(thread, 10000) == WAIT_OBJECT_0);
    CloseHandle(thread); CloseHandle(ready); CloseHandle(go);
    CHECK(_unlink(".console.lock") == 0);
}
int main(int argc, char **argv) {
    if (argc == 3 && !strcmp(argv[1], "--private")) {
        private_file(argv[2]); puts("PRIVATE-ACL-PASS"); return 0;
    }
    if (argc == 5 && !strcmp(argv[1], "--lease-child")) {
        HANDLE lease = (HANDLE)(uintptr_t)strtoull(argv[2], NULL, 10);
        HANDLE ready = (HANDLE)(uintptr_t)strtoull(argv[3], NULL, 10);
        HANDLE go = (HANDLE)(uintptr_t)strtoull(argv[4], NULL, 10);
        CHECK(SetEvent(ready)); CHECK(WaitForSingleObject(go, 10000) == WAIT_OBJECT_0);
        BY_HANDLE_FILE_INFORMATION info; CHECK(GetFileInformationByHandle(lease, &info));
        CHECK(win_open(".console.lock", O_RDWR | O_CREAT, 0600) < 0);
        CHECK(CloseHandle(lease));
        int fd = win_open(".console.lock", O_RDWR | O_CREAT, 0600); CHECK(fd >= 0);
        CHECK(_close(fd) == 0); return 0;
    }
    wchar_t program_wide[32768]; char program[32768];
    CHECK(GetModuleFileNameW(NULL, program_wide, 32768));
    win_utf8(program_wide, program, sizeof(program));
    test_host(); test_lease(program);
    puts("HOST-PROBES-PASS: binary I/O, private ACL, atomic no-replace publication, clock, timer, sockets, exclusive endpoint, inherited lease");
    return 0;
}
