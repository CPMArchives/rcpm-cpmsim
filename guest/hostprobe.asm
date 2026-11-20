; Test the native host-file port, bypassing CP/M BDOS file calls.
; Use only in the disposable fixture made by check_host_boundary.py.
        ORG 0100H
        LD B,16
FDCTEST: LD A,B
        OUT (10),A
        XOR A
        OUT (13),A
        IN A,(14)
        CP 1
        JR NZ,FDCFAIL
        INC B
        JR NZ,FDCTEST
        LD DE,FDCOK
        JR FDCDONE
FDCFAIL: LD DE,FDCBAD
FDCDONE: XOR A
        OUT (10),A
        LD C,9
        CALL 5
        LD DE,OLDNAME
        LD C,15
        LD A,0F0H
        OUT (161),A
        OR A
        LD DE,OPENNO
        JR NZ,OPENMSG
        LD C,16
        LD A,0EFH
        OUT (161),A
        LD DE,OPENYES
OPENMSG: LD C,9
        CALL 5
        LD DE,NEWNAME
        LD C,22
        LD A,0E9H
        OUT (161),A
        OR A
        LD DE,MAKENO
        JR NZ,MAKEMSG
        LD C,16
        LD A,0EFH
        OUT (161),A
        LD DE,MAKEYES
MAKEMSG: LD C,9
        CALL 5
        JP 0
OLDNAME: DB 0,'HOSTCHK TXT'
        DS 24
NEWNAME: DB 0,'HOSTNEW TXT'
        DS 24
OPENNO: DB 'HOST OPEN DENIED',13,10,'$'
OPENYES: DB 'HOST OPEN ALLOWED',13,10,'$'
MAKENO: DB 'HOST MAKE DENIED',13,10,'$'
MAKEYES: DB 'HOST MAKE ALLOWED',13,10,'$'
FDCOK: DB 'INVALID FDC DRIVES REJECTED',13,10,'$'
FDCBAD: DB 'INVALID FDC DRIVE ACCEPTED',13,10,'$'
