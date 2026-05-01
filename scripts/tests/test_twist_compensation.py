#!/usr/bin/env python3
"""Tests for the dynamic axis_twist_compensation calibration box.

Loads THE100-Configuration's twist-compensation.cfg through the enhanced
Klipper config parser and verifies that calibrate_start_x / calibrate_end_x
/ calibrate_start_y / calibrate_end_y:
- sit at least twist_compensation_margin away from every bed edge (probe
  stays on the bed; eddy-current sensor never reads infinity), AND
- imply a nozzle position that sits at least twist_compensation_margin
  away from every stepper limit (no virtual endstop trigger), for both
  the auto-probing nozzle (calibrate - probe_offset) AND the manual-
  probing nozzle (= calibrate, since the manual probe places the nozzle
  directly over the calibration point).

calibrate_*_x / calibrate_*_y are bed coordinates by Klipper convention
(the probe lands at these positions); the auto-probing nozzle position
is calibrate - probe_offset.
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


class TwistCompensationTest(unittest.TestCase):
    MARGIN = 15.0  # matches twist_compensation_margin in twist-compensation.cfg

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "config", "beds"))
        shutil.copy(
            os.path.join(REPO_ROOT, "config", "beds",
                         "twist-compensation.cfg"),
            os.path.join(self.tmp, "config", "beds",
                         "twist-compensation.cfg"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write_printer_cfg(self, constants_body):
        cfg = textwrap.dedent("""\
            [constants]
            {body}

            [include config/beds/twist-compensation.cfg]
        """).format(body=textwrap.indent(constants_body, ""))
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        return path

    def _load(self, constants_body):
        path = self._write_printer_cfg(constants_body)
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        return reader.build_fileconfig_with_includes(data, path)

    def _box(self, fileconfig):
        section = "axis_twist_compensation"
        return (
            float(fileconfig.get(section, "calibrate_start_x")),
            float(fileconfig.get(section, "calibrate_end_x")),
            float(fileconfig.get(section, "calibrate_start_y")),
            float(fileconfig.get(section, "calibrate_end_y")),
            float(fileconfig.get(section, "calibrate_x")),
            float(fileconfig.get(section, "calibrate_y")),
        )

    def _assert_safe(self, start_x, end_x, start_y, end_y, mid_x, mid_y,
                     pv_x, pv_y, offset_x, offset_y):
        """Probe (= calibrate), auto-probing nozzle (= calibrate - offset)
        and manual-probing nozzle (= calibrate) all sit inside
        [margin, pv - margin]."""
        margin = self.MARGIN

        def check(label, px, py):
            self.assertGreaterEqual(px, margin,
                                    "probe {} x off bed".format(label))
            self.assertLessEqual(px, pv_x - margin,
                                 "probe {} x off bed".format(label))
            self.assertGreaterEqual(py, margin,
                                    "probe {} y off bed".format(label))
            self.assertLessEqual(py, pv_y - margin,
                                 "probe {} y off bed".format(label))
            nx, ny = px - offset_x, py - offset_y
            self.assertGreaterEqual(nx, margin,
                                    "nozzle {} x past stepper".format(label))
            self.assertLessEqual(nx, pv_x - margin,
                                 "nozzle {} x past stepper".format(label))
            self.assertGreaterEqual(ny, margin,
                                    "nozzle {} y past stepper".format(label))
            self.assertLessEqual(ny, pv_y - margin,
                                 "nozzle {} y past stepper".format(label))

        # The four corners of the X- and Y-axis calibration strips.
        check("x_start", start_x, mid_y)
        check("x_end",   end_x,   mid_y)
        check("y_start", mid_x,   start_y)
        check("y_end",   mid_x,   end_y)

    def test_default_t250_constants(self):
        """T250 (probe behind+right of nozzle): X strip starts inside the
        bed by margin+offset_x on the -X side and ends at the bed-edge
        margin on the +X side; Y strip mirrors that on the Y axis."""
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
        start_x, end_x, start_y, end_y, mid_x, mid_y = self._box(fileconfig)
        # margin=15, offset=(1.875, 17.25):
        # start_x = max(15 + 1.875, 15)             = 16.875
        # end_x   = min(192 - 15 + 1.875, 192 - 15) = 177
        # start_y = max(15 + 17.25, 15)             = 32.25
        # end_y   = min(212 - 15 + 17.25, 212 - 15) = 197
        # mid_x = round(192/2) = 96, mid_y = round(212/2) = 106
        self.assertAlmostEqual(start_x, 16.875)
        self.assertAlmostEqual(end_x,   177.0)
        self.assertAlmostEqual(start_y, 32.25)
        self.assertAlmostEqual(end_y,   197.0)
        self.assertAlmostEqual(mid_x,   96.0)
        self.assertAlmostEqual(mid_y,   106.0)

    def test_nozzle_and_probe_both_respect_margin(self):
        """The hard safety invariant: every endpoint of both calibration
        strips — probe AND derived nozzle — must sit at least
        twist_compensation_margin away from its respective limit."""
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
        start_x, end_x, start_y, end_y, mid_x, mid_y = self._box(fileconfig)
        self._assert_safe(start_x, end_x, start_y, end_y, mid_x, mid_y,
                          192.0, 212.0, 1.875, 17.25)

    def test_zero_probe_offsets(self):
        """No probe offset → calibration strips collapse to bed minus
        margin on every side; nozzle and probe coincide."""
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
        start_x, end_x, start_y, end_y, _, _ = self._box(fileconfig)
        self.assertAlmostEqual(start_x, 15.0)
        self.assertAlmostEqual(end_x,   185.0)
        self.assertAlmostEqual(start_y, 15.0)
        self.assertAlmostEqual(end_y,   185.0)

    def test_sensor_right_of_nozzle(self):
        """Probe right of nozzle (offset_x > 0): the +X end of the strip
        is bounded by the bed edge; the -X start is bounded by the
        nozzle's stepper margin."""
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
        start_x, end_x, start_y, end_y, _, _ = self._box(fileconfig)
        # start_x = max(15 + 20, 15)             = 35    → nozzle 15
        # end_x   = min(200 - 15 + 20, 200 - 15) = 185   → nozzle 165
        self.assertAlmostEqual(start_x, 35.0)
        self.assertAlmostEqual(end_x,   185.0)
        self.assertAlmostEqual(start_y, 15.0)
        self.assertAlmostEqual(end_y,   185.0)
        self._assert_safe(start_x, end_x, start_y, end_y, 100.0, 100.0,
                          200.0, 200.0, 20.0, 0.0)

    def test_sensor_left_of_nozzle(self):
        """Probe left of nozzle (offset_x < 0): the -X start is bounded
        by the bed edge; the +X end is bounded by the nozzle's stepper
        margin."""
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
        start_x, end_x, _, _, _, _ = self._box(fileconfig)
        # start_x = max(15 + (-20), 15)             = 15    → nozzle 35
        # end_x   = min(200 - 15 + (-20), 200 - 15) = 165   → nozzle 185
        self.assertAlmostEqual(start_x, 15.0)
        self.assertAlmostEqual(end_x,   165.0)
        self._assert_safe(*self._box(fileconfig), pv_x=200.0, pv_y=200.0,
                          offset_x=-20.0, offset_y=0.0)

    def test_sensor_behind_nozzle(self):
        """Probe behind nozzle (offset_y > 0): the +Y end of the strip
        is bounded by the bed edge; the -Y start is bounded by the
        nozzle's stepper margin."""
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
        _, _, start_y, end_y, _, _ = self._box(fileconfig)
        # start_y = max(15 + 25, 15)             = 40    → nozzle 15
        # end_y   = min(200 - 15 + 25, 200 - 15) = 185   → nozzle 160
        self.assertAlmostEqual(start_y, 40.0)
        self.assertAlmostEqual(end_y,   185.0)
        self._assert_safe(*self._box(fileconfig), pv_x=200.0, pv_y=200.0,
                          offset_x=0.0, offset_y=25.0)

    def test_sensor_in_front_of_nozzle(self):
        """Probe in front of nozzle (offset_y < 0): the -Y start is
        bounded by the bed edge; the +Y end is bounded by the nozzle's
        stepper margin."""
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
        _, _, start_y, end_y, _, _ = self._box(fileconfig)
        # start_y = max(15 + (-15), 15)             = 15    → nozzle 30
        # end_y   = min(200 - 15 + (-15), 200 - 15) = 170   → nozzle 185
        self.assertAlmostEqual(start_y, 15.0)
        self.assertAlmostEqual(end_y,   170.0)
        self._assert_safe(*self._box(fileconfig), pv_x=200.0, pv_y=200.0,
                          offset_x=0.0, offset_y=-15.0)

    def assertAlmostEqual(self, first, second, places=6, msg=None):
        super().assertAlmostEqual(first, second, places=places, msg=msg)


if __name__ == "__main__":
    unittest.main()
