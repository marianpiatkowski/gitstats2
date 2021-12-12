# -*- python-indent-offset: 4 -*-
import os
import unittest
import gitstats2_collect_data as gitstats2
from gitstats2_collect_data import \
    ShortStatParserState, \
    ShortStatStateInitial, \
    ShortStatStateCommitInfo, \
    ShortStatStateChangesByCommit

class LogShortStatParserTestCase(unittest.TestCase) :
    def __init__(self, *args, **kwargs) :
        super().__init__(*args, **kwargs)
        self.decide_in_state = (
            ShortStatStateInitial.decide,
            ShortStatStateCommitInfo.decide,
            ShortStatStateChangesByCommit.decide )
        self.current_state = ShortStatParserState.Initial

    def setUp(self) :
        self.current_state = ShortStatParserState.Initial

    def tearDown(self) :
        print(f"=== {self.id()}")

    def test_parse_first_parent(self) :
        gitpath = "/Users/tasmania/packages/weather-metno-el/"
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        extra = '--first-parent -m'
        cmd = f"git log --shortstat {extra} --pretty=format:\"%at %aN\" HEAD"
        pipe_out = gitstats2.get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        prev_state = self.current_state
        for line in lines :
            self.decide(line)
            if prev_state == ShortStatParserState.Initial :
                self.assertEqual(self.current_state, ShortStatParserState.CommitInfo)
            if prev_state == ShortStatParserState.CommitInfo :
                self.assertEqual(self.current_state, ShortStatParserState.ChangesByCommit)
            if prev_state == ShortStatParserState.ChangesByCommit :
                self.assertIn(
                    self.current_state,
                    (ShortStatParserState.Initial, ShortStatParserState.CommitInfo))
            prev_state = self.current_state
        os.chdir(prev_dir)

    def test_parse_reversed_first_parent(self) :
        gitpath = "/Users/tasmania/packages/weather-metno-el/"
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        extra = '--first-parent -m'
        cmd = f"git log --shortstat {extra} --pretty=format:\"%at %aN\" HEAD"
        pipe_out = gitstats2.get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        prev_state = self.current_state
        for line in reversed(lines) :
            self.decide(line)
            if prev_state == ShortStatParserState.Initial :
                self.assertEqual(self.current_state, ShortStatParserState.ChangesByCommit)
            if prev_state == ShortStatParserState.ChangesByCommit :
                self.assertEqual(self.current_state, ShortStatParserState.CommitInfo)
            if prev_state == ShortStatParserState.CommitInfo :
                self.assertIn(
                    self.current_state,
                    (ShortStatParserState.Initial, ShortStatParserState.ChangesByCommit))
            prev_state = self.current_state
        os.chdir(prev_dir)

    def test_parse(self) :
        gitpath = "/Users/tasmania/packages/weather-metno-el/"
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        extra = ''
        cmd = f"git log --shortstat {extra} --pretty=format:\"%at %aN\" HEAD"
        pipe_out = gitstats2.get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        prev_state = self.current_state
        for line in lines :
            self.decide(line)
            if prev_state == ShortStatParserState.Initial :
                self.assertEqual(self.current_state, ShortStatParserState.CommitInfo)
            if prev_state == ShortStatParserState.CommitInfo :
                self.assertIn(
                    self.current_state,
                    (ShortStatParserState.CommitInfo, ShortStatParserState.ChangesByCommit))
            if prev_state == ShortStatParserState.ChangesByCommit :
                self.assertIn(
                    self.current_state,
                    (ShortStatParserState.Initial, ShortStatParserState.CommitInfo))
            prev_state = self.current_state
        os.chdir(prev_dir)

    def test_reversed_parse(self) :
        gitpath = "/Users/tasmania/packages/weather-metno-el/"
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        extra = ''
        cmd = f"git log --shortstat {extra} --pretty=format:\"%at %aN\" HEAD"
        pipe_out = gitstats2.get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        prev_state = self.current_state
        for line in reversed(lines) :
            self.decide(line)
            if prev_state == ShortStatParserState.Initial :
                self.assertEqual(self.current_state, ShortStatParserState.ChangesByCommit)
            if prev_state == ShortStatParserState.ChangesByCommit :
                self.assertEqual(self.current_state, ShortStatParserState.CommitInfo)
            if prev_state == ShortStatParserState.CommitInfo :
                self.assertIn(
                    self.current_state,
                    (ShortStatParserState.Initial, ShortStatParserState.CommitInfo))
            prev_state = self.current_state
        os.chdir(prev_dir)

    def decide(self, line) :
        self.decide_in_state[self.current_state](self, line)

    def toggle(self, target_state) :
        self.current_state = target_state

if __name__ == '__main__' :
    unittest.main()
