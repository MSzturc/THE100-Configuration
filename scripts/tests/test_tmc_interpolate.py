#!/usr/bin/env python3
"""Tests for the {xy,z,e}_interpolate constants overrides.

Every TMC stepper driver file under config/steppers/ must source its
`interpolate` parameter from constants:

    [tmcXXXX <section>]
    interpolate: ${constants.<axis>_interpolate:true}

so a printer.cfg can switch microstep interpolation in one place via

    [constants]
    xy_interpolate: false

The fallback `:true` matches Klipper's built-in default
(klippy/extras/tmc.py: `config.getboolean("interpolate", True)`).

Per stepper file:
  * default: no [constants] override -> interpolate == True
  * override: [constants].<axis>_interpolate wins for every TMC
    section the file defines (directly OR via [include]).

Plus a cross-axis isolation check so a stray `xy_interpolate:` cannot
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
#  includes, list of TMC sections whose interpolate this file controls)
XY_CASES = [
    ("steppers/automatic/5160/2wd.cfg", [],
     ["tmc5160 stepper_x", "tmc5160 stepper_y"]),
    ("steppers/automatic/5160/4wd.cfg",
     ["steppers/automatic/5160/2wd.cfg"],
     ["tmc5160 stepper_x", "tmc5160 stepper_x1",
      "tmc5160 stepper_y", "tmc5160 stepper_y1"]),
    ("steppers/generic/2209/24v-0.8a-x.cfg", [], ["tmc2209 stepper_x"]),
    ("steppers/generic/2209/24v-0.8a-y.cfg", [], ["tmc2209 stepper_y"]),
    ("steppers/generic/5160/54v-1.768a-x.cfg", [], ["tmc5160 stepper_x"]),
    ("steppers/generic/5160/54v-1.768a-x1.cfg", [], ["tmc5160 stepper_x1"]),
    ("steppers/generic/5160/54v-1.768a-y.cfg", [], ["tmc5160 stepper_y"]),
    ("steppers/generic/5160/54v-1.768a-y1.cfg", [], ["tmc5160 stepper_y1"]),
    ("steppers/generic/5160/54v-3.15a-x.cfg", [], ["tmc5160 stepper_x"]),
    ("steppers/generic/5160/54v-3.15a-x1.cfg", [], ["tmc5160 stepper_x1"]),
    ("steppers/generic/5160/54v-3.15a-y.cfg", [], ["tmc5160 stepper_y"]),
    ("steppers/generic/5160/54v-3.15a-y1.cfg", [], ["tmc5160 stepper_y1"]),
]

Z_CASES = [
    ("steppers/generic/2209/24v-0.8a-z.cfg", [], ["tmc2209 stepper_z"]),
    ("steppers/generic/5160/54v-0.5a-z.cfg", [], ["tmc5160 stepper_z"]),
    ("steppers/generic/5160/54v-0.5a-z1.cfg", [], ["tmc5160 stepper_z1"]),
    ("steppers/generic/5160/54v-0.5a-z2.cfg", [], ["tmc5160 stepper_z2"]),
]

E_CASES = [
    ("steppers/automatic/5160/extruder.cfg", [], ["tmc5160 extruder"]),
    ("steppers/moons-cse14hra1l410a/5160/54v-0.6a-e.cfg", [],
     ["tmc5160 extruder"]),
    ("steppers/moons-cse14hra1l410a/5160/54v-0.707a-e.cfg", [],
     ["tmc5160 extruder"]),
    ("steppers/generic/5160/54v-0.85a-e.cfg", [], ["tmc5160 extruder"]),
    ("steppers/generic/2209/24v-1.0a-e.cfg", [], ["tmc2209 extruder"]),
]


def _to_bool(value):
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    raise ValueError("not a boolean: {!r}".format(value))


class TmcInterpolateTest(unittest.TestCase):
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

    # Seed required constants so the "automatic" stepper-tuning files
    # (which reference xy_*/e_* without defaults) parse successfully.
    BASE_CONSTANTS = textwrap.dedent("""\
        xy_run_current: 1.0
        xy_motor: ldo-42sth48-2504mah
        xy_voltage: 24
        e_run_current: 0.6
        e_motor: ldo-36sth20-1004ahg
        e_voltage: 24
    """)

    def _load(self, entry, constants_body=""):
        cfg = textwrap.dedent("""\
            [constants]
            {base}{body}

            [include config/{entry}]
        """).format(base=self.BASE_CONSTANTS, body=constants_body,
                    entry=entry)
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        return reader.build_fileconfig_with_includes(data, path)

    def _assert_interpolate(self, fc, sections, expected, entry):
        for section in sections:
            self.assertEqual(
                _to_bool(fc.get(section, "interpolate")),
                expected,
                msg="{}: {} expected interpolate={}".format(
                    entry, section, expected),
            )

    def test_default_xy_interpolate_is_klipper_standard(self):
        """No override -> XY TMC drivers fall back to Klipper default (True)."""
        for entry, _, sections in XY_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry)
                self._assert_interpolate(fc, sections, True, entry)

    def test_default_z_interpolate_is_klipper_standard(self):
        """No override -> Z TMC drivers fall back to Klipper default (True)."""
        for entry, _, sections in Z_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry)
                self._assert_interpolate(fc, sections, True, entry)

    def test_default_e_interpolate_is_klipper_standard(self):
        """No override -> extruder TMC driver falls back to Klipper default."""
        for entry, _, sections in E_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry)
                self._assert_interpolate(fc, sections, True, entry)

    def test_xy_interpolate_override_false(self):
        """[constants].xy_interpolate=false wins for every XY TMC section."""
        for entry, _, sections in XY_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry, "xy_interpolate: false")
                self._assert_interpolate(fc, sections, False, entry)

    def test_z_interpolate_override_false(self):
        """[constants].z_interpolate=false wins for every Z TMC section."""
        for entry, _, sections in Z_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry, "z_interpolate: false")
                self._assert_interpolate(fc, sections, False, entry)

    def test_e_interpolate_override_false(self):
        """[constants].e_interpolate=false wins for the extruder TMC section."""
        for entry, _, sections in E_CASES:
            with self.subTest(entry=entry):
                fc = self._load(entry, "e_interpolate: false")
                self._assert_interpolate(fc, sections, False, entry)

    def test_axis_overrides_do_not_bleed(self):
        """A constant for one axis must not affect another axis's default."""
        for entry, _, sections in Z_CASES:
            with self.subTest(scenario="xy_override_does_not_touch_z",
                              entry=entry):
                fc = self._load(entry, "xy_interpolate: false")
                self._assert_interpolate(fc, sections, True, entry)
        for entry, _, sections in XY_CASES:
            with self.subTest(scenario="e_override_does_not_touch_xy",
                              entry=entry):
                fc = self._load(entry, "e_interpolate: false")
                self._assert_interpolate(fc, sections, True, entry)
        for entry, _, sections in E_CASES:
            with self.subTest(scenario="z_override_does_not_touch_e",
                              entry=entry):
                fc = self._load(entry, "z_interpolate: false")
                self._assert_interpolate(fc, sections, True, entry)


if __name__ == "__main__":
    unittest.main()
