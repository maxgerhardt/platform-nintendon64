# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import platform

from platformio.public import PlatformBase
from platformio import util
import sys

class Nintendon64Platform(PlatformBase):

    def is_embedded(self):
        return True

    def configure_default_packages(self, variables, targets):
        board = variables.get("board")
        board_config = self.board_config(board)
        # Use the same string identifier as seen in "pio system info" and registry
        sys_type = util.get_systype()
        frameworks = variables.get("pioframework", [])
        return super().configure_default_packages(variables, targets)

    def get_boards(self, id_=None):
        result = super().get_boards(id_)
        if not result:
            return result
        if id_:
            return self._add_default_debug_tools(result)
        else:
            for key in result:
                result[key] = self._add_default_debug_tools(result[key])
        return result

    def _add_default_debug_tools(self, board):
        debug = board.manifest.get("debug", {})
        upload_protocols = board.manifest.get("upload", {}).get(
            "protocols", [])
        if "tools" not in debug:
            debug["tools"] = {}

        reset_cmds = [
            "define pio_reset_halt_target",
            "end",
            "define pio_reset_run_target",
            "end",
        ]
        init_cmds = [
            "set mem inaccessible-by-default off",
            # ares automatically reports arch = mips:4000
            #"set arch mips:4300",
            "set remotetimeout unlimited",
            "target remote $DEBUG_PORT",
            "$INIT_BREAK",
            # don't load the executable into the emulator because it's already started with the ROM
            #"$LOAD_CMDS",
            "info functions", # wtf. it needs that so that symbols are located correctly to their source files
        ]
        libdragon_path = self.get_package_dir("framework-libdragon") or ""
        if libdragon_path != "":
            init_cmds.insert(0, 'set substitute-path libdragon "%s"' % libdragon_path.replace("\\","/"))

        for link in ["ares"]:
            if link not in upload_protocols or link in debug["tools"]:
                continue
            if link == "ares":
                debug["tools"][link] = {
                    "server": {
                        "package": "tool-ares",
                        "arguments": [
                            "C:/Users/Max/temp/pio-n64/ctest/.pio/build/n64/firmware.z64"
                            #DefaultEnvironment().subst("${BUILD_DIR}/${PROGNAME}.z64")
                       ],
                        "executable": "ares"
                    },
                    "onboard": link in debug.get("onboard_tools", []),
                    "init_cmds": reset_cmds + init_cmds,
                    #"load_cmds": "preload", # make it "upload" the file via Ares, but this actually starts the GDB server, too
                    "port": "localhost:9123"
                }
            debug["tools"][link]["onboard"] = link in debug.get("onboard_tools", [])
            debug["tools"][link]["default"] = link in debug.get("default_tools", [])

        board.manifest["debug"] = debug
        return board

    # nothing to do, we can't properly processs the "speed" option since we're using an emulator
    def configure_debug_session(self, debug_config):
        return
 