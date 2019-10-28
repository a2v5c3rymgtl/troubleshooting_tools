#!/usr/local/bin/python3.7
import re
import sys
import os
import argparse
from anytree import Node as BaseNode
from anytree import RenderTree
from anytree.exporter import DotExporter
from uuid import uuid4
from config import GENERAL_MESSAGE_PATTERN, COMPLETE_MESSAGE_PATTERN, COMMENCE_MESSAGE_PATTERN
from config import MESSAGE_LEVEL_GROUP, CALL_TIME, NEW_SCOPE_NAME
import colorama

colorama.init()


def is_valid_message(line: str) -> bool:
    return bool(re.match(GENERAL_MESSAGE_PATTERN, line))


def is_commence_message(line) -> bool:
    return bool(re.match(COMMENCE_MESSAGE_PATTERN, line))


def is_complete_message(line) -> bool:
    return bool(re.match(COMPLETE_MESSAGE_PATTERN, line))


def get_scope_name(line) -> str:
    return re.match(COMMENCE_MESSAGE_PATTERN, line).group(NEW_SCOPE_NAME)


def get_message_level(line) -> str:
    return re.match(GENERAL_MESSAGE_PATTERN, line).group(MESSAGE_LEVEL_GROUP)


def get_message_time(line) -> str:
    return re.match(GENERAL_MESSAGE_PATTERN, line).group(CALL_TIME)


class Node(BaseNode):
    def __init__(self, name, parent=None, children=None, error=False, warning=False, **kwargs):
        self.info = dict()
        self.call_id = uuid4()
        self.error = error
        self.warning = warning
        super(Node, self).__init__(name, parent, children, **kwargs)


class CallGraph:
    """
    TODO think up about the execution order and represent it something usefully and clearly
    TODO implement image render with collected info data
    TODO add an animation creation functionality
    """

    def __init__(self, parent: Node = None):
        self.node = parent
        self.main_scope = None
        self._balance = 0

    def commence(self, scope_name: str, call_time: int):
        self._balance += 1
        self.node = Node(name=f'{scope_name} ({call_time})', parent=self.node)
        if self.main_scope is None:
            self.main_scope = self.node

    def complete(self):
        self._balance -= 1
        if self.node.info.get('error'):
            self.node.error = True
        if self.node.info.get('warning'):
            self.node.warning = True

        if self._balance < 0:
            sys.stderr.write('main function has been completed and have not parents, log is incorrect\n')
            self.node = Node(name='OVERFLOW CONTEXT', parent=self.node)
        elif self._balance == 0 and self.node.parent is None:
            self.node = self.main_scope
        else:
            self.node = self.node.parent

    def add_info(self, **info):
        self.node.info.update(info)

    def _pprint(self, node, pre):
        error_mark = ''
        warning_mark = ''

        if node.error:
            error_mark = '[ERROR]'
        if node.warning:
            warning_mark = '[WARNING]'

        if node.error:
            sys.stdout.write(f'{colorama.Fore.RED}{pre}{node.name} {error_mark} {warning_mark}\n')
        elif node.warning:
            sys.stdout.write(f'{colorama.Fore.YELLOW}{pre}{node.name} {error_mark} {warning_mark}\n')
        else:
            sys.stdout.write(f'{colorama.Fore.CYAN}{pre}{node.name} {error_mark} {warning_mark}\n')

    def render_as_text(self):
        for pre, _, node in RenderTree(self.main_scope):
            self._pprint(node, pre)

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
        for line in self.content.split('\n'):
            self._analyse(line)

    def _analyse(self, line: str):
        if not is_valid_message(line):
            return
        if is_commence_message(line):
            call_time = get_message_time(line)
            scope_name = get_scope_name(line)
            self.call_graph.commence(scope_name, call_time)
        elif is_complete_message(line):
            self.call_graph.complete()

        msg_lvl = get_message_level(line)
        if msg_lvl == 'error':
            self.call_graph.add_info(error=True)
        if msg_lvl == 'warning':
            self.call_graph.add_info(warning=True)


def main(logfile: str, export_file_name: str=None, parent: Node=None, to_stdout: bool = True) -> CallGraph:
    if not os.path.exists(logfile):
        sys.stderr.write(f'{os.path.abspath(logfile)} is not exist\n')
        sys.exit(-1)

    reader = LogsReader(open(logfile).read(), parent=parent)

    try:
        reader.analyse()
    except ValueError as error:
        error_message = error.args[0]
        sys.stderr.write(f'{error_message}\n')
        sys.stderr.write(f'log file: {logfile}\n{open(logfile).read()}')
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
