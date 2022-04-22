#!/usr/bin/env python3

import sys
import os
import threading
import subprocess

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

def mount(base, view):
    # Check if view is an empty directory and fail if not
    # Create the directory if not present

    FUSE(Presenter(base), view, nothreads=True, foreground=True)

    # Provide a way to clean-up the view dir when we are done

def env_reader():
    ppid = os.getppid()

    ### The BPF command being used to spy on env var updates in the parent process
    # All the escaping is confusing here, so an explanation of what we are doing:
    # We run a uprobe trace on the "bind_variable" function in bash
    # we check the first argument - the key name, is not equal to "_"
    #   - this is because there are a *lot* of fires with that key, something like a processing step
    # We print out the first and second args, which happens to be the key and value
    # We restrict this tracing to only the parent shell

    # Obviously, this only works for bash, that too, one located at `/usr/bin/bash`.

    cmd = "sudo bpftrace -e 'uprobe:/usr/bin/bash:bind_variable /str(arg0) != \"_\"/{ printf(\"%s=%s\\n\", str(arg0), str(arg1)) }' -p " + str(ppid)

    tracer = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for line in tracer.stdout:
        entry = line.decode().rstrip()
        try:
            (key, value) = entry.split('=')
            # Only process keys which are all upper case
            if key.isupper():
                os.environ[key] = value
        except ValueError:
            # in case of any extra lines not in key = val format
            pass

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 2:
        print("Expect 2 args: <base dir> <view dir>")
        exit(1)

    envReader = threading.Thread(target=env_reader)
    envReader.start()

    mount(args[0], args[1])
