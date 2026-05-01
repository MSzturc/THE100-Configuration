#!/usr/bin/env python3
"""Tests for the nozzle_diameter constants override.

The hotend config files under config/hotends/ historically hard-coded
[extruder] nozzle_diameter to 0.4. This test pins the contract that
nozzle_diameter is sourced from ${constants.nozzle_diameter:0.4} so a
printer.cfg can drop a different nozzle in via

    [constants]
    nozzle_diameter: 0.6

without forking the hotend file.

Two invariants per hotend:
  * default: no [constants] override -> nozzle_diameter == 0.4
  * override: [constants].nozzle_diameter wins
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


# (hotend filename, supporting wiring include the hotend pulls in)
HOTENDS = [
    ("chc-pro.cfg", "default_wiring.cfg"),
    ("goliath.cfg", "default_wiring.cfg"),
    ("mosquito-magnum.cfg", "default_wiring.cfg"),
    ("rapido-uhf.cfg", "default_wiring.cfg"),
    ("std6-v2.cfg", "dual_wiring.cfg"),
]


class NozzleDiameterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "config", "hotends"))
        for hotend, wiring in HOTENDS:
            shutil.copy(
                os.path.join(REPO_ROOT, "config", "hotends", hotend),
                os.path.join(self.tmp, "config", "hotends", hotend),
            )
            shutil.copy(
                os.path.join(REPO_ROOT, "config", "hotends", wiring),
                os.path.join(self.tmp, "config", "hotends", wiring),
            )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _load(self, hotend, constants_body=""):
        cfg = textwrap.dedent("""\
            [constants]
            {body}

            [include config/hotends/{hotend}]
        """).format(body=constants_body, hotend=hotend)
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        return reader.build_fileconfig_with_includes(data, path)

    def test_default_nozzle_diameter_is_0_4(self):
        """No override in [constants] -> hotend falls back to 0.4."""
        for hotend, _ in HOTENDS:
            with self.subTest(hotend=hotend):
                fc = self._load(hotend)
                self.assertAlmostEqual(
                    float(fc.get("extruder", "nozzle_diameter")),
                    0.4,
                    msg="{} did not default to 0.4".format(hotend),
                )

    def test_nozzle_diameter_override_via_constants(self):
        """Setting [constants].nozzle_diameter overrides the hotend default."""
        for hotend, _ in HOTENDS:
            with self.subTest(hotend=hotend):
                fc = self._load(hotend, "nozzle_diameter: 0.6")
                self.assertAlmostEqual(
                    float(fc.get("extruder", "nozzle_diameter")),
                    0.6,
                    msg="{} ignored constants.nozzle_diameter".format(hotend),
                )

    def test_nozzle_diameter_override_accepts_arbitrary_value(self):
        """Override path must work for non-default sizes too (0.8 high-flow)."""
        for hotend, _ in HOTENDS:
            with self.subTest(hotend=hotend):
                fc = self._load(hotend, "nozzle_diameter: 0.8")
                self.assertAlmostEqual(
                    float(fc.get("extruder", "nozzle_diameter")),
                    0.8,
                    msg="{} ignored constants.nozzle_diameter=0.8".format(hotend),
                )


if __name__ == "__main__":
    unittest.main()
