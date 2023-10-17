#!/usr/bin/env python
import subprocess
import json
import glob
import hashlib
import os
import sys

os.chdir(sys.path[0])

EVAL_PATH = '.main.ncl.json'
BUILD_DIR = 'build'
SUBCOMMAND = sys.argv[1]


def compute_hash_sig():
    h = hashlib.sha256()

    for filepath in glob.glob('ncl/**/*.ncl', recursive=True):
        with open(filepath, 'r') as f:
            h.update(f.read().encode('utf-8'))

    return h.hexdigest()


def save_evaluation(hash_sig):
    completed_proc = subprocess.run(
        ['nickel', 'export', '--format', 'json', '-f', 'ncl/fak/main.ncl'],
        capture_output=True,
        text=True,
    )

    if completed_proc.returncode != 0:
        print(completed_proc.stderr)
        sys.exit(1)
    
    raw_result = completed_proc.stdout
    result = json.loads(raw_result)
    result['__hash__'] = hash_sig

    with open(EVAL_PATH, 'w') as f:
        f.write(json.dumps(result, indent=2))
    
    return result


def load_evaluation(hash_sig):
    if not os.path.isfile(EVAL_PATH):
        return None
    
    with open(EVAL_PATH, 'r') as f:
        result = json.loads(f.read())

        if result['__hash__'] == hash_sig:
            return result
    
    return None


def evaluate_ncl():
    hash_sig = compute_hash_sig()
    result = load_evaluation(hash_sig)

    if result is None:
        result = save_evaluation(hash_sig)
    
    return result


def subcmd_query_ncl():
    result = evaluate_ncl()
    selector = sys.argv[2]

    for key in selector.split('.'):
        result = result[key]
    
    print(result, end='')


def meson_configure():
    if not os.path.isdir(BUILD_DIR):
        subprocess.run(['meson', 'setup', BUILD_DIR], check=True)

    print("Evaluating Nickel files...")
    result = evaluate_ncl()

    for key, value in result['meson_options'].items():
        subprocess.run(['meson', 'configure', f'-D{key}={value}'], check=True, cwd=BUILD_DIR)
    
    return result


def subcmd_compile():
    meson_configure()
    subprocess.run(['meson', 'compile'], check=True, cwd=BUILD_DIR)


# TODO: Implement better flashing experience
# - Wait for bootloader device connection
# - Automatically flash whatever side(s) needs to reflash
def subcmd_flash_central():
    meson_configure()
    subprocess.run(['meson', 'compile', 'flash_central'], check=True, cwd=BUILD_DIR)


def subcmd_flash_peripheral():
    result = meson_configure()

    if 'peripheral' not in result:
        print("Error: Can't flash peripheral. The keyboard is not a split.")
        sys.exit(1)

    subprocess.run(['meson', 'compile', 'flash_peripheral'], check=True, cwd=BUILD_DIR)

# TODO: Use argparse

if SUBCOMMAND == 'query_ncl':
    subcmd_query_ncl()
elif SUBCOMMAND == 'compile':
    subcmd_compile()
elif SUBCOMMAND in ['flash', 'flash_c', 'flash_central']:
    subcmd_flash_central()
elif SUBCOMMAND in ['flash_p', 'flash_peripheral']:
    subcmd_flash_peripheral()
else:
    print("Error: Unknown subcommand")
    sys.exit(1)
