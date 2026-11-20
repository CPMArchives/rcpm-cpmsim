/* Binary transfer transport for the existing upload/YMODEM services.
 * Included after rcpm_modem.c; never send modem protocol bytes to the TTY.
 */
#include <stdint.h>

static int64_t rt_now(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return -1;
    return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int rcpm_transfer_read(BYTE *buffer, size_t size, int timeout)
{
    int64_t start = rt_now(), deadline;
    if (start < 0) return -1;
    deadline = start + timeout;
    while (size) {
        int64_t now = rt_now();
        if (now < 0 || now >= deadline) return -1;
        if (!rm_mode) {
            struct pollfd input = {STDIN_FILENO, POLLIN, 0};
            ssize_t count;
            int64_t remaining = deadline - now;
            if (remaining <= 0 || poll(&input, 1, (int)remaining) != 1 ||
                !(input.revents & POLLIN)) return -1;
            count = read(STDIN_FILENO, buffer, size);
            if (count <= 0) return -1;
            buffer += count;
            size -= (size_t)count;
        } else {
            unsigned char status = rcpm_modem_status();
            if (!(status & 4)) return -1;
            if (status & 1) {
                *buffer++ = rcpm_modem_read();
                size--;
            } else {
                (void)poll(NULL, 0, 1);
            }
        }
    }
    return 0;
}

static ssize_t rcpm_transfer_write(const void *data, size_t size)
{
    const BYTE *bytes = data;
    size_t sent = 0;
    int64_t start = rt_now(), deadline;
    if (start < 0) return -1;
    deadline = start + 30000;
    while (sent < size || (rm_mode && rm_nt)) {
        int64_t now = rt_now();
        if (now < 0 || now >= deadline) return -1;
        if (!rm_mode) {
            ssize_t count = write(STDOUT_FILENO, bytes + sent, size - sent);
            if (count < 0 && errno == EINTR) continue;
            if (count <= 0) return -1;
            sent += (size_t)count;
        } else {
            unsigned char status = rcpm_modem_status();
            if (!(status & 4)) return -1;
            if (sent < size && (status & 2))
                rcpm_modem_write(bytes[sent++]);
            else
                (void)poll(NULL, 0, 1);
        }
    }
    return (ssize_t)sent;
}

/* OUT 73 discards session-only service state. Committed inbox files remain. */
static void rcpm_services_reset(BYTE value)
{
    (void)value;
    upload_length = 0;
    upload_invalid = 0;
    upload_status = UPLOAD_INVALID;
    message_length = 0;
    message_status = 0;
    memset(message_text, 0, sizeof(message_text));
    end_y_source();
    y_status = 1;
    y_source_size = 0;
    y_name_length = 0;
    y_need_tail = 0;
    y_remaining = 0;
}
