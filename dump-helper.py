#!/usr/env python3
# -*- coding: utf-8 -*-

from operator import contains
import os
import sys
import subprocess
import argparse

def colorful_print(level, msg):
    if level == 'error':
        print(f"\033[31m{msg}\033[0m")
    elif level == 'warning':
        print(f"\033[33m{msg}\033[0m")
    elif level == 'info':
        print(f"\033[32m{msg}\033[0m")
    else:
        print(msg)
    
def print_separator(level, str = ''):
    len_str = len(str)
    if len_str > 0:
        total_hash = 80 - len_str - 2
        if total_hash < 2:
            total_hash = 2
        left_hash = total_hash // 2
        right_hash = total_hash - left_hash
        context = '#' * left_hash
        colorful_print(level, f"{context} {str} {'#' * right_hash}")
    else:
        colorful_print(level, '#' * 80)

def get_exec_postfix():
    if sys.platform == "win32":
        exec_postfix = ".exe"
    elif sys.platform == "linux":
        exec_postfix = ""
    elif sys.platform == "darwin":
        exec_postfix = ""
    else:
        colorful_print('error', f"# Unsupported platform: {sys.platform}")
        input("Press Enter to exit...")
        exit(1)
    return exec_postfix

def get_exec_dir():
    if sys.platform == "win32":
        exec_dir = "third-party/x86_64/win32"
    elif sys.platform == "linux":
        exec_dir = "third-party/x86_64/linux"
    elif sys.platform == "darwin":
        exec_dir = "third-party/x86_64/darwin"
    else:
        colorful_print('error', f"# Unsupported platform: {sys.platform}")
        input("Press Enter to exit...")
        exit(1)
    return exec_dir
    

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_dump_syms_path():
    dump_syms_path = get_resource_path(os.path.join(get_exec_dir(), f"dump_syms{get_exec_postfix()}"))
    if not os.path.exists(dump_syms_path):
        colorful_print('error', f"# ERROR: Tools [{dump_syms_path}] not exists!")
        input("Press Enter to exit...")
        exit(1)
    return dump_syms_path

def get_symbole_dir():
    symbol_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '.sym')
    if not os.path.exists(symbol_dir):
        os.makedirs(symbol_dir)
    return symbol_dir

def get_stackwalk_path():
    stackwalk_path = get_resource_path(os.path.join(get_exec_dir(), f"minidump-stackwalk{get_exec_postfix()}"))
    if not os.path.exists(stackwalk_path):
        colorful_print('error', f"# ERROR: Tools [{stackwalk_path}] not exists!")
        input("Press Enter to exit...")
        exit(1)
    return stackwalk_path

def dump_syms(so_path):
    if not os.path.exists(so_path):
        colorful_print('error', f"# ERROR: File [{so_path}] not exists!")
        exit(1)

    symbol_dir = get_symbole_dir()
    # dump symbols
    so_target_path = os.path.join(symbol_dir, os.path.basename(so_path))
    if not os.path.exists(so_target_path):
        os.makedirs(so_target_path)

    dump_syms_cmd = f"{get_dump_syms_path()} {so_path} > {so_target_path}.sym"
    
    subprocess.run(dump_syms_cmd, shell=True)

    # read id of symbols
    with open(f"{so_target_path}.sym", "r") as f:
        lines = f.readlines()
        if len(lines) < 2:
            colorful_print('error', "# Dump symbols failed")
            return
        id = lines[0].split()[3]
        colorful_print('debug', f"# Symbol id: {id}")

    # move symbols to symbols folder
    symbols_folder = os.path.join(symbol_dir, os.path.basename(so_path), id)
    if not os.path.exists(symbols_folder):
        os.makedirs(symbols_folder)

    target_sym_path = os.path.join(symbols_folder, os.path.basename(so_path) + ".sym")
    if os.path.exists(target_sym_path):
        colorful_print('warning', f"Symbols have already been parsed. Skipping regeneration. If you need to regenerate, please manually delete the following file and try again.\n{target_sym_path}")
        return

    os.rename(f"{so_target_path}.sym", target_sym_path)
    colorful_print('debug', f"# Symbols saved to {target_sym_path}")

def stack_walk(dump_path, generate_raw = False):
    if not os.path.exists(dump_path):
        colorful_print('error', f"# Dump file not exists: {dump_path}")
        return

    # check if stack walk already exists, skip or continue
    #if os.path.exists(dump_path + ".stack"):
    #    colorful_print('warning', "stack walk already exists! skip.")
    #    return

    # stack walk
    stack_walk_cmd = f"{get_stackwalk_path()} {dump_path} {get_symbole_dir()} > {dump_path}.stack"
    subprocess.run(stack_walk_cmd, shell=True)

    if generate_raw:
        stack_walk_cmd = f"{get_stackwalk_path()} {dump_path} {get_symbole_dir()} --dump > {dump_path}.raw"
        subprocess.run(stack_walk_cmd, shell=True)

    print_separator('info', 'Stack Brief')
    
    # read stack
    with open(f"{dump_path}.stack", "r") as f:
        lines = f.readlines()
        if len(lines) < 2:
            colorful_print('error', "# Stack walk failed!")
            return
        
        print_lines = 20

        # print 20 lines
        for line in lines:
            line = line.strip()
            if ".so" in line or ".lib" in line or "Thread" in line or "Crash" in line:
                # 原版格式中的文件名和行号距离太远。无法实现自动文件跳转
                line = line.replace(" : ", ":")
                print(line)
                print_lines -= 1
                if print_lines == 0:
                    break

    print_separator('info')

def main():

    print_separator('info', "Breakpad Dump Util (ToolFox.Net v20260327)")
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-close", action="store_true", help="Close automatically after processing")
    parser.add_argument("--raw", action="store_true", help="Generate .raw dump detail file")
    parser.add_argument("files", nargs="*", help="Files or directories to process")

    parsed_args = parser.parse_args()

    auto_close = parsed_args.auto_close
    raw = parsed_args.raw
    args = parsed_args.files

    if not args:
        # Wait user input library or dump file to process
        while True:
            file = input("# Please input library or dump file(one by one):")
            if file == "":
                break

            args.append(file)

    if len(args) == 0:
        colorful_print("error", "# No libraries or dump files input. Exit.")
        exit(1)

    # If put a directory, get all files in it.
    for dir_path in args:
        if os.path.isdir(dir_path):
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    args.append(os.path.join(root, file))

    # Parse libraries
    for so_path in args:
        # Fix param that endsWith space
        so_path = so_path.strip()
        if so_path.endswith(".so") or so_path.endswith(".dll") or so_path.endswith(".lib") or not '.' in so_path:
            colorful_print("debug", f"# Processing library symbols:\n# --> {so_path}")
            dump_syms(so_path)

    # Parse dump files
    for dump_path in args:
        # Fix param that endsWith space
        dump_path = dump_path.strip()
        if dump_path.endswith(".dmp") or dump_path.endswith(".minidump"):
            colorful_print("debug", f"# Processing dump files:\n# --> {dump_path}")
            stack_walk(dump_path, raw)

    # pause
    if not auto_close:
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
