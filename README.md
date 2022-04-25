# lft - live file templater

Dynamically re-templatize a folder of files.
Powered by FUSE and eBPF.

## What?

The problem this is meant is solve is the following:
1. You have a bunch of source template files that you want to fill variables in.
2. You don't know all the variables up-front.

Normally, you could use everything from `envsubst`, `jinja2`, `jq`, `yq` to `confd` to solve the problem of generating files from templates, but these 2 requirements make the process cumbersome. You will have to run them repeatedly on multiple inputs as your variables change.

How convenient would it be if env vars in files would resolve just like they would resolve in the shell, or in a script? As you update variables, the next command, the next line in the shell script would run differently. Similarly, what if files change as the env vars change?

Enter lft.

## Usage

Let's say you have a folder of files, each file consisting of env variables that you want to fill-in. For example, let us say, there is a folder `base1` with the following files:
```
hi.txt
subdir/notes.json
```

Where, `hi.txt` looks like:
```
My name is $NAME.
```
and, `subdir/notes.json` looks like this:
```
{
  "id": "$ID",
  "name": "$NAME"
}
```

First, you run the command:
```
<path to lft>/lft.py ./base1 ./view1 &
```
where `view1` is an empty dir to be used as the mount point for the filled-in files.

Now, if you look at `view1`, you will find that it mirrors the `base1` directory.

Now, the following works:
```
$ NAME=chanderg
$ cat ./view1/hi.txt
My name is chanderg.
$ NAME="not cg"
$ cat ./view1/hi.txt
My name is not cg.
```

You get the idea. Now, let's look at the other file in the folder.
```
$ cat ./view1/subdir/notes.json
{
  "id": "",
  "name": "not cg"
}
```

Let's complete the example:
```
$ ID="001"
$ cat ./view1/subdir/notes.json
{
  "id": "001",
  "name": "not cg"
}
```

That's the general gist. As you update variables, the files automatically get updated.

## Install

You need `python3`, and `bpftrace` installed.

Run:
```
pip3 install -r requirements
```

and use the script.

Currently, it only works with bash, though it should be easy enough to extend to other shells.

## How does this magic work?

This is a *MEGA* hack.

Firstly, we use the magic of FUSE - File System in User Space to mount a virtual files system mirroring the original source directory of files. This is needed since we need the most direct way to update files - right before they are accessed.

Secondly, we use the magic of eBPF (specifically bpftrace) to snoop in on bash user space functions responsible for setting user variables. How did I get the right user space probe to use? By reading source-code? Oh no - by good old-fashioned trial/error. 

Start a bash shell and note it's pid. In a different shell, start out broad:
```
bpftrace -e 'uprobe:/usr/bin/bash:*env* { printf("%s\n", func) }' -p <pid of the first bash shell>
```
gets you all user space functions with the word "env" in it. That got us 16 probes, but setting variables in the first bash gets no fires.

Luckily, the next guess of trying functions of the form `*var*` worked:
```
bpftrace -e 'uprobe:/usr/bin/bash:*var* { printf("%s\n", func) }' -p <pid of the first bash shell>
```

which gets us around 90 probes, many of which fire when you run a simple `foo=bar` on the first bash:
```
bind_variable
make_variable_value
stupidly_hack_special_variables
bind_variable
make_variable_value
find_variable
var_lookup
dispose_used_env_vars
find_variable
var_lookup
...
...
...
```

Now, simply update the `printf` command in the bpftrace command to print out args and boom - the very first probe is a hit.

Now, the main python program runs the bpftrace command in a thread and reads from the subprocess stdout, updating local state as bash variables are updated. For simplicity, we only consider ALL_UPPER variables from bash.

The templated files are all stored in-memory for now.

## Acknowledgements

1. https://www.stavros.io/posts/python-fuse-filesystem/
2. https://github.com/fusepy/fusepy/blob/master/examples/memory.py

## LICENSE 

MIT
