#!/usr/bin/env python3
"""Tests for hotends/dual_wiring.cfg alias resolution.

Verifies that the include chain
    config/hotends/std6-v2.cfg
        -> [include dual_wiring.cfg]
combined with the BTT Kraken board pin map
    config/boards/btt-kraken/config.cfg  ([board_pins kraken] aliases)
ends up wiring the dual heater on PF6 and PF7 (and the thermistor on PB1).

The check runs in two stages, mirroring how real Klippy resolves a heater_pin:
  1. The enhanced Klipper config parser (MSzturc/klipper fork) merges the
     includes and exposes [multi_pin dual_heater].pins as alias *names*
     (E_HEATER, E_HEATER_2) -- aliases are NOT substituted at config-load time.
  2. The actual substitution is done by klippy/pins.py:PinResolver when MCU
     commands are emitted. We instantiate that class directly with the
     aliases harvested from [board_pins kraken] and assert that an MCU
     command containing 'pin=E_HEATER' / 'pin=E_HEATER_2' / 'pin=E_TEMPERATURE'
     is rewritten to PF6 / PF7 / PB1.
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
import pins  # noqa: E402


def parse_aliases(aliases_value):
    """Mirror board_pins.py: split the [board_pins …] aliases value on
    newlines and commas, then on '=' for each name/value pair."""
    result = {}
    cleaned = aliases_value.replace("\n", ",")
    for entry in cleaned.split(","):
        entry = entry.strip()
        if not entry:
            continue
        name, sep, value = entry.partition("=")
        if not sep:
            continue
        result[name.strip()] = value.strip()
    return result


class DualWiringResolutionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Mirror the real on-disk layout so that the relative includes
        # inside std6-v2.cfg ('[include dual_wiring.cfg]') resolve.
        for sub in ("config/hotends", "config/boards/btt-kraken"):
            os.makedirs(os.path.join(self.tmp, sub), exist_ok=True)
        for rel in (
            "config/hotends/std6-v2.cfg",
            "config/hotends/dual_wiring.cfg",
            "config/boards/btt-kraken/config.cfg",
        ):
            shutil.copy(os.path.join(REPO_ROOT, rel),
                        os.path.join(self.tmp, rel))
        # Minimal printer.cfg fixture: enough to pull both files into the
        # merged fileconfig, nothing else. We are not booting Klippy --
        # missing steppers / kinematics never matter at the parse layer.
        printer_cfg = textwrap.dedent("""\
            [include config/boards/btt-kraken/config.cfg]
            [include config/hotends/std6-v2.cfg]
            """)
        self.printer_cfg = os.path.join(self.tmp, "printer.cfg")
        with open(self.printer_cfg, "w") as f:
            f.write(printer_cfg)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _load(self):
        reader = configfile.ConfigFileReader()
        data = reader.read_config_file(self.printer_cfg)
        return reader.build_fileconfig_with_includes(data, self.printer_cfg)

    def test_dual_wiring_include_brings_in_multi_pin_section(self):
        """std6-v2.cfg must transitively include dual_wiring.cfg, which
        adds [multi_pin dual_heater] and rewires [extruder].heater_pin
        to point at it."""
        fc = self._load()
        self.assertTrue(
            fc.has_section("multi_pin dual_heater"),
            "[multi_pin dual_heater] section missing -- "
            "[include dual_wiring.cfg] did not resolve",
        )
        self.assertEqual(
            fc.get("extruder", "heater_pin").strip(),
            "multi_pin:dual_heater",
        )

    def test_multi_pin_pins_list_uses_aliases_in_order(self):
        """[multi_pin dual_heater].pins must list the alias names, in the
        wired order: heater 1 (PF6) first, heater 2 (PF7) second.
        Order matters -- if the printer ever needs per-heater PWM the
        first entry is 'channel A'."""
        fc = self._load()
        items = [p.strip()
                 for p in fc.get("multi_pin dual_heater", "pins").split(",")
                 if p.strip()]
        self.assertEqual(items, ["E_HEATER", "E_HEATER_2"])

    def test_extruder_sensor_pin_uses_alias(self):
        """The thermistor goes through the same alias indirection."""
        fc = self._load()
        self.assertEqual(
            fc.get("extruder", "sensor_pin").strip(),
            "E_TEMPERATURE",
        )

    def test_kraken_aliases_parse_via_real_klippy_getlists(self):
        """Real Klippy code path: board_pins.py loads the [board_pins …]
        aliases via `config.getlists('aliases', seps=('=', ','), count=2)`.
        That parser splits the raw value on ',' first and on '=' second,
        and crucially does NOT treat newlines as separators. Any
        comma-less line break inside the aliases value glues two
        name=value pairs into one entry that splits into THREE '=' parts
        on the second pass and trips count=2 with
            'Option 'aliases' in section 'board_pins kraken' must have 2 elements'
        We instantiate a ConfigWrapper exactly as Klippy does at startup
        (printer=None is fine: getlists never touches it) and exercise
        the same call. If the kraken config is well-formed every line
        ends with a comma, no entry splits on a newline, getlists
        returns clean (name, value) pairs."""
        fc = self._load()
        wrapper = configfile.ConfigWrapper(
            printer=None,
            fileconfig=fc,
            access_tracking={},
            section="board_pins kraken",
        )
        # Reproduce board_pins.py:14 verbatim. If a comma is missing
        # anywhere in [board_pins kraken].aliases, this raises
        # configparser.Error here -- same error the user hits on the
        # printer.
        aliases = wrapper.getlists("aliases", seps=("=", ","), count=2)
        # And the dual-heater wiring must show up among them.
        as_dict = {name: value for name, value in aliases}
        self.assertEqual(as_dict.get("E_HEATER"), "PF6")
        self.assertEqual(as_dict.get("E_HEATER_2"), "PF7")
        self.assertEqual(as_dict.get("E_TEMPERATURE"), "PB1")

    def test_kraken_aliases_define_expected_hardware_pins(self):
        """[board_pins kraken] must define the three aliases the
        dual_wiring path depends on, mapped to the BTT Kraken's actual
        STM32H723 GPIOs."""
        fc = self._load()
        aliases = parse_aliases(fc.get("board_pins kraken", "aliases"))
        self.assertEqual(aliases.get("E_HEATER"), "PF6")
        self.assertEqual(aliases.get("E_HEATER_2"), "PF7")
        self.assertEqual(aliases.get("E_TEMPERATURE"), "PB1")

    def test_pin_resolver_rewrites_aliases_to_hardware_pins(self):
        """End-to-end: feed the [board_pins kraken] aliases into the
        same PinResolver class board_pins.py uses at runtime, and
        verify that a synthetic MCU command containing
            pin=E_HEATER       -> pin=PF6
            pin=E_HEATER_2     -> pin=PF7
            pin=E_TEMPERATURE  -> pin=PB1
        This is the moment the alias actually becomes a hardware pin --
        if this fails the heaters will never fire."""
        fc = self._load()
        aliases = parse_aliases(fc.get("board_pins kraken", "aliases"))

        resolver = pins.PinResolver()
        for name, value in aliases.items():
            # Skip reserved-pin markers (<...>); board_pins.py handles
            # those via reserve_pin, not alias_pin. None appear in the
            # current kraken config but stay defensive.
            if value.startswith("<") and value.endswith(">"):
                continue
            resolver.alias_pin(name, value)

        # PinResolver.update_command rewrites tokens of the form
        # ' pin=NAME' or '_pin=NAME'. Build commands that match.
        self.assertEqual(
            resolver.update_command("config_digital_out pin=E_HEATER"),
            "config_digital_out pin=PF6",
        )
        self.assertEqual(
            resolver.update_command("config_digital_out pin=E_HEATER_2"),
            "config_digital_out pin=PF7",
        )
        self.assertEqual(
            resolver.update_command("config_analog_in pin=E_TEMPERATURE"),
            "config_analog_in pin=PB1",
        )


if __name__ == "__main__":
    unittest.main()
