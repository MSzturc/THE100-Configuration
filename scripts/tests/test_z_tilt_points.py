#!/usr/bin/env python3
"""Tests for the dynamic z_tilt points calculation.

Loads the THE100-Configuration z-tilt config through the enhanced Klipper
config parser (from the MSzturc/klipper fork) and verifies that the
[z_tilt] `points` option resolves to the expected XY pairs given a set of
[constants].
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


def parse_points(points_value):
    """Parse the resolved 'points' option string into a list of (x, y)
    float tuples. The Klipper config parser leaves the value as the raw
    multi-line string with placeholders already substituted."""
    pairs = []
    for line in points_value.splitlines():
        line = line.strip()
        if not line:
            continue
        x_str, y_str = line.split(",")
        pairs.append((float(x_str), float(y_str)))
    return pairs


class ZTiltPointsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Mirror enough of the real layout that the include in the
        # printer fixture resolves to the actual z-tilt config under test.
        os.makedirs(os.path.join(self.tmp, "config", "beds", "ender-3"))
        shutil.copy(
            os.path.join(REPO_ROOT, "config", "beds", "ender-3",
                         "z-tilt-leveling-t250.cfg"),
            os.path.join(self.tmp, "config", "beds", "ender-3",
                         "z-tilt-leveling-t250.cfg"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write_printer_cfg(self, constants_body):
        # The fixture provides only what z-tilt-leveling-t250.cfg needs:
        # constants + the include. No steppers, no other includes.
        cfg = textwrap.dedent("""\
            [constants]
            {body}

            [include config/beds/ender-3/z-tilt-leveling-t250.cfg]
        """).format(body=textwrap.indent(constants_body, ""))
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        return path

    def _load(self, constants_body):
        path = self._write_printer_cfg(constants_body)
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        fileconfig = reader.build_fileconfig_with_includes(data, path)
        return fileconfig

    def test_points_are_nozzle_coordinates(self):
        """Points are interpreted as nozzle (toolhead) coordinates so
        the safety margin can be applied directly to them; that means
        z_tilt must NOT enable use_probe_xy_offsets (default False)."""
        fileconfig = self._load(textwrap.dedent("""\
            print_volume_x: 192
            print_volume_y: 212
            print_volume_z: 170
            center_x: round(${constants.print_volume_x} / 2)
            center_y: round(${constants.print_volume_y} / 2)
            homing_travelspeed_xy: 200
            probe_offset_x: 1.875
            probe_offset_y: 17.25
        """))
        # Either absent (default False) or explicitly false is acceptable.
        if fileconfig.has_option("z_tilt", "use_probe_xy_offsets"):
            self.assertEqual(
                fileconfig.get("z_tilt",
                               "use_probe_xy_offsets").strip().lower(),
                "false",
            )

    MARGIN = 15.0

    def test_default_t250_constants(self):
        """T250 (probe behind nozzle): the rear-side max tightens so
        the probe never overshoots the bed (eddy-current would read
        infinity and slam the nozzle through the plate)."""
        fileconfig = self._load(textwrap.dedent("""\
            print_volume_x: 192
            print_volume_y: 212
            print_volume_z: 170
            center_x: round(${constants.print_volume_x} / 2)
            center_y: round(${constants.print_volume_y} / 2)
            homing_travelspeed_xy: 200
            probe_offset_x: 1.875
            probe_offset_y: 17.25
        """))
        points = parse_points(fileconfig.get("z_tilt", "points"))
        self.assertEqual(len(points), 3)
        # Nozzle-coord constraints with margin=15, offset=(1.875, 17.25):
        # min_x = max(15, 15 - 1.875)             = 15
        # max_x = min(192 - 15, 192 - 15 - 1.875) = 175.125
        # min_y = max(15, 15 - 17.25)             = 15
        # max_y = min(212 - 15, 212 - 15 - 17.25) = 179.75
        # rear point uses center_x = round(192 / 2) = 96
        self.assertAlmostEqual(points[0], (15.0, 15.0))
        self.assertAlmostEqual(points[1], (175.125, 15.0))
        self.assertAlmostEqual(points[2], (96.0, 179.75))

    def test_nozzle_and_probe_both_respect_margin(self):
        """Hard safety invariant: every nozzle position AND every
        probe-contact position must sit inside [margin, pv - margin].
        Violating it on the probe side causes the eddy-current sensor
        to read infinity off-bed — and the nozzle gets driven into the
        plate during homing."""
        fileconfig = self._load(textwrap.dedent("""\
            print_volume_x: 192
            print_volume_y: 212
            print_volume_z: 170
            center_x: round(${constants.print_volume_x} / 2)
            center_y: round(${constants.print_volume_y} / 2)
            homing_travelspeed_xy: 200
            probe_offset_x: 1.875
            probe_offset_y: 17.25
        """))
        margin = self.MARGIN
        pv_x, pv_y = 192.0, 212.0
        offset_x, offset_y = 1.875, 17.25
        for nx, ny in parse_points(fileconfig.get("z_tilt", "points")):
            self.assertGreaterEqual(nx, margin)
            self.assertLessEqual(nx, pv_x - margin)
            self.assertGreaterEqual(ny, margin)
            self.assertLessEqual(ny, pv_y - margin)
            px, py = nx + offset_x, ny + offset_y
            self.assertGreaterEqual(px, margin)
            self.assertLessEqual(px, pv_x - margin)
            self.assertGreaterEqual(py, margin)
            self.assertLessEqual(py, pv_y - margin)

    def test_zero_probe_offsets_falls_back_to_pure_margin(self):
        """No probe offset → both constraints collapse onto the same
        bounds; points sit exactly at the margin."""
        fileconfig = self._load(textwrap.dedent("""\
            print_volume_x: 200
            print_volume_y: 200
            print_volume_z: 170
            center_x: round(${constants.print_volume_x} / 2)
            center_y: round(${constants.print_volume_y} / 2)
            homing_travelspeed_xy: 200
            probe_offset_x: 0
            probe_offset_y: 0
        """))
        points = parse_points(fileconfig.get("z_tilt", "points"))
        self.assertAlmostEqual(points[0], (15.0, 15.0))
        self.assertAlmostEqual(points[1], (185.0, 15.0))
        self.assertAlmostEqual(points[2], (100.0, 185.0))

    def test_sensor_right_of_nozzle(self):
        """Probe right of nozzle (offset_x > 0, offset_y = 0): only
        the +X side shrinks to keep the probe on the bed; -X and Y
        stay at the bare margin."""
        fileconfig = self._load(textwrap.dedent("""\
            print_volume_x: 200
            print_volume_y: 200
            print_volume_z: 170
            center_x: round(${constants.print_volume_x} / 2)
            center_y: round(${constants.print_volume_y} / 2)
            homing_travelspeed_xy: 200
            probe_offset_x: 20
            probe_offset_y: 0
        """))
        points = parse_points(fileconfig.get("z_tilt", "points"))
        # min_x = max(15, 15 - 20) = 15
        # max_x = min(185, 185 - 20) = 165
        # min_y = max(15, 15 - 0)  = 15
        # max_y = min(185, 185 - 0) = 185
        self.assertAlmostEqual(points[0], (15.0, 15.0))
        self.assertAlmostEqual(points[1], (165.0, 15.0))
        self.assertAlmostEqual(points[2], (100.0, 185.0))

    def test_sensor_left_of_nozzle(self):
        """Probe left of nozzle (offset_x < 0, offset_y = 0): only the
        -X side grows so the probe still lands on the bed; +X and Y
        stay at the bare margin."""
        fileconfig = self._load(textwrap.dedent("""\
            print_volume_x: 200
            print_volume_y: 200
            print_volume_z: 170
            center_x: round(${constants.print_volume_x} / 2)
            center_y: round(${constants.print_volume_y} / 2)
            homing_travelspeed_xy: 200
            probe_offset_x: -20
            probe_offset_y: 0
        """))
        points = parse_points(fileconfig.get("z_tilt", "points"))
        # min_x = max(15, 15 - (-20)) = max(15, 35) = 35
        # max_x = min(185, 185 - (-20)) = min(185, 205) = 185
        self.assertAlmostEqual(points[0], (35.0, 15.0))
        self.assertAlmostEqual(points[1], (185.0, 15.0))
        self.assertAlmostEqual(points[2], (100.0, 185.0))

    def test_sensor_behind_nozzle(self):
        """Probe behind nozzle (offset_y > 0, offset_x = 0): only the
        +Y side shrinks; X axis stays at the bare margin on both
        sides."""
        fileconfig = self._load(textwrap.dedent("""\
            print_volume_x: 200
            print_volume_y: 200
            print_volume_z: 170
            center_x: round(${constants.print_volume_x} / 2)
            center_y: round(${constants.print_volume_y} / 2)
            homing_travelspeed_xy: 200
            probe_offset_x: 0
            probe_offset_y: 25
        """))
        points = parse_points(fileconfig.get("z_tilt", "points"))
        # min_y = max(15, 15 - 25) = 15
        # max_y = min(185, 185 - 25) = 160
        self.assertAlmostEqual(points[0], (15.0, 15.0))
        self.assertAlmostEqual(points[1], (185.0, 15.0))
        self.assertAlmostEqual(points[2], (100.0, 160.0))

    def test_sensor_in_front_of_nozzle(self):
        """Probe in front of nozzle (offset_y < 0, offset_x = 0): only
        the -Y side grows; X axis stays at the bare margin on both
        sides."""
        fileconfig = self._load(textwrap.dedent("""\
            print_volume_x: 200
            print_volume_y: 200
            print_volume_z: 170
            center_x: round(${constants.print_volume_x} / 2)
            center_y: round(${constants.print_volume_y} / 2)
            homing_travelspeed_xy: 200
            probe_offset_x: 0
            probe_offset_y: -15
        """))
        points = parse_points(fileconfig.get("z_tilt", "points"))
        # min_y = max(15, 15 - (-15)) = max(15, 30) = 30
        # max_y = min(185, 185 - (-15)) = min(185, 200) = 185
        self.assertAlmostEqual(points[0], (15.0, 30.0))
        self.assertAlmostEqual(points[1], (185.0, 30.0))
        self.assertAlmostEqual(points[2], (100.0, 185.0))

    def assertAlmostEqual(self, first, second, places=6, msg=None):
        # Tuple-aware almost-equal so the test reads cleanly for points.
        if isinstance(first, tuple) and isinstance(second, tuple):
            self.assertEqual(len(first), len(second))
            for a, b in zip(first, second):
                super().assertAlmostEqual(a, b, places=places, msg=msg)
        else:
            super().assertAlmostEqual(first, second, places=places, msg=msg)


if __name__ == "__main__":
    unittest.main()
