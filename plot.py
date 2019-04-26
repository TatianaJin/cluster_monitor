#! /usr/bin/env python3

import json
import os.path
from pandas import concat
from pandas import read_csv

from numpy import arange
from os import system as os_sys
from sys import argv
from sys import stderr
from sys import stdout


# Arguments
from argparse import ArgumentParser
def parse_cmd(argv=None):
    parser = ArgumentParser(
        description='Plot CPU & network utilization from collectl logs.')
    parser.add_argument('-g','--generate-conf',dest='gen_conf',const='plot.json',nargs='?',
                        help='Generate the plot config json file. Default plot.json')
    parser.add_argument('input', type=str, nargs='+', help='The input data directory or file.')
    parser.add_argument('-o','--output',type=str,dest='output',help='The output directory.')
    parser.add_argument('-c','--conf',dest='conf',action='store',nargs='?',const='plot.json', help='The config file for plotting')
    parser.add_argument('-r','--raw',action='store_true',dest='raw_input',
                        help='Read raw collectl logs. Write preprocessed data to the dat dir under input dir.')
    parser.add_argument('--no-plot', dest='to_plot', action='store_false', help='Preprocess only, no plotting.')
    parser.add_argument('--skip_header',dest='skip_header',type=int,metavar='n',
                        help='The number of lines to skip in the beginning. This overwrites values in conf.')
    return parser.parse_args(argv)


class Conf:
    """ configurations for plotting """

    # default values
    def __init__(self, args = None):
        self.linewidth = 1
        self.max_net_rx_kb = 120832.0
        self.max_net_tx_kb = 120832.0
        self.max_disk_r_kb = 200000.0
        self.max_disk_w_kb = 200000.0
        self.scale_cpu = 1
        self.plot_average = 1
        self.mode = "util"

        # Default plot templates
        self.template = {
            "util": {
                "figsize": (8, 6),
                "columns": ['[CPU]User%', '[CPU]Totl%', '[MEM]Used%', '[NET]Receive%', '[NET]Transmit%', '[DSK]Read%', '[DSK]Write%'],
                "xlabel": 'Time(s)',
                "ylabel": 'Utilization %',
                "yticks": list(range(0, 101, 10))
            },
            "io": {
                "figsize": (8, 6),
                "columns": ['[NET]RxKBTot', '[NET]TxKBTot', '[DSK]ReadKBTot', '[DSK]WriteKBTot'],
                "xlabel": 'Time(s)',
                "ylabel": 'KB'
            }
        }

        self.skip_header = 0
        self.skip_last = None
        self.interval = 1

        if args is not None:
            self.get_conf(args)

    def set_attr(self, key, value):
        setattr(self, key, value)

    def get_conf(self, args):
        self.output = None
        self.xlim = None
        self.ylim = None
        # Load plot conf
        if args.conf is not None:
            with open(args.conf, 'r') as f:
                custom_conf = json.load(f)
                for k, v in custom_conf.items():
                    if v is not None:
                        self.set_attr(k, v)


        self.input = args.input
        self.output = args.output if args.output is not None else self.output
        if self.output is None:
            self.output = os.path.dirname(os.path.abspath(args.input[0])) + "/figs"
        # print("Outputs are put in {0}".format(self.output))
        self.skip_header = args.skip_header if args.skip_header is not None else self.skip_header
        assert(self.xlim is None or len(self.xlim) is 2)
        assert(self.ylim is None or len(self.ylim) is 2)

        # Retrieve input files
        self.in_files = []
        for input in self.input:
            if os.path.isdir(input):
                self.in_files.extend([
                    os.path.join(input, f) for f in os.listdir(input)
                    if os.path.isfile(os.path.join(input, f))
                ])
            elif os.path.isfile(input):
                self.in_files.append(input)
            else:
                stderr.write("Input path %s does not exist\n" % input)
        if len(self.in_files) is 0:
            exit(0)

    def generate_conf(self, conf_file):
        with open(conf_file, 'w') as f:
            json.dump(vars(self), f, indent=2, sort_keys=True)
        print("Generated config file %s" % conf_file)

    # For logging/debug
    def show_conf(self):
        print("Configuration:")
        json.dump(vars(self), stdout, sort_keys=True)
        stdout.write('\n')


