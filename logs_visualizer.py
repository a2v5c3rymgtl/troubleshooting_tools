#!/usr/local/bin/python3.7
import re
import sys
import os
import argparse
from typing import Dict, Any, Optional
from anytree import Node, RenderTree
from anytree.exporter import DotExporter
from uuid import uuid4
from config import GENERAL_MESSAGE_PATTERN, COMPLETE_MESSAGE_PATTERN, COMMENCE_MESSAGE_PATTERN
from config import SCOPE_NAME_GROUP, MESSAGE_LEVEL_GROUP
from dataclasses import dataclass, field
import colorama


colorama.init()


def is_valid_message(line: str) -> bool:
    return bool(re.match(GENERAL_MESSAGE_PATTERN, line))


def is_commence_message(line) -> bool:
    return bool(re.match(COMMENCE_MESSAGE_PATTERN, line))


def is_complete_message(line) -> bool:
    return bool(re.match(COMPLETE_MESSAGE_PATTERN, line))


def get_scope_name(line) -> str:
    return re.match(GENERAL_MESSAGE_PATTERN, line).group(SCOPE_NAME_GROUP)


def get_message_level(line) -> str:
    return re.match(GENERAL_MESSAGE_PATTERN, line).group(MESSAGE_LEVEL_GROUP)


@dataclass
class Context:
    node: Optional[Node]
    previous_context: Optional['Context']
    info: Dict[str, Any] = field(default_factory=dict)


class CallGraph:
    """
    TODO think up about the execution order and represent it something usefully and clearly
    TODO implement text render with collected_info data
    TODO implement image render with collected_info data
    TODO add colors in text render
    TODO add an animation creation functionality
    """

    def __init__(self, parent: Node = None):
        self.main_scope = Node(name='Start', parent=parent, call_id=None)
        self.collected_info = dict()
        self.context = Context(
            node=self.main_scope,
            previous_context=None
        )

    def commence(self, scope_name: str):
        self.context = Context(
            node=None,
            previous_context=self.context
        )
        node = Node(scope_name, self.context.previous_context.node, call_id=uuid4().hex, error=False,
                    warning=False)
        self.context.node = node
        self.collected_info[self.context.node.call_id] = dict()

    def complete(self):
        if self.context.info.get('error'):
            self.context.node.error = True
        if self.context.info.get('warning'):
            self.context.node.warning = True

        if self.context.previous_context is None:
            sys.stderr.write('main function has been completed and have not parents, log is incorrect\n')
            self.context = Context(
                node=Node(name='OWERFLOW CONTEXT',
                          parent=self.context.node,
                          call_id=uuid4().hex,
                          error=False,
                          warning=False),
                previous_context=None
            )
        else:
            self.context = self.context.previous_context

    def add_info(self, **info):
        self.context.info.update(info)

    def render_as_text(self):
        for pre, fill, node in RenderTree(self.main_scope):
            error_mark = ''
            warning_mark = ''
            if hasattr(node, 'error') and node.error:
                error_mark = '[ERROR]'
            if hasattr(node, 'warning') and node.warning:
                warning_mark = '[WARNING]'

            if error_mark:
                sys.stdout.write(f'{colorama.Fore.RED}{pre}{node.name} {error_mark} {warning_mark}\n')
            elif warning_mark:
                sys.stdout.write(f'{colorama.Fore.YELLOW}{pre}{node.name} {error_mark} {warning_mark}\n')
            else:
                sys.stdout.write(f'{colorama.Fore.CYAN}{pre}{node.name} {error_mark} {warning_mark}\n')

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
