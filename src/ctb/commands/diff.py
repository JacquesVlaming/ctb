#!/usr/bin/python
# coding: utf-8

# Proprietary packages
from ctb.utils import cmd, env

def run(scenario_from, scenario_to="stable"):
    """Compare the given scenario from "stable" by default."""
    if scenario_to == "stable":
        scenario_to = scenario_from
        scenario_from = "stable"

    cmd("""
    git diff -w --diff-filter=M --no-index -- "{dir}/hipstershop/scenarios/{a}" "{dir}/hipstershop/scenarios/{b}"
    """.format(dir=env("BASEDIR"), a=scenario_from, b=scenario_to))
