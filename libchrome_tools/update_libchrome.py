#!/usr/bin/python3

# Copyright (C) 2018 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Updates libchrome.

This script uprevs the libchrome library with newer Chromium code.
How to use:

Prepare your local Chromium repository with the target revision.
$ cd external/libchrome
$ python3 libchrome_tools/update_libchrome.py \
      --chromium_root=${PATH_TO_YOUR_LOCAL_CHROMIUM_REPO}

This script does following things;
- Clean existing libchrome code, except some manually created files and tools.
- Copy necessary files from original Chromium repository.
- Apply patches to the copied files, if necessary.
"""


import argparse
import fnmatch
import glob
import os
import re
import shutil
import subprocess


_TOOLS_DIR = os.path.dirname(os.path.realpath(__file__))
_LIBCHROME_ROOT = os.path.dirname(_TOOLS_DIR)


# Files which are in the repository, but should not be imported from Chrome
# repository.
_IMPORT_BLACKLIST = [
    # Libchrome specific files.
    'Android.bp',
    'MODULE_LICENSE_BSD',
    'NOTICE',
    'OWNERS',
    'SConstruct',
    'testrunner.cc',

    # libchrome_tools is out of the update target.
    'libchrome_tools/*',

    # Those files should be generated. Please see also buildflag_header.patch.
    'base/allocator/features.h',
    'base/debug/debugging_flags.h',

    # Blacklist several third party libraries, instead system libraries should
    # be used.
    'base/third_party/libevent/*',
    'base/third_party/symbolize/*',
    'testing/gmock/*',
    'testing/gtest/*',
    'third_party/*',
]

def _find_target_files():
  """Returns target files to be upreved."""
  output = subprocess.check_output(
      ['git', 'ls-tree', '-r', '--name-only', '--full-name', 'HEAD'],
      cwd=_LIBCHROME_ROOT).decode('utf-8')
  exclude_pattern = re.compile('|'.join(
      '(?:%s)' % fnmatch.translate(pattern) for pattern in _IMPORT_BLACKLIST))
  return [filepath for filepath in output.splitlines()
          if not exclude_pattern.match(filepath)]


def _clean_existing_dir(output_root):
  """Removes existing libchrome files.

  Args:
    output_root: Path to the output directory.
  """
  os.makedirs(output_root, mode=0o755, exist_ok=True)
  for path in os.listdir(output_root):
    target_path = os.path.join(output_root, path)
    if not os.path.isdir(target_path) or path in ('.git', 'libchrome_tools'):
      continue
    shutil.rmtree(target_path)


def _import_files(chromium_root, output_root):
  """Copies files from Chromium repository into libchrome.

  Args:
    chromium_root: Path to the Chromium's repository.
    output_root: Path to the output directory.
  """
  for filepath in _find_target_files():
    target_path = os.path.join(output_root, filepath)
    os.makedirs(os.path.dirname(target_path), mode=0o755, exist_ok=True)
    shutil.copy2(os.path.join(chromium_root, filepath), target_path)


def _apply_patch_files(patch_root, output_root):
  """Applies patches.

  libchrome needs some modification from Chromium repository, e.g. supporting
  toolchain which is not used by Chrome, or using system library rather than
  the library checked in the Chromium repository.
  See each *.patch file in libchrome_tools/patch/ directory for details.

  Args:
    patch_root: Path to the directory containing patch files.
    output_root: Path to the output directory.
  """
  for patch_file in glob.iglob(os.path.join(patch_root, '*.patch')):
    with open(patch_file, 'r') as f:
      subprocess.check_call(['patch', '-p1'], stdin=f, cwd=output_root)


def _parse_args():
  """Parses commandline arguments."""
  parser = argparse.ArgumentParser()

  # TODO(hidehiko): Support to specify the Chromium's revision number.
  parser.add_argument(
      '--chromium_root',
      help='Root directory to the local chromium repository.')
  parser.add_argument(
      '--output_root',
      default=_LIBCHROME_ROOT,
      help='Output directory, which is libchrome root directory.')
  parser.add_argument(
      '--patch_dir',
      default=os.path.join(_TOOLS_DIR, 'patch'),
      help='Directory containing patch files to be applied.')

  return parser.parse_args()


def main():
  args = _parse_args()
  _clean_existing_dir(args.output_root)
  _import_files(args.chromium_root, args.output_root)
  _apply_patch_files(args.patch_dir, args.output_root)
  # TODO(hidehiko): Create a git commit with filling templated message.


if __name__ == '__main__':
  main()
