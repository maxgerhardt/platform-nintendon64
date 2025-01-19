# Copyright 2024-present Maximilian Gerhardt <maximilian.gerhardt@rub.de>
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

import os, re, sys
from SCons.Script import DefaultEnvironment, Builder, AlwaysBuild

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()
chip = board.get("build.cpu")

# Load baremetal settings
env.SConscript("_bare.py")

FRAMEWORK_DIR = platform.get_package_dir("framework-libdragon")
assert os.path.isdir(FRAMEWORK_DIR)

flatten_cppdefines = env.Flatten(env['CPPDEFINES'])

# update progsize expression to also check for bootloader.
env.Replace(
    SIZEPROGREGEXP=r"^(?:\.boot2|\.text|\.data|\.rodata|\.text.align)\s+(\d+).*"
)

env.Append(
    ASFLAGS=env.get("CCFLAGS", [])[:],
)

env.Append(
    CCFLAGS=[
        "-g", # debug symbols by default (needed for symbol generation)
        "-g3",
        "-ggdb3",
        "-ffast-math",
        "-ftrapping-math",
        "-fno-associative-math",
        "-Wall",
        "-Werror",
        "-Wno-error=deprecated-declarations",
        "-fdiagnostics-color=always",
        "-Wno-error=unused-variable",
        "-Wno-error=unused-but-set-variable",
        "-Wno-error=unused-function",
        "-Wno-error=unused-parameter",
        "-Wno-error=unused-but-set-parameter",
        "-Wno-error=unused-label",
        "-Wno-error=unused-local-typedefs",
        "-Wno-error=unused-const-variable",
        '-ffile-prefix-map="%s"=libdragon' % FRAMEWORK_DIR 
    ],

    CFLAGS=[
        "-std=gnu99"
    ],

    CXXFLAGS=[
        "-std=gnu++17",
    ],

    CPPPATH=[
        # ToDo fill in libdragon paths
        os.path.join(FRAMEWORK_DIR, "include"),
        os.path.join(FRAMEWORK_DIR, "src"),
    ],

    LINKFLAGS=[
        "-Wl,--wrap",
        "-Wl,__do_global_ctors",
        "-Wl,--no-warn-rwx-segments",
        '-Wl,-Map="%s"' % os.path.join("${BUILD_DIR}", "${PROGNAME}.map")
    ],
)

env.Replace(
    LIBS=[
        "c", "m"
    ]
)

# if no custom linker script is provided, we use the default one
if not board.get("build.ldscript", ""):
    env.Replace(LDSCRIPT_PATH=os.path.join(FRAMEWORK_DIR, "n64.ld"))

libs = []

# libs.append(
#     env.BuildLibrary(
#         os.path.join("$BUILD_DIR", "FrameworkLibdragon"),
#         os.path.join(FRAMEWORK_DIR, "src")))


# # Add bootloader file (boot2.o)
# # Only build the needed .S file, exclude all others via src_filter.
# env.BuildSources(
#     os.path.join("$BUILD_DIR", "FrameworkArduinoBootloader"),
#     os.path.join(FRAMEWORK_DIR, "boot2", chip),
#     "-<*> +<%s>" % bootloader_src_file,
# )

env.Prepend(LIBS=libs)