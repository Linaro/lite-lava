# Copyright (C) 2012 Linaro Limited
#
# Author: Andy Doan <andy.doan@linaro.org>
#
# This file is part of LAVA Dispatcher.
#
# LAVA Dispatcher is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# LAVA Dispatcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along
# with this program; if not, see <http://www.gnu.org/licenses>.

import contextlib
import logging
import tempfile
import json

from lava_dispatcher.utils import rmtree

from lava_dispatcher.lava_test_shell import (
    _result_to_dir,
    _result_from_dir,
)


class BaseSignalHandler(object):

    def __init__(self, testdef_obj):
        self.testdef_obj = testdef_obj

    def start(self):
        pass

    def end(self):
        pass

    def starttc(self, test_case_id):
        pass

    def endtc(self, test_case_id):
        pass

    def custom_signal(self, signame, params):
        pass

    def postprocess_test_run(self, test_run):
        pass


class SignalHandler(BaseSignalHandler):

    def __init__(self, testdef_obj):
        BaseSignalHandler.__init__(self, testdef_obj)
        self._case_data = {}
        self._cur_case_id = None
        self._cur_case_data = None

    def starttc(self, test_case_id):
        if self._cur_case_data:
            logging.warning(
                "unexpected cur_case_data %s", self._cur_case_data)
        self._cur_case_id = test_case_id
        data = None
        try:
            data = self.start_testcase(test_case_id)
        except:
            logging.exception("start_testcase failed for %s", test_case_id)
        self._cur_case_data = self._case_data[test_case_id] = data

    def endtc(self, test_case_id):
        if self._cur_case_id != test_case_id:
            logging.warning(
                "stoptc for %s received but expecting %s",
                test_case_id, self._cur_case_id)
        else:
            try:
                self.end_testcase(test_case_id, self._cur_case_data)
            except:
                logging.exception(
                    "stop_testcase failed for %s", test_case_id)
        self._cur_case_data = None

    def postprocess_test_run(self, test_run):
        for test_result in test_run['test_results']:
            tc_id = test_result.get('test_case_id')
            if not tc_id:
                continue
            if tc_id not in self._case_data:
                continue
            data = self._case_data[tc_id]
            try:
                self.postprocess_test_result(test_result, data)
            except:
                logging.exception("postprocess_test_result failed for %s", tc_id)

    @contextlib.contextmanager
    def _result_as_dir(self, test_result):
        scratch_dir = self.testdef_obj.context.client.target_device.scratch_dir
        rdir = tempfile.mkdtemp(dir=scratch_dir)
        try:
            tcid = test_result['test_case_id']
            _result_to_dir(test_result, rdir)
            yield rdir
            test_result.clear()
            test_result.update(_result_from_dir(rdir, tcid))
        finally:
            rmtree(rdir)

    def start_testcase(self, test_case_id):
        return {}

    def end_testcase(self, test_case_id, data):
        pass

    def postprocess_test_result(self, test_result, case_data):
        pass


class SignalDirector(object):

    def __init__(self, client, testdefs_by_uuid):
        self.client = client
        self.testdefs_by_uuid = testdefs_by_uuid
        self._test_run_data = []
        self._cur_handler = None
        self.context = None
        self.connection = None

    def signal(self, name, params, context=None):
        self.context = context
        handler = getattr(self, '_on_' + name, None)
        if not handler and self._cur_handler:
            handler = self._cur_handler.custom_signal
            params = [name] + list(params)
        if handler:
            try:
                handler(*params)
            except:
                logging.exception("handling signal %s failed", name)

    def setConnection(self, connection):
        self.connection = connection

    def _on_STARTRUN(self, test_run_id, uuid):
        self._cur_handler = None
        testdef_obj = self.testdefs_by_uuid.get(uuid)
        if testdef_obj:
            self._cur_handler = testdef_obj.handler
        if self._cur_handler:
            self._cur_handler.start()

    def _on_ENDRUN(self, test_run_id, uuid):
        if self._cur_handler:
            self._cur_handler.end()

    def _on_STARTTC(self, test_case_id):
        if self._cur_handler:
            self._cur_handler.starttc(test_case_id)

    def _on_ENDTC(self, test_case_id):
        if self._cur_handler:
            self._cur_handler.endtc(test_case_id)

    def _on_SEND(self, *args):
        arg_length = len(args)
        if arg_length == 1:
            msg = {"request": "lava_send", "messageID": args[0], "message": None}
        else:
            message_id = args[0]
            remainder = args[1:arg_length]
            logging.debug("%d key value pair(s) to be sent." % int(len(remainder)/2))
            data = {}
            for message in remainder:
                detail = str.split(message, "=")
                if len(detail) == 2:
                    data[detail[0]] = detail[1]
            msg = {"request": "lava_send", "messageID": message_id, "message": data}
        logging.debug("Handling signal <LAVA_SEND %s>" % msg)
        reply = self.context.transport(json.dumps(msg))
        logging.debug("Node transport replied with %s" % reply)

    def _on_SYNC(self, message_id):
        if not self.connection:
            logging.error("No connection available for on_SYNC")
            return
        logging.debug("Handling signal <LAVA_SYNC %s>" % message_id)
        msg={"request": "lava_sync", "messageID": message_id, "message": None}
        reply = self.context.transport(json.dumps(msg))
        logging.debug("Node transport replied with %s" % reply)
        ret = self.connection.sendline("<LAVA_SYNC_COMPLETE> %s" % json.dumps(reply))
        logging.debug("runner._connection.sendline wrote %d bytes" % ret)

    def _on_WAIT(self, message_id):
        if not self.connection:
            logging.error("No connection available for on_WAIT")
            return
        logging.debug("Handling signal <LAVA_WAIT %s>" % message_id)
        msg={"request": "lava_wait", "messageID": message_id, "message": None}
        reply = self.context.transport(json.dumps(msg))
        logging.debug("Node transport replied with %s" % reply)
        message_str = ""
        for key, value in reply[0].items():
            message_str += " %s=%s" % (key, value)
        self.connection.sendline("<LAVA_WAIT_COMPLETE%s>" % message_str)

    def _on_WAIT_ALL(self, message_id, role=None):
        if not self.connection:
            logging.error("No connection available for on_WAIT_ALL")
            return
        logging.debug("Handling signal <LAVA_WAIT_ALL %s>" % message_id)
        msg={"request": "lava_wait_all", "messageID": message_id, "role": role}
        reply = self.context.transport(json.dumps(msg))
        logging.debug("Node transport replied with %s" % reply)
        message_str = ""
        #FIXME:this function is Incomplete,we need get target info from reply
        for key, value in reply.items():
            message_str += " %s:%s=%s" % ("target", key, value)
        self.connection.sendline("<LAVA_WAIT_ALL_COMPLETE%s>" % message_str)

    def postprocess_bundle(self, bundle):
        for test_run in bundle['test_runs']:
            uuid = test_run['analyzer_assigned_uuid']
            testdef_obj = self.testdefs_by_uuid.get(uuid)
            if testdef_obj.handler:
                try:
                    testdef_obj.handler.postprocess_test_run(test_run)
                except:
                    logging.exception(
                        "postprocessing test run with uuid %s failed", uuid)

