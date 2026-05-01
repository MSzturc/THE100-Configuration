#!/usr/bin/env python3
"""Tests for the brushless print pipeline.

Pins the contracts of PRINT_START, PRINT_END, CANCEL_PRINT, and
NOZZLE_WIPE_BED. These macros are co-designed for BDsensor collision
homing without a hardware brush, so the ordering and gating that keep
that working ARE the API. Breaking any of them silently regresses
first-layer quality or, worse, crashes the toolhead.

Tested invariants per macro:

PRINT_START
  * Phase 2 hits the soft-preheat temp via M109 BEFORE G32 fires --
    collision homing requires solid filament.
  * HEATSOAK_BED is called with both BED and SOAK params.
  * The thermal Z offset (SET_GCODE_OFFSET Z=...) is applied AFTER the
    final M109 EXTRUDER -- it compensates for nozzle expansion at print
    temp, so applying it before the ramp is meaningless.
  * The nozzle parks over the wipe strip BEFORE the final ramp so
    drips land on the wipe strip rather than on the part.
  * PRIME_LINE is the very last command -- residue from the final ramp
    has to hit the bed, not the part.

PRINT_END
  * TURN_OFF_HEATERS is issued BEFORE any extruder retract -- the
    cooldown window absorbs the retract heat and reduces ooze on the
    escape.
  * Tip-forming retract is two-stage (fast then slow).
  * Escape sequence: tiny Z (clear top layer) -> rapid XY (snap
    strings) -> full Z lift. Reversing this either hits the part or
    pulls a string up.
  * Park position never goes negative (CoreXY safety) and always lands
    inside `[safety_margin, axis_max - safety_margin]`.
  * Exit-purge is gated on `printer.extruder.temperature > 170`.
  * BED_MESH_CLEAR happens before the final park so the park move
    doesn't get warped by a stale mesh.

CANCEL_PRINT
  * CLEAR_PAUSE is the first command (don't strand the printer in a
    paused state).
  * Homed: delegates to PRINT_END for the full cleanup pipeline.
  * Not homed: degrades to the safe minimum (heaters/fans off, M84) --
    no XY moves without homing.
  * BASE_CANCEL_PRINT runs LAST so the SD job stops only after cleanup.

NOZZLE_WIPE_BED
  * Aborts via RESPOND when axes aren't homed (no blind XY move).
  * Default of 4 wipe pairs maps to 8 X-moves; WIPES param overrides.
  * Wipe travels stay inside [wipe_x_min, wipe_x_max] on X and at the
    rear `wipe_y` strip on Y -- never near the print.
  * Z toggles between `wipe_z` (low, scraping) and `wipe_travel_z`
    (high, traversal).
"""

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


def _printer_ctx(*, axis_max=(192.0, 212.0), homed="xyz",
                 extruder_temp=200.0):
    return _Attr(
        toolhead=_Attr(
            axis_maximum=_Attr(x=axis_max[0], y=axis_max[1]),
            homed_axes=homed,
        ),
        extruder=_Attr(temperature=extruder_temp),
    )


_NUMBER = r'-?\d+(?:\.\d+)?'


def _commands(rendered):
    """Return list of dicts: {idx, head, params, raw}.

    head is the uppercased first whitespace-delimited token (G1, M104,
    NOZZLE_WIPE_BED, ...). params is a flat dict of single-letter
    Klipper params (X/Y/Z/E/F/S) parsed out of the line where they
    occur as <LETTER><number>. Macro args like FAN=CPAP land in raw,
    not params -- callers grep raw for those."""
    out = []
    for raw in rendered.splitlines():
        line = raw.split(';', 1)[0].split('#', 1)[0].strip()
        if not line:
            continue
        head = line.split()[0].upper()
        params = {}
        for kv in re.finditer(
                r'(?<![A-Z_])([XYZEFS])\s*(' + _NUMBER + r')',
                line, re.IGNORECASE):
            params[kv.group(1).upper()] = float(kv.group(2))
        out.append({"idx": len(out), "head": head,
                    "params": params, "raw": line})
    return out


def _index_of(cmds, predicate):
    """First index where predicate(cmd) is true, or -1."""
    for cmd in cmds:
        if predicate(cmd):
            return cmd["idx"]
    return -1


