#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil


def should_remove_file(filename):
    return filename.endswith('.pyc') or filename.endswith('.pyo') or filename.endswith('.pyd')


def clear_cache(root_dir):
    removed_dirs = 0
    removed_files = 0

    for current_root, dirs, files in os.walk(root_dir, topdown=True):
        dirs_to_remove = [d for d in dirs if d == '__pycache__']
        for d in dirs_to_remove:
            full_path = os.path.join(current_root, d)
            try:
                shutil.rmtree(full_path)
                removed_dirs += 1
                print(f"[DIR]  removed: {full_path}")
            except Exception as e:
                print(f"[DIR]  failed:  {full_path} -> {e}")

        for f in files:
            if should_remove_file(f):
                full_path = os.path.join(current_root, f)
                try:
                    os.remove(full_path)
                    removed_files += 1
                    print(f"[FILE] removed: {full_path}")
                except Exception as e:
                    print(f"[FILE] failed:  {full_path} -> {e}")

    print("\nSummary:")
    print(f"  removed __pycache__ dirs: {removed_dirs}")
    print(f"  removed cache files:      {removed_files}")


if __name__ == '__main__':
    project_root = os.path.abspath(os.path.dirname(__file__))
    if len(sys.argv) > 1:
        target = os.path.abspath(sys.argv[1])
    else:
        target = project_root

    print(f"Clearing Python cache under: {target}")
    clear_cache(target)
