#!/usr/bin/env bash
# One-line resource snapshot: load, memory, and the heaviest python processes.
echo "load: $(cut -d' ' -f1-3 /proc/loadavg)  $(free -g | awk '/Mem:/{print "mem used/avail GB:",$3"/"$7}')"
ps -eo rss,etime,args --sort=-rss | grep -E 'expanded_42seeds|orchestrate' | grep -v grep | head -12 \
  | awk '{printf "%6.2f GB  %s  ", $1/1048576, $2; for(i=3;i<=NF;i++) if ($i ~ /--dataset|--seeds/) printf "%s %s ", $i, $(i+1); print ""}'
