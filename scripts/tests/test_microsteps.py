#!/usr/bin/env python3
"""Tests for the {xy,z,e}_microsteps constants overrides.

The stepper config files under config/axis/ and config/extruders/
historically hard-coded `microsteps:` per axis (16 for XY/E, 32 for Z).
This test pins the contract that microsteps are sourced from
${constants.xy_microsteps:16}, ${constants.z_microsteps:16}, and
${constants.e_microsteps:16} so a printer.cfg can switch microstepping
in one place via

    [constants]
    xy_microsteps: 32

without forking the stepper file.

Two invariants per stepper file:
  * default: no [constants] override -> microsteps == 16
  * override: [constants].<axis>_microsteps wins for every stepper
    section the file defines (directly OR via [include]).

Plus a cross-axis isolation check so a stray `xy_microsteps:` cannot
bleed into Z or E.
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
#  includes, list of stepper sections whose microsteps this file controls)
XY_CASES = [
    ("axis/X/default_microstepping.cfg", [], ["stepper_x"]),
    ("axis/X/awd_microstepping.cfg",
     ["axis/X/default_microstepping.cfg"],
     ["stepper_x", "stepper_x1"]),
    ("axis/Y/default_microstepping.cfg", [], ["stepper_y"]),
    ("axis/Y/awd_microstepping.cfg",
     ["axis/Y/default_microstepping.cfg"],
     ["stepper_y", "stepper_y1"]),
]

Z_CASES = [
    ("axis/Z/default_TR8x8_1.8deg.cfg",
     ["axis/Z/default_wiring_1M.cfg", "axis/Z/default_speed.cfg"],
     ["stepper_z"]),
    ("axis/Z/z_tilt_TR8x8_1.8deg.cfg",
     ["axis/Z/default_wiring_3M.cfg", "axis/Z/default_speed.cfg"],
     ["stepper_z", "stepper_z1", "stepper_z2"]),
]

E_CASES = [
    ("extruders/bmg-bowden.cfg",
     ["extruders/default_wiring.cfg"],
     ["extruder"]),
    ("extruders/t250-bmg.cfg",
     ["extruders/default_wiring.cfg"],
     ["extruder"]),
    ("extruders/t250-vzg.cfg",
     ["extruders/default_wiring.cfg"],
     ["extruder"]),
]


class MicrostepsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        files = set()
        for cases in (XY_CASES, Z_CASES, E_CASES):
            for entry, deps, _ in cases:
                files.add(entry)
                files.update(deps)
        for rel in files:
            src = os.path.join(REPO_ROOT, "config", rel)
            dst = os.path.join(self.tmp, "config", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _load(self, entry, constants_body=""):
        cfg = textwrap.dedent("""\
            [constants]
            {body}

            [include config/{entry}]
        """).format(body=constants_body, entry=entry)
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        return reader.build_fileconfig_with_includes(data, path)

    def _assert_microsteps(self, fc, sections, expected, entry):
        for section in sections:
            self.assertEqual(
                int(fc.get(section, "microsteps")),
                expected,
                msg="{}: {} expected microsteps={}".format(
                    entry, section, expected),
            )

    def test_default_xy_microsteps_is_16(self):
        """No override -> XY steppers fall back to 16."""
        for entry, _, sections in XY_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry)
                self._assert_microsteps(fc, sections, 16, entry)

    def test_default_z_microsteps_is_16(self):
        """No override -> Z steppers fall back to 16."""
        for entry, _, sections in Z_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry)
                self._assert_microsteps(fc, sections, 16, entry)

    def test_default_e_microsteps_is_16(self):
        """No override -> extruder falls back to 16."""
        for entry, _, sections in E_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry)
                self._assert_microsteps(fc, sections, 16, entry)

    def test_xy_microsteps_override_via_constants(self):
        """[constants].xy_microsteps wins for every stepper_x{,1} / y{,1}."""
        for entry, _, sections in XY_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry, "xy_microsteps: 32")
                self._assert_microsteps(fc, sections, 32, entry)

    def test_z_microsteps_override_via_constants(self):
        """[constants].z_microsteps wins for every stepper_z{,1,2}."""
        for entry, _, sections in Z_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry, "z_microsteps: 64")
                self._assert_microsteps(fc, sections, 64, entry)

    def test_e_microsteps_override_via_constants(self):
        """[constants].e_microsteps wins for the extruder section."""
        for entry, _, sections in E_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry, "e_microsteps: 32")
                self._assert_microsteps(fc, sections, 32, entry)

    def test_axis_overrides_do_not_bleed(self):
        """A constant for one axis must not affect another axis's default."""
        for entry, _, sections in Z_CASES:
            with self.subTest(scenario="xy_override_does_not_touch_z",
                              entry=entry):
                fc = self._load(entry, "xy_microsteps: 256")
                self._assert_microsteps(fc, sections, 16, entry)
        for entry, _, sections in XY_CASES:
            with self.subTest(scenario="e_override_does_not_touch_xy",
                              entry=entry):
                fc = self._load(entry, "e_microsteps: 256")
                self._assert_microsteps(fc, sections, 16, entry)
        for entry, _, sections in E_CASES:
            with self.subTest(scenario="z_override_does_not_touch_e",
                              entry=entry):
                fc = self._load(entry, "z_microsteps: 256")
                self._assert_microsteps(fc, sections, 16, entry)


if __name__ == "__main__":
    unittest.main()
