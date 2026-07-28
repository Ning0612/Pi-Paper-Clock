# main.py
import time
import gc
from wifi_manager import wifi_manager, create_lan_config_server
from netutils import sync_time
from discord_notifier import send_lan_ip, consume_autoreset_ip


# Keep the first TLS allocation ahead of the display, sensor, weather, and
# controller imports.  Those modules are intentionally loaded below only
# after the startup webhook has had its low-memory window.
_startup_wlan = wifi_manager()
_startup_lan_ip = None
_startup_network_connected = bool(_startup_wlan and _startup_wlan.isconnected())
_startup_discord_sent = False
# Consumed before the connected check, not inside it: the note describes *this*
# boot, and one that comes up without a link has no notice to suppress.  Leaving
# it behind would apply it to some later boot that has every reason to announce.
_autoreset_ip = consume_autoreset_ip()
if _startup_network_connected:
    _startup_lan_ip = _startup_wlan.ifconfig()[0]
    _startup_wlan = None
    gc.collect()
    sync_time()
    # A memory auto-reset buys exactly one usable TLS window, and the online
    # notice would spend it repeating an address the user was already told.
    # Skip it in that case and let the pending backlog below have the window --
    # the whole point of the reboot.  The note is consumed on read, so a power
    # cycle or a changed address still announces normally.
    #
    # "Unchanged" means the same IPv4 string, deliberately: a different network
    # that hands out the same address would also be skipped, but the announced
    # URL still works there, and the note only ever survives from an auto-reset
    # to the boot it caused -- moving the device involves a power cycle, which
    # clears it.
    if _startup_lan_ip and _autoreset_ip == _startup_lan_ip:
        print("Info: LAN IP unchanged after a memory auto-reset; skipping the online notice.")
        # Marked sent so the controller does not retry it every 30 s either.
        _startup_discord_sent = True
    else:
        _startup_discord_sent = send_lan_ip(_startup_lan_ip) is True
    from discord_notifier import send_presence_session, send_presence_summary
    from presence_manager import PresenceManager

    startup_presence = PresenceManager(
        discord_sender=send_presence_summary,
        session_sender=send_presence_session
    )
    flushed = startup_presence.flush_startup_discord()
    if flushed:
        print("Info: Flushed {} pending Discord notification(s) before app init.".format(flushed))
    startup_presence = None
    gc.collect()
_startup_wlan = None


def main():
    """Main function to initialize and run the Pico Clock Weather Display application."""
    from display_manager import update_page_loading
    from app_state import AppState
    from hardware_manager import HardwareManager
    from app_controller import AppController
    from image_manager import image_store

    recovered = image_store.recover_partial_uploads()

    if recovered:
        print("Recovered {} interrupted image transaction(s).".format(recovered))

    # Initial display and hardware setup follows the memory-sensitive webhook.
    update_page_loading(False)
    app_state = AppState()
    hardware = HardwareManager()

    controller = AppController(app_state, hardware, None, _startup_lan_ip)
    controller.startup_discord_sent = _startup_discord_sent

    if _startup_network_connected:
        controller.lan_server = create_lan_config_server()

    while True:
        controller.run_main_loop()
        time.sleep(1)


if __name__ == "__main__":
    main()
