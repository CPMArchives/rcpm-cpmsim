; Disposable hardware qualification only; never install on public caller media.
; DIALPRB 127.0.0.1:PORT dials the controlled fixture, echoes 1024 bytes,
; drops DTR and returns to CP/M. Harness bounds execution externally.
BDOS EQU 5
STATUS EQU 70
DATA EQU 71
CONTROL EQU 72
        ORG 100H
        LD A,1
        OUT (CONTROL),A
        LD HL,INITSTR
        CALL STRING
        LD HL,OK
        CALL MATCH
        ; Stable DTR high for >250ms at the qualified 4 MHz.
        LD B,4
DELAY0: LD DE,0
DELAY1: DEC DE
        LD A,D
        OR E
        JR NZ,DELAY1
        DJNZ DELAY0
        LD HL,DIAL
        CALL STRING
        LD A,(80H)
        LD B,A
        LD HL,81H
TAIL:   LD A,(HL)
        CP ' '
        JR Z,SKIP
        LD C,A
        CALL SEND
SKIP:   INC HL
        DJNZ TAIL
        LD C,13
        CALL SEND
        LD HL,CONNECT
        CALL MATCH
LINE:   CALL RECEIVE
        CP 10
        JR NZ,LINE
        LD DE,ONLINE
        LD C,9
        CALL BDOS
        LD DE,1024
ECHO:   CALL RECEIVE
        LD C,A
        CALL SEND
        DEC DE
        LD A,D
        OR E
        JR NZ,ECHO
        ; Drain the hardware TX queue before hanging up: fixture sends Q only
        ; after receiving all echoed bytes.
ACK:    CALL RECEIVE
        CP 'Q'
        JR NZ,ACK
        XOR A
        OUT (CONTROL),A
LOST:   IN A,(STATUS)
        AND 4
        JR NZ,LOST
        LD DE,DONE
        LD C,9
        CALL BDOS
        RET
STRING: LD A,(HL)
        OR A
        RET Z
        LD C,A
        CALL SEND
        INC HL
        JR STRING
MATCH:  CALL RECEIVE
        CP (HL)
        JR NZ,MATCH
        INC HL
        LD A,(HL)
        OR A
        JR NZ,MATCH
        RET
SEND:   IN A,(STATUS)
        AND 2
        JR Z,SEND
        LD A,C
        OUT (DATA),A
        RET
RECEIVE: IN A,(STATUS)
        AND 1
        JR Z,RECEIVE
        IN A,(DATA)
        RET
INITSTR: DB 'ATE0V1&C1&D2S0=0',13,0
OK: DB 'OK',13,10,0
DIAL: DB 'ATD',0
CONNECT: DB 'CONNECT',0
ONLINE: DB 'OUTBOUND CARRIER ON',13,10,'$'
DONE: DB 'OUTBOUND PASS',13,10,'$'
        END
