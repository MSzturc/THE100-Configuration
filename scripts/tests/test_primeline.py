#!/usr/bin/env python3
"""Tests for the PRIME_LINE macro.

Pins the contract that the macro derives every position and extrusion
amount from the Klipper runtime (printer.toolhead.axis_maximum and
printer.configfile.settings.extruder) instead of hard-coded values --
only safety_margin comes from the fork-specific [constants] pipeline,
since stock Klipper has no equivalent. This keeps the macro usable on
both the MSzturc fork and on mainline Klipper.

Extrusion follows the volumetric formula
    E = (line_width * layer_height * line_length) / filament_area
with line_width = 1.2 * nozzle_diameter, layer_height = 0.6 *
nozzle_diameter (typical fat-prime values for first-layer adhesion)
and filament_area = pi * (filament_diameter / 2)^2.

Coordinate invariants:
  * Both prime lines run inside [safety_margin, bed_x - safety_margin]
    on X and stay above safety_margin on Y so the nozzle never crashes
    a stepper limit.
  * Line length and extrusion both scale linearly with the X axis
    maximum from the toolhead.
  * Extrusion scales quadratically with nozzle_diameter (width AND
    height both scale linearly with the nozzle).
"""

import math
import os
import re
import shutil
import sys
import tempfile
import textwrap
import unittest

import jinja2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
WORKSPACE_ROOT = os.path.abspath(os.path.join(REPO_ROOT, ".."))
KLIPPY_DIR = os.path.join(WORKSPACE_ROOT, "klipper", "klippy")

sys.path.insert(0, KLIPPY_DIR)
import configfile  # noqa: E402


class _Attr(dict):
    """dict that also supports attribute access, so a Jinja2 template
    can read both printer.toolhead.axis_maximum.x and
    printer["toolhead"]["axis_maximum"]["x"]."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e


def _printer_ctx(*, axis_max_x, axis_max_y, nozzle, filament):
    """Mirror the parts of Klipper's `printer` object PRIME_LINE
    actually reads. Anything outside this surface is none of the
    macro's business."""
    return _Attr(
        toolhead=_Attr(
            axis_maximum=_Attr(x=axis_max_x, y=axis_max_y),
        ),
        configfile=_Attr(
            settings=_Attr(
                extruder=_Attr(
                    nozzle_diameter=nozzle,
                    filament_diameter=filament,
                ),
            ),
        ),
    )


def _parse_moves(gcode):
    """Return a list of dicts, one per G0/G1 line, with X/Y/Z/E/F as floats."""
    moves = []
    for raw in gcode.splitlines():
        line = raw.split(';', 1)[0]
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        head_match = re.match(r'^(G0|G1)\b', line, re.IGNORECASE)
        if not head_match:
            continue
        rest = line[head_match.end():]
        params = {}
        for kv in re.finditer(r'([XYZEF])\s*(-?\d+(?:\.\d+)?)',
                              rest, re.IGNORECASE):
            params[kv.group(1).upper()] = float(kv.group(2))
        moves.append(params)
    return moves


def _prime_lines(moves):
    """The two extruding travels along X (the priming lines themselves).
    Identified by: G1 with both X movement AND a positive E (E>1 filters
    out small retract-restores)."""
    return [m for m in moves if 'X' in m and 'E' in m and m['E'] > 1.0]


class PrimeLineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "macros", "helpers"))
        shutil.copy(
            os.path.join(REPO_ROOT, "macros", "helpers", "primeline.cfg"),
            os.path.join(self.tmp, "macros", "helpers", "primeline.cfg"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _render(self, *, nozzle=0.4, filament=1.75,
                axis_max=(192.0, 212.0), safety_margin=15):
        body = ("safety_margin: {}".format(safety_margin)
                if safety_margin is not None else "")
        cfg = textwrap.dedent("""\
            [constants]
            {body}

            [include macros/helpers/primeline.cfg]
        """).format(body=body)
        path = os.path.join(self.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)

        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(path)
        fc = reader.build_fileconfig_with_includes(data, path)
        template_source = fc.get("gcode_macro PRIME_LINE", "gcode")

        env = jinja2.Environment(
            variable_start_string="{",
            variable_end_string="}",
            block_start_string="{%",
            block_end_string="%}",
            keep_trailing_newline=True,
        )
        template = env.from_string(template_source)
        ctx = _printer_ctx(
            axis_max_x=axis_max[0], axis_max_y=axis_max[1],
            nozzle=nozzle, filament=filament,
        )
        return template.render(printer=ctx)

    @staticmethod
    def _expected_e(nozzle, filament, line_len):
        line_width = 1.2 * nozzle
        layer_height = 0.6 * nozzle
        fil_area = math.pi * (filament / 2.0) ** 2
        return line_width * layer_height * line_len / fil_area

    def test_prime_lines_stay_within_safety_margin(self):
        """Every priming-line move sits inside [margin, bed_x - margin]
        on X and above margin on Y -- never crashes a stepper limit."""
        gcode = self._render(axis_max=(192, 212), safety_margin=15)
        lines = _prime_lines(_parse_moves(gcode))
        self.assertGreaterEqual(len(lines), 2,
                                "expected at least two priming lines")
        for move in lines:
            self.assertGreaterEqual(move['X'], 15.0 - 1e-6,
                                    "X off bed (-X side)")
            self.assertLessEqual(move['X'], 192 - 15.0 + 1e-6,
                                 "X off bed (+X side)")
            if 'Y' in move:
                self.assertGreaterEqual(move['Y'], 15.0 - 1e-6,
                                        "Y off bed (front)")
                self.assertLessEqual(move['Y'], 212 - 15.0 + 1e-6,
                                     "Y off bed (back)")

    def test_prime_line_extrusion_matches_volumetric_formula(self):
        """E for each priming line equals the volumetric formula
        within a 0.05 mm tolerance (covers rounding inside the macro)."""
        nozzle, filament, margin, bed_x = 0.4, 1.75, 15, 192
        gcode = self._render(nozzle=nozzle, filament=filament,
                             axis_max=(bed_x, 212), safety_margin=margin)
        line_len = bed_x - 2 * margin
        expected = self._expected_e(nozzle, filament, line_len)
        for move in _prime_lines(_parse_moves(gcode)):
            self.assertAlmostEqual(
                move['E'], expected, delta=0.05,
                msg="E={} but volumetric formula yields {}".format(
                    move['E'], expected),
            )

    def test_extrusion_scales_quadratically_with_nozzle_diameter(self):
        """Doubling the nozzle (read from
        printer.configfile.settings.extruder.nozzle_diameter)
        quadruples the extrusion -- line_width and layer_height both
        scale linearly with the nozzle."""
        small = _prime_lines(_parse_moves(
            self._render(nozzle=0.4)))[0]['E']
        large = _prime_lines(_parse_moves(
            self._render(nozzle=0.8)))[0]['E']
        self.assertAlmostEqual(large / small, 4.0, places=2)

    def test_extrusion_scales_inversely_with_filament_area(self):
        """Switching to 2.85mm filament cuts E by (1.75/2.85)^2 -- the
        cross-section grows quadratically so the same volume needs
        proportionally less filament length. Confirms that
        printer.configfile.settings.extruder.filament_diameter is the
        actual source of truth, not a hard-coded 1.75."""
        e_175 = _prime_lines(_parse_moves(
            self._render(filament=1.75)))[0]['E']
        e_285 = _prime_lines(_parse_moves(
            self._render(filament=2.85)))[0]['E']
        self.assertAlmostEqual(e_285 / e_175,
                               (1.75 / 2.85) ** 2, places=2)

    def test_line_length_scales_with_toolhead_axis_maximum(self):
        """Bigger bed (= higher printer.toolhead.axis_maximum.x) ->
        longer prime line -> proportionally more filament."""
        small = _prime_lines(_parse_moves(
            self._render(axis_max=(192, 212))))[0]
        large = _prime_lines(_parse_moves(
            self._render(axis_max=(300, 212))))[0]
        # Endpoints
        self.assertAlmostEqual(small['X'], 192 - 15, places=2)
        self.assertAlmostEqual(large['X'], 300 - 15, places=2)
        # Extrusion ratio matches length ratio
        ratio_e = large['E'] / small['E']
        ratio_l = (300 - 30) / (192 - 30)
        self.assertAlmostEqual(ratio_e, ratio_l, places=2)

    def test_safety_margin_override_shifts_lines_inward(self):
        """Increasing safety_margin (the only [constants] knob the
        macro still reads) pulls the start point in and shortens the
        line; extrusion drops accordingly."""
        m15 = _prime_lines(_parse_moves(
            self._render(safety_margin=15)))[0]
        m25 = _prime_lines(_parse_moves(
            self._render(safety_margin=25)))[0]
        # End point shifts inward
        self.assertAlmostEqual(m25['X'], 192 - 25, places=2)
        # E is smaller for the bigger margin (shorter line)
        self.assertLess(m25['E'], m15['E'])

    def test_safety_margin_falls_back_when_constant_undefined(self):
        """A printer.cfg without [constants].safety_margin keeps the
        macro working via the :15 default -- so the fork-specific
        constants pipeline is optional, not required."""
        gcode = self._render(safety_margin=None)
        line = _prime_lines(_parse_moves(gcode))[0]
        # Default margin is 15 -> end at 192-15 = 177
        self.assertAlmostEqual(line['X'], 192 - 15, places=2)


if __name__ == "__main__":
    unittest.main()
