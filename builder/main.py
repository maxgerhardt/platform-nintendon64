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

import sys
from platform import system
from os import makedirs, environ, listdir
from os.path import basename, isdir, join, exists
from pathlib import Path

from SCons.Script import (ARGUMENTS, COMMAND_LINE_TARGETS, AlwaysBuild,
                          Builder, Default, DefaultEnvironment, Copy)

from platformio.public import list_serial_ports

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

env.Replace(
    AR="mips64-elf-gcc-ar",
    AS="mips64-elf-as",
    CC="mips64-elf-gcc",
    CXX="mips64-elf-g++",
    LINK="mips64-elf-g++",
    GDB="gdb-multiarch",
    # not yet available, see https://github.com/DragonMinded/libdragon/issues/668
    #GDB="mips64-elf-gdb",
    OBJCOPY="mips64-elf-objcopy",
    RANLIB="mips64-elf-gcc-ranlib",
    SIZETOOL="mips64-elf-size",
    STRIP="mips64-elf-strip",
    N64SYM="n64sym", # these comes from tool-n64
    N64ELFCOMPRESS="n64elfcompress",
    N64TOOL="n64tool",
    MKDFSTOOL="mkdfs", # digital file system
    N64_FS_IMAGE_NAME="fs",
    PROJECT_DATA_DIR="assets", # folder for unconverted files

    ARFLAGS=["rc"],

    SIZEPROGREGEXP=r"^(?:\.text|\.data|\.rodata|\.text.align|\.ARM.exidx)\s+(\d+).*",
    SIZEDATAREGEXP=r"^(?:\.data|\.bss|\.sbss|\.sdata|\.lit8|\.lit4|\.noinit)\s+(\d+).*",
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD='$SIZETOOL -B -d $SOURCES',

    PROGSUFFIX=".elf"
)

# N64Tool needs this to locate mips64-elf-readelf and similiar tools
environ["N64_INST"] = platform.get_package_dir("toolchain-gccmips64")

# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

env.Append(
    BUILDERS=dict(
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "binary",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".bin"
        ),
        ElfToSym=Builder(
            action=env.VerboseAction(" ".join([
                "$N64SYM",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".elf.sym"
        ),
        ElfToStrippedElf=Builder(
            action=env.VerboseAction(" ".join([
                "$STRIP",
                "-s",
                "-o",
                "$TARGET",
                "$SOURCES"
                ]), "Building $TARGET"),
            suffix=".elf.stripped"
        ),
        StrippedElfToCompressedElf=Builder(
            action=[
                # make a copy of the original stripped elf because the compress is in-place
                Copy('${TARGET}', '${SOURCE}'),
                env.VerboseAction(" ".join([
                "$N64ELFCOMPRESS",
                #"-o",
                #"${BUILD_DIR}",
                "-c",
                "1", # compression level
                "$TARGET"
                ]), "Building $TARGET"),
            ],
            suffix=".elf.stripped.compressed"
        ),
        ElfToZ64=Builder(
            action=env.VerboseAction(" ".join([
                "$N64TOOL",
                "--title",
                '"%s"' % "Controller Test",
                "--toc",
                "--output",
                "$TARGET",
                "--align",
                "256",
                "${SOURCES[0]}", # stripped + compressed elf file
                "--align",
                "8",
                "${SOURCES[1]}", # symbol file
                "--align",
                "8"
            ]), "Building $TARGET"),
            suffix=".z64"
        ),
        ElfToZ64WithDFS=Builder(
            action=env.VerboseAction(" ".join([
                "$N64TOOL",
                "--title",
                '"%s"' % "Controller Test",
                "--toc",
                "--output",
                "$TARGET",
                "--align",
                "256",
                "${SOURCES[0]}", # stripped + compressed elf file
                "--align",
                "8",
                "${SOURCES[1]}", # symbol file
                "--align",
                "16",
                "${SOURCES[2]}" # dfs file (filesystem)
            ]), "Building $TARGET"),
            suffix=".z64"
        ),
        DataToDfs=Builder(
            action=env.VerboseAction(" ".join([
                '"$MKDFSTOOL"',
                "$TARGET",
                "$SOURCE"
            ]), "Building file system image from '$SOURCE' directory to $TARGET"),
            source_factory=env.Dir,
            suffix=".dfs"
        )
    )
)

if not env.get("PIOFRAMEWORK"):
    env.SConscript("frameworks/_bare.py")

#
# Target: Build executable and linkable firmware
#

frameworks = env.get("PIOFRAMEWORK", [])

target_elf = None
if "nobuild" in COMMAND_LINE_TARGETS:
    target_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_z64 = join("$BUILD_DIR", "${PROGNAME}.z64")
    target_dfs = join("$BUILD_DIR", "${N64_FS_IMAGE_NAME}.dfs")
else:
    target_elf = env.BuildProgram()
    target_sym = env.ElfToSym(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    target_stripped_elf = env.ElfToStrippedElf(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    target_stripped_compressed_elf = env.StrippedElfToCompressedElf(join("$BUILD_DIR", "${PROGNAME}"), target_stripped_elf)
    # filesystem
    data_dir = join(env.subst("$PROJECT_DIR"), env.subst("$PROJECT_DATA_DIR"))
    # do we have files to build at all?
    if exists(data_dir) and isdir(data_dir) and len(listdir(data_dir)) != 0:
        converted_assets = []
        asset_files = env.Glob(join("${PROJECT_DIR}", "${PROJECT_DATA_DIR}", "**/*"))
        target_dfs = env.DataToDfs(join("$BUILD_DIR", "${N64_FS_IMAGE_NAME}"), [data_dir])
        env.Requires(target_dfs, asset_files)
        target_z64 = env.ElfToZ64WithDFS(join("$BUILD_DIR", "${PROGNAME}"), [target_stripped_compressed_elf, target_sym, target_dfs])
    else:
        target_z64 = env.ElfToZ64(join("$BUILD_DIR", "${PROGNAME}"), [target_stripped_compressed_elf, target_sym])

    env.Depends(target_z64, "checkprogsize")

AlwaysBuild(env.Alias("nobuild", target_z64))
target_buildprog = env.Alias("buildprog", target_z64, target_z64)

#
# Target: Print binary size
#

target_size = env.Alias(
    "size", target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"))
AlwaysBuild(target_size)

#
# Target: Upload by default .z64 file
#

upload_protocol = env.subst("$UPLOAD_PROTOCOL")
debug_tools = board.get("debug.tools", {})
upload_source = target_z64
upload_actions = []

if upload_protocol == "ares":
    env.Replace(
        UPLOADER="ares",
        UPLOADERFLAGS=[
        ],
        UPLOADCMD='$UPLOADER $UPLOADERFLAGS "$SOURCE"'
    )
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

# custom upload tool
elif upload_protocol == "custom":
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

else:
    sys.stderr.write("Warning! Unknown upload protocol %s\n" % upload_protocol)

AlwaysBuild(env.Alias("upload", upload_source, upload_actions))

#
# Default targets
#

Default([target_buildprog, target_size])