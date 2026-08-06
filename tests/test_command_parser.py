"""
test_command_parser.py — Unit test cho CommandParser (Role A)
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.command_parser import CommandParser, FTPCommand


class TestCommandParser(unittest.TestCase):
    def test_empty_and_whitespace_input(self):
        cmd = CommandParser.parse("")
        self.assertEqual(cmd.name, "")
        self.assertEqual(cmd.argument, "")

        cmd_ws = CommandParser.parse("   \t \r\n ")
        self.assertEqual(cmd_ws.name, "")
        self.assertEqual(cmd_ws.argument, "")

    def test_single_word_command(self):
        cmd = CommandParser.parse("pwd")
        self.assertEqual(cmd.name, "PWD")
        self.assertEqual(cmd.argument, "")

        cmd_quit = CommandParser.parse("QUIT\r\n")
        self.assertEqual(cmd_quit.name, "QUIT")
        self.assertEqual(cmd_quit.argument, "")

    def test_command_with_argument(self):
        cmd = CommandParser.parse("USER admin")
        self.assertEqual(cmd.name, "USER")
        self.assertEqual(cmd.argument, "admin")

        cmd_cwd = CommandParser.parse("cwd /path/to/dir")
        self.assertEqual(cmd_cwd.name, "CWD")
        self.assertEqual(cmd_cwd.argument, "/path/to/dir")

    def test_command_with_spaces_in_argument(self):
        cmd = CommandParser.parse("STOR my long file.txt")
        self.assertEqual(cmd.name, "STOR")
        self.assertEqual(cmd.argument, "my long file.txt")


if __name__ == "__main__":
    unittest.main()
