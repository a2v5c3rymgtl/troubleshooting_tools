#!/usr/local/bin/python3.7
from typing import Dict, Any
from anytree import Node, RenderTree
from anytree.exporter import DotExporter
from uuid import uuid4
import re
import sys


class CallGraph:
    """
    TODO think up about execution order and represent it something usefully and clearly
    TODO implement text render with collected_info data
    TODO implement image render with collected_info data
    TODO add colors in text render
    """
    current_node: Node
    previous_scope: Node
    collected_info: Dict[str, Dict[str, Any]]
    current_call_id: str
    previous_call_id: str

    def __init__(self):
        self.main_scope = Node(name='main')
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
    TODO add user-defined regexp patterns

    """
    common_pattern = re.compile(
        "^\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}.\d{3}): \[((?:trivia|verbose|info|warning|error))\] "
        "'(.*)' (.*.cs) (\d{1,4}) .* \(Process id=(\d{1,9})\) \(Thread id=(\d{1,3})\)\]: (.*)")

    commence_pattern = re.compile(
        "^\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}.\d{3}): \[((?:trivia|verbose|info|warning|error))\] '(.*)' (.*.cs) "
        "(\d{1,4}) .* \(Process id=(\d{1,9})\) \(Thread id=(\d{1,3})\)\]: Commence: (.*)")

    complete_pattern = re.compile(
        "^\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}.\d{3}): \[((?:trivia|verbose|info|warning|error))\] '(.*)' (.*.cs) "
        "(\d{1,4}) .* \(Process id=(\d{1,9})\) \(Thread id=(\d{1,3})\)\]: Complete: (.*)"
    )

    def __init__(self, content: str):
        self.content = content
        self.call_graph = CallGraph()

    def analyse(self):
        for line_no, line in enumerate(self.content.split('\n')):
            if not self._is_valid_message(line):
                continue

            if self._is_commence_message(line):
                self.call_graph.commence(self._get_scope_name(line))
                self.call_graph.add_info(error=False)
                self.call_graph.add_info(warning=False)
            elif self._is_complete_message(line):
                self.call_graph.complete()

            msg_lvl = self._get_message_level(line)

            if msg_lvl == 'error':
                self.call_graph.add_info(error=True)

            if msg_lvl == 'warning':
                self.call_graph.add_info(warning=True)

    def _is_valid_message(self, line: str):
        return bool(re.match(self.common_pattern, line))

    def _is_commence_message(self, line):
        return bool(re.match(self.commence_pattern, line))

    def _is_complete_message(self, line):
        return bool(re.match(self.complete_pattern, line))

    def _get_scope_name(self, line):
        return re.match(self.common_pattern, line).group(4)

    def _get_message_level(self, line):
        return re.match(self.common_pattern, line).group(3)


if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Logs visualizer')
    parser.add_argument('logfile', help='one logfile for visualization', metavar='some_procedure.log')
    parser.add_argument('--export', help='export call graph to image', metavar='output.jpg')

    args = parser.parse_args()
    logfile = args.logfile

    if not os.path.exists(logfile):
        sys.stderr.write(f'{os.path.abspath(logfile)} is not exist\n')
        sys.exit(-1)

    export_file_name = args.export
    reader = LogsReader(open(logfile).read())

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
    else:
        reader.call_graph.render_as_text()
