#!/usr/bin/env python3
"""Tests for the filament_diameter constants override.

The extruder config files under config/extruders/ historically
hard-coded [extruder] filament_diameter to 1.750. This test pins the
contract that filament_diameter is sourced from
${constants.filament_diameter:1.75} so a printer.cfg can switch to a
different filament size in via

    [constants]
    filament_diameter: 2.85

without forking the extruder file.

Two invariants per extruder:
  * default: no [constants] override -> filament_diameter == 1.75
  * override: [constants].filament_diameter wins
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


# Each extruder includes default_wiring.cfg from the extruders/ dir.
EXTRUDERS = ["bmg-bowden.cfg", "t250-bmg.cfg", "t250-vzg.cfg"]
WIRING_INCLUDES = ["default_wiring.cfg"]


class FilamentDiameterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "config", "extruders"))
        for name in EXTRUDERS + WIRING_INCLUDES:
            shutil.copy(
                os.path.join(REPO_ROOT, "config", "extruders", name),
                os.path.join(self.tmp, "config", "extruders", name),
            )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _load(self, extruder, constants_body=""):
        cfg = textwrap.dedent("""\
            [constants]
            {body}

            [include config/extruders/{extruder}]
        """).format(body=constants_body, extruder=extruder)
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        return reader.build_fileconfig_with_includes(data, path)

    def test_default_filament_diameter_is_1_75(self):
        """No override in [constants] -> extruder falls back to 1.75."""
        for extruder in EXTRUDERS:
            with self.subTest(extruder=extruder):
                fc = self._load(extruder)
                self.assertAlmostEqual(
                    float(fc.get("extruder", "filament_diameter")),
                    1.75,
                    msg="{} did not default to 1.75".format(extruder),
                )

    def test_filament_diameter_override_via_constants(self):
        """Setting [constants].filament_diameter overrides the default."""
        for extruder in EXTRUDERS:
            with self.subTest(extruder=extruder):
                fc = self._load(extruder, "filament_diameter: 2.85")
                self.assertAlmostEqual(
                    float(fc.get("extruder", "filament_diameter")),
                    2.85,
                    msg="{} ignored constants.filament_diameter".format(
                        extruder),
                )

    def test_filament_diameter_override_accepts_arbitrary_value(self):
        """Override path must work for non-standard values too (3.0)."""
        for extruder in EXTRUDERS:
            with self.subTest(extruder=extruder):
                fc = self._load(extruder, "filament_diameter: 3.0")
                self.assertAlmostEqual(
                    float(fc.get("extruder", "filament_diameter")),
                    3.0,
                    msg="{} ignored constants.filament_diameter=3.0".format(
                        extruder),
                )


if __name__ == "__main__":
    unittest.main()