def _all_indices(cmds, predicate):
    return [c["idx"] for c in cmds if predicate(c)]


class _PipelineFixture(unittest.TestCase):
    """Loads macros/print.cfg + macros/helpers/nozzle_wipe.cfg through
    the Klipper config parser so [constants] substitution happens, then
    exposes the post-substitution Jinja templates for rendering."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(cls.tmp, "macros", "helpers"))
        shutil.copy(
            os.path.join(REPO_ROOT, "macros", "print.cfg"),
            os.path.join(cls.tmp, "macros", "print.cfg"),
        )
        shutil.copy(
            os.path.join(REPO_ROOT, "macros", "helpers", "nozzle_wipe.cfg"),
            os.path.join(cls.tmp, "macros", "helpers", "nozzle_wipe.cfg"),
        )
        cfg = textwrap.dedent("""\
            [constants]
            print_volume_x: 192
            print_volume_y: 212
            safety_margin: 15
            center_x: round(${constants.print_volume_x} / 2)

            [include macros/helpers/nozzle_wipe.cfg]
            [include macros/print.cfg]
        """)
        path = os.path.join(cls.tmp, "printer.cfg")
        with open(path, "w") as f:
            f.write(cfg)
        reader = configfile.ConfigFileReader()
        cls.fc = reader.build_fileconfig_with_includes(
            reader.read_config_file(path), path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def _render(self, macro, *, params=None, ctx=None):
        body = self.fc.get("gcode_macro " + macro, "gcode")
        env = jinja2.Environment(
            variable_start_string="{",
            variable_end_string="}",
            block_start_string="{%",
            block_end_string="%}",
            keep_trailing_newline=True,
        )
        template = env.from_string(body)
        return template.render(
            printer=ctx if ctx is not None else _printer_ctx(),
            params=params or {},
        )


# ----------------------------- NOZZLE_WIPE_BED -----------------------

class NozzleWipeBedTest(_PipelineFixture):
    def test_aborts_when_axes_not_homed(self):
        """Without homing every G1 would crash -- the macro must
        respond with an error and emit no G1."""
        rendered = self._render(
            "NOZZLE_WIPE_BED", ctx=_printer_ctx(homed=""))
        self.assertIn("RESPOND TYPE=error", rendered)
        self.assertNotIn("G1", rendered.upper())

    def test_default_count_yields_four_wipe_pairs(self):
        """Default wipe_count=4 -> 4 back-and-forth pairs = 8 X-moves
        across the strip (excluding the entry/exit travel)."""
        cmds = _commands(self._render("NOZZLE_WIPE_BED"))
        # X-only G1 moves at speed F=wipe_speed (6000) are the wipes.
        wipes = [c for c in cmds
                 if c["head"] == "G1"
                 and "X" in c["params"]
                 and "Y" not in c["params"]
                 and c["params"].get("F") == 6000.0]
        self.assertEqual(
            len(wipes), 8,
            "expected 4 wipe pairs (8 X-moves), got {}".format(len(wipes)))

    def test_wipes_param_overrides_default_count(self):
        """WIPES=2 -> 4 X-moves (2 pairs)."""
        cmds = _commands(self._render(
            "NOZZLE_WIPE_BED", params={"WIPES": "2"}))
        wipes = [c for c in cmds
                 if c["head"] == "G1"
                 and "X" in c["params"]
                 and "Y" not in c["params"]
                 and c["params"].get("F") == 6000.0]
        self.assertEqual(len(wipes), 4)

    def test_wipe_strip_geometry(self):
        """Every wipe stays inside [wipe_x_min, wipe_x_max] on X and at
        the rear wipe_y on Y. Z toggles between wipe_z (0.2) and
        wipe_travel_z (6) -- never below 0 or above the travel ceiling."""
        cmds = _commands(self._render("NOZZLE_WIPE_BED"))
        for cmd in cmds:
            if cmd["head"] != "G1":
                continue
            p = cmd["params"]
            if "X" in p:
                self.assertGreaterEqual(p["X"], 15.0 - 1e-6, cmd["raw"])
                self.assertLessEqual(p["X"], 45.0 + 1e-6, cmd["raw"])
            if "Y" in p:
                self.assertAlmostEqual(p["Y"], 207.0, places=4,
                                       msg="Y must equal wipe_y=207")
            if "Z" in p:
                self.assertIn(p["Z"], (0.2, 6.0),
                              msg="Z must be wipe_z or wipe_travel_z")


# ------------------------------ PRINT_START --------------------------

class PrintStartTest(_PipelineFixture):
    def _cmds(self, params=None):
        return _commands(self._render("PRINT_START", params=params or {}))

    def test_soft_preheat_completes_before_g32(self):
        """M109 S150 (Phase 2 wait) MUST come before G32 -- collision
        homing relies on solid filament at the nozzle."""
        cmds = self._cmds()
        i_soft = _index_of(
            cmds, lambda c: c["head"] == "M109"
            and c["params"].get("S") == 150.0)
        i_g32 = _index_of(cmds, lambda c: c["head"] == "G32")
        self.assertGreaterEqual(i_soft, 0, "M109 S150 missing")
        self.assertGreaterEqual(i_g32, 0, "G32 missing")
        self.assertLess(i_soft, i_g32,
                        "M109 S150 must precede G32")

    def test_heatsoak_is_called_with_bed_and_soak_params(self):
        """HEATSOAK_BED has to receive S=BED and T=SOAK so the soak
        time the slicer requested actually happens."""
        rendered = self._render(
            "PRINT_START", params={"BED": "70", "SOAK": "5"})
        line = next(
            (l for l in rendered.splitlines()
             if l.lstrip().startswith("HEATSOAK_BED")),
            None)
        assert line is not None, "HEATSOAK_BED not invoked"
        self.assertIn("S=70", line)
        self.assertIn("T=5", line)

    def test_thermal_offset_applied_after_final_extruder_temp(self):
        """SET_GCODE_OFFSET Z=<thermal> is meaningful only AFTER the
        nozzle reached print temp -- compensates for thermal expansion
        from soft-preheat to print temp."""
        cmds = self._cmds()
        i_final_m109 = max(_all_indices(
            cmds, lambda c: c["head"] == "M109"), default=-1)
        i_offset = _index_of(
            cmds, lambda c: c["head"] == "SET_GCODE_OFFSET"
            and "MOVE=1" in c["raw"])
        self.assertGreater(i_final_m109, 0)
        self.assertGreater(i_offset, i_final_m109)

    def test_park_over_wipe_strip_before_final_ramp(self):
        """The toolhead parks at (wipe_x_min, wipe_y) BEFORE the final
        M109 EXTRUDER ramp so the ooze drops onto the wipe strip."""
        cmds = self._cmds()
        i_final_m109 = max(_all_indices(
            cmds, lambda c: c["head"] == "M109"))
        # The G1 immediately before that M109 must put us at (15, 207).
        i_park = _index_of(
            cmds, lambda c: c["head"] == "G1"
            and c["params"].get("X") == 15.0
            and c["params"].get("Y") == 207.0)
        self.assertGreater(i_park, 0)
        self.assertLess(i_park, i_final_m109)

    def test_prime_line_is_last(self):
        """Anything after PRIME_LINE leaks ooze onto the part."""
        cmds = self._cmds()
        last = cmds[-1]
        self.assertEqual(last["head"], "PRIME_LINE")

    def test_default_params_resolve(self):
        """Calling with no params must still render to valid g-code
        (BED=60, EXTRUDER=210, SOAK=0)."""
        cmds = self._cmds()
        # Default EXTRUDER=210 -> the *final* M109 picks that up.
        finals = [c for c in cmds if c["head"] == "M109"]
        self.assertEqual(finals[-1]["params"].get("S"), 210.0)


# ------------------------------- PRINT_END ---------------------------

class PrintEndTest(_PipelineFixture):
    def _cmds(self, *, extruder_temp=200.0):
        return _commands(self._render(
            "PRINT_END",
            ctx=_printer_ctx(extruder_temp=extruder_temp)))

    def test_heaters_off_before_any_retract(self):
        """Cool-while-retract: TURN_OFF_HEATERS must come before any
        G1 with E<0."""
        cmds = self._cmds()
        i_off = _index_of(cmds, lambda c: c["head"] == "TURN_OFF_HEATERS")
        i_first_retract = _index_of(
            cmds, lambda c: c["head"] == "G1"
            and "E" in c["params"] and c["params"]["E"] < 0)
        self.assertGreater(i_off, 0, "TURN_OFF_HEATERS missing")
        self.assertGreater(i_first_retract, 0, "no retract emitted")
        self.assertLess(i_off, i_first_retract)

    def test_two_stage_tip_forming_retract(self):
        """Tip-forming wants both a fast initial pull and a slow tail
        -- one stage doesn't form a clean tip."""
        cmds = self._cmds()
        retracts = [c for c in cmds
                    if c["head"] == "G1"
                    and "E" in c["params"] and c["params"]["E"] < 0
                    and "Z" not in c["params"]]
        self.assertGreaterEqual(
            len(retracts), 2,
            "expected at least two extruder-only retract moves")
        # First should be much faster than second (fast + slow tail).
        f_fast = retracts[0]["params"].get("F")
        f_slow = retracts[1]["params"].get("F")
        self.assertGreater(f_fast, f_slow,
                           "first retract must be faster than the tail")

    def test_escape_ordering_z_then_xy_then_z_lift(self):
        """Sequence: small Z hop (clear last layer) -> rapid XY (snap
        strings) -> full Z lift. Reverse triggers either part-collision
        or string-pull."""
        cmds = self._cmds()
        # The first Z-only move after retract is the small clear (0.2).
        # Then a rapid XY at high feedrate. Then the full-lift Z move.
        i_off = _index_of(cmds, lambda c: c["head"] == "TURN_OFF_HEATERS")
        post = [c for c in cmds if c["idx"] > i_off]
        z_clear = next(
            (c for c in post
             if c["head"] == "G1" and "Z" in c["params"]
             and "X" not in c["params"] and "Y" not in c["params"]),
            None)
        rapid_xy = next(
            (c for c in post
             if c["head"] == "G1" and "X" in c["params"] and "Y" in c["params"]
             and c["params"].get("F", 0) >= 12000),
            None)
        z_lift = next(
            (c for c in post
             if c["head"] == "G1" and "Z" in c["params"]
             and "X" not in c["params"] and "Y" not in c["params"]
             and c["params"]["Z"] > 1.0),
            None)
        assert z_clear is not None, "no small-Z clear move"
        assert rapid_xy is not None, "no rapid XY escape"
        assert z_lift is not None, "no full Z lift"
        self.assertLess(z_clear["idx"], rapid_xy["idx"])
        self.assertLess(rapid_xy["idx"], z_lift["idx"])
        self.assertLessEqual(
            z_clear["params"]["Z"], 0.5,
            "clear Z must stay tiny so a fresh top layer doesn't get hit")

    def test_park_position_inside_safe_bed_envelope(self):
        """CoreXY -- no negative coords. Final park (X=cx, Y=max_y -
        safety_margin) must sit inside the safe envelope."""
        cmds = self._cmds()
        # Last G1 with both X and Y is the park.
        park = next(
            (c for c in reversed(cmds)
             if c["head"] == "G1" and "X" in c["params"]
             and "Y" in c["params"]),
            None)
        assert park is not None, "no park move"
        park_x = park["params"]["X"]
        park_y = park["params"]["Y"]
        self.assertGreaterEqual(park_x, 15.0)
        self.assertLessEqual(park_x, 192.0 - 15.0)
        self.assertGreaterEqual(park_y, 15.0)
        self.assertLessEqual(park_y, 212.0 - 15.0)
        # CoreXY: also assert center.
        self.assertAlmostEqual(park_x, 96.0, places=2)

    def test_exit_purge_runs_when_hot(self):
        """At extruder temperature 200 the exit-purge emits a positive
        E move on the wipe strip."""
        cmds = self._cmds(extruder_temp=200.0)
        purge = [c for c in cmds
                 if c["head"] == "G1"
                 and c["params"].get("E", 0) > 0]
        self.assertTrue(purge,
                        "exit-purge missing when nozzle hot enough")

    def test_exit_purge_skipped_when_cold(self):
        """At extruder temperature 100 (below the 170 gate) the
        exit-purge must NOT extrude -- cold extrusion damages the
        gear."""
        cmds = self._cmds(extruder_temp=100.0)
        purge = [c for c in cmds
                 if c["head"] == "G1"
                 and c["params"].get("E", 0) > 0]
        self.assertFalse(
            purge,
            "exit-purge ran cold (E>0 below 170 C threshold)")

    def test_bed_mesh_clear_before_park(self):
        """The final park move sometimes uses Z=wipe_travel_z; if the
        mesh is still active, that Z gets warped. Clear first."""
        cmds = self._cmds()
        i_clear = _index_of(cmds, lambda c: c["head"] == "BED_MESH_CLEAR")
        # Park = the last G1 with both X and Y.
        i_park = max(_all_indices(
            cmds, lambda c: c["head"] == "G1"
            and "X" in c["params"] and "Y" in c["params"]))
        self.assertGreater(i_clear, 0, "BED_MESH_CLEAR missing")
        self.assertLess(i_clear, i_park)

    def test_speed_and_extrude_overrides_reset_at_end(self):
        """M220/M221 back to 100 so a follow-up print starts clean."""
        cmds = self._cmds()
        m220s = [c for c in cmds if c["head"] == "M220"]
        m221s = [c for c in cmds if c["head"] == "M221"]
        self.assertTrue(m220s and m220s[-1]["params"].get("S") == 100.0)
        self.assertTrue(m221s and m221s[-1]["params"].get("S") == 100.0)


