# -*- python-indent-offset: 4 -*-
"""
Copyright (C) 2021-  Marian Piatkowski

This file is a part of GitStats2.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import time
import re
import collections
import unittest
import warnings
from collections import Counter
from multiprocessing import Pool
from functools import partial
import icontract
import gitstats2_collect_data as gitstats2

########################################################################################
# To supress resource warnings, the script can be also run as:
# python3 -W ignore:ResourceWarning test_gitstats2_collect_data.py
########################################################################################

class ParallelTester :
    @staticmethod
    def add_file_node(line) :
        line_splitted = re.split(r'\s+', line, 4)
        if line_splitted[0] == '160000' :
            # skip submodules
            return None
        return line_splitted[-1]

    @staticmethod
    def add_lines_by_authors(revfile) :
        commit_hash = "a3810bfe95be7d1b005bfb8bdacd77485d6834e8"
        cmd = f"git blame --line-porcelain {commit_hash} -- {revfile}"
        pipe_out = gitstats2.get_pipe_output([cmd, "sed -n 's/^author //p'"], quiet=True)
        return Counter(pipe_out.split('\n'))

    @staticmethod
    def add_ext_blob(line, max_ext_length) :
        if not line :
            return None
        parts = re.split(r'\s+', line, 4)
        if parts[0] == '160000' and parts[3] == '-' :
            # skip submodules
            return None
        blob_id = parts[2]
        fullpath = parts[4]
        filename = fullpath.split('/')[-1]
        first_dot = filename.find('.')
        last_dot = filename.rfind('.')
        if first_dot == -1 or last_dot == 0 or \
           len(filename)-last_dot-1 > max_ext_length :
            ext = ''
        else :
            ext = filename[(last_dot+1):]
        return (ext, blob_id)

    @staticmethod
    def add_linecount(ext, blob_id) :
        cmd = f"git cat-file blob {blob_id}"
        pipe_out = gitstats2.get_pipe_output([cmd, 'wc -l'], quiet=True)
        return (ext, int(pipe_out))

class GitStatisticsDataMock :
    def __init__(self, conf, gitpaths) :
        self.configuration = conf.copy()
        self._gitpaths = gitpaths

    def get_gitpaths(self) :
        return self._gitpaths

    def get_log_range(self, default_range='HEAD', end_only=True) :
        commit_range = self.get_commit_range(default_range, end_only)
        if self.configuration['start_date'] :
            return f"--since=\"{self.configuration['start_date']}\" \"{commit_range}\""
        return commit_range

    def get_commit_range(self, default_range='HEAD', end_only=True) :
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

class GitStatisticsCollectTestCase(unittest.TestCase) :
    def __init__(self, *args, **kwargs) :
        super().__init__(*args, **kwargs)
        self.git_statistics = GitStatisticsDataMock(
            {'max_ext_length' : 8},
            ["/Users/tasmania/packages/ABAPInEmacs/"])

    def setUp(self) :
        self.time_start = time.time()

    def tearDown(self) :
        time_end = time.time()
        print(f"=== Execution time of {self.id()}, {(time_end-self.time_start):.3f}s")

    @staticmethod
    def _get_expected_file_tree() :
        return [
            '.gitignore', '.gitmodules', 'LICENSE', 'Notes.md', 'README.md',
            'abap-cds-mode.el', 'abap-ddic-mode.el', 'abap-flycheck.el',
            'abap-indention.el', 'abap-mode.el', 'abap.el', 'abaplib.el',
            'test/change_property_file.el', 'test/outline/objectstructure_zmp_decorator_demo1',
            'test/outline/objectstructure_zsmp_etagstemplate', 'test/outline/options_zmp_decorator_demo1',
            'test/outline/options_zsmp_etagstemplate', 'test/outline/outline_zmp_decorator_demo1.org',
            'test/outline/outline_zsmp_etagstemplate.org', 'test/outline/zmp_decorator_demo1.abap',
            'test/outline/zsmp_etagstemplate.abap', 'test/properties_template.json',
            'test/snippets.el', 'test/where-used/template_where_used.json',
            'test/where-used/template_where_used.xml']

    def test_file_tree_sequential(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        commit_hash = "a3810bfe95be7d1b005bfb8bdacd77485d6834e8"
        pipe_out = gitstats2.get_pipe_output([f"git ls-tree -r {commit_hash}"])
        lines = pipe_out.split('\n')
        lines_splitted = list(map(lambda line : re.split(r'\s+', line, 4), lines))
        # skip submodules
        lines_filtered = list(filter(lambda line : line[0] != '160000', lines_splitted))
        file_tree = [el for *_, el in lines_filtered]
        os.chdir(prev_dir)
        self.assertEqual(file_tree, self._get_expected_file_tree())

    def test_file_tree_parallel(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        commit_hash = "a3810bfe95be7d1b005bfb8bdacd77485d6834e8"
        pipe_out = gitstats2.get_pipe_output([f"git ls-tree -r {commit_hash}"])
        lines = pipe_out.split('\n')
        with Pool(processes=8) as pool :
            file_tree = [el for el in pool.map(
                ParallelTester.add_file_node, lines) if el is not None]
            pool.terminate()
            pool.join()
        os.chdir(prev_dir)
        self.assertEqual(file_tree, self._get_expected_file_tree())

    @staticmethod
    def _get_expected_lines_by_author() :
        return Counter(
            {'Marian Piatkowski': 3433, 'qianmarv': 949, 'Marvin': 674, 'Marvin Qian': 186})

    def test_lines_by_author_sequential(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        commit_hash = "a3810bfe95be7d1b005bfb8bdacd77485d6834e8"
        file_tree = self._get_expected_file_tree()
        lines_by_author = Counter()
        for revfile in file_tree :
            cmd = f"git blame --line-porcelain {commit_hash} -- {revfile}"
            pipe_out = gitstats2.get_pipe_output([cmd, "sed -n 's/^author //p'"], quiet=True)
            lines_by_author += Counter(pipe_out.split('\n'))
        os.chdir(prev_dir)
        self.assertEqual(lines_by_author, self._get_expected_lines_by_author())

    def test_lines_by_author_parallel(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        file_tree = self._get_expected_file_tree()
        with Pool(processes=8) as pool :
            lines_by_author_list = pool.map(ParallelTester.add_lines_by_authors, file_tree)
            pool.terminate()
            pool.join()
        lines_by_author = sum(lines_by_author_list, collections.Counter())
        os.chdir(prev_dir)
        self.assertEqual(lines_by_author, self._get_expected_lines_by_author())

    def test_lines_by_author_parallel2(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        file_tree = self._get_expected_file_tree()
        commit_hash = "a3810bfe95be7d1b005bfb8bdacd77485d6834e8"
        lines_by_authors = gitstats2.GitStatisticsParallel.lines_by_authors(
            file_tree, commit_hash, processes=8)
        os.chdir(prev_dir)
        self.assertEqual(lines_by_authors, self._get_expected_lines_by_author())

    @staticmethod
    def _get_expected_ext_blob() :
        return [
            ('', "1162455d2be181b368e57f103381fe0d7e0e16e4"),
            ('', "ecbf727c8d94696ad01500e1c59206b58b59e959"),
            ('', "94a9ed024d3859793618152ea559a168bbcbb5e2"),
            ('md', "f8a7dca9bf214d18efe495ee204b3f765a48f575"),
            ('md', "c89e09264684b21422a571437844b0537146b942"),
            ('el', "c071c0583639e1d59821a7a8f4f38f812a7d1b65"),
            ('el', "a6963410e0495264b8bf58b6df82d2bdd1741eee"),
            ('el', "2f0556b57622ae8530f61297cfb0f8cec3a84520"),
            ('el', "70d585d0a411ea93fab89f47d00dfec2eba13283"),
            ('el', "5d5820690e06b7eefe807bf1e0ca5f7b9e916cbe"),
            ('el', "8fc8992081a7f5040e186590f85e230127f467b1"),
            ('el', "d2eae9dcdf781a750bce240a682389238d0fd7bb"),
            ('el', "dcf625c7bcfa434344376b2f1052af01d019e793"),
            ('', "b575d9f4a0fa904592bf7b7bb76cff315118e232"),
            ('', "77d434c5ab2a239b99e9ae99b1d8230b1e9ee41a"),
            ('', "24335b12cf8828b4206313bb47f370b38acd9974"),
            ('', "a91bb80a6e2e29d66a158a33908b7867248a0406"),
            ('org', "0180dda9e576bb9a390ab218f81e69b88c9b18ef"),
            ('org', "7f8059c8156cf1abb88018097600713f6788337f"),
            ('abap', "348f32bfac2b27ca277c99a1249f9c4b90bb3a65"),
            ('abap', "7cd09b030ae4e92ba3b82ea421e074ff431f93d7"),
            ('json', "ca44c10e81e7d6245c5ff2e65ded4eff2f18fea9"),
            ('el', "e36ea89d8a0697b0e50ee46ecf8aeb14e18efb75"),
            ('json', "31e3f10c01931fbe6401a409ac198fe5c44874c9"),
            ('xml', "1053141ecd821f3dc05790d4bfc64f9181fb220c")
            ]

    def test_ext_blob_sequential(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        commit_hash = "a3810bfe95be7d1b005bfb8bdacd77485d6834e8"
        pipe_out = gitstats2.get_pipe_output([f"git ls-tree -r -l {commit_hash}"])
        lines = pipe_out.split('\n')
        ext_blob = [el for el in map(
            partial(ParallelTester.add_ext_blob,
                    max_ext_length=self.git_statistics.configuration['max_ext_length']),
            lines) if el is not None]
        os.chdir(prev_dir)
        self.assertEqual(ext_blob, self._get_expected_ext_blob())

    def test_ext_blob_parallel(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        commit_hash = "a3810bfe95be7d1b005bfb8bdacd77485d6834e8"
        pipe_out = gitstats2.get_pipe_output([f"git ls-tree -r -l {commit_hash}"])
        lines = pipe_out.split('\n')
        with Pool(processes=8) as pool :
            ext_blob = [el for el in pool.map(
                partial(ParallelTester.add_ext_blob,
                        max_ext_length=self.git_statistics.configuration['max_ext_length']),
                lines) if el is not None]
            pool.terminate()
            pool.join()
        os.chdir(prev_dir)
        self.assertEqual(ext_blob, self._get_expected_ext_blob())

    @staticmethod
    def _get_expected_ext_linecount() :
        return [
            ('', 1),
            ('', 3),
            ('', 674),
            ('md', 23),
            ('md', 144),
            ('el', 0),
            ('el', 0),
            ('el', 75),
            ('el', 0),
            ('el', 0),
            ('el', 431),
            ('el', 2561),
            ('el', 15),
            ('', 0),
            ('', 0),
            ('', 0),
            ('', 0),
            ('org', 31),
            ('org', 10),
            ('abap', 122),
            ('abap', 29),
            ('json', 17),
            ('el', 354),
            ('json', 636),
            ('xml', 107)
            ]

    def test_ext_linecount_sequential(self) :
        warnings.simplefilter(action="ignore", category="ResourceWarning")
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        ext_blob = self._get_expected_ext_blob()
        ext_linecount = [ParallelTester.add_linecount(ext, blob_id) for ext, blob_id in ext_blob]
        os.chdir(prev_dir)
        self.assertEqual(ext_linecount, self._get_expected_ext_linecount())

    def test_ext_linecount_parallel(self) :
        gitpath = self.git_statistics.get_gitpaths()[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        ext_blob = self._get_expected_ext_blob()
        with Pool(processes=8) as pool :
            ext_linecount = pool.starmap(ParallelTester.add_linecount, ext_blob)
            pool.terminate()
            pool.join()
        os.chdir(prev_dir)
        self.assertEqual(ext_linecount, self._get_expected_ext_linecount())

class RequireCWDGitTestCase(unittest.TestCase) :
    def setUp(self) :
        self.time_start = time.time()

    def tearDown(self) :
        time_end = time.time()
        print(f"=== Execution time of {self.id()}, {(time_end-self.time_start):.3f}s")

    @staticmethod
    @icontract.require(gitstats2.cwd_git)
    def require_cwd_git() :
        pass

    def test_cwd_git(self) :
        prev_dir = os.getcwd()
        os.chdir("/Users/tasmania/packages/ABAPInEmacs")
        self.require_cwd_git()
        os.chdir(prev_dir)

    def test_cwd_not_git(self) :
        prev_dir = os.getcwd()
        os.chdir("/Users/tasmania/packages/")
        with self.assertRaises(icontract.errors.ViolationError) :
            self.require_cwd_git()
        os.chdir(prev_dir)

if __name__ == '__main__' :
    unittest.main()
