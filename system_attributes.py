"""Explicit A0 directory-display policy for prepared caller-tool systems."""
import subprocess
from caller_policy import policy


HIDDEN = ('!(C)1988', 'BYEDRIV.COM', 'CPM3.SYS', 'PATH.COM', 'PROFILE.SUB',
          'STARTZ3P.COM', 'SUBMIT.COM', 'VT100DYN.COM', 'Z3PLUS.COM', 'Z3PLUS.LBR')


def apply(image, tools):
    """Only call on new or exclusively locked, staged media; retain other bits."""
    visible = tuple(policy()['programs']) + ('-SYSTEM', 'WELCOME.TXT')
    expected = {name: False for name in visible}
    expected.update({name: True for name in HIDDEN})
    for attributes, names in (('ms', visible), ('s', HIDDEN)):
        subprocess.run([str(tools / 'cpmchattr'), '-f', 'ibm-3740', str(image),
                        attributes, *('0:' + name for name in names)],
                       check=True, capture_output=True)
    listing = subprocess.run([str(tools / 'cpmls'), '-A', '-f', 'ibm-3740',
                              str(image), '0:*'], check=True, capture_output=True,
                             text=True).stdout
    actual = {}
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) == 2 and len(fields[0]) == 9:
            actual[fields[1].upper()] = fields[0][4] == 's'
    for name, sys in expected.items():
        if actual.get(name) is not sys:
            raise ValueError('A0 SYS attribute verification failed: ' + name)
    return dict(visible=list(visible), sys=list(HIDDEN))
