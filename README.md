# Simple scripts to show cluster utilization

Execute `./collectl.py -h` to see how to collect statistics from machines. You need to give a worker file like "[workers](https://github.com/TatianaJin/cluster_monitor/blob/master/workers)".

Execute `./plot.py -h` to see the help. Below are some example operations:
1. `./plot.py collectl_raw_file -r` to plot from collectl raw file. A preprocessed files will be generated from the raw file.
1. `./plot.py directory -r` to plot from collectl raw files in the specified directory.
1. `./plot.py dat_file` to plot from preprocessed files in the specified directory.
1. `./plot.py -g` to generate configuration file for customization.
1. Supported plot fields include '[CPU]Totl%', '[MEM]Used%', '[NET]Receive%', '[NET]Transmit%', '[DSK]Read%', '[DSK]Write%', '[CPU]User%', '[CPU]Nice%', '[CPU]Sys%', '[CPU]Wait%', '[CPU]Irq%', '[CPU]Soft%', '[CPU]Steal%', '[CPU]Idle%', '[CPU]Guest%', '[CPU]GuestN%', '[CPU]Intrpt/sec', '[CPU]Ctx/sec', '[CPU]Proc/sec', '[CPU]ProcQue', '[CPU]ProcRun', '[CPU]L-Avg1', '[CPU]L-Avg5', '[CPU]L-Avg15', '[CPU]RunTot', '[CPU]BlkTot', '[MEM]Tot', '[MEM]Used', '[MEM]Free', '[MEM]Shared', '[MEM]Buf', '[MEM]Cached', '[MEM]Slab', '[MEM]Map', '[MEM]Anon', '[MEM]Commit', '[MEM]Locked', '[MEM]SwapTot', '[MEM]SwapUsed', '[MEM]SwapFree', '[MEM]SwapIn', '[MEM]SwapOut', '[MEM]Dirty', '[MEM]Clean', '[MEM]Laundry', '[MEM]Inactive', '[MEM]PageIn', '[MEM]PageOut', '[MEM]PageFaults', '[MEM]PageMajFaults', '[MEM]HugeTotal', '[MEM]HugeFree', '[MEM]HugeRsvd', '[MEM]SUnreclaim', '[NET]RxPktTot', '[NET]TxPktTot', '[NET]RxKBTot', '[NET]TxKBTot', '[NET]RxCmpTot', '[NET]RxMltTot', '[NET]TxCmpTot', '[NET]RxErrsTot', '[NET]TxErrsTot', '[DSK]ReadTot', '[DSK]WriteTot', '[DSK]OpsTot', '[DSK]ReadKBTot', '[DSK]WriteKBTot', '[DSK]KbTot', '[DSK]ReadMrgTot', '[DSK]WriteMrgTot', '[DSK]MrgTot'.
