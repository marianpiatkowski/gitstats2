# -*- python-indent-offset: 4 -*-
import os
import time
import collections
import re
from multiprocessing import Pool
from collections import Counter
from functools import partial
from gitstats2_collect_data import GitStatisticsData

class GitStatisticsCollectParallel(GitStatisticsData) :
    def main(self) :
        gitpath = self._gitpaths[0]
        prev_dir = os.getcwd()
        os.chdir(gitpath)
        print('=== Collecting revision lists of repoository...')
        cmd = f"git rev-list --pretty=format:\"%at %T %H\" {self._get_log_range('HEAD')}"
        pipe_out = self._get_pipe_output([cmd, 'grep -v ^commit'])
        lines = pipe_out.strip().split('\n')
        lines.reverse()
        print('=== Sequential execution of git ls-tree for all revisions')
        time_start = time.time()
        self._file_tree_by_revlist_sequential(lines)
        time_end = time.time()
        print(f"=== Execution time {(time_end-time_start):.3f}s")
        print('=== Parallel execution of git ls-tree for all revisions')
        time_start = time.time()
        time_files_commit = self._file_tree_by_revlist_parallel(lines)
        time_end = time.time()
        print(f"=== Execution time {(time_end-time_start):.3f}s")
        print('=== Sequential execution of git blame --line-porcelain for all commit hashes')
        time_start = time.time()
        # self._lines_by_author_by_stamp_sequential(time_files_commit)
        time_end = time.time()
        print(f"=== Execution time {(time_end-time_start):.3f}s")
        print('=== Parallel execution of git blame --line-porcelain for all commit hashes')
        time_start = time.time()
        lines_by_authors_by_stamp = \
            self._lines_by_author_by_stamp_parallel(time_files_commit)
        time_end = time.time()
        print(f"=== Execution time {(time_end-time_start):.3f}s")
        print('=== Collecting blob ids for HEAD...')
        cmd = f"git ls-tree -r -l {self._get_commit_range('HEAD', end_only=True)}"
        pipe_out = self._get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        ext_blob = [el for el in map(self._add_ext_blob, lines) if el is not None]
        print('=== Sequential execution of git cat-file for all blob ids')
        time_start = time.time()
        self._ext_lines_by_blob_sequential(ext_blob)
        time_end = time.time()
        print(f"=== Execution time {(time_end-time_start):.3f}s")
        print('=== Parallel execution of git cat-file for all blob ids')
        time_start = time.time()
        ext_lines = self._ext_lines_by_blob_parallel(ext_blob)
        time_end = time.time()
        print(f"=== Execution time {(time_end-time_start):.3f}s")
        os.chdir(prev_dir)

    def _add_time_files_commit(self, line) :
        timestamp, rev, commit_hash = line.split()
        pipe_out = self._get_pipe_output([f"git ls-tree -r \"{rev}\""], quiet=True)
        file_tree = self._file_tree_by_revision(pipe_out)
        return (timestamp, file_tree, commit_hash)

    def _file_tree_by_revlist_sequential(self, lines) :
        time_files_commit = []
        for line in lines :
            if not line :
                continue
            timestamp, rev, commit_hash = line.split()
            pipe_out = self._get_pipe_output([f"git ls-tree -r \"{rev}\""], quiet=True)
            file_tree = self._file_tree_by_revision(pipe_out)
            time_files_commit.append((timestamp, file_tree, commit_hash))

    def _file_tree_by_revlist_parallel(self, lines) :
        with Pool(processes=self.configuration['processes']) as pool :
            time_files_commit = pool.map(self._add_time_files_commit, lines)
            pool.terminate()
            pool.join()
        return time_files_commit

    def _lines_by_author_by_stamp_sequential(self, time_files_commit) :
        for timestamp, file_tree, commit_hash in time_files_commit :
            lines_by_author = Counter()
            for revfile in file_tree :
                cmd = f"git blame --line-porcelain {commit_hash} -- {revfile}"
                pipe_out = self._get_pipe_output([cmd, "sed -n 's/^author //p'"], quiet=True)
                lines_by_author += Counter(pipe_out.split('\n'))

    def _add_lines_by_authors(self, revfile, commit_hash) :
        cmd = f"git blame --line-porcelain {commit_hash} -- {revfile}"
        pipe_out = self._get_pipe_output([cmd, "sed -n 's/^author //p'"], quiet=True)
        return Counter(pipe_out.split('\n'))

    def _lines_by_author(self, file_tree, commit_hash) :
        with Pool(processes=self.configuration['processes']) as pool :
            lines_by_author_list = pool.map(
                partial(self._add_lines_by_authors, commit_hash=commit_hash), file_tree)
            pool.terminate()
            pool.join()
        return sum(lines_by_author_list, collections.Counter())

    def _lines_by_author_by_stamp_parallel(self, time_files_commit) :
        return [(timestamp, self._lines_by_author(file_tree, commit_hash))
                for timestamp, file_tree, commit_hash in time_files_commit]

    def _add_ext_blob(self, line) :
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
           len(filename)-last_dot-1 > self.configuration['max_ext_length'] :
            ext = ''
        else :
            ext = filename[(last_dot+1):]
        return (ext, blob_id)

    def _add_linecount(self, ext, blob_id) :
        cmd = f"git cat-file blob {blob_id}"
        pipe_out = self._get_pipe_output([cmd, 'wc -l'], quiet=True)
        return (ext, int(pipe_out))

    def _ext_lines_by_blob_sequential(self, ext_blob) :
        ext_linecount = [self._add_linecount(ext, blob_id) for ext, blob_id in ext_blob]

    def _ext_lines_by_blob_parallel(self, ext_blob) :
        with Pool(processes=self.configuration['processes']) as pool :
            ext_linecount = pool.starmap(self._add_linecount, ext_blob)
            pool.terminate()
            pool.join()
        return ext_linecount

if __name__ == '__main__' :
    GitStatisticsCollectParallel(
        {'max_ext_length' : 8,
         'commit_end' : 'HEAD',
         'start_date' : '',
         'processes' : 8,
        },
        ["/Users/tasmania/packages/ABAPInEmacs/"]).main()
