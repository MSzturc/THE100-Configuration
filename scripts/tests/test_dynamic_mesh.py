#!/usr/bin/env python3
"""Tests for the dynamic bed_mesh box calculation.

Loads THE100-Configuration's dynamic_mesh.cfg through the enhanced
Klipper config parser and verifies that mesh_min / mesh_max:
- sit at least bed_mesh_margin away from every bed edge (probe stays
  on the bed; eddy-current sensor never reads infinity), AND
- imply a nozzle position that sits at least bed_mesh_margin away
  from every stepper limit (no virtual endstop trigger).

mesh_min / mesh_max are PROBE coordinates by Klipper convention; the
nozzle position is mesh_xy - probe_offset.
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


class DynamicMeshTest(unittest.TestCase):
    MARGIN = 15.0  # matches bed_mesh_margin in dynamic_mesh.cfg

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Copy the two real config files under test so includes resolve
        # against the same paths the printer fixture uses.
        os.makedirs(os.path.join(self.tmp, "config", "beds"))
        for name in ("dynamic_size.cfg", "dynamic_mesh.cfg"):
            shutil.copy(
                os.path.join(REPO_ROOT, "config", "beds", name),
                os.path.join(self.tmp, "config", "beds", name),
            )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write_printer_cfg(self, constants_body):
        cfg = textwrap.dedent("""\
            [constants]
            {body}

            [include config/beds/dynamic_size.cfg]
            [include config/beds/dynamic_mesh.cfg]
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

    def _mesh_box(self, fileconfig):
        return (
            parse_pair(fileconfig.get("bed_mesh", "mesh_min")),
            parse_pair(fileconfig.get("bed_mesh", "mesh_max")),
        )

    def _assert_safe(self, mesh_min, mesh_max, pv_x, pv_y, offset_x, offset_y):
        """Both probe and nozzle must sit inside [margin, pv - margin]."""
        margin = self.MARGIN
        for label, (px, py) in (("min", mesh_min), ("max", mesh_max)):
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

    def test_default_t250_constants(self):
        """T250 (probe behind+right of nozzle): probe sits at bed-edge
        margin on the +X/+Y side; nozzle sits at stepper-edge margin
        on the -X/-Y side."""
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
        mesh_min, mesh_max = self._mesh_box(fileconfig)
        # Probe-coord constraints with margin=15, offset=(1.875, 17.25):
        # mesh_min_x = max(15 + 1.875, 15)             = 16.875
        # mesh_min_y = max(15 + 17.25, 15)             = 32.25
        # mesh_max_x = min(192 - 15 + 1.875, 192 - 15) = 177
        # mesh_max_y = min(212 - 15 + 17.25, 212 - 15) = 197
        self.assertAlmostEqual(mesh_min[0], 16.875)
        self.assertAlmostEqual(mesh_min[1], 32.25)
        self.assertAlmostEqual(mesh_max[0], 177.0)
        self.assertAlmostEqual(mesh_max[1], 197.0)

    def test_nozzle_and_probe_both_respect_margin(self):
        """The hard safety invariant: every corner of the mesh box —
        probe AND derived nozzle — must sit at least bed_mesh_margin
        away from its respective limit."""
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
        mesh_min, mesh_max = self._mesh_box(fileconfig)
        self._assert_safe(mesh_min, mesh_max, 192.0, 212.0, 1.875, 17.25)

    def test_zero_probe_offsets(self):
        """No probe offset → mesh box collapses to the bed minus the
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
        mesh_min, mesh_max = self._mesh_box(fileconfig)
        self.assertAlmostEqual(mesh_min[0], 15.0)
        self.assertAlmostEqual(mesh_min[1], 15.0)
        self.assertAlmostEqual(mesh_max[0], 185.0)
        self.assertAlmostEqual(mesh_max[1], 185.0)

    def test_sensor_right_of_nozzle(self):
        """Probe right of nozzle (offset_x > 0): the +X side of the
        mesh is bounded by the bed edge; the -X side is bounded by
        the nozzle's stepper margin."""
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
        mesh_min, mesh_max = self._mesh_box(fileconfig)
        # mesh_min_x = max(15 + 20, 15)             = 35   → nozzle 15
        # mesh_max_x = min(200 - 15 + 20, 200 - 15) = 185  → nozzle 165
        # mesh_min_y = max(15 + 0, 15)              = 15
        # mesh_max_y = min(200 - 15 + 0, 200 - 15)  = 185
        self.assertAlmostEqual(mesh_min[0], 35.0)
        self.assertAlmostEqual(mesh_max[0], 185.0)
        self.assertAlmostEqual(mesh_min[1], 15.0)
        self.assertAlmostEqual(mesh_max[1], 185.0)
        self._assert_safe(mesh_min, mesh_max, 200.0, 200.0, 20.0, 0.0)

    def test_sensor_left_of_nozzle(self):
        """Probe left of nozzle (offset_x < 0): the -X side of the
        mesh is bounded by the bed edge; the +X side is bounded by
        the nozzle's stepper margin."""
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
        mesh_min, mesh_max = self._mesh_box(fileconfig)
        # mesh_min_x = max(15 + (-20), 15)             = 15   → nozzle 35
        # mesh_max_x = min(200 - 15 + (-20), 200 - 15) = 165  → nozzle 185
        self.assertAlmostEqual(mesh_min[0], 15.0)
        self.assertAlmostEqual(mesh_max[0], 165.0)
        self._assert_safe(mesh_min, mesh_max, 200.0, 200.0, -20.0, 0.0)

    def test_sensor_behind_nozzle(self):
        """Probe behind nozzle (offset_y > 0): the +Y side of the mesh
        is bounded by the bed edge; the -Y side is bounded by the
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
        mesh_min, mesh_max = self._mesh_box(fileconfig)
        # mesh_min_y = max(15 + 25, 15)             = 40   → nozzle 15
        # mesh_max_y = min(200 - 15 + 25, 200 - 15) = 185  → nozzle 160
        self.assertAlmostEqual(mesh_min[1], 40.0)
        self.assertAlmostEqual(mesh_max[1], 185.0)
        self._assert_safe(mesh_min, mesh_max, 200.0, 200.0, 0.0, 25.0)

    def test_sensor_in_front_of_nozzle(self):
        """Probe in front of nozzle (offset_y < 0): the -Y side of the
        mesh is bounded by the bed edge; the +Y side is bounded by
        the nozzle's stepper margin."""
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
        mesh_min, mesh_max = self._mesh_box(fileconfig)
        # mesh_min_y = max(15 + (-15), 15)             = 15   → nozzle 30
        # mesh_max_y = min(200 - 15 + (-15), 200 - 15) = 170  → nozzle 185
        self.assertAlmostEqual(mesh_min[1], 15.0)
        self.assertAlmostEqual(mesh_max[1], 170.0)
        self._assert_safe(mesh_min, mesh_max, 200.0, 200.0, 0.0, -15.0)

    def assertAlmostEqual(self, first, second, places=6, msg=None):
        super().assertAlmostEqual(first, second, places=places, msg=msg)


if __name__ == "__main__":
    unittest.main()
