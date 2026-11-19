#include <stdio.h>
#include <libdsk.h>

int main(int argc, char **argv)
{
    DSK_PDRIVER driver;
    DSK_GEOMETRY geometry;
    dsk_err_t error;

    if (argc != 2) {
        fprintf(stderr, "Usage: probe_geometry image.dsk\n");
        return 2;
    }
    error = dsk_open(&driver, argv[1], "raw", NULL);
    if (error != DSK_ERR_OK) {
        fprintf(stderr, "%s\n", dsk_strerror(error));
        return 1;
    }
    error = dsk_getgeom(driver, &geometry);
    if (error == DSK_ERR_OK) {
        printf("sides=%d cylinders=%u heads=%u sectors=%u base=%u sector_bytes=%lu\n",
               (int)geometry.dg_sidedness, geometry.dg_cylinders,
               geometry.dg_heads, geometry.dg_sectors, geometry.dg_secbase,
               (unsigned long)geometry.dg_secsize);
    } else {
        fprintf(stderr, "%s\n", dsk_strerror(error));
    }
    dsk_close(&driver);
    return error == DSK_ERR_OK ? 0 : 1;
}
