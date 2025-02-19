"""
Copyright (c) Microsoft Corporation.
Licensed under the MIT license.
"""

import fire
import logging
import os
import datetime

from .cli import get_cli_version
import common.api as api
from common.apiclient import DEFAULT_POLL_WAIT_TIME, InvalidConfigurationException, NotEnoughArguments
from common.clustermanager import read_job_cluster_config

import common.resultsview as view
from .eventhandlers import ConsoleEventHandler
from .resultsvalidator import ExecutionResultsValidator
from .reportsman import ReportWriters
from . import reportsman as reports



def get_cli_header():
    header = 'Nutter Version {}\n'.format(get_cli_version())
    header += '+' * 50
    header += '\n'

    return header


class NutterCLI(object):

    def __init__(self, debug=False, log_to_file=False, version=False):
        self._logger = logging.getLogger('NutterCLI')
        self._handle_show_version(version)

        # CLI only logger so the output is not dictated
        # by the logging configuration of all the other components
        self._set_debugging(debug, log_to_file)
        self._print_cli_header()
        self._set_nutter(debug)
        super().__init__()

    def run(self, test_pattern, cluster_id=None,
            timeout=120, junit_report=False,
            tags_report=False, max_parallel_tests=1,
            recursive=False, poll_wait_time=DEFAULT_POLL_WAIT_TIME, notebook_params=None,
            cluster_conf_path: str = None, cluster_type: str = None, cluster_config: dict = None):
        try:
            if not bool(cluster_conf_path) and not bool(cluster_id) and not bool(cluster_config):
                raise NotEnoughArguments("cluster_conf_path or cluster_id or cluster_config must be provided")

            logging.debug(""" Running tests. test_pattern: {} cluster_id: {}  notebook_params: {} timeout: {}
                               junit_report: {} max_parallel_tests: {}
                               tags_report: {}  recursive:{} cluster_conf_path: {} cluster_type: {}
                               cluster_config: {}"""
                          .format(test_pattern, cluster_id, notebook_params, timeout,
                                  junit_report, max_parallel_tests,
                                  tags_report, recursive, cluster_conf_path, cluster_type, cluster_config))

            logging.debug("Executing test(s): {}".format(test_pattern))

            if cluster_config is None:
                if cluster_conf_path:
                    cluster_conf = read_job_cluster_config(cluster_conf_path, cluster_type)
                else:
                    cluster_conf = None
            else:
                cluster_conf = cluster_config

            if self._is_a_test_pattern(test_pattern):
                logging.debug('Executing pattern')
                results = self._nutter.run_tests(
                    pattern=test_pattern,
                    cluster_id=cluster_id,
                    cluster_conf=cluster_conf,
                    timeout=timeout,
                    max_parallel_tests=max_parallel_tests,
                    recursive=recursive,
                    poll_wait_time=poll_wait_time,
                    notebook_params=notebook_params
                )
                self._nutter.events_processor_wait()
                self._handle_results(results, junit_report, tags_report)
                return

            logging.debug('Executing single test')
            result = self._nutter.run_test(test_pattern, cluster_id,
                                           timeout, poll_wait_time)

            self._handle_results([result], junit_report, tags_report)

        except Exception as error:
            self._logger.fatal(error)
            exit(1)

    def list(self, path, recursive=False):
        try:
            logging.debug("Running tests. path: {}".format(path))
            results = self._nutter.list_tests(path, recursive)
            self._nutter.events_processor_wait()
            self._display_list_results(results)
        except Exception as error:
            self._logger.fatal(error)
            exit(1)

    def _handle_results(self, results, junit_report, tags_report):
        self._display_test_results(results)

        report_man = self._get_report_writer_manager(junit_report, tags_report)
        self._handle_reports(report_man, results)

        ExecutionResultsValidator().validate(results)

    def _get_report_writer_manager(self, junit_report, tags_report):
        writers = 0
        if junit_report:
            writers = ReportWriters.JUNIT
        if tags_report:
            writers = writers + ReportWriters.TAGS

        return reports.get_report_writer_manager(writers)

    def _handle_reports(self, report_manager, exec_results):
        if not report_manager.has_providers():
            logging.debug('No providers were registered.')
            return
        for provider in report_manager.providers_names():
            print('Writing {} report.'.format(provider))

        for exec_result in exec_results:
            t_result = api.to_testresults(
                exec_result.notebook_result.exit_output)
            if t_result is None:
                print('Warning:')
                print('\tThe output of {} is missing or the format is invalid.'.format(
                    exec_result.notebook_path))
                continue
            report_manager.add_result(exec_result.notebook_path, t_result)

        for file_name in report_manager.write():
            print('File {} written'.format(file_name))

    def _display_list_results(self, results):
        list_results_view = view.get_list_results_view(results)
        view.print_results_view(list_results_view)

    def _display_test_results(self, results):
        results_view = view.get_run_results_views(results)
        view.print_results_view(results_view)

    def _is_a_test_pattern(self, pattern):
        segments = pattern.split('/')
        if len(segments) > 0:
            search_pattern = segments[len(segments)-1]
            if api.TestNotebook._is_valid_test_name(search_pattern):
                return False
            return True
        logging.Fatal(
            """ Invalid argument.
                 The value must be the full path to the test or a pattern """)

    def _print_cli_header(self):
        print(get_cli_header())

    def _set_nutter(self, debug):
        try:
            event_handler = ConsoleEventHandler(debug)
            self._nutter = api.get_nutter(event_handler)
        except InvalidConfigurationException as ex:
            logging.debug(ex)
            self._print_config_error_and_exit()

    def _handle_show_version(self, version):
        if not version:
            return
        print(self._get_version_label())
        exit(0)

    def _get_version_label(self):
        version = get_cli_version()
        return 'Nutter Version {}'.format(version)

    def _print_config_error_and_exit(self):
        print(""" Invalid configuration.\n
                  DATABRICKS_HOST and DATABRICKS_TOKEN
                   environment variables are not set """)
        exit(1)

    def _set_debugging(self, debug, log_to_file):
        if debug:
            log_name = None
            if log_to_file:
                log_name = 'nutter-exec-{0:%Y.%m.%d.%H%M%S%f}.log'.format(
                    datetime.datetime.utcnow())
            logging.basicConfig(
                filename=log_name,
                format="%(asctime)s:%(levelname)s:%(message)s",
                level=logging.DEBUG)


def main():
    fire.Fire(NutterCLI)


if __name__ == '__main__':
    main()
