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
from os import makedirs, environ, listdir, makedirs, walk, sep
from os.path import basename, isdir, isfile, join, exists, relpath, dirname, abspath
from pathlib import Path
import shutil
import glob

from SCons.Script import (ARGUMENTS, COMMAND_LINE_TARGETS, AlwaysBuild,
                          Builder, Default, DefaultEnvironment, Copy, Scanner)

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
    N64_AUDIOCONV="audioconv64",
    N64_MKSPRITE="mksprite",
    N64_DSO="n64dso",
    N64_DSOEXTERN="n64dso-extern",
    N64_DSOMSYM="n64dso-msym",
    N64_MKFONT="mkfont", # note: Only available in preview branch.
    N64_MKMODEL="mkmodel", # note: Only available in preview branch.

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

def process_directory(target, source, env):
    env.Depends(target, source)
    tgt_dir = abspath(str(target[0]))

    # Ensure target directory exists
    if exists(tgt_dir):
        shutil.rmtree(tgt_dir)
    makedirs(tgt_dir, exist_ok=True)

    # Retrieve custom conversion rules from platformio.ini
    conv_rules: str = env.GetProjectOption("custom_conversions", "")
    custom_conversions = {}
    if conv_rules:
        for line in conv_rules.strip().split("\n"):
            parts = [part.strip() for part in line.split(",", maxsplit=2)]
            if len(parts) == 3:
                command_template = parts[2].strip()
                if "$SOURCE" not in command_template:
                    command_template += " $SOURCE"
                custom_conversions[parts[0].lower()] = (parts[1].strip(), command_template)

    def process_file(src_file, tgt_dir):
        """ Process a single file based on conversion rules or copy if no rule applies. """
        file_name = basename(src_file)
        file_lower = file_name.lower()
        output_dir = tgt_dir
        makedirs(output_dir, exist_ok=True)

        if file_lower in custom_conversions:
            target_ext, command_template = custom_conversions[file_lower]
            tgt_file = join(output_dir, file_name[:file_name.rfind(".")] + target_ext)
            src_parent_dir = abspath(dirname(src_file))
            command = command_template.replace("$TARGETDIR", output_dir).replace("$TARGET", tgt_file).replace("$SOURCE", file_name)
            if "${N64_MKFONT}" in command:
                # the mkfont binary is special: it expects mksprite to be available at
                # $N64_INST/bin/mksprite
                # instead of patching the mkfont source code (which we can!), we just clone the env
                # and set the N64_INST variable to the right folder.
                # note that this only works because it doesn't access any compiler bins like mips64-elf-gcc
                mkfont_env = env.Clone()
                mkfont_env["ENV"]["N64_INST"] = platform.get_package_dir("tool-n64")
                mkfont_env.Execute(env.VerboseAction(
                    f"cd {src_parent_dir} && {command}",
                    f"(Font) Converting {src_file} to {tgt_file}"
                ))
                mkfont_env["ENV"]["N64_INST"] = platform.get_package_dir("toolchain-gccmips64")
            else:
                env.Execute(env.VerboseAction(
                    f"cd {src_parent_dir} && {command}",
                    f"Converting {src_file} to {tgt_file}"
                ))
        elif file_lower.endswith(".xm"):
            tgt_file = join(output_dir, file_name[:-3] + ".xm64")
            env.Execute(env.VerboseAction(f"${{N64_AUDIOCONV}} -o {tgt_file} {src_file}",
                                          f"Converting {src_file} to {tgt_file}"))
        elif file_lower.endswith(".ym"):
            tgt_file = join(output_dir, file_name[:-3] + ".ym64")
            env.Execute(env.VerboseAction(f"${{N64_AUDIOCONV}} -o {tgt_file} {src_file}",
                                          f"Converting {src_file} to {tgt_file}"))
        elif file_lower.endswith(".wav"):
            tgt_file = join(output_dir, file_name[:-4] + ".wav64")
            env.Execute(env.VerboseAction(f"${{N64_AUDIOCONV}} --wav-compress 3 -o {tgt_file} {src_file}",
                                          f"Converting {src_file} to {tgt_file}"))
        elif file_lower.endswith(".png"):
            tgt_file = join(output_dir, file_name[:-4] + ".sprite")
            env.Execute(env.VerboseAction(
                f"cd {dirname(src_file)} && ${{N64_MKSPRITE}} -o {output_dir} {file_name}",
                f"Converting {src_file} to {tgt_file}"
            ))
        else:
            tgt_file = join(output_dir, file_name)
            shutil.copy2(src_file, tgt_file)
            print(f"Copied: {src_file} -> {tgt_file}")
        return tgt_file

    # Process all source elements
    for s in source:
        s_path = str(s)
        if isfile(s_path):
            tgt = process_file(s_path, tgt_dir)
        elif isdir(s_path):
            for root, _, files in walk(s_path):
                for file in files:
                    tgt = process_file(join(root, file), tgt_dir)

    return None  # Must return None to indicate success in SCons

