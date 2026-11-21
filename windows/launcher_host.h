/* Windows implementations used by the shared release launcher source. */
#ifndef RCPM_WINDOWS_LAUNCHER_HOST_H
#define RCPM_WINDOWS_LAUNCHER_HOST_H
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <aclapi.h>
#include <bcrypt.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <io.h>
#include <limits.h>
#include <process.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#ifdef PATH_MAX
#undef PATH_MAX
#endif
#define PATH_MAX 32768
#define LOCK_EX 1
#define LOCK_NB 2
static void fail(const char *);
static void io_fail(const char *);

static wchar_t *win_wide(const char *text) {
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text, -1, NULL, 0);
    if (!count) fail("Invalid UTF-8 path");
    wchar_t *result = malloc((size_t)count * sizeof(*result));
    if (!result) fail("Out of memory");
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text, -1, result, count)) fail("Path conversion failed");
    return result;
}
static void win_utf8(const wchar_t *text, char *result, size_t capacity) {
    if (!WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, text, -1, result, (int)capacity, NULL, NULL))
        fail("Package path too long");
}
static PACL private_acl;
static SECURITY_DESCRIPTOR private_descriptor;
static SECURITY_ATTRIBUTES *win_private_security(int inherit) {
    static SECURITY_ATTRIBUTES attributes;
    if (!private_acl) {
        HANDLE token;
        DWORD size = 0;
        if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) fail("Cannot read account identity");
        GetTokenInformation(token, TokenUser, NULL, 0, &size);
        TOKEN_USER *user = malloc(size);
        if (!user || !GetTokenInformation(token, TokenUser, user, size, &size)) fail("Cannot read account SID");
        CloseHandle(token);
        EXPLICIT_ACCESSW entry;
        memset(&entry, 0, sizeof(entry));
        entry.grfAccessPermissions = GENERIC_ALL;
        entry.grfAccessMode = SET_ACCESS;
        entry.grfInheritance = SUB_CONTAINERS_AND_OBJECTS_INHERIT;
        entry.Trustee.TrusteeForm = TRUSTEE_IS_SID;
        entry.Trustee.TrusteeType = TRUSTEE_IS_USER;
        entry.Trustee.ptstrName = (LPWSTR)user->User.Sid;
        if (SetEntriesInAclW(1, &entry, NULL, &private_acl) != ERROR_SUCCESS ||
            !InitializeSecurityDescriptor(&private_descriptor, SECURITY_DESCRIPTOR_REVISION) ||
            !SetSecurityDescriptorDacl(&private_descriptor, TRUE, private_acl, FALSE) ||
            !SetSecurityDescriptorControl(&private_descriptor, SE_DACL_PROTECTED, SE_DACL_PROTECTED))
            fail("Cannot establish private file permissions");
        free(user);
    }
    attributes.nLength = sizeof(attributes);
    attributes.lpSecurityDescriptor = &private_descriptor;
    attributes.bInheritHandle = inherit;
    return &attributes;
}
static int win_permissions(int fd, int mode) {
    (void)mode;
    win_private_security(0);
    DWORD error = SetSecurityInfo((HANDLE)_get_osfhandle(fd), SE_FILE_OBJECT,
                DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
                NULL, NULL, private_acl, NULL);
    if (error != ERROR_SUCCESS) { SetLastError(error); errno = EACCES; return -1; }
    return 0;
}
static void win_private_directory(const char *name) {
    wchar_t *path = win_wide(name);
    DWORD flags = GetFileAttributesW(path);
    if (flags == INVALID_FILE_ATTRIBUTES || !(flags & FILE_ATTRIBUTE_DIRECTORY) ||
        (flags & FILE_ATTRIBUTE_REPARSE_POINT)) fail("Expected an owned package directory");
    win_private_security(0);
    DWORD error = SetNamedSecurityInfoW(path, SE_FILE_OBJECT,
        DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
        NULL, NULL, private_acl, NULL);
    free(path);
    if (error != ERROR_SUCCESS) fail("Filesystem must support private Windows ACLs");
}
static int win_open(const char *name, int flags, ...) {
    int lease = !strcmp(name, ".console.lock");
    DWORD access = (flags & O_RDWR) ? GENERIC_READ | GENERIC_WRITE :
                    (flags & O_WRONLY) ? GENERIC_WRITE : GENERIC_READ;
    DWORD creation = (flags & O_CREAT) ? ((flags & O_TRUNC) ? CREATE_ALWAYS : OPEN_ALWAYS) : OPEN_EXISTING;
    wchar_t *path = win_wide(name);
    HANDLE handle = CreateFileW(path, access | FILE_READ_ATTRIBUTES | ((flags & (O_RDWR | O_WRONLY | O_CREAT)) ? WRITE_DAC : 0),
        lease ? 0 : FILE_SHARE_READ, (flags & O_CREAT) ? win_private_security(lease) : NULL,
        creation, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    free(path);
    if (handle == INVALID_HANDLE_VALUE) {
        DWORD error = GetLastError();
        errno = error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND ? ENOENT : EACCES;
        return -1;
    }
    BY_HANDLE_FILE_INFORMATION info;
    if (!GetFileInformationByHandle(handle, &info) || (info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)) {
        CloseHandle(handle); errno = EACCES; return -1;
    }
    int fd = _open_osfhandle((intptr_t)handle, (flags & (O_RDWR | O_WRONLY)) | _O_BINARY |
                            (lease ? 0 : _O_NOINHERIT));
    if (fd < 0) CloseHandle(handle);
    return fd;
}
static int win_rename(const char *source, const char *target) {
    wchar_t *from = win_wide(source), *to = win_wide(target);
    BOOL ok = MoveFileExW(from, to, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH);
    free(from); free(to);
    if (!ok) { errno = EACCES; return -1; }
    return 0;
}
static int win_lstat(const char *name, struct stat *info) {
    wchar_t *path = win_wide(name);
    DWORD flags = GetFileAttributesW(path);
    free(path);
    if (flags != INVALID_FILE_ATTRIBUTES && (flags & FILE_ATTRIBUTE_REPARSE_POINT)) {
        errno = EACCES; return -1;
    }
    return stat(name, info);
}
static int win_ftruncate(int fd, off_t size) {
    return _chsize_s(fd, size) ? -1 : 0;
}
static int win_setenv(const char *key, const char *value, int replace) {
    if (!replace && getenv(key)) return 0;
    return _putenv_s(key, value);
}
/* Quote every argument according to the Microsoft CRT command-line rules. */
static void win_argument(wchar_t *command, size_t *used, const wchar_t *value) {
    size_t slashes = 0;
#define PUT(c) do { if (*used >= 32766) fail("Command line too long"); command[(*used)++] = (c); } while (0)
    if (*used) PUT(L' ');
    PUT(L'"');
    for (; *value; value++) {
        if (*value == L'\\') { slashes++; continue; }
        if (*value == L'"') {
            while (slashes) { PUT(L'\\'); PUT(L'\\'); slashes--; }
            PUT(L'\\'); PUT(L'"');
        } else {
            while (slashes) { PUT(L'\\'); slashes--; }
            PUT(*value);
        }
    }
    while (slashes) { PUT(L'\\'); PUT(L'\\'); slashes--; }
    PUT(L'"'); command[*used] = 0;
#undef PUT
}
static BOOL WINAPI win_parent_control(DWORD event) {
    return event == CTRL_C_EVENT || event == CTRL_BREAK_EVENT;
}
static int win_process(char *const args[], int guest) {
    DWORD old_input = 0, old_output = 0;
    BOOL has_input = GetConsoleMode(GetStdHandle(STD_INPUT_HANDLE), &old_input);
    BOOL has_output = GetConsoleMode(GetStdHandle(STD_OUTPUT_HANDLE), &old_output);
    if (guest) SetConsoleCtrlHandler(win_parent_control, TRUE);
    wchar_t command[32768]; size_t used = 0;
    for (size_t k = 0; args[k]; k++) {
        wchar_t *value = win_wide(args[k]);
        win_argument(command, &used, value); free(value);
    }
    STARTUPINFOW startup; PROCESS_INFORMATION process;
    memset(&startup, 0, sizeof(startup)); startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    HANDLE inherited[3];
    DWORD standard[] = {STD_INPUT_HANDLE, STD_OUTPUT_HANDLE, STD_ERROR_HANDLE};
    for (size_t k = 0; k < 3; k++) {
        if (!DuplicateHandle(GetCurrentProcess(), GetStdHandle(standard[k]),
            GetCurrentProcess(), &inherited[k], 0, TRUE, DUPLICATE_SAME_ACCESS))
            fail("Cannot inherit console handles");
    }
    startup.hStdInput = inherited[0];
    startup.hStdOutput = inherited[1];
    startup.hStdError = inherited[2];
    /* The lease handle is inheritable: exclusive sharing remains enforced even
     * if the launcher exits before its child. A job also prevents orphan guests. */
    HANDLE job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits;
    memset(&limits, 0, sizeof(limits));
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits)))
        fail("Cannot create child process containment");
    wchar_t *application = win_wide(args[0]);
    fflush(NULL);
    BOOL ok = CreateProcessW(application, command, NULL, NULL, TRUE, CREATE_SUSPENDED,
                            NULL, NULL, &startup, &process);
    free(application);
    for (size_t k = 0; k < 3; k++) CloseHandle(inherited[k]);
    if (!ok) { CloseHandle(job); fail("Cannot start bundled executable"); }
    if (!AssignProcessToJobObject(job, process.hProcess)) {
        TerminateProcess(process.hProcess, 1); CloseHandle(process.hThread);
        CloseHandle(process.hProcess); CloseHandle(job); fail("Cannot contain child process");
    }
    if (ResumeThread(process.hThread) == (DWORD)-1) {
        CloseHandle(process.hThread); CloseHandle(process.hProcess); CloseHandle(job);
        fail("Cannot resume bundled executable");
    }
    CloseHandle(process.hThread);
    if (WaitForSingleObject(process.hProcess, INFINITE) != WAIT_OBJECT_0) fail("Child wait failed");
    DWORD code;
    if (!GetExitCodeProcess(process.hProcess, &code)) fail("Cannot read child exit status");
    CloseHandle(process.hProcess); CloseHandle(job);
    if (guest) {
        if (has_input) SetConsoleMode(GetStdHandle(STD_INPUT_HANDLE), old_input);
        if (has_output) SetConsoleMode(GetStdHandle(STD_OUTPUT_HANDLE), old_output);
        SetConsoleCtrlHandler(win_parent_control, FALSE);
    }
    if (!guest && code) fail("Bundled disk tool failed; guest was not started.");
    return code > 255 ? 1 : (int)code;
}
static void run(char *const args[]) { (void)win_process(args, 0); }
static void password(char result[25], char prefix) {
    unsigned char bytes[12];
    const char *hex = "0123456789ABCDEF";
    if (BCryptGenRandom(NULL, bytes, sizeof(bytes), BCRYPT_USE_SYSTEM_PREFERRED_RNG) != 0)
        fail("System randomness unavailable");
    for (size_t k = 0; k < sizeof(bytes); k++) {
        result[k * 2] = hex[bytes[k] >> 4]; result[k * 2 + 1] = hex[bytes[k] & 15];
    }
    result[0] = prefix; result[24] = 0;
    SecureZeroMemory(bytes, sizeof(bytes));
}
static void location(const char *unused) {
    (void)unused;
    wchar_t executable[32768];
    DWORD count = GetModuleFileNameW(NULL, executable, 32768);
    if (!count || count >= 32768) fail("Executable path too long");
    wchar_t *end = wcsrchr(executable, L'\\');
    if (!end) fail("Invalid launcher location");
    *end = 0; end = wcsrchr(executable, L'\\');
    if (!end) fail("Invalid package location");
    *end = 0;
    if (!SetCurrentDirectoryW(executable)) fail("Cannot select package directory");
    char path[PATH_MAX];
    if (wcslen(executable) + 18 >= 32768) fail("Package path too long");
    wcscat(executable, L"\\runtime\\diskdefs");
    win_utf8(executable, path, sizeof(path));
    if (win_setenv("DISKDEFS", path, 1)) fail("Cannot set disk definitions");
}
static int win_flock(int fd, int mode) { (void)mode; return fd >= 0 ? 0 : -1; }
#define open win_open
#define fchmod win_permissions
#define fsync _commit
#define rename win_rename
#define lstat win_lstat
#define ftruncate win_ftruncate
#define setenv win_setenv
#define flock win_flock
#define umask _umask
#endif
