# RBBS 4.1 Edit 02 test system

The isolated test uses the RCP/M 1.1.1 release system with a newly compiled
RBBS 4.1 Edit 02 and fresh PERSONAL, GENERAL, CPM and TEST message areas.
The ordinary 3.7 installation and published release are not modified.

Build with `build_rbbs41.py`, then assemble a new test installation with
`prepare_rbbs41_system.py`. Both accept explicit local input paths.
The source inputs are rbbs4102.zip and the author's bdsc-all.zip distribution.
BDS C 1.60's supplied BDSCIO.H and DEFF15.CRL provide the older runtime API.
Compiler externals start at 9000h; CLINK uses a 1000h reference table.
Input and executable hashes are recorded in build/rbbs41/BUILD.json.

## Adaptations

- Keep A15: executable loading and private I15: data under the existing BYE
  application boundary, changing the exact admitted board name to RBBS41.
- Use the fixed public RBBS alias, with no executable parameter substitution.
- Keep LASTREAD and LASTWRITE disabled; each entry authenticates independently.
- Allow ordinary accounts to return to CP/M, without granting wheel privilege.
- Read the date from CP/M 3 function 105 rather than prompting each visitor.
- End message text with a period on a line by itself.
- Bound board subject selection to 1–8, cap subject creation at eight entries,
  and allow room for the new-account location string's terminator.
- Disable the old low-memory rerun authentication shortcut.
- Use the same named BYE5 RSX logout request as B5ENTRY.ASM for disconnects.
  The original C runtime executable chaining restarted the board in this setup.
- Preserve CRLF in RMAC assembly input. An initial build incorrectly changed
  BYE source to LF and produced an empty resident driver, causing a startup
  opcode trap. The builder now rejects zero-length LINK output.

## Results on November 23, 2026

Local CP/M 3 checks passed: SYSOP login, registration, invalid forum selection,
forum separation, posting and reading, account/message persistence, private
mail sender/recipient visibility, and maintenance-utility startup.

Raw TCP checks passed on a disposable copy at 4 MHz: welcome display, direct
private executable rejection, public entry from WORK, forum selection,
posting/readback, return to CP/M with private data inaccessible, board reentry,
G disconnect, reconnection, and carrier-loss recovery.

The earlier loopback-permission block was lifted when execution resumed; the
remote check then exposed and verified the fixes above. The local check does
not by itself establish BYE or AUTH compatibility.

Results are in build/local-check-05/result.json and
build/remote-check-05/result.json. The original test installation at
build/trial-02/RBBS41-Test was repaired in place while stopped, with A:/I:
backups retained in build/trial-02-before-startup-fix. Test credentials and
forum data were preserved. Its VALIDATION.json records both check groups.

## Running

Run Start-RBBS41.command in Terminal. Connect SyncTERM by Raw TCP to
127.0.0.1:4002 and enter RBBS at the CP/M prompt. Read TEST-CREDENTIALS.json
for the generated SYSOP password. F selects an area; E posts; R reads;
C returns to CP/M; G disconnects. Non-expert callers may be asked whether
to skip leaving a message for the sysop when exiting.

This test uses its dedicated Python launcher, not runtime/rcpm's legacy 3.7
initialization. J:/P: are empty test images. Stock six-character passwords
and small message limits remain. IP232 drivers are built but not qualified
by this raw TCP check. No production upgrade or publication is implied.
