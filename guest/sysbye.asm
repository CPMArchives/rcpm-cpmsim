; BYE.COM for the local CP/M 3 sysop console.
; Flush pending BDOS writes before halting the emulator for publication.
BDOS    EQU     0005H

        ORG     0100H
        LD      C,48
        LD      E,0
        CALL    BDOS
        OR      A
        JR      NZ,FAILED
        HALT
FAILED: LD      DE,FAILMSG
        LD      C,9
        CALL    BDOS
        RET
FAILMSG: DB     'Flush failed. Console remains active.',13,10,'$'
        END
