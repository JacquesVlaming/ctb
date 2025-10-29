#!/usr/bin/python
# coding: utf-8
"""
Pre-compiled regular expressions.
"""
import re

ENV_VAR = re.compile(r"^\s*([^\#\=][^\=]*)=(.*)\s*\r?\n?")
EXPAND_VARS = re.compile(r"(?<!\\)\$[A-Za-z_][A-Za-z0-9_]*")
NEWLINE = re.compile(r"\r?\n$")
STATUS = re.compile(r"^status: (.*)", re.MULTILINE)
