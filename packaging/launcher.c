/* Native POSIX release launcher. No Python, tmux, or installed CP/M tools.
 * Run only against an unpacked, writable RCP/M package. */
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

static void fail(const char *message) { fprintf(stderr, "RCP/M: %s\n", message); exit(1); }
static void io_fail(const char *message) { fprintf(stderr, "RCP/M: %s: %s\n", message, strerror(errno)); exit(1); }
static void write_all(int fd, const void *data, size_t size) {
    const unsigned char *bytes = data;
    while (size) { ssize_t n = write(fd, bytes, size); if (n < 0 && errno == EINTR) continue;
        if (n <= 0) io_fail("write"); bytes += n; size -= (size_t)n; }
}
static void copy(const char *source, const char *target) {
    unsigned char buffer[16384]; ssize_t n;
    int in = open(source, O_RDONLY), out;
    if (in < 0) io_fail(source);
    out = open(target, O_WRONLY|O_CREAT|O_TRUNC, 0600); if (out < 0) io_fail(target);
    while ((n = read(in, buffer, sizeof(buffer))) > 0) write_all(out, buffer, (size_t)n);
    if (n < 0 || fsync(out) < 0) io_fail("copy");
    close(in); close(out);
}
static void run(char *const argv[]) {
    fflush(NULL);
    pid_t child = fork(); int status;
    if (child < 0) io_fail("fork");
    if (child == 0) { execv(argv[0], argv); perror(argv[0]); _exit(127); }
    while (waitpid(child, &status, 0) < 0) if (errno != EINTR) io_fail("waitpid");
    if (!WIFEXITED(status) || WEXITSTATUS(status)) fail("Bundled disk tool failed; guest was not started.");
}
static void atomic_text(const char *path, const char *text) {
    char temporary[PATH_MAX];
    if (snprintf(temporary, sizeof(temporary), "%s.new", path) >= (int)sizeof(temporary)) fail("Path too long");
    int fd = open(temporary, O_WRONLY|O_CREAT|O_TRUNC, 0600);
    if (fd < 0) io_fail(temporary);
    if (fchmod(fd, 0600)) io_fail("permissions");
    write_all(fd, text, strlen(text)); if (fsync(fd)) io_fail("sync"); close(fd);
    if (rename(temporary, path)) io_fail(path);
}
static void password(char result[25], char prefix) {
    unsigned char bytes[12]; size_t got = 0; const char *hex = "0123456789ABCDEF";
    int fd = open("/dev/urandom", O_RDONLY); if (fd < 0) io_fail("random source");
    while (got < sizeof(bytes)) { ssize_t n = read(fd, bytes + got, sizeof(bytes) - got);
        if (n < 0 && errno == EINTR) continue; if (n <= 0) io_fail("random source"); got += (size_t)n; }
    close(fd);
    for (size_t k = 0; k < sizeof(bytes); k++) { result[k*2] = hex[bytes[k]>>4]; result[k*2+1] = hex[bytes[k]&15]; }
    result[0] = prefix; result[24] = 0;
}
static void initialize(void) {
    struct stat st;
    if (!stat("state/initialized", &st)) {
        if (stat("SYSOP.DOC", &st)) fail("SYSOP.DOC is missing; restore it from your backup.");
        return;
    }
    if (errno != ENOENT) io_fail("state/initialized");
    char direct[25], sysop[25], validation[25], contents[128], doc[1800];
    unsigned char directory[32768], record[128]; int found = 0; unsigned block = 0;
    password(direct, 'D'); password(sysop, 'S'); password(validation, 'V');
    snprintf(contents, sizeof(contents), "%s,%s,NOPASS,CPM,%s,N\r\n10,24,1,0,0,1,1,0\r\n\032", direct, sysop, validation);
    memset(record, 0x1a, sizeof(record)); memcpy(record, contents, strlen(contents));
    copy("disks/drivei.dsk", "state/drivei.new.dsk");
    int fd = open("state/drivei.new.dsk", O_RDWR); if (fd < 0) io_fail("I: initialization");
    if (read(fd, directory, sizeof(directory)) != sizeof(directory)) fail("Unexpected I: geometry");
    for (size_t k = 0; k < sizeof(directory); k += 32) {
        if (directory[k] == 15 && !memcmp(directory+k+1, "pwds       ", 11)) {
            if (directory[k+12] || directory[k+14] || directory[k+15] != 1) fail("Unexpected RBBS password extent");
            block = directory[k+16] | ((unsigned)directory[k+17] << 8); found++;
        }
    }
    if (found != 1 || block < 16 || block >= 2040) fail("Cannot locate fresh RBBS password record");
    if (lseek(fd, (off_t)block * 2048, SEEK_SET) < 0) io_fail("I: password seek");
    write_all(fd, record, sizeof(record)); if (fsync(fd)) io_fail("I: sync"); close(fd);
    snprintf(doc, sizeof(doc),
        "PRIVATE RCP/M SYSOP INFORMATION\n\nGenerated for this installation on first start. Keep this file private.\n\n"
        "RBBS sysop password: %s\nRBBS validation password: %s\nRBBS direct-CP/M password: %s\n\n"
        "Use the local console. With a caller connected, Ctrl-B blanks the caller\n"
        "and enables private sysop operation. Enter RBBS, then enter SYSOP at\n"
        "FIRST Name and the sysop password at LAST Name. Type slowly rather than\n"
        "pasting a burst. At SYSOP? Your Command, P validates a member: supply\n"
        "their first/last names and the validation password when requested.\n"
        "Leave RBBS with J before unblanking the caller.\n\n"
        "Do not delete state/initialized to reset passwords. Back up this whole\n"
        "directory while stopped, including SYSOP.DOC, state/ and disks/.\n",
        sysop, validation, direct);
    atomic_text("SYSOP.DOC", doc);
    if (rename("state/drivei.new.dsk", "disks/drivei.dsk")) io_fail("install initialized I:");
    atomic_text("state/initialized", "RCP/M initialized\n");
    puts("Fresh RBBS passwords have been saved in private SYSOP.DOC.");
}
static void mount_disk(void) {
    struct stat st;
    if (!stat("disks/drivej.dsk", &st)) return;
    if (errno != ENOENT) io_fail("J: mount disk");
    unsigned char directory[32768]; memset(directory, 0xe5, sizeof(directory));
    int fd = open("state/drivej.new.dsk", O_WRONLY|O_CREAT|O_TRUNC, 0600);
    if (fd < 0) io_fail("create J:");
    write_all(fd, directory, sizeof(directory));
    if (ftruncate(fd, 255L*128*128) || fsync(fd) || fchmod(fd, 0600)) io_fail("initialize J:");
    close(fd);
    if (rename("state/drivej.new.dsk", "disks/drivej.dsk")) io_fail("install J:");
}
static void driver(const char *mode) {
    char filename[100];
    snprintf(filename, sizeof(filename), "drivers/%s/BYEDRIV.COM", mode);
    /* Always stage the boot image: failures leave the installed A: intact. */
    copy("disks/drivea.dsk", "state/drivea.new.dsk");
    char *remove[] = {"runtime/cpmrm", "-f", "ibm-3740", "state/drivea.new.dsk", "0:BYEDRIV.COM", NULL};
    char *install[] = {"runtime/cpmcp", "-f", "ibm-3740", "state/drivea.new.dsk", filename, "0:BYEDRIV.COM", NULL};
    char *hide[] = {"runtime/cpmchattr", "-f", "ibm-3740", "state/drivea.new.dsk", "s", "0:BYEDRIV.COM", NULL};
    run(remove); run(install); run(hide);
    int fd = open("state/drivea.new.dsk", O_RDWR); if (fd < 0 || fsync(fd)) io_fail("A: sync"); close(fd);
    if (rename("state/drivea.new.dsk", "disks/drivea.dsk")) io_fail("install selected BYE driver");
}
static void location(const char *argv0) {
    char executable[PATH_MAX], resolved[PATH_MAX];
#ifdef __APPLE__
    uint32_t size = sizeof(executable);
    (void)argv0;
    if (_NSGetExecutablePath(executable, &size)) fail("Executable path too long");
#else
    ssize_t size = readlink("/proc/self/exe", executable, sizeof(executable)-1);
    if (size < 0) { if (strlen(argv0) >= sizeof(executable)) fail("Executable path too long"); strcpy(executable, argv0); }
    else executable[size] = 0;
#endif
    if (!realpath(executable, resolved)) io_fail("launcher path");
    char *last = strrchr(resolved, '/'); if (!last) fail("launcher path"); *last = 0;
    last = strrchr(resolved, '/'); if (!last) fail("package path"); *last = 0;
    if (chdir(resolved)) io_fail("package directory");
    char definitions[PATH_MAX];
    if (snprintf(definitions, sizeof(definitions), "%s/runtime/diskdefs", resolved) >= (int)sizeof(definitions)) fail("Package path too long");
    if (setenv("DISKDEFS", definitions, 1)) io_fail("DISKDEFS");
}
/* F4 is an operator approval marker, read from the actual directory by BYE.
 * Only protected A:/P:/catalog J: sources are eligible, never caller WORK. */
