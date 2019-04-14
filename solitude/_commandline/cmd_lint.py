# Copyright (c) 2019, Solitude Developers
#
# This source code is licensed under the BSD-3-Clause license found in the
# COPYING file in the root directory of this source tree

import sys
from solitude import Factory
from solitude.common.errors import CLIError
from solitude.common.report import FileMessageReport
from solitude._commandline.text_util import open_write


def main():
    cfg = read_config_file(args.config)
    factory = Factory(cfg)
    linter = factory.create_linter()
    sources = factory.get_sourcelist()
    if args.report:
        lint_to_report(linter, args.report_template, args.report)
    else:
        lint_to_stderr(linter)


def lint_as_text(linter, output="-"):
    errors = False
    with open_write(output) as fp:
        for filename, output in linter.lint_iter(sources):
            for message in output:
                errors = True
                print(file_message_format(message), file=fp)
        if errors:
            raise CLIError("")


def lint_as_report(linter, report_template, output="-"):
    errors = False
    report = FileMessageReport(
        report_template,
        project=factory.get_project_name(),
        component="Linter")
    report.add_info("Timestamp", datetime.datetime.utcnow().isoformat())
    files_without_errors = []
    for filename, output in linter.lint_iter(sources):
        if len(output):
            errors = True
            report.add_file(filename, output)
        else:
            files_without_errors.append(filename)
    for filename in files_without_errors:
        report.add_file(filename, [])
    with open_write(output) as fp:
        report.dump(fp)
    if errors:
        raise CLIError("")
