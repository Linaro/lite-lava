# Copyright (C) 2016 Linaro Limited
#
# Author: Tyler Baker <tyler.baker@linaro.org>
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

# from lava_common.utils import debian_filename_version
from lava_dispatcher.action import Pipeline, Action, JobError
from lava_dispatcher.logical import Boot, RetryAction
from lava_dispatcher.actions.boot import BootAction
from lava_dispatcher.connections.serial import ConnectDevice
# from lava_dispatcher.utils.shell import which
# from lava_dispatcher.utils.strings import substitute
from lava_dispatcher.power import ResetDevice
from lava_dispatcher.utils.udev import WaitDeviceBoardID
# from lava_common.exceptions import InfrastructureError

# import subprocess


class JLink(Boot):

    compatibility = 4  # FIXME: change this to 5 and update test cases

    def __init__(self, parent, parameters):
        super().__init__(parent)
        self.action = BootJLink()
        self.action.section = self.action_type
        self.action.job = self.job
        parent.add_action(self.action, parameters)

    @classmethod
    def accepts(cls, device, parameters):
        if "jlink" not in device["actions"]["boot"]["methods"]:
            return False, '"jlink" was not in the device configuration boot methods'
        if "method" not in parameters:
            return False, '"method" was not in parameters'
        if parameters["method"] != "jlink":
            return False, '"method" was not "jlink"'
        if "board_id" not in device:
            return False, '"board_id" is not in the device configuration'
        return True, "accepted"


class BootJLink(BootAction):

    name = "boot-jlink-image"
    description = "boot jlink image with retry"
    summary = "boot jlink image with retry"

    def populate(self, parameters):
        self.internal_pipeline = Pipeline(
            parent=self, job=self.job, parameters=parameters
        )
        self.internal_pipeline.add_action(BootJLinkRetry())


class BootJLinkRetry(RetryAction):

    name = "boot-jlink-image"
    description = "boot jlink image using the command line interface"
    summary = "boot jlink image"

    def populate(self, parameters):
        self.internal_pipeline = Pipeline(
            parent=self, job=self.job, parameters=parameters
        )
        if self.job.device.hard_reset_command:
            self.internal_pipeline.add_action(ResetDevice())
            self.internal_pipeline.add_action(
                WaitDeviceBoardID(self.job.device.get("board_id"))
            )
        self.internal_pipeline.add_action(FlashJLinkAction())
        self.internal_pipeline.add_action(ConnectDevice())


class FlashJLinkAction(Action):

    name = "flash-jlink"
    description = "flash jlink to boot the image"
    summary = "flash jlink to boot the image"

    @staticmethod
    def filename_version(binary):
        # if binary is not absolute, fail.
        msg = "Unable to retrieve version of %s" % binary
        ver_str = "TODO later - read version"
        # try:
        #     ver_str = (
        #         subprocess.check_output([binary, "-version"])
        #         .decode("utf-8", errors="replace")
        #     )
        #     self.logger.info('version = ', binary)
        #     if not ver_str:
        #         raise InfrastructureError(msg+" 1 "+binary)
        # except subprocess.CalledProcessError:
        #     raise InfrastructureError(msg+" 2 "+ver_str)
        return "%s, version %s" % (binary, ver_str)

    def __init__(self):
        super().__init__()
        self.base_command = []
        self.exec_list = []

    def validate(self):
        super().validate()
        boot = self.job.device["actions"]["boot"]["methods"]["jlink"]
        jlink_binary = boot["parameters"]["command"]
        load_address = boot["parameters"]["address"]
        # binary = which(jlink_binary)
        self.logger.info(self.filename_version(jlink_binary))
        # self.logger.info(self.run_command("pwd"))
        self.base_command = [jlink_binary]
        self.base_command.extend(boot["parameters"].get("options", []))
        if self.job.device["board_id"] == "0000000000":
            self.errors = "[JLink] board_id unset"
        substitutions = {}
        # self.base_command.extend(["--board", self.job.device["board_id"]])
        for action in self.get_namespace_keys("download-action"):
            jlink_full_command = []
            image_arg = self.get_namespace_data(
                action="download-action", label=action, key="image_arg"
            )
            action_arg = self.get_namespace_data(
                action="download-action", label=action, key="file"
            )
            binary_image = action_arg

            jlink_full_command.extend(self.base_command)

            lines = ['r']          # Reset and halt the target
            lines.append('h')      # Reset and halt the target
            lines.append('erase')  # Erase all flash sectors
            lines.append('sleep 500')

            # if image_arg:
            #     if not isinstance(image_arg, str):
            #         self.errors = "image_arg is not a string (try quoting it)"
            #         continue
            #     substitutions["{%s}" % action] = action_arg
            #     binary_image = substitute([image_arg]
            # else:
            #     binary_image = action_arg

            lines.append('loadfile {} 0x{:x}'.format(binary_image,
                         load_address))
            lines.append('verifybin {} 0x{:x}'.format(binary_image,
                         load_address))
            lines.append('r')   # Restart the CPU
            lines.append('qc')  # Close the connection and quit

            self.logger.info("JLink command file: \n" + ''.join(lines))

            fname = 'cmd.jlink'
            with open(fname, 'wb') as f:
                f.writelines(bytes(line + '\n', 'utf-8') for line in lines)
                f.close()

            self.exec_list.append(jlink_full_command)
        if not self.exec_list:
            self.errors = "No JLink command to execute"

    def run(self, connection, max_end_time):
        connection = self.get_namespace_data(
            action="shared", label="shared", key="connection", deepcopy=False
        )
        connection = super().run(connection, max_end_time)
        for jlink_command in self.exec_list:
            jlink = " ".join(jlink_command)
            self.logger.info("JLink command: %s", jlink)
            if not self.run_command(jlink.split(" ")):
                raise JobError("%s command failed" % (jlink.split(" ")))
        self.set_namespace_data(
            action="shared", label="shared", key="connection", value=connection
        )
        return connection
