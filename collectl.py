#! /usr/bin/env python

import os
import sys
import json

from os.path import isfile

from argparse import ArgumentParser

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

def clear_logs(worker_host, worker_path):
    os.system("ssh %s '[ -e %s ] && rm -r %s'" % (worker_host, worker_path, worker_path))
    sys.stdout.write("Cleared logs on %s.\n" % worker_host)

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

def start_on_worker(worker_host, worker_path, is_stop, interval = 1):
    check_existing_collectl_cmd = 'ssh %s "cat collectl.pid 2> /dev/null"' % (worker_host)
    existing_pid = os.popen(check_existing_collectl_cmd).read().strip()

    if is_stop:
        if existing_pid == "":
            sys.stdout.write("Collectl is not running on %s\n" % worker_host)
            return

        # Stop collectl
        os.system('ssh %s "kill %s && rm collectl.pid"' % (worker_host, existing_pid))

        sys.stdout.write("Collectl on %s stopped.\n" % worker_host)
    else:
        # Check whether there's already a running Worker
        if existing_pid != "":
            sys.stdout.write("Collectl on %s already started (PID: %s)\n" % (worker_host, existing_pid))
            return

        # Create the output directory if it's not there
        os.system('ssh %s "mkdir -p %s"' % (worker_host, worker_path))

        # Start collectl
        os.system('ssh {0} "collectl -scdmn -i {1} -f {2}/ 2>/dev/null & echo \$! > collectl.pid && wait \$!" &'.format(
            worker_host,
            interval,
            worker_path
        ))

        sys.stdout.write("Collectl started on %s.\n" % worker_host)

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
        for worker_host in worker_hosts:
            start_on_worker(worker_host, args.output, False, args.interval)
    else:
        empty = True
        # Stop
        if args.stop:
            empty = False
            for worker_host in worker_hosts:
                start_on_worker(worker_host, args.output, True)
        # Collect
        if args.collect:
            empty = False
            sys.stdout.write("To collect to %s.\n" % args.collect)
            for worker_host in worker_hosts:
                collect_logs(worker_host, args.output, args.collect)
        # Clear
        if args.clear:
            empty = False
            for worker_host in worker_hosts:
                clear_logs(worker_host, args.output)
        if empty:
            get_parser().print_help()
