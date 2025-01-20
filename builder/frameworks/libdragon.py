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
from pathlib import Path
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

env.Append(
    ASFLAGS=env.get("CCFLAGS", [])[:],
)

env.Append(
    CCFLAGS=[
        "-g3", # all debug symbols by default (needed for symbol generation)
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
        # This makes it such that GDB can't find the file path again
        # unless we do set substitute-path libdragon FRAMEWORK_DIR as GDB cmd,
        # which we do in platform.py
        # This means that the binary itself will still have the short paths.
        '-ffile-prefix-map="%s"=libdragon' % FRAMEWORK_DIR 
    ],

    CFLAGS=[
        "-std=gnu99"
    ],

    CXXFLAGS=[
        "-std=gnu++17",
    ],

    CPPPATH=[
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

# Automatically find all libdragon source files, except the Audio library, which is special.
libdragon_src_dir = Path(os.path.join(FRAMEWORK_DIR, "src"))
libdragon_srcs = [
        str(file.relative_to(libdragon_src_dir))  for file in libdragon_src_dir.rglob('*') 
        if file.suffix in {'.c', '.cpp', '.S'} and 
        'audio' not in (file.relative_to(libdragon_src_dir).parts[:1]) and 
        file.name != 'debugcpp.cpp']

# we musn't build libopus.c, omongst other files. it weirdly #include c files. Only build these for now.
audio_lib = [
  "audio/mixer.c", "audio/samplebuffer.c", "audio/rsp_mixer.c", "audio/wav64.c",
  "audio/wav64_vadpcm.c", "audio/xm64.c", "audio/libxm/play.c", "audio/libxm/context.c",
  "audio/libxm/load.c", "audio/ym64.c", "audio/ay8910.c"
]

# RSP assembly sources have to be built differently, filter them out at this stage
def is_rsp_file(file: str) -> bool:
    return Path(file).name.startswith("rsp") and file.endswith(".S")
rsp_srcs = [x for x in libdragon_srcs if is_rsp_file(x)]
libdragon_srcs = [x for x in libdragon_srcs if not is_rsp_file(x)]
libdragon_srcs += audio_lib

libs.append(
   env.BuildLibrary(
        os.path.join("$BUILD_DIR", "FrameworkLibdragon"),
        os.path.join(FRAMEWORK_DIR, "src"),
        "-<*> " + " ".join(["+<%s>" % src for src in libdragon_srcs])
))


libs.append(
    env.BuildLibrary(
        os.path.join("$BUILD_DIR", "FrameworkLibdragonSys"),
        os.path.join(FRAMEWORK_DIR, "src"),
        "-<*> +<system.c>"
    ))


def post_process_rsp_file(source, target, env):
    src_file = source[0] # the .S file
    src_filename = os.path.splitext(os.path.basename(str(source[0])))[0]
    target_file = target[0] # the .o file
    target_elf = os.path.splitext(str(target_file))[0] + ".elf"
    target_map = os.path.splitext(str(target_file))[0] + ".map"
    target_textsection = os.path.splitext(str(target_file))[0] + ".text"
    target_datasection = os.path.splitext(str(target_file))[0] + ".data"
    symprefix = str(os.path.splitext(str(target_file))[0]).replace(".", "_").replace("/", "_").replace("\\", "_")
    # print("POST PROCESS RSP for SRC " + str(src_file) + " TARGET " + str(target_file))
    actions = [
        env.VerboseAction(" ".join([
            "$CC",
            "-march=mips1",
            "-mabi=32",
            "-Wa,--fatal-warnings",
            "-nostartfiles",
            "-I",
            '"%s"' % os.path.join(FRAMEWORK_DIR, "src"),
            "-I",
            '"%s"' % os.path.join(FRAMEWORK_DIR, "include"),
            "-L",
            os.path.join(FRAMEWORK_DIR),
            "-Wl,-Trsp.ld",
            "-Wl,--gc-sections",
            '-Wl,-Map="%s"' % target_map,
            "-o",
            '"%s"' % target_elf,
            '"%s"' % str(src_file)
        ]), "Relinking RSP ELF " + target_elf),
        # make a copy of the original stripped elf because the compress is in-place
        #Copy(target_elf, target_file),
        env.VerboseAction(" ".join([
            "$OBJCOPY",
            "-O",
            "binary",
            "-j",
            ".text",
            '"%s"' % target_elf,
            '"%s"' % (target_textsection + ".bin")
        ]), "Generating text segment " + (target_textsection + ".bin")),
        env.VerboseAction(" ".join([
            "$OBJCOPY",
            "-O",
            "binary",
            "-j",
            ".data",
            '"%s"' % target_elf,
            '"%s"' % (target_datasection + ".bin")
        ]), "Generating data segment " + (target_datasection + ".bin")),
        env.VerboseAction(" ".join([
            "$OBJCOPY",
            "-I",
            "binary",
            "-O",
            "elf32-bigmips",
            "-B",
            "mips4300",
            "--redefine-sym",
            "_binary_%s_text_bin_start=%s_text_start" % (symprefix, src_filename),
            "--redefine-sym",
            "_binary_%s_text_bin_end=%s_text_end" % (symprefix, src_filename),
            "--redefine-sym",
            "_binary_%s_text_bin_size=%s_text_size" % (symprefix, src_filename),
            "--set-section-alignment",
            ".data=8",
            "--rename-section",
            ".text=.data",
            '"%s"' % (target_textsection + ".bin"),
            '"%s"' % (target_textsection + ".o")
        ]), "Generating textsection object " + target_textsection + ".o"),
        env.VerboseAction(" ".join([
            "$OBJCOPY",
            "-I",
            "binary",
            "-O",
            "elf32-bigmips",
            "-B",
            "mips4300",
            "--redefine-sym",
            "_binary_%s_data_bin_start=%s_data_start" % (symprefix, src_filename),
            "--redefine-sym",
            "_binary_%s_data_bin_end=%s_data_end" % (symprefix, src_filename),
            "--redefine-sym",
            "_binary_%s_data_bin_size=%s_data_size" % (symprefix, src_filename),
            "--set-section-alignment",
            ".data=8",
            "--rename-section",
            ".text=.data",
            '"%s"' % (target_datasection + ".bin"),
            '"%s"' % (target_datasection + ".o")
        ]), "Generating datasection object " + target_datasection + ".o"),
        # final relink to object file
        env.VerboseAction(" ".join([
            "mips64-elf-ld",
            "-relocatable",
            '"%s"' % (target_textsection + ".o"),
            '"%s"' % (target_datasection + ".o"),
            "-o",
            '"%s"' % str(target_file)
        ]), "Relinking object file " + str(target_file)),
    ]    
    env.Execute(actions)

def build_rsp_file(env, node):
    global rsp_env
    print("Building: " + str(node))
    env.AddPostAction(node, post_process_rsp_file)
    return rsp_env.Object(node)

# Somehow only works for files in the user's project directory
env.AddBuildMiddleware(build_rsp_file, "rsp*.S")

rsp_env = env.Clone()
rsp_env.Replace(
    AS="mips64-elf-gcc",
    LINK="mips64-elf-gcc",
    ASFLAGS=[
        "-march=mips1",
        "-mabi=32",
        "-Wa,--fatal-warnings",
    ]
)

# get RSP sources into the build system. Sadly we must rebuild the ".o" entirely because
# we need to link it as a fully fledged ELF file, then extract .data and .text sections out of it,
# and then repackage it, with changed symbol names, into an elf / object file that will finally be linked.
rsp_env.BuildSources(
     os.path.join("$BUILD_DIR", "FrameworkLibdragonRSP"),
     os.path.join(FRAMEWORK_DIR, "src"),
     "-<*> " + " ".join(["+<%s>" % src for src in rsp_srcs])
)
for src in rsp_srcs:
    # actual build logic happens in the post processing. The regular "build" step is just enough to not crash.
    env.AddPostAction("$BUILD_DIR/FrameworkLibdragonRSP/%s.o" % src.replace(".S", ""), post_process_rsp_file)

env.Prepend(LIBS=libs)