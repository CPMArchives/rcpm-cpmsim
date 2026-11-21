; Maze Chase's documented cursor hook (06A1h), for ANSI/VT100 terminals.
; Verified Small-C callers push column, then row: row SP+2, column SP+4.
; Coordinates start at zero. Read parameters before adding our own pushes.
; Original MCHASE.DOC permits a JMP hook and code above 63A0h.
 ORG 063A0H
LOCATE: LD HL,2
 ADD HL,SP
 LD A,(HL)
 INC A
 LD (ROW),A
 INC HL
 INC HL
 LD A,(HL)
 INC A
 LD (COL),A
 PUSH BC
 PUSH DE
 PUSH HL
 LD A,27
 CALL CHAR
 LD A,'['
 CALL CHAR
 LD A,(ROW)
 CALL NUM
 LD A,';'
 CALL CHAR
 LD A,(COL)
 CALL NUM
 LD A,'H'
 CALL CHAR
 POP HL
 POP DE
 POP BC
 RET
NUM: LD B,'0'
TENS: CP 10
 JR C,ONES
 SUB 10
 INC B
 JR TENS
ONES: PUSH AF
 LD A,B
 CP '0'
 CALL NZ,CHAR
 POP AF
 ADD A,'0'
CHAR: LD E,A
 LD C,2
 JP 5
ROW: DB 0
COL: DB 0
