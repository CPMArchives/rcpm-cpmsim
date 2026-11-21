#!/usr/bin/env python3
"""Regression checks for stable tmux IDs and interrupted-launch recovery."""
from pathlib import Path
import subprocess
import shlex
import tempfile
import unittest
from unittest.mock import Mock, patch

from shared_launcher import Tmux, ensure_session, guest_command


class Session:
    def __init__(self, root, owner=None, port='4002', started=None, exists=True):
        self.root, self.owner, self.port = root, str(root) if owner is None else owner, port
        self.started, self.present, self.calls = started, exists, []
    def find(self, name):
        return '$42' if self.present else None
    def run(self, *args):
        self.calls.append(args)
        if '-t' in args:
            assert args[args.index('-t') + 1] == '$42', args
        value = ''
        if args[0] == 'new-session':
            assert '-P' in args and '#{session_id}' in args
            self.present = True
            value = '$42\n'
        elif args[0] == 'show-options':
            value = self.owner if args[-1] == '@rcpm_instance' else self.port
        elif args[0] == 'list-panes':
            value = self.started if args[-1] == '#{pane_start_command}' else '0'
        return subprocess.CompletedProcess(args, 0, value or '', '')


class LauncherChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.validation = patch('shared_launcher.validate')
        self.validation.start()
    def tearDown(self):
        self.validation.stop()
        self.temporary.cleanup()
    def test_exact_name_resolves_to_id(self):
        tmux = object.__new__(Tmux)
        tmux.run = Mock(return_value=subprocess.CompletedProcess([], 0,
            '$8\trcpm-shared-other\n$42\trcpm-shared\n', ''))
        self.assertEqual(tmux.find('rcpm-shared'), '$42')
        self.assertIsNone(tmux.find('rcpm'))
    def test_new_session_and_reuse_use_id(self):
        tmux = Session(self.root, exists=False)
        with patch('shared_launcher.running', side_effect=[False, True]), patch('shared_launcher.port_busy', side_effect=[False, True]):
            self.assertEqual(ensure_session(self.root, 4002, 'rcpm-shared', tmux), '$42')
        with patch('shared_launcher.running', return_value=True), patch('shared_launcher.port_busy', return_value=True):
            self.assertEqual(ensure_session(self.root, 4002, 'rcpm-shared', tmux), '$42')
        self.assertEqual(sum(row[0] == 'new-session' for row in tmux.calls), 1)
    def test_interrupted_metadata_recovers_matching_guest(self):
        tmux = Session(self.root, owner='', port='', started=guest_command(self.root, 4002))
        with patch('shared_launcher.running', return_value=True), patch('shared_launcher.port_busy', return_value=True):
            self.assertEqual(ensure_session(self.root, 4002, 'rcpm-shared', tmux), '$42')
        self.assertEqual(sum(row[0] == 'set-option' for row in tmux.calls), 2)
        self.assertFalse(any(row[0] in ('kill-session', 'new-session') for row in tmux.calls))
    def test_same_name_foreign_guest_is_not_adopted(self):
        tmux = Session(self.root, owner='', port='', started='exec another-program')
        with self.assertRaisesRegex(RuntimeError, 'Cannot confirm ownership'):
            ensure_session(self.root, 4002, 'rcpm-shared', tmux)
        self.assertFalse(any(row[0] in ('set-option', 'kill-session', 'new-session') for row in tmux.calls))
    def test_tmux_quoted_command_recovers_without_new_guest(self):
        command = guest_command(self.root, 4002)
        for quoted in (shlex.quote(command), '"' + command + '"'):
            with self.subTest(quoted=quoted):
                tmux = Session(self.root, owner='', port='', started=quoted)
                with patch('shared_launcher.running', return_value=True), patch('shared_launcher.port_busy', return_value=True):
                    self.assertEqual(ensure_session(self.root, 4002, 'rcpm-shared', tmux), '$42')
                self.assertFalse(any(row[0] in ('kill-session', 'new-session') for row in tmux.calls))


if __name__ == '__main__':
    unittest.main()
