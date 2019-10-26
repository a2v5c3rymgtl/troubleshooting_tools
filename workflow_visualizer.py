#!/usr/local/bin/python3.7
import logs_visualizer
import sys
from typing import List
from stat import S_ISREG, ST_MTIME, ST_MODE
from anytree import Node
import argparse
import os


def get_files_sorted_by_creation_time(dirpath: str) -> List[str]:
    entries = (os.path.join(dirpath, fn) for fn in os.listdir(dirpath))
    entries = ((os.stat(path), path) for path in entries)
    entries = ((stat[ST_MTIME], path)
               for stat, path in entries if S_ISREG(stat[ST_MODE]))
    return [path for _, path in sorted(entries)]


class WorkflowVisualizer:
    def __init__(self, directory: str, name: str):
        self.directory = directory

        if name is None:
            name = 'workflow'

        self.main = logs_visualizer.CallGraph()
        self.main.main_scope = Node(name=name, call_id=None)

    def analyse(self):
        for log_file in get_files_sorted_by_creation_time(self.directory):
            parent = Node(log_file, parent=self.main.main_scope, call_id=None)
            logs_visualizer.main(log_file, None, parent=parent, to_stdout=False)

    def render_as_text(self):
        return self.main.render_as_text()


def main(logs_dir: str, export_file_name: str, name: str) -> logs_visualizer.CallGraph:
    if not os.path.exists(logs_dir):
        sys.stderr.write(f'{os.path.abspath(logs_dir)} is not exist\n')
        sys.exit(-1)

    visualizer = WorkflowVisualizer(logs_dir, name)
    visualizer.analyse()

    try:
        visualizer.analyse()
    except ValueError as error:
        error_message = error.args[0]
        sys.stderr.write(f'{error_message}\n')
        sys.exit(-1)

    if export_file_name:
        try:
            open(export_file_name, 'wb').close()
            visualizer.main.render_as_picture(export_file_name)
        except Exception as e:
            message = e.args[1]
            sys.stderr.write(f'{message}\n')
            sys.stderr.write('change filename and try again\n')
            sys.exit(-1)
    else:
        visualizer.main.render_as_text()
    return visualizer.main


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Logs visualizer')
    parser.add_argument('logdir', help='path to logs directory for visualization', metavar='./logs')
    parser.add_argument('--name', help='name of workflow')
    parser.add_argument('--export', help='export call graph to image', metavar='output.jpg')
    args = parser.parse_args()
    main(args.logdir, args.export, args.name)