def preprocess(in_files, raw_input):
    preprocessed = []
    cmd = ""
    for in_file in in_files:
        out_file = os.path.basename(in_file).split('.')[0]
        cmd = "{3} echo 'Save preprocessed file {2} to {4}' && collectl -p {0} -P -oU -scdmn --sep 9 > {1}/{2} &".format(in_file, raw_input, out_file, cmd, os.path.relpath(raw_input))
        preprocessed.append(os.path.join(raw_input, out_file))

    os_sys("mkdir -p {0}".format(raw_input))
    cmd = "{0} wait".format(cmd)
    os_sys(cmd)
    return preprocessed


def calculate_percent_util(data, conf):
    data['[CPU]Totl%'] = data['[CPU]Totl%'] * conf.scale_cpu
    data['[MEM]Used%'] = (data['[MEM]Used'] - data['[MEM]Buf'] - data['[MEM]Cached']) / (data['[MEM]Tot'] / 100)
    data['[NET]Receive%'] = data['[NET]RxKBTot'] / (conf.max_net_rx_kb / 100)
    data['[NET]Transmit%'] = data['[NET]TxKBTot'] / (conf.max_net_tx_kb / 100)
    data['[DSK]Read%'] = data['[DSK]ReadKBTot'] / (conf.max_disk_r_kb / 100)
    data['[DSK]Write%'] = data['[DSK]WriteKBTot'] / (conf.max_disk_w_kb / 100)


# No X11
from matplotlib import use as pltUse
pltUse('Agg')
from matplotlib import pyplot as plt

