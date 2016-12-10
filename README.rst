======================
README - Peek Platform
======================

Windows Support
---------------

The Peek platform is designed to run on Linux, however, it is compatible with windows.
This section describes the requirements and configuration for windows.

Requirements
````````````

GitBash
:Download: https://github.com/git-for-windows/git/releases/download/v2.11.0.windows.1/Git-2.11.0-64-bit.exe
:From: https://git-for-windows.github.io


OS Commands
```````````

The config file for each service in the peek platform describes the location of the BASH
interpreter. Peek is coded to use the bash interpreter and basic posix compliant utilites
for all OS commands.

When peek generates it's config it should automatically choose the right interpreter.
     "C:\Program Files\Git\bin\bash.exe" if isWindows else "/bin/bash"

SymLinks
````````

:TODO BRENTON: Include instructions on how to enable windows symlinks
See peek_platform.WindowsPatch for my cross platform symlink code.
http://superuser.com/questions/104845/permission-to-make-symbolic-links-in-windows-7

