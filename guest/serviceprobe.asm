; Test media only: check reset statuses and attempt to save any leftover draft.
        ORG 0100H
        IN A,(61)
        CP 1
        JR NZ,FAIL
        IN A,(63)
        CP 1
        JR NZ,FAIL
        XOR A
        OUT (62),A
        LD DE,OK
        JR PRINT
FAIL:   LD DE,BAD
PRINT:  LD C,9
        CALL 5
        RET
OK:     DB 'SERVICE STATE RESET',13,10,'$'
BAD:    DB 'SERVICE STATE NOT RESET',13,10,'$'
