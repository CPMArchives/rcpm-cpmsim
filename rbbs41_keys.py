"""Single-key menus in normal mode; preserve expert command-line input."""


def configure_keys(files):
    files['RBBS4.H']=files['RBBS4.H'].replace(
        'int\texpert;', 'int keymenus;\n\tint\texpert;')
    files['RBBS4.C']=files['RBBS4.C'].replace(
        'instr("",cmd2,1);', 'menuin(cmd2,"CEFGKRSNBMPTUWX?");').replace(
        'instr("",input,3);', 'menuin(input,"123456789");')
    files['ENTER.C']=files['ENTER.C'].replace(
        'instr("",cmd2,1);', 'menuin(cmd2,personal ? "HLSRCEAX?" : "HLSCEAX?");')
    files['UTIL.C']=files['UTIL.C'].replace('upstr("dummy");',
        'keymenus=TRUE;\n\tupstr("dummy");').replace(
        'instr("",c,1);', 'menuin(c,"123456789");')
    files['UTILFN.C']=files['UTILFN.C'].replace(
        'instr("",input,3);', 'menuin(input,"123456789");')
    files['RBBSCIO.C']=files['RBBSCIO.C'].replace(
        'instr("",ans2,1);', 'menuin(ans2,"YN");')
    files['RBBSCIO.C'] += '''
/****************************************************************/
/* Only explicit menu sites use this helper. Text stays line-edited. */
menuin(input,keys)
char *input,*keys;
{
    int i;
    char key;
    if (expert && !keymenus) {
        instr("",input,1);
        return;
    }
    while (TRUE) {
        if (*sav) {
            instr("",input,1);
            key=toupper(*input);
        } else {
            key=toupper(bios(3));
            if (key=='\\r' || key=='\\n') continue;
            for (i=0; keys[i] && keys[i]!=key; ++i);
            if (!keys[i]) { bios(4,7); continue; }
            bios(4,key);
            ++icnt;
        }
        for (i=0; keys[i] && keys[i]!=key; ++i);
        if (!keys[i]) continue;
        input[0]=key; input[1]=0;
        cflg=0;
        return;
    }
}
'''
    files['HELP.CCC']=files['HELP.CCC'].replace('  R;123',
        '  Menus: press a key. Text and message numbers: press Return.\n'
        '  X toggles expert mode (Return-based commands and shortcuts).\n\n'
        '  R;123',1)
    return files