static void caller_files(const char *operation, const char *argument) {
    char target[80], image[100], pattern[20], prefix[9], *colon, *name = NULL, *end;
    unsigned long user = 0; const char *format; struct stat st;
    int listing = !strcmp(operation, "--caller-list");
    if (strlen(argument) >= sizeof(target)) fail("Caller target too long");
    strcpy(target, argument);
    for (char *p = target; *p; p++) *p = (char)toupper((unsigned char)*p);
    colon = strchr(target, ':');
    if (!listing) {
        if (!colon) fail("Use IMAGE:USER:FILE.COM, for example GAMES:1:ADV.COM");
        *colon++ = 0; errno = 0; user = strtoul(colon, &end, 10);
        if (errno || end == colon || *end != ':' || user > 15) fail("User must be 0-15");
        name = end + 1;
        char *dot = strchr(name, '.');
        if (!dot || dot == name || dot-name > 8 || strcmp(dot, ".COM")) fail("Expected an exact 8.3 COM filename");
        for (char *p = name; p < dot; p++)
            if (!isalnum((unsigned char)*p) && !strchr("_!#$%&'()-@^{}~", *p)) fail("Invalid COM filename");
        snprintf(pattern, sizeof(pattern), "%lu:%s", user, name);
    }
    if (!*target || strlen(target) > 8) fail("Invalid image name");
    for (char *p = target; *p; p++) if (!isalnum((unsigned char)*p) && *p != '_') fail("Invalid image name");
    strcpy(prefix, target);
    if (!strcmp(prefix, "A")) { strcpy(image, "disks/drivea.dsk"); format = "ibm-3740"; }
    else if (!strcmp(prefix, "P")) { strcpy(image, "disks/drivep.dsk"); format = "z80pack-hdb"; }
    else {
        if (strlen(prefix) == 1) fail("Use A, P or a catalog image name such as GAMES; WORK is not executable");
        snprintf(image, sizeof(image), "volumes/%s.dsk", prefix); format = "z80pack-hd";
    }
    if (lstat(image, &st) || !S_ISREG(st.st_mode)) fail("Expected an owned regular disk image");
    int lease = open(".console.lock", O_RDWR|O_CREAT, 0600); if (lease < 0) io_fail("instance lock");
    if (flock(lease, LOCK_EX|LOCK_NB)) fail("Stop RCP/M before listing or changing caller approvals");
    if (!listing) {
        copy(image, "state/caller-image.new.dsk");
        unlink("state/caller-check.COM");
        char *exists[] = {"runtime/cpmcp", "-f", (char *)format, "state/caller-image.new.dsk", pattern, "state/caller-check.COM", NULL};
        run(exists);
        struct stat program;
        if (lstat("state/caller-check.COM", &program) || !S_ISREG(program.st_mode) || program.st_size == 0)
            fail("The exact COM file does not exist or is empty; image was not changed");
        unlink("state/caller-check.COM");
        char *attributes[] = {"runtime/cpmchattr", "-f", (char *)format, "state/caller-image.new.dsk",
                              !strcmp(operation, "--caller-allow") ? "4" : "m4", pattern, NULL};
        run(attributes);
        copy(image, "state/caller-image.previous.dsk");
        char note[300]; snprintf(note, sizeof(note), "Last caller-approval change: %s %s\nRestore state/caller-image.previous.dsk to %s while stopped to roll back.\n", operation, argument, image);
        atomic_text("state/CALLER-CHANGE.DOC", note);
        int fd = open("state/caller-image.new.dsk", O_RDWR);
        if (fd < 0 || fsync(fd) || fchmod(fd, st.st_mode & 0777)) io_fail("approval sync");
        close(fd);
        if (rename("state/caller-image.new.dsk", image)) io_fail("install caller approval");
        printf("%s %s. Run AUTH inside private CP/M for live administration.\n",
               !strcmp(operation, "--caller-allow") ? "Approved" : "Revoked additional approval for", argument);
    }
    puts("Approval requires F4, caller read access and no caller write access; other flags are unchanged.\n"
         "F4 appears in column 4 below.");
    char *show[] = {"runtime/cpmls", "-A", "-f", (char *)format, image, NULL}; run(show);
    close(lease);
}
int main(int argc, char **argv) {
    char mode[16] = "direct", address[64] = "127.0.0.1", port[16] = "4000", line[256];
    int check = 0; struct in_addr ip; char *end; long number;
    location(argv[0]);
    if (argc == 3 && (!strcmp(argv[1], "--caller-allow") || !strcmp(argv[1], "--caller-deny") || !strcmp(argv[1], "--caller-list"))) {
        umask(077); caller_files(argv[1], argv[2]); return 0;
    }
    FILE *config = fopen("RCPM.CONF", "r"); if (!config) io_fail("RCPM.CONF");
    while (fgets(line, sizeof(line), config)) {
        char key[32], value[96], extra;
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        if (sscanf(line, "%31[^=]=%95s %c", key, value, &extra) != 2) fail("Invalid RCPM.CONF line");
        if (!strcmp(key, "MODE") && strlen(value) < sizeof(mode)) strcpy(mode, value);
        else if (!strcmp(key, "ADDRESS") && strlen(value) < sizeof(address)) strcpy(address, value);
        else if (!strcmp(key, "PORT") && strlen(value) < sizeof(port)) strcpy(port, value);
        else fail("Unknown or invalid RCPM.CONF setting");
    }
    if (ferror(config)) io_fail("Read RCPM.CONF"); fclose(config);
    for (int k = 1; k < argc; k++) {
        if (!strcmp(argv[k], "--check")) { check = 1; continue; }
        if (!strcmp(argv[k], "--help")) {
            puts("RCP/M [--mode direct|ip232] [--address IPv4] [--port NUMBER] [--check]\n"
                 "RCP/M --caller-allow IMAGE:USER:FILE.COM\nRCP/M --caller-deny IMAGE:USER:FILE.COM\nRCP/M --caller-list IMAGE\n"
                 "IMAGE is A, P, or a catalog name such as GAMES. Stop the guest first.\nDefaults come from RCPM.CONF. See SYSOP-GUIDE.DOC."); return 0;
        }
        if (k+1 >= argc) fail("Missing option value; use --help");
        if (!strcmp(argv[k], "--mode") && strlen(argv[k+1]) < sizeof(mode)) strcpy(mode, argv[k+1]);
        else if (!strcmp(argv[k], "--address") && strlen(argv[k+1]) < sizeof(address)) strcpy(address, argv[k+1]);
        else if (!strcmp(argv[k], "--port") && strlen(argv[k+1]) < sizeof(port)) strcpy(port, argv[k+1]);
        else fail("Unknown option; use --help"); k++;
    }
    errno = 0; number = strtol(port, &end, 10);
    if (errno || !*port || *end || number < 1 || number > 65535 || inet_pton(AF_INET, address, &ip) != 1) fail("Invalid IPv4 address or port");
    if (strcmp(mode, "direct") && strcmp(mode, "ip232")) fail("MODE must be direct or ip232");
    if (check) { printf("RCP/M configuration: %s %s:%s\n", mode, address, port); return 0; }
    if (!isatty(0) || !isatty(1)) fail("Start RCP/M in an interactive terminal");
    umask(077);
    int lease = open(".console.lock", O_RDWR|O_CREAT, 0600); if (lease < 0) io_fail("instance lock");
    if (flock(lease, LOCK_EX|LOCK_NB)) fail("This installation is already running. Use its current console.");
    /* The lock deliberately survives exec into cpmsim. */
    initialize(); mount_disk(); driver(mode);
    if (setenv("RCPM_MODEM", mode, 1) || setenv("RCPM_MODEM_HOST", address, 1) ||
        setenv("RCPM_MODEM_PORT", port, 1) || setenv("RCPM_ANNOUNCE", "1", 1)) io_fail("runtime environment");
    fflush(NULL);
    char *guest[] = {"runtime/cpmsim", "-f", "4", NULL}; execv(guest[0], guest); io_fail("cpmsim");
}
