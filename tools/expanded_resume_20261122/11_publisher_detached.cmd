@echo off
rem Detached publisher (launched via WMI); output only to files.
cd /d D:\Desk\LEM2-worktrees\expanded-42seeds-results
python -I D:\Desk\LEM2_expanded_resume\tools\publish.py --main "\\wsl.localhost\Ubuntu\home\user\lem2_runs\expanded_188_42seeds" --worktree D:\Desk\LEM2-worktrees\expanded-42seeds-results --log D:\Desk\LEM2_expanded_resume\reports\publish.log --interval 300 >> D:\Desk\LEM2_expanded_resume\reports\publisher_stdout.log 2>&1
echo %date% %time% publisher exited with %errorlevel% >> D:\Desk\LEM2_expanded_resume\reports\publisher_stdout.log
