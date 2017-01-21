#!/usr/bin/env python3

import sys, os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import argparse
from dazeus import DaZeus, Scope

def main():
    parser = argparse.ArgumentParser(description="Start the echo plugin")
    parser.add_argument(
        'address',
        type=str,
        help='Address of the DaZeus instance to connect to. Use either ' +
             '`unix:/path/to/file` or `tcp:host:port`.'
    )
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    with DaZeus(args.address, args.verbose) as dazeus:
        dazeus.subscribe_command("echo", lambda event, reply: reply(event['params'][4]))
        dazeus.listen()

if __name__ == '__main__':
    main()