class Painter:
    def __init__(self, conf):
        self.conf = conf
        self.columns = ['Time', '[CPU]User%', '[CPU]Nice%', '[CPU]Sys%', '[CPU]Wait%', '[CPU]Irq%', '[CPU]Soft%', '[CPU]Steal%', '[CPU]Idle%', '[CPU]Totl%', '[CPU]Guest%', '[CPU]GuestN%', '[CPU]Intrpt/sec', '[CPU]Ctx/sec', '[CPU]Proc/sec', '[CPU]ProcQue', '[CPU]ProcRun', '[CPU]L-Avg1', '[CPU]L-Avg5', '[CPU]L-Avg15', '[CPU]RunTot', '[CPU]BlkTot', '[MEM]Tot', '[MEM]Used', '[MEM]Free', '[MEM]Shared', '[MEM]Buf', '[MEM]Cached', '[MEM]Slab', '[MEM]Map', '[MEM]Anon', '[MEM]Commit', '[MEM]Locked', '[MEM]SwapTot', '[MEM]SwapUsed', '[MEM]SwapFree', '[MEM]SwapIn', '[MEM]SwapOut', '[MEM]Dirty', '[MEM]Clean', '[MEM]Laundry', '[MEM]Inactive', '[MEM]PageIn', '[MEM]PageOut', '[MEM]PageFaults', '[MEM]PageMajFaults', '[MEM]HugeTotal', '[MEM]HugeFree', '[MEM]HugeRsvd', '[MEM]SUnreclaim', '[NET]RxPktTot', '[NET]TxPktTot', '[NET]RxKBTot', '[NET]TxKBTot', '[NET]RxCmpTot', '[NET]RxMltTot', '[NET]TxCmpTot', '[NET]RxErrsTot', '[NET]TxErrsTot', '[DSK]ReadTot', '[DSK]WriteTot', '[DSK]OpsTot', '[DSK]ReadKBTot', '[DSK]WriteKBTot', '[DSK]KbTot', '[DSK]ReadMrgTot', '[DSK]WriteMrgTot', '[DSK]MrgTot']
        self.plot_conf = self.conf.template[self.conf.mode]
        if "xlabel" not in self.plot_conf:
            self.plot_conf["xlabel"] = "X"
        if "ylabel" not in self.plot_conf:
            self.plot_conf["ylabel"] = "Y"
        if "figsize" not in self.plot_conf:
            self.plot_conf["figsize"] = None

    def plot_all(self):
        if len(self.conf.in_files) is 0:
            return
        with open(self.conf.in_files[0]) as cur_f:
            self.columns = cur_f.readline().strip()[1:].split('\t')
        for in_file in self.conf.in_files:
            # load data
            data = read_csv(in_file, sep="\t", comment='#', names=self.columns)
            # prepare data
            if self.conf.mode is not "io":
                calculate_percent_util(data, self.conf)
            # plot
            output_file = os.path.join(self.conf.output, os.path.splitext(os.path.basename(in_file))[0] + '.png')
            last_point = len(data) if self.conf.skip_last is None else self.conf.skip_last
            if self.conf.plot_average is not 1:
                self.plot(data[self.conf.skip_header:last_point].groupby(arange(len(data))//self.conf.plot_average).mean()[self.plot_conf["columns"]], output_file)
            else:
                self.plot(data[self.conf.skip_header:last_point][self.plot_conf["columns"]], output_file)

    def plot_average(self):
        if len(self.conf.in_files) is 0:
            return
        with open(self.conf.in_files[0]) as cur_f:
            self.columns = cur_f.readline().strip()[1:].split('\t')
        data = read_csv(self.conf.in_files[0], sep="\t", comment='#', names=self.columns)
        for in_file in self.conf.in_files[1:]:
            # load data
            data = concat([data,read_csv(in_file, sep="\t", comment='#', names=self.columns)])
        data = data.groupby(level=0).mean()
        # prepare data
        if self.conf.mode is not "io":
            calculate_percent_util(data, self.conf)
        # plot
        output_file = os.path.join(self.conf.output, 'average.png')
        last_point = len(data) if self.conf.skip_last is None else self.conf.skip_last
        self.plot(data[self.conf.skip_header:last_point][self.plot_conf["columns"]], output_file)

    def plot(self, df, output_file):
        fig, ax = plt.subplots(figsize=self.plot_conf["figsize"])
        ax.set_xlabel(self.plot_conf["xlabel"], fontsize=18)
        ax.set_ylabel(self.plot_conf["ylabel"], fontsize=18)
        if "yticks" in self.plot_conf:
            ax.set_yticks(self.plot_conf["yticks"])
        plt.tick_params(labelsize=16)
        if self.conf.xlim != None:
            ax.set_xlim(self.conf.xlim)
        if self.conf.ylim != None:
            ax.set_ylim(self.conf.ylim)
        if self.conf.interval is not 1:
            df['Time(s)'] = arange(0, round(len(df) * self.conf.interval,2), self.conf.interval)
            df.plot(x='Time(s)', linewidth=self.conf.linewidth, ax=ax,
                    #color=['#edf8b1', '#7fcdbb', '#2c7fb8'],
                    color='brg',
                    #style=['-','--','-.']
                    )
        else:
            df.plot(linewidth=self.conf.linewidth, ax=ax)
        lgd = plt.legend(bbox_to_anchor=(1, 1), loc=1, borderaxespad=0.1, prop={'size': 18})
        plt.savefig(output_file, bbox_extra_artists=(lgd, ), bbox_inches='tight')
        print("Saved fig {0}".format(output_file))
        plt.close()


def main(args):
    conf = Conf(args)

    if args.raw_input:
        conf.in_files = preprocess(conf.in_files, os.path.dirname(os.path.abspath(args.input[0])) + "/dat")

    if args.to_plot is False:
        return

    # Create output dir in case it does not exist
    os_sys('mkdir -p %s' % conf.output)

    Painter(conf).plot_all()
    Painter(conf).plot_average()


if __name__ == "__main__":
    if '-g' in argv:
        parser = ArgumentParser()
        parser.add_argument('-g','--generate-conf',dest='gen_conf',const='plot.json',nargs='?',
                            help='Generate the plot config json file. Default plot.json')
        Conf().generate_conf(parser.parse_args(argv[1:]).gen_conf)
        exit(0)
    args = parse_cmd(argv[1:])
    main(args)
