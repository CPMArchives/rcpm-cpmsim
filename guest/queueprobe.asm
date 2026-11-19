; Disposable lifecycle test. Queue a recognizable command, then block in
; ordinary console input so BYE must clear it when the lifecycle changes.
        ORG 0100H
        JP START
        DB 'Z3ENV',1
ENV:    DW 0
START:  LD HL,(ENV)
        LD A,H
        OR L
        JR Z,FAIL
        LD DE,18H
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        LD A,D
        OR E
        JR Z,FAIL
        EX DE,HL
        PUSH HL
        LD BC,4
        ADD HL,BC
        LD D,H
        LD E,L
        POP HL
        LD (HL),E
        INC HL
        LD (HL),D
        INC HL
        INC HL
        LD (HL),0
        LD HL,COMMAND
        LD BC,COMMANDEND-COMMAND
        LDIR
        LD DE,READY
        LD C,9
        CALL 5
        LD C,1
        CALL 5
        JP 0
FAIL:   LD DE,ERROR
        LD C,9
        CALL 5
        JP 0
COMMAND: DB 'TYPE QUEUED.TXT',0
COMMANDEND:
READY:  DB 'PENDING COMMAND ARMED',13,10,'$'
ERROR:  DB 'NO Z3PLUS COMMAND BUFFER',13,10,'$'
