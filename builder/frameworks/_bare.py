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

#
# Default flags for bare-metal programming (without any framework layers)
#

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()

env.Append(
    ASFLAGS=[
    ],
    ASPPFLAGS=[
        "-x", "assembler-with-cpp",
    ],

    # -Os needs some patches: https://github.com/DragonMinded/libdragon/pull/669
    CCFLAGS=[
        "-O2",  # optimize speed
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-falign-functions=32",
        "-Wall",
    ],

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions"
    ],

    CPPDEFINES=[
        ("F_CPU", "$BOARD_F_CPU")
    ],

    LINKFLAGS=[
        "-Wl,--gc-sections"#,--relax",
    ],

    LIBS=["c", "gcc", "m", "stdc++"]
)

if "BOARD" in env:
    env.Append(
        ASFLAGS=[
            "-march=%s" % env.BoardConfig().get("build.cpu"),
            "-mtune=%s" % env.BoardConfig().get("build.cpu")
        ],
        CCFLAGS=[
            "-march=%s" % env.BoardConfig().get("build.cpu"),
            "-mtune=%s" % env.BoardConfig().get("build.cpu")
        ],
        LINKFLAGS=[
            "-march=%s" % env.BoardConfig().get("build.cpu"),
            "-mtune=%s" % env.BoardConfig().get("build.cpu")
        ]
    )