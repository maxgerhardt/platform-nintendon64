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

# depending on whether we're using the preview version of libdragon or not, we need changed options
is_preview_branch = "libdragon-preview" in env.subst("$PIOFRAMEWORK")
if is_preview_branch:
    env.Append(
        CCFLAGS=[
            "-include",
            "ktls.h",
            "-ftrivial-auto-var-init=pattern"
        ],
        CPPPATH=[
            os.path.join(FRAMEWORK_DIR, "include", "newlib_overrides")
        ]
    )
    c_ver = "-std=gnu17"
else:
    c_ver = "-std=gnu99"

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
        c_ver
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
# We need to ignore audio/opus/* there.
libdragon_src_dir = Path(os.path.join(FRAMEWORK_DIR, "src"))
libdragon_srcs = [
        str(file.relative_to(libdragon_src_dir)) for file in libdragon_src_dir.rglob('*') 
        if file.suffix in {'.c', '.cpp', '.S'} and 
        not file.relative_to(libdragon_src_dir).parts[:2] == ('audio', 'opus') and 
        file.name != 'debugcpp.cpp']

# finally, we have to do a modification to build audio/libopus.c: Disable all warnings.
def build_with_no_warnings(env, node):
    return env.Object(
        node,
        CCFLAGS=env["CCFLAGS"] + ["-Wno-all", "-Wno-error"]
    )
env.AddBuildMiddleware(build_with_no_warnings, "**/audio/libopus.c")

# RSP assembly sources have to be built differently, filter them out at this stage
def is_rsp_file(file: str) -> bool:
    return Path(file).name.startswith("rsp") and file.endswith(".S")
rsp_srcs = [x for x in libdragon_srcs if is_rsp_file(x)]
libdragon_srcs = [x for x in libdragon_srcs if not is_rsp_file(x)]

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
    global is_preview_branch
    src_file = source[0] # the .S file
    src_filename = os.path.splitext(os.path.basename(str(source[0])))[0]
    target_file = target[0] # the .o file
    target_elf = os.path.splitext(str(target_file))[0] + ".elf"
    target_map = os.path.splitext(str(target_file))[0] + ".map"
    target_textsection = os.path.splitext(str(target_file))[0] + ".text"
    target_datasection = os.path.splitext(str(target_file))[0] + ".data"
    target_metasection = os.path.splitext(str(target_file))[0] + ".meta"
    symprefix = str(os.path.splitext(str(target_file))[0]).replace(".", "_").replace("/", "_").replace("\\", "_")
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
            '"%s"' % os.path.join(FRAMEWORK_DIR),
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
        ]), "Generating data segment " + (target_datasection + ".bin"))
    ]
    if is_preview_branch:
        # we additionally create the metasection
        def build_metasegment_and_fixup(source, target, env):
            # First, run the original verbose action
            output_file = target_metasection + ".bin"
            env.Execute(env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O", "binary",
                "-j", ".meta",
                '"%s"' % target_elf,
                '"%s"' % (target_metasection + ".bin"),
                "--set-section-flags", ".meta=alloc,load"
            ]), "Generating meta segment " + (target_metasection + ".bin")))

            # Then call the fixup_meta_data function
            if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                print(f"Fixing up empty file: {output_file}")
                with open(output_file, "wb") as f:
                    f.write(b"\x00")  # Write a single 0x00 byte

        actions.extend([
            env.VerboseAction(build_metasegment_and_fixup, "Generating and fixing up meta segment " + (target_metasection + ".bin")),
            env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-I",
                "binary",
                "-O",
                "elf32-bigmips",
                "-B",
                "mips4300",
                "--redefine-sym",
                "_binary_%s_meta_bin_start=%s_meta_start" % (symprefix, src_filename),
                "--redefine-sym",
                "_binary_%s_meta_bin_end=%s_meta_end" % (symprefix, src_filename),
                "--redefine-sym",
                "_binary_%s_meta_bin_size=%s_meta_size" % (symprefix, src_filename),
                "--set-section-alignment",
                ".data=8",
                "--rename-section",
                ".text=.data",
                '"%s"' % (target_metasection + ".bin"),
                '"%s"' % (target_metasection + ".o")
            ]), "Generating data segment " + (target_metasection + ".bin")),
        ])
    actions.extend([
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
            (('"%s"' % (target_metasection + ".o")) if is_preview_branch else ""),
            "-o",
            '"%s"' % str(target_file)
        ]), "Relinking object file " + str(target_file)),
    ])
    env.Execute(actions)

# Add a new builder. After many tries with post actions, this actually works.
env.Append(BUILDERS={'CustomRspBuilder': Builder(action=post_process_rsp_file, suffix=".o")})

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

def build_rsp_file(env, node):
    ret = rsp_env.CustomRspBuilder(node)
    return ret

# Somehow only works for files in the user's project directory
env.AddBuildMiddleware(build_rsp_file, "**/rsp*.S")

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