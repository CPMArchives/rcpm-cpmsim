; Test-only approved-program stand-in, installed as HELP.COM on test disks.
; S initializes a scratch RAM sentinel; M tests RAM without disk operations.
; Default mode verifies denied writes to the immutable command disk.
        ORG 100H
        LD A,(82H)
        CP 'S'
        JR NZ,CHECK
        LD A,5AH
        LD (8000H),A
        JR GOOD
CHECK:  LD A,(8000H)
        CP 5AH
        JP NZ,FAIL
        LD A,(82H)
        CP 'M'
        JR Z,GOOD
        LD HL,FUNCS
LOOP:   LD A,(HL)
        OR A
        JR Z,GOOD
        LD C,A
        PUSH HL
        LD DE,FCB
        CALL 5
        POP HL
        CP 0FFH
        JR NZ,FAIL
        INC HL
        JR LOOP
GOOD:   LD DE,OK
        JR PRINT
FAIL:   LD DE,BAD
PRINT:  LD C,9
        CALL 5
        RET
FUNCS:  DB 19,21,22,23,30,34,40,41,99,100,103,0
FCB:    DB 1,'GUARD   TXT'
        DS 24,0
OK:     DB 'EXECUTION-BOUNDARY-PASS',13,10,'$'
BAD:    DB 'EXECUTION-BOUNDARY-FAIL',13,10,'$'
        END
