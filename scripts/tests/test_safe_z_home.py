#!/usr/bin/env python3
"""Pins the [safe_z_home] block in beds/dynamic_size.cfg.

[safe_z_home].home_xy_position must be the print bed center, derived
from print_volume_x/y by dynamic_size.cfg itself. The printer.cfg only
has to set print_volume_x/y -- center_x/center_y are exported as
default constants from dynamic_size.cfg so every consumer
(dynamic_mesh.cfg, twist-compensation.cfg, z-tilt, macros/print.cfg)
gets them for free.
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


def parse_pair(value):
    x_str, y_str = value.split(",")
    return float(x_str.strip()), float(y_str.strip())


# (print_volume_x, print_volume_y, homing_travelspeed_xy)
BED_CASES = [
    (192, 212, 200),  # T250 default
    (200, 200, 150),  # square
    (300, 250, 250),  # wide
]


class SafeZHomeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "config", "beds"))
        shutil.copy(
            os.path.join(REPO_ROOT, "config", "beds", "dynamic_size.cfg"),
            os.path.join(self.tmp, "config", "beds", "dynamic_size.cfg"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _load(self, pv_x, pv_y, travel):
        # Intentionally NO center_x/center_y: dynamic_size.cfg owns them.
        constants = textwrap.dedent("""\
            print_volume_x: {pv_x}
            print_volume_y: {pv_y}
            print_volume_z: 170
            homing_travelspeed_xy: {travel}
        """).format(pv_x=pv_x, pv_y=pv_y, travel=travel)
        cfg = textwrap.dedent("""\
            [constants]
            {constants}
            [include config/beds/dynamic_size.cfg]
        """).format(constants=constants)
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        return reader.build_fileconfig_with_includes(data, path)

    def test_home_xy_position_is_bed_center(self):
        for pv_x, pv_y, travel in BED_CASES:
            with self.subTest(pv_x=pv_x, pv_y=pv_y):
                fc = self._load(pv_x, pv_y, travel)
                hx, hy = parse_pair(fc.get("safe_z_home", "home_xy_position"))
                self.assertAlmostEqual(hx, pv_x / 2.0,
                    msg="home_xy_x must equal print_volume_x/2")
                self.assertAlmostEqual(hy, pv_y / 2.0,
                    msg="home_xy_y must equal print_volume_y/2")

    def test_speed_tracks_homing_travelspeed_xy(self):
        for pv_x, pv_y, travel in BED_CASES:
            with self.subTest(travel=travel):
                fc = self._load(pv_x, pv_y, travel)
                self.assertEqual(
                    int(fc.get("safe_z_home", "speed")),
                    travel,
                    msg="safe_z_home.speed must source homing_travelspeed_xy",
                )

    def test_z_hop_defaults(self):
        """Conservative z_hop defaults preserved across the migration."""
        fc = self._load(*BED_CASES[0])
        self.assertEqual(int(fc.get("safe_z_home", "z_hop")), 3)
        self.assertEqual(int(fc.get("safe_z_home", "z_hop_speed")), 50)


if __name__ == "__main__":
    unittest.main()
