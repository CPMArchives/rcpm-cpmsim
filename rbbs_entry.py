"""Build the fixed public RBBS alias from a pinned preserved Z3PLUS alias."""
import hashlib
from prepare_z3plus import configure_startup

PREVIOUS_POLICY = 'e96f7e6bbac74a2a638561e85e77be861da3c84ffaf19ff7756993f32db34440'
ALIAS_SHA256 = '7d5b5d376a0f1922ef1bf6bd3e6962ccb999f0b38d1adcebf3cf3f395162c7bd'
BOARD_SHA256 = '60164511a0365583e94b3e88e859375f0e6499d9a93a82728a475772b8666526'


def public_entry(romwbw, user):
    if user != 15:
        raise ValueError('Public RBBS entry requires the upper-area A15:/I15: profile')
    source = romwbw / 'Source/Images/d_z3plus/u0/STARTZ3P.COM'
    if hashlib.sha256(source.read_bytes()).hexdigest() != ALIAS_SHA256:
        raise ValueError('Public RBBS requires the pinned, reviewed alias executable')
    # No parameter substitution or caller-supplied executable name.
    # Select safe A0: first: Z3PLUS changes user before drive, so a direct
    # A15: from I0: would momentarily attempt forbidden I15: selection.
    return bytes(configure_startup(source, f'A0:;A{user}:;A{user}:RBBS37'))
