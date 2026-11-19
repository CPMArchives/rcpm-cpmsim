; Disposable fixture only: create a readonly/system file in I0: WORK.
        ORG 0100H
        LD C,32
        LD E,0FFH
        CALL 5
        LD (USER),A
        LD C,32
        LD E,0
        CALL 5
        LD DE,FCB
        LD C,22
        CALL 5
        CP 0FFH
        JR Z,FAIL
        LD DE,BODY
        LD C,26
        CALL 5
        LD DE,FCB
        LD C,21
        CALL 5
        OR A
        JR NZ,FAIL
        LD DE,FCB
        LD C,16
        CALL 5
        CP 0FFH
        JR Z,FAIL
        LD A,0D4H
        LD (FCB+9),A
        LD A,0D8H
        LD (FCB+10),A
        LD DE,FCB
        LD C,30
        CALL 5
        CP 0FFH
        JR Z,FAIL
        LD C,48
        LD E,0
        CALL 5
        OR A
        JR NZ,FAIL
        LD DE,OK
        JR DONE
FAIL:   LD DE,BAD
DONE:   PUSH DE
        LD A,(USER)
        LD E,A
        LD C,32
        CALL 5
        LD DE,80H
        LD C,26
        CALL 5
        POP DE
        LD C,9
        CALL 5
        RET
USER:   DB 0
FCB:    DB 9,'WORKTESTTXT'
        DS 24,0
BODY:   DS 128,055H
OK:     DB 'READONLY WORK FILE CREATED',13,10,'$'
BAD:    DB 'WORK FIXTURE FAILED',13,10,'$'
