; Diagnostic only. Installed as CLS on disposable qualification disks.
        ORG 100H
        LD A,13
        LD (USER),A
AGAIN:  LD C,32
        LD A,(USER)
        LD E,A
        CALL 5
        LD HL,FUNCS
LOOP:   LD A,(HL)
        OR A
        JR Z,NEXT
        LD C,A
        PUSH HL
        LD DE,PRIVATE
        CALL 5
        POP HL
        CP 0FFH
        JP NZ,FAIL
        INC HL
        JR LOOP
NEXT:   LD A,(USER)
        CP 15
        JR Z,HELP
        LD A,15
        LD (USER),A
        JR AGAIN
HELP:   LD C,32
        LD E,14
        CALL 5
        LD C,15
        LD DE,TOPIC
        CALL 5
        CP 0FFH
        JP Z,FAIL
        LD C,16
        LD DE,TOPIC
        CALL 5
        LD HL,MUTATE
HLOOP:  LD A,(HL)
        OR A
        JR Z,SCAN
        LD C,A
        PUSH HL
        LD DE,TOPIC
        CALL 5
        POP HL
        CP 0FFH
        JP NZ,FAIL
        INC HL
        JR HLOOP
SCAN:   LD C,14
        LD E,8
        CALL 5
        LD C,17
        LD DE,ALLFCB
        CALL 5
        CP 0FFH
        JR NZ,FAIL
        LD DE,OK
        JR PRINT
FAIL:   LD DE,BAD
PRINT:  PUSH DE
        LD C,32
        LD E,0
        CALL 5
        LD C,14
        LD E,0
        CALL 5
        POP DE
        LD C,9
        CALL 5
        RET
USER:   DB 0
FUNCS:  DB 15,16,17,18,19,20,21,22,23,30,33,34,35,36,40
        DB 41,42,43,59,99,100,102,103,0
MUTATE: DB 19,21,22,23,30,34,40,41,99,100,103,0
PRIVATE:DB 9,'USERS      '
        DS 24,0
TOPIC:  DB 9,'TOPIC   HLP'
        DS 24,0
ALLFCB: DB '?','???????????'
        DS 24,0
OK:     DB 'UPPER-ACCESS-PASS',13,10,'$'
BAD:    DB 'UPPER-ACCESS-FAIL',13,10,'$'
        END