def build_custom_dsos(env):
    custom_dsos = str(env.GetProjectOption("custom_dsos", "")).strip()
    if not custom_dsos:
        return []

    dso_targets = []
    for line in custom_dsos.splitlines():
        output_file, sources = line.split(":", maxsplit=1)
        output_file = output_file.strip()
        sources = [src.strip() for src in sources.split()]

        # Define the build directory for object files
        obj_dir = join("$BUILD_DIR", "dsos", output_file.replace(".dso", ""))

        # Clone environment and configure DSO-specific flags
        dso_env = env.Clone()
        dso_env.Append(
            CCFLAGS=["-mno-gpopt", "-DN64_DSO"],
            CPPPATH=join("$PROJECT_DIR", "include"),
        )

        platform = env.PioPlatform()
        FRAMEWORK_DIR = platform.get_package_dir("framework-libdragon") or ""
        dso_env.Replace(
            LINK="mips64-elf-ld",
            LINKFLAGS=[
                "--emit-relocs",
                "--unresolved-symbols=ignore-all",
                "--nmagic",
                "-L",
                '"%s"' % FRAMEWORK_DIR,
                "-T", "dso.ld"
            ],
            LIBS=[],
            _LIBFLAGS="",
        )

        # Explicitly create object files in $BUILD_DIR
        object_files = []
        for src in sources:
            src_path = join("$PROJECT_DIR", src)
            obj_name = join(obj_dir, src.split("/")[-1] + ".o")  # Ensure unique object name
            obj_target = dso_env.Object(target=obj_name, source=src_path)
            object_files.append(obj_target)

        # Generate ELF file for the DSO
        dso_elf_target = dso_env.Program(
            target=join("$BUILD_DIR", output_file.replace(".dso", ".elf")),
            source=object_files,  # Use manually created object files
        )

        # Convert ELF to DSO
        dso_target = env.DsoBuilder(
            target=[join("$BUILD_DIR", output_file), join("$BUILD_DIR", output_file + ".sym")],
            source=dso_elf_target,
        )
        dso_targets.append(dso_target)

    return dso_targets

