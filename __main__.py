#!/usr/local/bin/python3.7
import argparse
import os
import logs_visualizer
import workflow_visualizer

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Troubleshooting tool')
    parser.add_argument('logs', help='log file or path to logs directory', metavar='./logs/some_procedure.log')
    parser.add_argument('--export', help='export call graph to image', metavar='output.jpg')
    parser.add_argument('--name', help='name of workflow')
    args = parser.parse_args()

    if os.path.isdir(args.logs):
        workflow_visualizer.main(args.logs, args.export, args.name)
    else:
        logs_visualizer.main(args.logs, args.export, to_stdout=not args.export)
