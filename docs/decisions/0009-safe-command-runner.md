# 0009 Safe Command Runner

DreamNav runs processing tools through argv-only command specs so reconstruction stages can capture stdout, stderr, exit codes, and timeouts without introducing shell-string execution.
