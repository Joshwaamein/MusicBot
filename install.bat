@ECHO off
REM ============================================================================
REM install.bat — MusicBot Windows Installer Launcher
REM Joshwaamein/MusicBot (forked from Just-Some-Bots/MusicBot)
REM
REM Usage:   Double-click or run from Command Prompt
REM
REM This script launches install.ps1 (PowerShell) which handles:
REM   - Python installation check
REM   - Git installation check
REM   - Dependency installation via pip
REM   - Initial configuration
REM ============================================================================

CHCP 65001 > NUL

REM --> The install.bat script only exists to easily launch the PowerShell script.
REM --> By default powershell might error about running unsigned scripts...

CD "%~dp0"

SET InstFile="%~dp0%\install.ps1"
IF exist %InstFile% (
    powershell.exe -noprofile -executionpolicy bypass -file "%InstFile%" %*
) ELSE (
    echo Could not locate install.ps1
    echo Please ensure it is available to continue the automatic install.
)