def dso_builder_action(target, source, env):
    dso_elf = str(source[0])  # The program ELF file
    dso_file = str(target[0])  # The output DSO file
    dso_sym = str(target[1]) # The corresponding sym file
    elf_dir = dirname(dso_elf)
    # Define the absolute path to the filesystem folder
    out_dir = join(env.subst("$BUILD_DIR"))

    # Ensure the filesystem folder exists
    if not exists(out_dir):
        makedirs(out_dir)

    actions = [
        env.VerboseAction(
            f"${{SIZETOOL}} -G {dso_elf}",
            f"Checking size of {dso_elf}"),
        # Generate the DSO file
        env.VerboseAction(
            f"cd {elf_dir} && ${{N64_DSO}} -o {out_dir} -c 1 {basename(dso_elf)}",
            f"Creating DSO {dso_file} from ELF {dso_elf}"),
        # Generate the .sym file
        env.VerboseAction(" ".join([
            "${N64SYM}",
            dso_elf,
            dso_sym
        ]), f"Generating sym file {dso_sym} from ELF {dso_elf}")
    ]

    # Execute all actions
    return env.Execute(actions)

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
        ElfToMSym=Builder(
            action=env.VerboseAction(" ".join([
                "${N64_DSOMSYM}",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".msym"
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
        ElfToZ64WithDFSAndMSYS=Builder(
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
                "8",
                "${SOURCES[2]}", # msym file
                "--align",
                "16",
                "${SOURCES[3]}" # dfs file (filesystem)
            ]), "Building $TARGET"),
            suffix=".z64"
        ),
        ConvertAssets=Builder(
            action=process_directory,
            source_factory=env.Entry, # Source should be a directory or file
            target_factory=env.Dir,  # Target should be a directory
        ),
        DataToDfs=Builder(
            action=env.VerboseAction(" ".join([
                '"$MKDFSTOOL"',
                "$TARGET",
                "$SOURCE"
            ]), "Building file system image from '$SOURCE' directory to $TARGET"),
            source_factory=env.Dir,
            suffix=".dfs"
        ),
        DsoBuilder=Builder(
            action=dso_builder_action,
        ),
        DsoExternsBuilder=Builder(
            action=env.VerboseAction(" ".join([
                "${N64_DSOEXTERN}",
                "-o",
                "$TARGET",
                "$SOURCES"
            ]), "Building DSO externals $TARGET"),
            suffix=".externs"
        ),
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

    # Filesystem handling
    data_dir = join(env.subst("$PROJECT_DIR"), env.subst("$PROJECT_DATA_DIR"))
    filesystem_dir = join("$BUILD_DIR", "filesystem")
    custom_dsos = build_custom_dsos(env)

    data_dir_exists = exists(data_dir) and isdir(data_dir) and len(listdir(data_dir)) != 0
    has_custom_dsos = bool(custom_dsos)

    if data_dir_exists or has_custom_dsos:
        asset_sources = []

        if data_dir_exists:
            asset_sources.append(data_dir)

        if has_custom_dsos:
            # add the .dso as well as .dso.sym files to the filesytem, but flatten array
            asset_sources.extend([x for pair in custom_dsos for x in pair])

        target_converted_assets = env.ConvertAssets(filesystem_dir, asset_sources)

        target_dfs = env.DataToDfs(join("$BUILD_DIR", "${N64_FS_IMAGE_NAME}"), target_converted_assets)

        # Track changes and rebuild filesystem if any asset file changes, as-needed. 
        # TODO: This doesn't work at all. It's worked-around by AlwaysBuild() below.
        # The target_converted_assets / env.ConvertAssets() build doesn't properly know about
        # what output files it will produce, it might need an emitter function to properly track
        # its targets and dependencies.
        AlwaysBuild(target_converted_assets)
        AlwaysBuild(target_dfs)

        if has_custom_dsos:
            # the .externs file is only built from the .dso files, not .dso.sym files
            target_dso_externs = env.DsoExternsBuilder(
                join("${BUILD_DIR}", "${PROGNAME}.externs"), 
                [x for pair in custom_dsos for x in pair if str(x).endswith(".dso")]
            )
            env.Append(LINKFLAGS=["-Wl,-T", str(target_dso_externs[0])])
            # .externs file must exist before elf is linked!! (because it's a linker script)
            env.Requires(target_elf, target_dso_externs)
            target_msym = env.ElfToMSym(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
            target_z64 = env.ElfToZ64WithDFSAndMSYS(
                join("$BUILD_DIR", "${PROGNAME}"),
                [target_stripped_compressed_elf, target_sym, target_msym, target_dfs]
            )
        else:
            target_z64 = env.ElfToZ64WithDFS(
                join("$BUILD_DIR", "${PROGNAME}"),
                [target_stripped_compressed_elf, target_sym, target_dfs]
            )
    else:
        target_z64 = env.ElfToZ64(
            join("$BUILD_DIR", "${PROGNAME}"),
            [target_stripped_compressed_elf, target_sym]
        )

    env.Depends(target_z64, "checkprogsize")
    AlwaysBuild(target_z64)

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
if upload_protocol == "sc64":
    env.Replace(
        UPLOADER="sc64deployer",
        UPLOADERFLAGS=[
            "--reboot"
        ],
        UPLOADCMD='$UPLOADER upload $UPLOADERFLAGS "$SOURCE"'
    )
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]
# custom upload tool
elif upload_protocol == "custom":
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

else:
    sys.stderr.write("Warning! Unknown upload protocol %s\n" % upload_protocol)

AlwaysBuild(env.Alias("upload", upload_source, upload_actions))

# additional project tasks
if upload_protocol == "sc64":
    sc64_tool = join(platform.get_package_dir("tool-summercart64") or "", "sc64deployer")
    env.AddPlatformTarget(
        name="sc64_reset",
        dependencies=None,
        actions=[
            env.VerboseAction("\"%s\" reset" % (sc64_tool), "Resetting SummerCart64")
        ],
        title="Reset SummerCart64"
    )
    env.AddPlatformTarget(
        name="sc64_sd_upload",
        dependencies=upload_source,
        actions=[
            env.VerboseAction("\"%s\" sd upload \"%s\"" % (sc64_tool, str(target_z64[0])), "Uploading to SD (SummerCart64)")
        ],
        title="Upload to SD (SC64)"
    )

#
# Default targets
#

Default([target_buildprog, target_size])