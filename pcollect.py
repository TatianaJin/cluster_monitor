#! /usr/bin/env python3

import os
import sys
import json

from os.path import isfile
from argparse import ArgumentParser

# Select pssh & pscp command
pssh = ''
pscp = ''
if os.popen('which pssh').read().strip() != '':
    pssh = 'pssh'
    pscp = 'pscp'
elif os.popen('which parallel-ssh').read().strip() != '':
    pssh = 'parallel-ssh'
    pscp = 'parallel-scp'
else:
    sys.stderr.write("Cannot find command pssh or parallel-ssh.\n")
    exit(0)


def get_parser():
    parser = ArgumentParser(description='Collectl on a set of hosts')
    group = parser.add_mutually_exclusive_group()
    # group.add_argument('option',  action='store', nargs='+', help='Actions')
    group.add_argument('--start', dest='start', action='store_true', help='start collectl on the machines')
    group.add_argument('--stop', dest='stop', action='store_true', help='stop collectl on the machines')
    group.add_argument('--scc', dest='scc', action='store_true', help='stop collect clear')
    parser.add_argument('--clear', dest='clear', action='store_true', help='clear the logs on the machines')
    parser.add_argument('--collect', dest='collect', action='store', nargs='?', const='tmp', help='collect the logs on the machines to local')
    parser.add_argument('-o', '--output', dest='output', action='store', default='collectl', help='the path for collectl to log to on the machines. used when start/collect')
    parser.add_argument('-m', '--machine_file', dest='workers', action='store', metavar='workers', default='workers', help='json file storing the hostnames')
    parser.add_argument('-i', '--interval', dest='interval', action='store', metavar='second(s)', default=1, type=float, help='collectl interval')
    return parser


def start_on_workers(worker_hosts, output_dir, interval):

    # Check running collectl processes
    tmp_dir = './tmp_host'
    host_list = []
    host_opt = '-H ' + ' -H '.join(worker_hosts)
    check_pid_cmd = '{0} {1} -o {2} "cat collectl.pid 2> /dev/null"'.format(pssh, host_opt, tmp_dir)
    existing_pid = os.popen(check_pid_cmd).read().strip()

    for w in worker_hosts:
        pid = open(os.path.join(tmp_dir,w)).read().strip();
        if pid != "":
            sys.stderr.write("Collectl already running on {0} (PID: {1})\n".format(w, pid))
        else:
            host_list.append(w)
    os.system('rm {0} -r'.format(tmp_dir))
    
    # Launch collectl 
    if len(host_list) is 0:
        return
    host_opt = '-H ' + ' -H '.join(host_list)
    local_host_name = '\`hostname\`'

    start_collectl_cmd = 'stop() {{ {5} --scc; }}; trap stop INT; {0} -P {1} -t 0 "collectl -scdmn -i {2} -f {3}/ 2>/dev/null & echo \$! > collectl.pid && echo started collectl on {4}"'.format(
      pssh,
      host_opt,
      interval,
      output_dir,
      '\`hostname\`',
      __file__
    )

    os.system(start_collectl_cmd)

 
def stop_on_workers(worker_hosts, output_dir):
    host_opt = '-H ' + ' -H '.join(worker_hosts)
    stop_collectl_cmd = "{0} -P {1} 'pid=`cat collectl.pid 2>/dev/null` && kill $pid || echo Collectl is not running; rm -f collectl.pid' | grep -v SUCCESS | sort -V".format(pssh, host_opt)
    os.system(stop_collectl_cmd)


# TODO(tatiana): parallel version
def collect_logs(worker_host, worker_path, collect_path):
    # Check if the source dir exists
    check_existing_logs_cmd = 'ssh %s "if [ -d %s ]; then echo 1; fi"' % (worker_host, worker_path)
    if os.popen(check_existing_logs_cmd).read().strip() is not "1":
        sys.stdout.write("Directory %s does not exist on %s.\n" % (worker_path, worker_host))
        return

    # Create the collect directory if not existing
    # os.system("mkdir -p %s" % collect_path)

    # Collect files
    os.system("rsync -q -r %s:%s %s" % (worker_host, worker_path, collect_path))

    sys.stdout.write("Collected logs from %s.\n" % worker_host)


def clear_logs(worker_hosts, worker_path):
    host_opt = '-H ' + ' -H '.join(worker_hosts)
    os.system("{0} {1} '[ -e {2} ] && rm -r {2}'".format(pssh, host_opt, worker_path))
    sys.stdout.write("Cleared logs on %s.\n" % worker_host)


if __name__ == '__main__':
    args = get_parser().parse_args()

    if args.scc:
        args.stop = True
        args.clear = True
        if not args.collect:
            args.collect = 'tmp'

    # Read worker hosts
    if not isfile(args.workers):
        print("{0} file does not exit! Please give a worker file.".format(args.workers))
        exit(0)
    f = open(args.workers)
    lines = f.readlines()
    f.close()
    worker_hosts = set([worker_host.strip()for worker_host in lines])

    # Start
    if args.start:
        start_on_workers(worker_hosts, args.output, args.interval)
    else:
        empty = True
        # Stop
        if args.stop:
            empty = False
            stop_on_workers(worker_hosts, args.output)
        # Collect
        if args.collect:
            empty = False
            sys.stdout.write("To collect to %s.\n" % args.collect)
            for worker_host in worker_hosts:
                collect_logs(worker_host, args.output, args.collect)
        # Clear
        if args.clear:
            empty = False
            clear_logs(worker_hosts, args.output)
        if empty:
            get_parser().print_help()
