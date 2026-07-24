import importlib.util
import sys
import time
import types
import unittest
from pathlib import Path


class AppControllerDateChangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_modules = {
            name: sys.modules.get(name)
            for name in (
                "config_manager",
                "netutils",
                "weather",
                "display_manager",
                "display_utils",
                "image_manager",
                "wifi_manager",
                "chime",
                "discord_notifier",
                "presence_manager",
                "env_manager",
            )
        }
        cls.sync_calls = []
        cls.clear_calls = []

        config_module = types.ModuleType("config_manager")
        config_module.config_manager = types.SimpleNamespace(
            get=lambda _key, default=None: default,
            get_global=lambda _key, default=None: default,
        )
        sys.modules["config_manager"] = config_module

        netutils_module = types.ModuleType("netutils")
        netutils_module.sync_time = lambda: cls.sync_calls.append(True)
        netutils_module.get_local_time = lambda offset=0: (2026, 7, 17, 0, 0, 0, 4, 198)
        sys.modules["netutils"] = netutils_module

        weather_module = types.ModuleType("weather")
        weather_module.fetch_current_weather = lambda *_args: None
        weather_module.fetch_weather_forecast = lambda *_args, **_kwargs: []
        sys.modules["weather"] = weather_module

        display_module = types.ModuleType("display_manager")
        for name in (
            "update_page_weather",
            "update_page_time_image",
            "update_page_birthday",
            "update_page_image_preview",
        ):
            setattr(display_module, name, lambda *_args, **_kwargs: None)
        sys.modules["display_manager"] = display_module

        display_utils_module = types.ModuleType("display_utils")
        display_utils_module.release_display_workspace = lambda: None
        display_utils_module.clear_display_and_sleep = lambda: cls.clear_calls.append(True)
        sys.modules["display_utils"] = display_utils_module

        image_module = types.ModuleType("image_manager")
        image_module.image_catalog = types.SimpleNamespace()
        image_module.image_store = types.SimpleNamespace()
        sys.modules["image_manager"] = image_module

        wifi_module = types.ModuleType("wifi_manager")
        wifi_module.reset_wifi_and_reboot = lambda: None
        sys.modules["wifi_manager"] = wifi_module

        chime_module = types.ModuleType("chime")
        chime_module.Chime = lambda *_args, **_kwargs: None
        sys.modules["chime"] = chime_module

        discord_module = types.ModuleType("discord_notifier")
        discord_module.send_lan_ip = lambda *_args: False
        discord_module.send_presence_session = lambda *_args: False
        discord_module.send_presence_summary = lambda *_args: False
        sys.modules["discord_notifier"] = discord_module

        presence_module = types.ModuleType("presence_manager")
        presence_module.PresenceManager = type("PresenceManager", (), {})
        presence_module.set_presence_manager = lambda *_args: None
        sys.modules["presence_manager"] = presence_module

        env_module = types.ModuleType("env_manager")
        env_module.EnvManager = type(
            "EnvManager", (), {"__init__": lambda self, *_a, **_kw: None, "update": lambda self, *_a, **_kw: None}
        )
        env_module.set_env_manager = lambda *_args: None
        sys.modules["env_manager"] = env_module

        source = Path(__file__).resolve().parents[1] / "src" / "app_controller.py"
        spec = importlib.util.spec_from_file_location("app_controller_test_target", source)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        for name, module in cls.original_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def setUp(self):
        self.sync_calls.clear()
        self.clear_calls.clear()

    def test_new_day_resets_weather_retry_gates(self):
        state = types.SimpleNamespace(
            last_day=16,
            current_weather=(30, "Clouds"),
            current_weather_last_updated=123,
            current_weather_last_attempted=456,
            weather_forecast=[("07-16", 29, "Clouds", 20)],
            weather_forecast_last_updated=789,
            weather_forecast_last_attempted=987,
            is_first_run=False,
        )
        controller = object.__new__(self.module.AppController)
        controller.state = state

        self.assertTrue(controller._handle_date_change(17))
        self.assertEqual(state.last_day, 17)
        self.assertIsNone(state.current_weather)
        self.assertIsNone(state.weather_forecast)
        self.assertEqual(state.current_weather_last_updated, -1)
        self.assertEqual(state.current_weather_last_attempted, -1)
        self.assertEqual(state.weather_forecast_last_updated, -1)
        self.assertEqual(state.weather_forecast_last_attempted, -1)
        self.assertEqual(self.sync_calls, [True])

        self.assertFalse(controller._handle_date_change(17))
        self.assertEqual(self.sync_calls, [True])

    def test_new_day_allows_immediate_weather_requests(self):
        state = types.SimpleNamespace(
            last_day=16,
            current_weather=(30, "Clouds"),
            current_weather_last_updated=123,
            current_weather_last_attempted=456,
            weather_forecast=[("07-16", 29, "Clouds", 20)],
            weather_forecast_last_updated=789,
            weather_forecast_last_attempted=987,
            is_first_run=False,
        )
        controller = object.__new__(self.module.AppController)
        controller.state = state
        controller.api_key = "test-key"
        controller.location = "Zhunan"
        controller.time_zone_offset = 8

        original_ticks_ms = getattr(time, "ticks_ms", None)
        original_ticks_diff = getattr(time, "ticks_diff", None)
        original_current = self.module.fetch_current_weather
        original_forecast = self.module.fetch_weather_forecast
        calls = []
        try:
            time.ticks_ms = lambda: 100000
            time.ticks_diff = lambda new, old: new - old
            self.module.fetch_current_weather = lambda *_args: calls.append("current") or (30, "Clouds")
            self.module.fetch_weather_forecast = lambda *_args, **kwargs: calls.append(
                ("forecast", kwargs["days_limit"])
            ) or [("07-17", 29, "Clouds", 20)]

            controller._handle_date_change(17)

            self.assertTrue(controller._update_weather())
            self.assertEqual(calls, ["current", ("forecast", 5)])
        finally:
            self.module.fetch_current_weather = original_current
            self.module.fetch_weather_forecast = original_forecast
            if original_ticks_ms is None:
                delattr(time, "ticks_ms")
            else:
                time.ticks_ms = original_ticks_ms
            if original_ticks_diff is None:
                delattr(time, "ticks_diff")
            else:
                time.ticks_diff = original_ticks_diff

    def test_confirmed_away_transition_clears_display_once(self):
        class FakePresence:
            def __init__(self):
                self.states = iter((True, False, False, True))
                self.responses = iter((False, True, False, False))
                self.current_state = None

            def update(self, *_args):
                self.current_state = next(self.states)
                return next(self.responses)

            def flush_discord(self):
                return False

        state = types.SimpleNamespace(
            last_touch_time=-1,
            is_first_run=False,
            partial_update=True,
            last_minute=-1,
        )
        adc_values = iter((200, 60000, 200, 200))
        hardware = types.SimpleNamespace(
            get_adc_value=lambda: next(adc_values),
            get_touch_state=lambda: None,
            handle_button_long_press=lambda _callback: None,
        )
        class TestController(self.module.AppController):
            pass

        controller = object.__new__(TestController)
        controller.state = state
        controller.hw = hardware
        controller.lan_server = None
        controller.presence = FakePresence()
        controller.env = types.SimpleNamespace(update=lambda *_args, **_kwargs: None)
        controller.time_zone_offset = 8
        controller.boot_ms = 0
        # Already latched, so this test does not need the ticks_* shims.
        controller.min_uptime_reached = True
        controller.auto_reset_blocked = True
        controller._send_startup_discord_if_ready = lambda: False
        controller._startup_discord_pending = lambda: False
        display_updates = []
        controller._handle_date_change = lambda _day: False
        controller._perform_chime = lambda _time: None
        controller._update_sensor_data = lambda: None
        controller._update_weather = lambda: False
        controller._update_display = lambda _time: display_updates.append(True)
        controller.handle_touch = lambda _touch: None

        original_consume_preview = getattr(self.module.image_store, "consume_preview", None)
        self.module.image_store.consume_preview = lambda: None
        try:
            for _ in range(4):
                controller.run_main_loop()
        finally:
            if original_consume_preview is None:
                delattr(self.module.image_store, "consume_preview")
            else:
                self.module.image_store.consume_preview = original_consume_preview

        self.assertEqual(self.clear_calls, [True])
        self.assertEqual(len(display_updates), 2)
        self.assertFalse(state.is_first_run)
        self.assertTrue(state.partial_update)


