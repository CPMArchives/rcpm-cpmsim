; HUMONGOUS CHAT46 extension. Existing BYE RSX; no resident changes.
; No alternate screen, scroll margins, colors, or cursor visibility state:
; carrier loss can return through BYE without leaving a terminal mode set.
SPWIDTH EQU 76
SPROWS  EQU 8
SPSIZE  EQU SPWIDTH*SPROWS

SPINIT: MVI A,1
        STA SPACT
        LXI H,SPBUF
        LXI B,SPSIZE*2
SPZERO: MVI M,' '
        INX H
        DCX B
        MOV A,B
        ORA C
        JNZ SPZERO
        XRA A
        STA SPROW
        STA SPCOL
        STA SPROW+1
        STA SPCOL+1
        STA SPWHO
        CALL SPDRAW

; Keep calling the combined BIOS status path for BYE carrier/inactivity
; handling, but read each input through its distinct extended BDOS call.
; Service at most one byte from each keyboard per pass for fairness.
SPLOOP: CALL CSTAT
        MVI C,66
        CALL BDOS
        ORA A
        JZ SPRMT
        MVI C,67
        CALL BDOS
        STA SPCHAR
        ; Ctrl-B remains BYE's private-console toggle. End chat locally
        ; on entry to private mode; private text must never enter chat buffers.
        MVI C,77
        MVI E,255
        CALL BDOS
        ORA A
        JNZ EXIT1
        XRA A
        STA SPWHO
        CALL SPINPUT
SPRMT:  CALL CSTAT
        MVI C,61
        CALL BDOS
        ORA A
        JZ SPLOOP
        MVI C,64
        CALL BDOS
        ANI 7FH
        STA SPCHAR
        MVI A,1
        STA SPWHO
        CALL SPINPUT
        JMP SPLOOP

; A separate row/column and text buffer belong to each participant.
SPINPUT:LDA SPCHAR
        CPI 3
        JZ EXIT1
        CPI 24
        JZ EXIT1
        CPI 18
        JZ SPDRAW
        CPI CR
        JZ SPNEW
        CPI BS
        JZ SPBACK
        CPI DEL
        JZ SPBACK
        CPI TAB
        JZ SPTAB
        CPI ' '
        RC
        CPI 127
        RNC
        CALL SPADDR
        LDA SPCHAR
        MOV M,A
        PUSH PSW
        CALL SPPOS
        POP PSW
        MOV C,A
        CALL CONOUT
        CALL SPCPTR
        INR M
        MOV A,M
        CPI SPWIDTH
        JZ SPNEW
        RET

SPTAB:  MVI A,' '
        STA SPCHAR
        CALL SPINPUT
        CALL SPCPTR
        MOV A,M
        ANI 7
        JNZ SPTAB
        RET

SPBACK: CALL SPCPTR
        MOV A,M
        ORA A
        RZ
        DCR M
        CALL SPADDR
        MVI M,' '
        JMP SPREFR

SPNEW:  CALL SPCPTR
        MVI M,0
        CALL SPRPTR
        INR M
        MOV A,M
        CPI SPROWS
        JC SPREDR
        DCR M
        ; Drop the oldest line in this pane only.
        CALL SPBASE
        XCHG
        LXI H,SPWIDTH
        DAD D
        LXI B,SPSIZE-SPWIDTH
SPSHFT: MOV A,M
        STAX D
        INX H
        INX D
        DCX B
        MOV A,B
        ORA C
        JNZ SPSHFT
        MVI B,SPWIDTH
SPCLEAR:MVI A,' '
        STAX D
        INX D
        DCR B
        JNZ SPCLEAR
SPREDR:
SPREFR: CALL SPPAINT
        JMP SPPOS

SPCPTR: LXI H,SPCOL
        JMP SPINDEX
SPRPTR: LXI H,SPROW
SPINDEX:LDA SPWHO
        MOV E,A
        MVI D,0
        DAD D
        RET
SPBASE: LXI H,SPBUF
        LDA SPWHO
        ORA A
        RZ
        LXI D,SPSIZE
        DAD D
        RET
SPADDR: CALL SPRPTR
        MOV B,M
        CALL SPBASE
        LXI D,SPWIDTH
SPAD1:  MOV A,B
        ORA A
        JZ SPAD2
        DAD D
        DCR B
        JMP SPAD1
SPAD2:  PUSH H
        CALL SPCPTR
        MOV E,M
        MVI D,0
        POP H
        DAD D
        RET

; CUP takes one-based row B, column D. Output stays on normal BYE CONOUT.
SPCUP:  PUSH B
        PUSH D
        CALL ILPRT
        DB ESC,'[',0
        POP D
        POP B
        PUSH D
        MOV A,B
        CALL SPDEC
        MVI C,';'
        CALL CONOUT
        POP D
        MOV A,D
        CALL SPDEC
        MVI C,'H'
        JMP CONOUT
SPDEC:  MVI B,'0'
SPD10:  CPI 10
        JC SPD1
        SUI 10
        INR B
        JMP SPD10
SPD1:   PUSH PSW
        MOV A,B
        CPI '0'
        JZ SPD2
        MOV C,A
        CALL CONOUT
SPD2:   POP PSW
        ADI '0'
        MOV C,A
        JMP CONOUT

SPPOS:  CALL SPRPTR
        MOV B,M
        LDA SPWHO
        ORA A
        MVI A,4
        JZ SPP1
        MVI A,14
SPP1:   ADD B
        PUSH PSW
        CALL SPCPTR
        MOV A,M
        ADI 2
        MOV D,A
        POP PSW
        MOV B,A
        JMP SPCUP

SPDRAW: LDA SPWHO
        PUSH PSW
        CALL ILPRT
        DB ESC,'[2J',ESC,'[1;1H'
        DB '========================== HUMONGOUS RCP/M CHAT =========================='
        DB ESC,'[3;1H',' SYSOP'
        DB ESC,'[12;1H','--------------------------------------------------------------------------'
        DB ESC,'[13;1H',' CALLER'
        DB ESC,'[23;1H',' Ctrl-C / Ctrl-X: end   Ctrl-R: redraw   CHAT /S: scrolling mode',0
        XRA A
        STA SPWHO
        CALL SPPAINT
        MVI A,1
        STA SPWHO
        CALL SPPAINT
        POP PSW
        STA SPWHO
        JMP SPPOS

SPPAINT:CALL SPBASE
        SHLD SPREAD
        LDA SPWHO
        ORA A
        MVI A,4
        JZ SPPN1
        MVI A,14
SPPN1:  STA SPLINE
        MVI A,SPROWS
        STA SPLINES
SPPN2:  LDA SPLINE
        MOV B,A
        MVI D,2
        CALL SPCUP
        LHLD SPREAD
        MVI B,SPWIDTH
SPPN3:  MOV C,M
        PUSH B
        PUSH H
        CALL CONOUT
        POP H
        POP B
        INX H
        DCR B
        JNZ SPPN3
        SHLD SPREAD
        LDA SPLINE
        INR A
        STA SPLINE
        LDA SPLINES
        DCR A
        STA SPLINES
        JNZ SPPN2
        RET

SPQUIT: LDA SPACT
        ORA A
        RZ
        CALL ILPRT
        DB ESC,'[24;1H',ESC,'[2K',0
        RET

SPMODE: DB 1
SPACT:  DB 0
SPWHO:  DB 0
SPCHAR: DB 0
SPROW:  DB 0,0
SPCOL:  DB 0,0
SPREAD: DW 0
SPLINE: DB 0
SPLINES:DB 0
SPBUF:  DS SPSIZE*2
