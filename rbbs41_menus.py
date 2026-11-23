"""Approved plain-text menu presentation; command dispatch and data stay intact."""

RULE = '-' * 57


def lines(values):
    for value in values:
        if len(value) > 79:
            raise ValueError('Menu line exceeds terminal width')
    return '\n'.join('outstr("' + s + '",1);' for s in values)


def between(source, start, end, replacement):
    if source.count(start) != 1:
        raise ValueError('Menu source anchor changed: ' + start)
    first = source.index(start)
    last = source.index(end, first)
    return source[:first] + replacement + source[last:]


def configure_menus(files):
    menu = [RULE, '', 'MESSAGES',
            '  E Enter       R Read        N New         S Summary',
            '  K Delete      F Forums      M Status', '', 'INFORMATION',
            '  B Bulletins   U Users       W Welcome', '', 'SESSION',
            '  P Password    T Bell        X Expert      ? Help',
            '  C CP/M        G Disconnect', '']
    files['RBBS4.C'] = between(files['RBBS4.C'], '\t\tstrcpy(tmpstr,"COMMAND: ");',
        '\t\toutstr(tmpstr,4);', '''        if (!expert) {
            crlf(1);
            sprintf(tmpstr,"RBBS 4.1                                    Forum: %s",cmsgfile);
            outstr(tmpstr,1);
''' + lines(menu) + '''
            strcpy(tmpstr,"Command: ");
        } else sprintf(tmpstr,"%s Command: ",cmsgfile);
''')
    files['RBBS4.C'] = files['RBBS4.C'].replace('outstr("Subjects are:",2);', '')
    files['RBBS4.C'] = files['RBBS4.C'].replace('File number: ', 'Forum number: ')
    files['RBBS4.C'] = files['RBBS4.C'].replace(
        'sprintf(tmpstr,"Highest message number seen in this file is %d.",u->lstmsg[cchoice-1]);',
        'sprintf(tmpstr,"  Last read:        %d",u->lstmsg[cchoice-1]);')
    files['RBBS4.C'] = files['RBBS4.C'].replace('outstr(tmpstr,2);\n\t}\n}\n#endif',
                                                         'outstr(tmpstr,1);\n\t}\n}\n#endif')
    files['RBBS4.C'] = files['RBBS4.C'].replace(
        'sprintf(tmpstr,"Checking the %s Messages File...",cmsgfile);',
        'sprintf(tmpstr,"Mail for you in %s: ",cmsgfile);')
    files['RBBS4.C'] = files['RBBS4.C'].replace('No new mail for you.', 'None addressed to you.')

    files['RBBSFN.C'] = files['RBBSFN.C'].replace('char\t*rec;\n{\n\tint\ti;',
        'char\t*rec;\n{\n\tint\ti;\n\tchar area[9];')
    files['RBBSFN.C'] = between(files['RBBSFN.C'], '\tcrlf(1);\n\tfor ( i = 1; i <= n; i++)',
        '\n}\n/****************************************************************/\nload_cntrl', '''    crlf(1);
    outstr("FORUMS",1);
    outstr("--------------------------",1);
    for (i=1; i<=n; i++) {
        movmem(rec+8*i,area,8); area[8]=0;
        sprintf(tmpstr,"  %d %-8.8s",i,area);
        if (!strcmp(area,"PERSONAL")) strcat(tmpstr," (private mail)");
        outstr(tmpstr,1);
    }
    crlf(1);''')
    files['RBBSFN.C'] = files['RBBSFN.C'].replace(
        'sprintf(tmpstr,"Current Message file: %s",cmsgfile);\n\toutstr(tmpstr,2);', '')
    files['RBBSFN.C'] = between(files['RBBSFN.C'], '\tif (print)\n\t{\nsprintf(tmpstr,"First Active Msg #:',
        '\n}\n/***************************************************************/\nprnt_txt', '''    if (print) {
        crlf(1);
        outstr(cmsgfile,1);
        outstr("--------------------------",1);
        sprintf(tmpstr,"  Active messages:  %d",actmsg); outstr(tmpstr,1);
        sprintf(tmpstr,"  Stored messages:  %d",msgct); outstr(tmpstr,1);
        sprintf(tmpstr,"  First / last:     %d / %d",frstmsg,lastmsg); outstr(tmpstr,1);
    }''')
    files['RBBSFN.C'] = files['RBBSFN.C'].replace(
        'Hit CTL-S or s to Pause; any key to Resume.  Hit CTL-K or k to Abort.',
        'Ctrl-S pauses; any key resumes. Ctrl-K stops output.')

    draft = ['MESSAGE OPTIONS', RULE,
             '  S Save        L Preview     H Edit header',
             '  E Edit text   C Continue    A Discard',
             '  X Expert      ? Help']
    files['ENTER.C'] = between(files['ENTER.C'], '\tstrcpy(tmpstr,"SELECT: ");',
        '\toutstr(tmpstr,4);', '''    if (!expert) {
        crlf(1);
''' + lines(draft) + '''
        if (personal) outstr("  R Save another copy",1);
        crlf(1);
    }
    strcpy(tmpstr,"Choice: ");
''')
    files['ENTER.C'] = files['ENTER.C'].replace(
        'Enter Text (?<cr> on a new line for help)', 'Enter text (. to finish, ? for help)')
    files['ENTER.C'] = files['ENTER.C'].replace(
        'strcpy(tmpstr,"Enter Text");', 'strcpy(tmpstr,"Enter text");').replace(
        'strcat(tmpstr," (?<cr> on a new line for help)");',
        'strcat(tmpstr," (. to finish, ? for help)");')

    maintenance = [RULE, '', 'MESSAGES                       FORUMS',
                   '  1 Compact                      4 Select',
                   '  2 Read                         5 Add',
                   '  8 Import text', '', 'USERS',
                   '  6 Add / edit', '  7 Compact',
                   '  3 RESET DATABASE (deletes existing accounts)', '',
                   '  9 Return to CP/M', '']
    files['UTIL.C'] = between(files['UTIL.C'],
        'outstr("**************************************************************",2);',
        '\t\tinstr("",c,1);', '''        crlf(1);
        sprintf(tmpstr,"RBBS 4.1 - SYSOP                            Forum: %s",cmsgfile);
        outstr(tmpstr,1);
''' + lines(maintenance) + '''
        outstr("Choice: ",4);
''')
    files['UTILFN.C'] = files['UTILFN.C'].replace('outstr("Subjects are:",2);', '')
    files['UTILFN.C'] = files['UTILFN.C'].replace('File number: ', 'Forum number: ')
    files['UTILFN.C'] = files['UTILFN.C'].replace(
        'Current SUBJECT File: %s', 'Forum: %s').replace(
        'Enter new subject <Max 8 chars>: ', 'New forum name (up to 8 characters): ')

    files['HELP.CCC'] = '\n'.join([
        'HELP', RULE,
        '  R;123     Read message 123',
        '  R;1+      Read from 1, pausing between messages',
        '  R;1*      Read from 1 without pauses',
        '  N         Read new messages (R;#+)', '',
        '  + and * also work with S and K.',
        '  # selects the next unread message.', '',
        '  Ctrl-S    Pause output; any key resumes',
        '  Ctrl-K    Stop output', '',
        '  C         Return to CP/M',
        '            YSEND downloads; UPLOAD receives files', ''])
    files['SELHELP.CCC'] = '\n'.join(draft + ['  R Save another copy (PERSONAL only)', ''])
    files['MSGHELP.CCC'] = '\n'.join([
        'WRITING A MESSAGE', RULE,
        '  Type . on its own line to finish. Blank lines are allowed.',
        '  Choose S to save, L to preview, or A to discard.', '',
        '  Ctrl-V shows line-editing keys.',
        '  In Edit text, -n inserts before line n.',
        '  To delete a line, erase it and enter a single period.', '',
        '  PERSONAL is private mail. Other forums are public.',
        '  In PERSONAL, R saves a copy; H changes its recipient.', ''])
    return files
