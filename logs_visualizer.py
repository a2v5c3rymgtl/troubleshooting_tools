#!/usr/local/bin/python3.7
from typing import Dict, Any
from anytree import Node, RenderTree
from anytree.exporter import DotExporter
from uuid import uuid4
from config import GENERAL_MESSAGE_PATTERN, COMPLETE_MESSAGE_PATTERN, COMMENCE_MESSAGE_PATTERN
from config import SCOPE_NAME_GROUP, MESSAGE_LEVEL_GROUP
import re
import sys
import os
import argparse


class CallGraph:
    """
    TODO think up about the execution order and represent it something usefully and clearly
    TODO implement text render with collected_info data
    TODO implement image render with collected_info data
    TODO add colors in text render
    TODO add an animation creation functionality
    """
    current_node: Node
    previous_scope: Node
    collected_info: Dict[str, Dict[str, Any]]
    current_call_id: str
    previous_call_id: str

    def __init__(self, parent: Node = None):
        self.main_scope = Node(name='Start', parent=parent)
        self.previous_scope = self.main_scope
        self.previous_call_id = None
        self.current_call_id = 'main'
        self.collected_info = dict()

    def commence(self, scope_name: str):
        self.previous_call_id = self.current_call_id
        self.current_call_id = uuid4().hex
        self.current_node = Node(scope_name, parent=self.previous_scope, call_id=self.current_call_id)
        self.previous_scope = self.current_node
        self.collected_info[self.current_call_id] = dict()

    def complete(self):
        if self.previous_scope is None:
            raise ValueError('main function has been completed and have not parents, log is incorrect')
        self.previous_scope = self.previous_scope.parent

    def add_info(self, **info):
        self.collected_info[self.current_call_id].update(info)

    def get_info(self, call_id: str, key: str) -> Any:
        return self.collected_info[call_id][key]

    def render_as_text(self):
        for pre, fill, node in RenderTree(self.main_scope):
            sys.stdout.write(f'{pre}{node.name}\n')

    def _get_node_attrs(self, node):
        has_error = self.get_info(node.call_id, 'error')
        has_warning = self.get_info(node.call_id, 'warning')
        return f'{node.name} {has_error} {has_warning} {node.call_id}'

    def render_as_picture(self, picture_name: str):
        DotExporter(self.main_scope).to_picture(picture_name)


class LogsReader:
    """
    TODO add parsing of XMLs and JSONs and validate it by user defined schemas
    """

    def __init__(self, content: str, parent=None):
        self.content = content
        self.call_graph = CallGraph(parent)

    def analyse(self):
        for line_no, line in enumerate(self.content.split('\n')):
            if not is_valid_message(line):
                continue

            if is_commence_message(line):
                self.call_graph.commence(get_scope_name(line))
                self.call_graph.add_info(error=False)
                self.call_graph.add_info(warning=False)
            elif is_complete_message(line):
                self.call_graph.complete()

            msg_lvl = get_message_level(line)

            if msg_lvl == 'error':
                self.call_graph.add_info(error=True)

            if msg_lvl == 'warning':
                self.call_graph.add_info(warning=True)


def main(logfile: str, export_file_name: str, parent=None, to_stdout: bool=True) -> CallGraph:
    if not os.path.exists(logfile):
        sys.stderr.write(f'{os.path.abspath(logfile)} is not exist\n')
        sys.exit(-1)

    reader = LogsReader(open(logfile).read(), parent=parent)

    try:
        reader.analyse()
    except ValueError as error:
        error_message = error.args[0]
        sys.stderr.write(f'{error_message}\n')
        sys.exit(-1)

    if export_file_name:
        try:
            open(export_file_name, 'wb').close()
            reader.call_graph.render_as_picture(export_file_name)
        except Exception as e:
            message = e.args[1]
            sys.stderr.write(f'{message}\n')
            sys.stderr.write('change filename and try again\n')
            sys.exit(-1)
    if to_stdout:
        reader.call_graph.render_as_text()
    return reader.call_graph


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Logs visualizer')
    parser.add_argument('logfile', help='one logfile for visualization', metavar='some_procedure.log')
    parser.add_argument('--export', help='export call graph to image', metavar='output.jpg')
    args = parser.parse_args()
    main(args.logfile, args.export, to_stdout=not args.export)
