#!/usr/bin/python
# coding: utf-8
"""
Common utility functions.
"""

# Standard packages
import io
import json
import multiprocessing
import os
import re
import shlex
import subprocess

# Proprietary packages
from ctb import patterns


def env(variable):
    """Shorthand for accessing environment variables."""
    return os.environ.get(variable)

def update_envfile():
    """Update the .env file with current applicable environment variables."""
    updated = []
    with open(env("ENVFILE"), "r") as file:
        for line in file:
            line = re.sub(patterns.NEWLINE, "", line)
            matches = re.findall(patterns.ENV_VAR, line)
            if len(matches) > 0:
                variable, old_value = matches[0]
                updated.append("{}={}".format(variable, env(variable)))
            else:
                updated.append(line)
    with open(env("ENVFILE"), "w") as file:
        file.write("\n".join(updated))

def expandvars(s):
    """Expand environment variables in a string like Bash (e.g. $VARIABLE)."""
    return re.sub(patterns.EXPAND_VARS, "", os.path.expandvars(s))

def load_file(filepath):
    """Read a file."""
    with io.open(filepath, mode="r", encoding="utf-8") as file:
        return file.read()

def load_template(filepath):
    """Read a file and populate its variables."""
    return expandvars(load_file(filepath).strip()).encode("utf-8")

def load_template_json(filepath):
    """Read a file containing a JSON template, populate its variables, and
    convert it to a JSON object."""
    return json.loads(load_template(filepath))

def cmd(command, stdout=True):
    """Execute a shell command."""
    args = shlex.split(expandvars(command))
    if stdout:
        return subprocess.call(args)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    exitcode = p.returncode
    return exitcode, out, err

def parallel_tasks(function, tasks, num_processes=4):
    pool = multiprocessing.Pool(processes=num_processes)
    try:
        result = pool.map_async(function, tasks).get(60)
    except KeyboardInterrupt:
        pool.terminate()
    else:
        pool.close()
    pool.join()
