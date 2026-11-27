/* Windows foreground modem ownership; the add-on is not involved. */
static int launch_guest(char *const guest[], int owned_modem,
                        const char *address, const char *port, int lease) {
    (void)lease;
    if (!owned_modem) return win_process(guest, 1);
    WSADATA ws;
    if (WSAStartup(MAKEWORD(2, 2), &ws)) fail("Cannot initialize virtual modem sockets");
    SOCKET reservation = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    struct sockaddr_in endpoint; memset(&endpoint, 0, sizeof(endpoint));
    endpoint.sin_family = AF_INET; endpoint.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    int size = sizeof(endpoint);
    if (reservation == INVALID_SOCKET || bind(reservation, (struct sockaddr *)&endpoint, size) ||
        getsockname(reservation, (struct sockaddr *)&endpoint, &size)) fail("Cannot select private modem port");
    char serial[40], callers[96], internal_port[16];
    snprintf(internal_port, sizeof(internal_port), "%u", ntohs(endpoint.sin_port));
    snprintf(serial, sizeof(serial), "127.0.0.1:%s", internal_port);
    snprintf(callers, sizeof(callers), "%s:%s", address, port);
    closesocket(reservation); WSACleanup();
    char *args[] = {"runtime/tcpser.exe", "-v", serial, "-p", callers, "-s", "2400",
                   "-S", "2400", "-i", "e0v1&c1&d2", "-l", "0", NULL};
    wchar_t command[32768]; size_t used = 0;
    for (size_t k = 0; args[k]; k++) {
        wchar_t *value = win_wide(args[k]); win_argument(command, &used, value); free(value);
    }
    HANDLE job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits; memset(&limits, 0, sizeof(limits));
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits)))
        fail("Cannot contain bundled modem");
    STARTUPINFOW startup; PROCESS_INFORMATION process;
    memset(&startup, 0, sizeof(startup)); startup.cb = sizeof(startup);
    if (!CreateProcessW(L"runtime\\tcpser.exe", command, NULL, NULL, FALSE,
                        CREATE_SUSPENDED | CREATE_NO_WINDOW, NULL, NULL, &startup, &process)) {
        CloseHandle(job); fail("Cannot start bundled runtime/tcpser.exe");
    }
    if (!AssignProcessToJobObject(job, process.hProcess) || ResumeThread(process.hThread) == (DWORD)-1) {
        TerminateProcess(process.hProcess, 1); CloseHandle(process.hThread);
        CloseHandle(process.hProcess); CloseHandle(job); fail("Cannot start contained modem");
    }
    CloseHandle(process.hThread);
    if (WaitForSingleObject(process.hProcess, 100) != WAIT_TIMEOUT) {
        CloseHandle(process.hProcess); CloseHandle(job); fail("Bundled modem exited during startup");
    }
    if (win_setenv("RCPM_MODEM_HOST", "127.0.0.1", 1) ||
        win_setenv("RCPM_MODEM_PORT", internal_port, 1)) {
        CloseHandle(process.hProcess); CloseHandle(job); fail("Cannot configure modem endpoint");
    }
    printf("RCP/M virtual modem caller address: %s:%s\n", address, port); fflush(NULL);
    int code = win_process(guest, 1);
    CloseHandle(process.hProcess); CloseHandle(job);
    return code;
}
