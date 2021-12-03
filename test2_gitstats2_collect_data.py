# -*- python-indent-offset: 4 -*-
import os
import time
import unittest
import warnings
import gitstats2_collect_data as gitstats2

class GitStatisticsDataMock :
    def __init__(self, conf, gitpaths) :
        self.configuration = conf.copy()
        self._gitpaths = gitpaths

    def get_gitpaths(self) :
        return self._gitpaths

    def get_log_range(self, default_range='HEAD', end_only=True) :
        commit_range = self._get_commit_range(default_range, end_only)
        if self.configuration['start_date'] :
            return f"--since=\"{self.configuration['start_date']}\" \"{commit_range}\""
        return commit_range

    def _get_commit_range(self, default_range='HEAD', end_only=True) :
        if self.configuration['commit_end'] :
            if end_only or not self.configuration['commit_begin'] :
                return self.configuration['commit_end']
            return f"{self.configuration['commit_begin']}..{self.configuration['commit_end']}"
        return default_range

class GitStatisticsRevListTestCase(unittest.TestCase) :
    def __init__(self, *args, **kwargs) :
        super().__init__(*args, **kwargs)
        self.git_statistics = GitStatisticsDataMock(
            {'max_ext_length' : 8,
             'commit_end' : 'HEAD',
             'start_date' : '',
             'processes' : 8
            },
            ["/Users/tasmania/packages/ABAPInEmacs/"])
        self.time_start = 0.0

    def setUp(self) :
        self.time_start = time.time()

    def tearDown(self) :
        time_end = time.time()
        print(f"=== Execution time of {self.id()}, {(time_end-self.time_start):.3f}s")

    def test_file_tree_by_revlist_sequential(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        cmd = f"git rev-list --pretty=format:\"%at %T %H\" {self.git_statistics.get_log_range('HEAD')}"
        pipe_out = gitstats2.get_pipe_output([cmd, 'grep -v ^commit'])
        lines = pipe_out.strip().split('\n')
        lines.reverse()
        time_files_commit = self._file_tree_by_revlist_sequential(lines)
        # test whether time_files_commit result is ordered by timestamp
        # so ignore filetree for now and only compare the order of stamps and commit hashes
        time_commit = [(stamp, commit_hash) for stamp, _, commit_hash in time_files_commit]
        expected = self._get_expected_time_commit()
        os.chdir(prev_dir)
        self.assertEqual(time_commit, expected)

    def test_file_tree_by_revlist_parallel(self) :
        warnings.simplefilter(action="ignore", category="ResourceWarning")
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        cmd = f"git rev-list --pretty=format:\"%at %T %H\" {self.git_statistics.get_log_range('HEAD')}"
        pipe_out = gitstats2.get_pipe_output([cmd, 'grep -v ^commit'])
        lines = pipe_out.strip().split('\n')
        lines.reverse()
        time_files_commit = gitstats2.GitStatisticsParallel.file_tree_by_revlist(
            lines, self.git_statistics.configuration['processes'], quiet=True)
        # test whether time_files_commit result is ordered by timestamp
        # so ignore filetree for now and only compare the order of stamps and commit hashes
        time_commit = [(stamp, commit_hash) for stamp, _, commit_hash in time_files_commit]
        expected = self._get_expected_time_commit()
        os.chdir(prev_dir)
        self.assertEqual(time_commit, expected)

    @staticmethod
    def _file_tree_by_revlist_sequential(lines) :
        time_files_commit = []
        for line in lines :
            if not line :
                continue
            timestamp, rev, commit_hash = line.split()
            pipe_out = gitstats2.get_pipe_output([f"git ls-tree -r \"{rev}\""], quiet=True)
            file_tree = gitstats2.GitStatisticsParallel.file_tree_by_revision(pipe_out)
            time_files_commit.append((timestamp, file_tree, commit_hash))
        return time_files_commit

    def _get_expected_time_commit(self) :
        cmd = f"git rev-list --pretty=format:\"%at %H\" {self.git_statistics.get_log_range('HEAD')}"
        pipe_out = gitstats2.get_pipe_output([cmd, 'grep -v ^commit'])
        lines = pipe_out.strip().split('\n')
        return [tuple(line.split()) for line in reversed(lines)]

if __name__ == '__main__' :
    unittest.main()