# ----------------------------- CANCEL_PRINT --------------------------

class CancelPrintTest(_PipelineFixture):
    def test_clear_pause_is_first(self):
        """If CANCEL is invoked while paused, every later G1 would
        otherwise sit in the pause queue."""
        cmds = _commands(self._render("CANCEL_PRINT"))
        self.assertEqual(cmds[0]["head"], "CLEAR_PAUSE")

    def test_homed_path_delegates_to_print_end(self):
        """When axes are homed, cleanup IS PRINT_END -- not a parallel
        re-implementation that drifts."""
        rendered = self._render(
            "CANCEL_PRINT", ctx=_printer_ctx(homed="xyz"))
        cmds = _commands(rendered)
        heads = [c["head"] for c in cmds]
        self.assertIn("PRINT_END", heads)
        # Must NOT inline the not-homed branch's cleanup.
        self.assertNotIn("M84", heads,
                         "homed path leaked into not-homed branch")

    def test_unhomed_path_skips_xy_and_emits_safe_minimum(self):
        """No homing -> no XY moves; just heaters/fans off + M84."""
        rendered = self._render(
            "CANCEL_PRINT", ctx=_printer_ctx(homed=""))
        cmds = _commands(rendered)
        heads = [c["head"] for c in cmds]
        self.assertIn("TURN_OFF_HEATERS", heads)
        self.assertIn("M84", heads)
        self.assertNotIn("PRINT_END", heads,
                         "PRINT_END must not run without homing")
        # No raw G0/G1 moves emitted.
        self.assertFalse(
            any(c["head"] in ("G0", "G1") for c in cmds),
            "unhomed cancel must not emit G1")

    def test_base_cancel_print_is_last(self):
        """BASE_CANCEL_PRINT actually stops the SD job. It MUST run
        after cleanup, never before -- otherwise the cleanup is racing
        Klipper's own cancel handling."""
        for homed in ("xyz", ""):
            with self.subTest(homed=homed):
                cmds = _commands(self._render(
                    "CANCEL_PRINT", ctx=_printer_ctx(homed=homed)))
                self.assertEqual(cmds[-1]["head"], "BASE_CANCEL_PRINT")
                # SDCARD_RESET_FILE must precede BASE_CANCEL_PRINT.
                i_sd = _index_of(
                    cmds, lambda c: c["head"] == "SDCARD_RESET_FILE")
                self.assertGreater(i_sd, 0)
                self.assertLess(i_sd, cmds[-1]["idx"])


if __name__ == "__main__":
    unittest.main()
