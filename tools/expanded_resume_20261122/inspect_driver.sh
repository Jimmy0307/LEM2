#!/usr/bin/env bash
# Show what the driver process is doing (state, wait channel, threads, open files).
pid=$(pgrep -f 'orchestrate.py.*--snapshot-dir' | head -1)
echo "driver pid=$pid"
grep -E 'State|Threads|VmRSS' /proc/$pid/status
for t in /proc/$pid/task/*; do echo "thread $(basename $t): $(cat $t/wchan 2>/dev/null) $(awk '{print $3}' $t/stat)"; done
ls -l /proc/$pid/fd 2>/dev/null | awk '{print $NF}' | grep -vE '^(pipe|socket|anon_inode)' | sort | uniq -c | sort -rn | head
echo "--- children"
ps --ppid $pid -o pid,etime,stat,args | cut -c1-160
echo "--- snapshot tmp"
du -sh "$HOME/lem2_runs/.snapshot_tmp" 2>/dev/null; find "$HOME/lem2_runs/.snapshot_tmp" -maxdepth 3 | head -5
