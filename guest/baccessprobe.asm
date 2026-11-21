; Disposable test only. Verify B: selection, FCB reads, writes and metadata
; are refused in caller mode. Denied selections now abort to a corrected
; prompt; the shell-level checks cover that path separately.
        ORG 100H
        LD C,14
        LD E,0
        CALL 5
        LD HL,FUNCS
LOOP:   LD A,(HL)
        OR A
        JR Z,DRIVES
        LD C,A
        PUSH HL
        LD DE,FCB
        CALL 5
        POP HL
        CP 0FFH
        JP NZ,FAIL
        INC HL
        JR LOOP
DRIVES: LD C,46
        LD E,1
        CALL 5
        CP 0FFH
        JR NZ,FAIL
        LD C,101
        LD E,1
        CALL 5
        CP 0FFH
        JR NZ,FAIL
        ; Explicit I: file requests from user 2 must fail outside RBBS.
        LD C,32
        LD E,2
        CALL 5
        LD HL,FUNCS
ILOOP:  LD A,(HL)
        OR A
        JR Z,ALLUSER
        LD C,A
        PUSH HL
        LD DE,PRIVATE
        CALL 5
        POP HL
        CP 0FFH
        JR NZ,IFAIL
        INC HL
        JR ILOOP
ALLUSER:LD C,32
        LD E,0
        CALL 5
        LD C,14
        LD E,8
        CALL 5
        LD C,17
        LD DE,ALLFCB
        CALL 5
        CP 0FFH
        JR NZ,IFAIL
        LD C,18
        CALL 5
        CP 0FFH
        JR NZ,IFAIL
        LD C,14
        LD E,0
        CALL 5
        LD DE,OK
        JR PRINT
IFAIL:  LD C,32
        LD E,0
        CALL 5
        LD C,14
        LD E,0
        CALL 5
FAIL:   LD DE,BAD
PRINT:  LD C,9
        CALL 5
        RET
FUNCS:  DB 15,16,17,18,19,20,21,22,23,30,33,34,35,36,40
        DB 41,42,43,59,99,100,102,103,0
FCB:    DB 2,'VOLUME  TXT'
        DS 24,0
DEFAULT:DB 0,'VOLUME  TXT'
        DS 24,0
PRIVATE:DB 9,'USERS      '
        DS 24,0
ALLFCB: DB '?','???????????'
        DS 24,0
OK:     DB 'B-ACCESS-DENIED-PASS',13,10,'$'
BAD:    DB 'B-ACCESS-DENIED-FAIL',13,10,'$'
        END
