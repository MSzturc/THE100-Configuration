#!/usr/bin/env python3
"""Pins second_homing_speed for X/Y in sensorless endstop configs.

For X/Y this parameter is only meaningful when sensorless homing is in
play, so the override lives in config/endstops/sensorless/<driver>.cfg
(NOT in axis/X/default_speed.cfg). The second pass should match the
first pass speed (100 mm/s) so a sensorless restart is not silently
slow.

The 5160-awd variant only adds [tmc5160 stepper_x1]/[tmc5160 stepper_y1]
overrides on top of [include 5160.cfg], so it must inherit the same
second_homing_speed transparently.
"""

import os
import sys
import shutil
import tempfile
import textwrap
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
WORKSPACE_ROOT = os.path.abspath(os.path.join(REPO_ROOT, ".."))
KLIPPY_DIR = os.path.join(WORKSPACE_ROOT, "klipper", "klippy")

sys.path.insert(0, KLIPPY_DIR)
import configfile  # noqa: E402


# (entry file relative to config/, support files needed by transitive
#  includes, list of (section, expected) tuples)
CASES = [
    ("endstops/sensorless/5160.cfg", [],
     [("stepper_x", 100), ("stepper_y", 100)]),
    ("endstops/sensorless/2209.cfg", [],
     [("stepper_x", 100), ("stepper_y", 100)]),
    ("endstops/sensorless/5160-awd.cfg",
     ["endstops/sensorless/5160.cfg"],
     [("stepper_x", 100), ("stepper_y", 100)]),
]


class SecondHomingSpeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        files = set()
        for entry, deps, _ in CASES:
            files.add(entry)
            files.update(deps)
        for rel in files:
            src = os.path.join(REPO_ROOT, "config", rel)
            dst = os.path.join(self.tmp, "config", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _load(self, entry):
        cfg = textwrap.dedent("""\
            [include config/{entry}]
        """).format(entry=entry)
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        return reader.build_fileconfig_with_includes(data, path)

    def test_xy_second_homing_speed_in_sensorless_configs(self):
        for entry, _, expectations in CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry)
                for section, expected in expectations:
                    self.assertEqual(
                        int(fc.get(section, "second_homing_speed")),
                        expected,
                        msg="{}: {} expected second_homing_speed={}".format(
                            entry, section, expected),
                    )


if __name__ == "__main__":
    unittest.main()
