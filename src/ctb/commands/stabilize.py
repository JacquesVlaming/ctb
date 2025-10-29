#!/usr/bin/python
# coding: utf-8
"""
Bring the microservices to a stable state.
"""

# Proprietary packages
import ctb.commands.start

def run(quiet=False):
    return ctb.commands.start.run("stable", quiet)