class DiscordStallResetTests(unittest.TestCase):
    """The reboot of last resort must fire only when Discord is genuinely wedged."""

    @classmethod
    def setUpClass(cls):
        cls.module = AppControllerDateChangeTests.module

    def _controller(self, failures, pending, uptime_ms, blocked=False,
                    persist_failed=False, uptime_latched=False):
        controller = object.__new__(self.module.AppController)
        controller.presence = types.SimpleNamespace(
            discord_mem_failures=failures,
            discord_failures=failures,
            pending_summary=pending,
            pending_session=None,
            pending_persist_failed=persist_failed,
        )
        controller.auto_reset_blocked = blocked
        controller.min_uptime_reached = uptime_latched
        controller.boot_ms = 0
        original_ticks_ms = getattr(time, "ticks_ms", None)
        original_ticks_diff = getattr(time, "ticks_diff", None)
        time.ticks_ms = lambda: uptime_ms
        time.ticks_diff = lambda new, old: new - old
        self.addCleanup(self._restore_ticks, original_ticks_ms, original_ticks_diff)
        return controller

    def _restore_ticks(self, original_ticks_ms, original_ticks_diff):
        if original_ticks_ms is None:
            if hasattr(time, "ticks_ms"):
                delattr(time, "ticks_ms")
        else:
            time.ticks_ms = original_ticks_ms
        if original_ticks_diff is None:
            if hasattr(time, "ticks_diff"):
                delattr(time, "ticks_diff")
        else:
            time.ticks_diff = original_ticks_diff

    def _assert_no_reset(self, controller):
        """_check_discord_stall would import machine to reboot; reaching it raises."""
        sys.modules.pop("machine", None)
        controller._check_discord_stall()

    def test_no_reset_below_the_failure_threshold(self):
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES - 1, "20260725,1,1,1,1", 60 * 60 * 1000
        )
        self._assert_no_reset(controller)

    def test_no_reset_when_nothing_is_pending(self):
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES + 5, None, 60 * 60 * 1000
        )
        self._assert_no_reset(controller)

    def test_no_reset_before_minimum_uptime(self):
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES + 5, "20260725,1,1,1,1", 60 * 1000
        )
        self._assert_no_reset(controller)

    def test_no_reset_while_cooldown_blocks_it(self):
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES + 5,
            "20260725,1,1,1,1",
            60 * 60 * 1000,
            blocked=True,
        )
        self._assert_no_reset(controller)

    def test_no_reset_for_non_memory_failures(self):
        """A deleted webhook must never be 'fixed' by rebooting every two hours."""
        controller = self._controller(
            0, "20260725,1,1,1,1", 60 * 60 * 1000, uptime_latched=True
        )
        # Plenty of total failures, but none of them memory-related.
        controller.presence.discord_failures = 500
        controller.presence.discord_mem_failures = 0
        self._assert_no_reset(controller)

    def test_no_reset_when_pending_never_reached_flash(self):
        """Rebooting would discard a notification that only exists in RAM."""
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES + 5,
            "20260725,1,1,1,1",
            60 * 60 * 1000,
            persist_failed=True,
            uptime_latched=True,
        )
        self._assert_no_reset(controller)

    def test_uptime_latch_survives_ticks_wraparound(self):
        """ticks_diff is only valid for ~6.2 days; the latch must not un-set."""
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES,
            "20260725,1,1,1,1",
            self.module.DISCORD_STALL_MIN_UPTIME_MS + 1,
        )
        self.assertFalse(controller.min_uptime_reached)
        original_allowed = self.module.AppController._auto_reset_allowed
        try:
            # Block before rebooting, so only the latch transition is exercised.
            self.module.AppController._auto_reset_allowed = lambda _self: False
            controller._check_discord_stall()
            self.assertTrue(controller.min_uptime_reached)

            # Simulate the counter wrapping to a bogus negative difference.
            time.ticks_diff = lambda new, old: -1
            controller._check_discord_stall()
            self.assertTrue(controller.min_uptime_reached)
        finally:
            self.module.AppController._auto_reset_allowed = original_allowed

    def test_latch_is_set_before_any_stall_exists(self):
        """The latch must not wait for a stall: by then ticks_diff may be useless."""
        controller = self._controller(
            0, None, self.module.DISCORD_STALL_MIN_UPTIME_MS + 1
        )
        self.assertFalse(controller.min_uptime_reached)
        self._assert_no_reset(controller)
        self.assertTrue(controller.min_uptime_reached)

    def test_cooldown_file_is_not_read_on_every_loop(self):
        """While stalled, the cooldown file must be re-read only periodically."""
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES + 1,
            "20260725,1,1,1,1",
            60 * 60 * 1000,
            uptime_latched=True,
        )
        reads = []
        original_allowed = self.module.AppController._auto_reset_allowed
        try:
            self.module.AppController._auto_reset_allowed = (
                lambda _self: reads.append(True) or False
            )
            controller._check_discord_stall()
            self.assertEqual(reads, [], "31 failures is not a multiple of the threshold")

            controller.presence.discord_mem_failures = (
                self.module.DISCORD_STALL_RESET_FAILURES * 2
            )
            controller._check_discord_stall()
            self.assertEqual(len(reads), 1)
        finally:
            self.module.AppController._auto_reset_allowed = original_allowed

    def test_reset_blocked_when_timestamp_cannot_be_persisted(self):
        """Fail-safe: without a durable cooldown the reboot must not happen."""
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES,
            "20260725,1,1,1,1",
            60 * 60 * 1000,
            uptime_latched=True,
        )
        original_state_file = self.module.AUTO_RESET_STATE_FILE
        try:
            self.module.AUTO_RESET_STATE_FILE = str(
                Path("no-such-dir") / "nested" / "autoreset.log"
            )
            self._assert_no_reset(controller)
            self.assertTrue(controller.auto_reset_blocked)
        finally:
            self.module.AUTO_RESET_STATE_FILE = original_state_file

    def test_reset_fires_once_every_condition_is_met(self):
        controller = self._controller(
            self.module.DISCORD_STALL_RESET_FAILURES, "20260725,1,1,1,1", 60 * 60 * 1000
        )
        resets = []
        machine_module = types.ModuleType("machine")
        machine_module.reset = lambda: resets.append(True)
        sys.modules["machine"] = machine_module
        original_state_file = self.module.AUTO_RESET_STATE_FILE
        try:
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                self.module.AUTO_RESET_STATE_FILE = str(Path(directory) / "autoreset.log")
                controller._check_discord_stall()
                self.assertEqual(resets, [True])
                # The timestamp must be persisted so the cooldown survives the reboot.
                self.assertTrue(Path(self.module.AUTO_RESET_STATE_FILE).exists())
        finally:
            self.module.AUTO_RESET_STATE_FILE = original_state_file
            sys.modules.pop("machine", None)

    def test_cooldown_blocks_a_second_reset_within_the_window(self):
        original_state_file = self.module.AUTO_RESET_STATE_FILE
        controller = object.__new__(self.module.AppController)
        try:
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "autoreset.log"
                self.module.AUTO_RESET_STATE_FILE = str(path)

                path.write_text(str(int(time.time())), encoding="utf-8")
                self.assertFalse(controller._auto_reset_allowed())

                stale = int(time.time()) - self.module.MIN_SECONDS_BETWEEN_AUTO_RESETS - 60
                path.write_text(str(stale), encoding="utf-8")
                self.assertTrue(controller._auto_reset_allowed())

                path.write_text("not-a-number", encoding="utf-8")
                self.assertTrue(controller._auto_reset_allowed())
        finally:
            self.module.AUTO_RESET_STATE_FILE = original_state_file

    def test_missing_state_file_allows_reset(self):
        original_state_file = self.module.AUTO_RESET_STATE_FILE
        controller = object.__new__(self.module.AppController)
        try:
            self.module.AUTO_RESET_STATE_FILE = str(Path("no-such-dir") / "autoreset.log")
            self.assertTrue(controller._auto_reset_allowed())
        finally:
            self.module.AUTO_RESET_STATE_FILE = original_state_file


if __name__ == "__main__":
    unittest.main()
