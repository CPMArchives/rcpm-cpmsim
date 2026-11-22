/* RCP/M J:/P: mount port 60. Fixed geometry, no guest-supplied host paths.
 * FF/FE retain legacy J: start/list. FD/FC are P: start/list; FB probes
 * capabilities (A2); F9/FA restore the J:/P: startup image. */
static char volume_name[9], mounted_volume[2][10];
static size_t volume_length, catalog_offset;
static BYTE mount_status = 1;
static int invalid_volume_name, listing, mount_slot;
static DIR *catalog_dir;
static char catalog_line[40];

static int volume_character(BYTE c)
{
    return (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_';
}
static int mount_drive(void) { return mount_slot ? 15 : 9; }
static const char *mount_folder(void) { return mount_slot ? "archives" : "volumes"; }
static void close_catalog(void)
{
    if (catalog_dir) closedir(catalog_dir);
    catalog_dir = NULL;
}
static int open_volume(const char *name, int original)
{
    char path[256];
    struct stat st;
    int fd;
    off_t expected = mount_slot ? (off_t)536870912 : (off_t)4177920;
    if (original) snprintf(path, sizeof(path), "disks/%s", disks[mount_drive()].fn);
    else snprintf(path, sizeof(path), "%s/%s.dsk", mount_folder(), name);
    fd = open(path, O_RDWR | O_NONBLOCK);
    if (fd < 0) fd = open(path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) { mount_status = 2; return -1; }
    if (fstat(fd, &st) || !S_ISREG(st.st_mode)) {
        close(fd); mount_status = 2; return -1;
    }
    if (st.st_size != expected) { close(fd); mount_status = 3; return -1; }
    return fd;
}
static void adopt_volume(int original)
{
    int replacement, drive = mount_drive();
    mount_status = 2;
    if (!disks[drive].fd) return;
    replacement = open_volume(volume_name, original);
    if (replacement < 0) return;
    close(*disks[drive].fd);
    *disks[drive].fd = replacement;
    strcpy(mounted_volume[mount_slot], original ? "<default>" : volume_name);
    mount_status = 0;
}
static BYTE mount_in(void)
{
    struct dirent *entry;
    char name[9];
    size_t i, length;
    int fd;
    if (!listing) return mount_status;
    if (catalog_line[catalog_offset]) return (BYTE)catalog_line[catalog_offset++];
    while (catalog_dir && (entry = readdir(catalog_dir)) != NULL) {
        length = strlen(entry->d_name);
        if (length < 5 || length > 12 || strcmp(entry->d_name + length - 4, ".dsk")) continue;
        length -= 4;
        for (i = 0; i < length && volume_character((BYTE)entry->d_name[i]); ++i) name[i] = entry->d_name[i];
        if (i != length) continue;
        name[i] = 0;
        fd = open_volume(name, 0);
        if (fd < 0) continue;
        close(fd);
        snprintf(catalog_line, sizeof(catalog_line), "  %s\r\n", name);
        catalog_offset = 1;
        return (BYTE)catalog_line[0];
    }
    close_catalog(); listing = 0;
    return 0;
}
static void mount_out(BYTE data)
{
    if (data >= 0xf9) {
        close_catalog(); listing = 0;
        if (data == 0xfb) { mount_status = 0xa2; return; }
        mount_slot = (data == 0xfd || data == 0xfc || data == 0xfa);
        if (data == 0xfe || data == 0xfc) {
            catalog_dir = opendir(mount_folder());
            snprintf(catalog_line, sizeof(catalog_line), "%c: %s\r\nVolumes:\r\n",
                     mount_slot ? 'P' : 'J', mounted_volume[mount_slot][0] ? mounted_volume[mount_slot] : "<default>");
            catalog_offset = 0; listing = 1; return;
        }
        if (data == 0xf9 || data == 0xfa) { adopt_volume(1); return; }
        volume_length = 0; invalid_volume_name = 0; mount_status = 1;
        return;
    }
    if (data) {
        if (volume_length >= 8 || !volume_character(data)) invalid_volume_name = 1;
        else volume_name[volume_length++] = (char)data;
        return;
    }
    if (invalid_volume_name || !volume_length) { mount_status = 1; return; }
    volume_name[volume_length] = 0;
    adopt_volume(0);
}
