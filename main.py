#!/usr/bin/env python3

import sys
import os
from fuse import FUSE, FuseOSError, Operations, fuse_get_context

class Presenter(Operations):
    def __init__(self, base):
        self.base = base

    def _base_path(self, relpath):
        if relpath.startswith("/"):
            relpath = relpath[1:]
        path = os.path.join(self.base, relpath)
        return path

    def access(self, path, mode):
        orig_path = self._base_path(path)
        if not os.access(orig_path, mode):
            raise FuseOSError(errno.EACCES)

    def getattr(self, path, fh=None):
        orig_path = self._base_path(path)
        st = os.lstat(orig_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        orig_path = self._base_path(path)

        dirents = ['.', '..']
        if os.path.isdir(orig_path):
            dirents.extend(os.listdir(orig_path))
        for r in dirents:
            yield r

    def open(self, path, flags):
        orig_path = self._base_path(path)
        return os.open(orig_path, flags)

def main(base, view):
    # Check if view is an empty directory and fail if not
    # Create the directory if not present

    FUSE(Presenter(base), view, nothreads=True, foreground=True)

    # Provide a way to clean-up the view dir when we are done

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 2:
        print("Expect 2 args: <base dir> <view dir>")
        exit(1)

    main(args[0], args[1])
