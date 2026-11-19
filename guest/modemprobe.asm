; Hardware acceptance probe, not a BYE replacement.
; MODEMPRB I initializes tcpser; MODEMPRB alone selects direct TCP.
; Local H hangs up, D drops DTR, A enables direct answering, P disables it,
; Q returns to CP/M. Only echo received data while carrier is present.
BDOS    EQU 5
STATUS  EQU 70
DATA    EQU 71
CONTROL EQU 72
        ORG 0100H
        LD A,3
        OUT (CONTROL),A
        LD A,(0080H)
        OR A
        JR Z,READY
        LD A,1
        LD (MODEM),A
        LD HL,INITSTR
INIT:   LD A,(HL)
        OR A
        JR Z,READY
        LD C,A
        CALL SEND
        INC HL
        JR INIT
READY:  LD DE,BANNER
        LD C,9
        CALL BDOS
LOOP:   IN A,(STATUS)
        AND 4
        LD B,A
        LD A,(CARRIER)
        CP B
        JR Z,KEY
        LD A,B
        LD (CARRIER),A
        OR A
        LD DE,LOST
        JR Z,REPORT
        LD A,(MODEM)
        OR A
        JR Z,CONNECTED
        ; Consume tcpser's CONNECT result before echoing caller data.
        LD HL,CONNECT
MATCH:  CALL RECEIVE
        CP (HL)
        JR NZ,RESTART
        INC HL
        LD A,(HL)
        OR A
        JR NZ,MATCH
ENDLINE: CALL RECEIVE
        CP 10
        JR NZ,ENDLINE
        JR CONNECTED
RESTART: LD HL,CONNECT
        JR MATCH
CONNECTED: LD DE,ONLINE
REPORT: LD C,9
        CALL BDOS
KEY:    LD C,6
        LD E,0FFH
        CALL BDOS
        CP 'Q'
        JR Z,QUIT
        CP 'H'
        JR Z,HANG
        CP 'D'
        JR Z,DROP
        CP 'A'
        JR Z,ANSWER
        CP 'P'
        JR Z,PAUSE
INPUT:  IN A,(STATUS)
        AND 1
        JP Z,LOOP
        IN A,(DATA)
        LD C,A
        LD A,(CARRIER)
        OR A
        JP Z,LOOP
        CALL SEND
        JP LOOP
HANG:   LD A,7
        OUT (CONTROL),A
        JP LOOP
DROP:   XOR A
        OUT (CONTROL),A
        JP LOOP
ANSWER: LD A,3
        OUT (CONTROL),A
        JP LOOP
PAUSE:  LD A,1
        OUT (CONTROL),A
        JP LOOP
QUIT:   XOR A
        OUT (CONTROL),A
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
CARRIER: DB 0
MODEM:  DB 0
CONNECT: DB 'CONNECT',0
INITSTR: DB 'ATE0V1&C1&D2S0=1',13,0
BANNER: DB 'MODEM PROBE READY',13,10,'$'
ONLINE: DB 'CARRIER ON',13,10,'$'
LOST:   DB 'CARRIER OFF',13,10,'$'
        END
