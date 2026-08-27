"""
HomeKit-controllable lamp + scene buttons for a Raspberry Pi + Pimoroni
Unicorn HAT.

Exposes a HomeKit Bridge with:
  - "Diamond Lamp"  a Lightbulb (On / Brightness / Hue / Saturation)
  - Five scene Switches, one per ore: Diamond, Redstone, Emerald, Lapis,
    Gold. Each sets the lamp to a precise, repeatable color -- the Home
    app's color wheel is too imprecise to reliably land on the same
    color by hand, so these switches exist to hit exact values.

Scene switches are momentary: turning one on applies the preset (and
updates the lamp's own On/Hue/Saturation/Brightness so the Home app stays
in sync) then the switch flips itself back off a moment later, so it
behaves like a scene button rather than a toggle.

No Homebridge/Node required -- this talks HomeKit directly via HAP-python.

Run as root (LED driver needs DMA/PWM access):
    sudo /var/unicorn-lamp/venv/bin/python3 /var/unicorn-lamp/unicorn_lamp.py
"""
import colorsys
import logging
import signal
import threading

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_LIGHTBULB, CATEGORY_SWITCH

import unicornhat as unicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unicorn-lamp")

# If you have the smaller Unicorn pHAT instead of the full Unicorn HAT,
# uncomment the next line:
# unicorn.set_layout(unicorn.PHAT)

unicorn.rotation(0)
unicorn.brightness(1.0)

# Presets: (hue 0-360, saturation 0-100, brightness 0-100)
SCENES = {
    "Diamond Ore": (190, 55, 100),   # icy cyan-blue
    "Redstone Ore": (355, 90, 90),   # deep red
    "Emerald Ore": (140, 75, 90),    # rich green
    "Lapis Ore": (222, 85, 85),      # dark blue
    "Gold Ore": (45, 80, 90),        # warm yellow-gold
}


class UnicornLamp(Accessory):
    """A solid-color lamp: fills every pixel with one color, which is
    what you want for a diffused 3D-printed lamp shade rather than a
    pixel-art display."""

    category = CATEGORY_LIGHTBULB

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        serv_light = self.add_preload_service(
            "Lightbulb", chars=["On", "Brightness", "Hue", "Saturation"]
        )

        serv_light.configure_char("On", setter_callback=self.set_on)
        serv_light.configure_char("Brightness", setter_callback=self.set_brightness)
        serv_light.configure_char("Hue", setter_callback=self.set_hue)
        serv_light.configure_char("Saturation", setter_callback=self.set_saturation)
        self.serv_light = serv_light

        self._on = False
        self._brightness = 100  # 0-100
        self._hue = 190         # 0-360, default icy diamond-ore blue
        self._saturation = 55   # 0-100

    def _apply(self):
        if not self._on:
            unicorn.off()
            return

        r, g, b = colorsys.hsv_to_rgb(
            self._hue / 360.0, self._saturation / 100.0, 1.0
        )
        unicorn.brightness(max(self._brightness, 1) / 100.0)
        unicorn.set_all(int(r * 255), int(g * 255), int(b * 255))
        unicorn.show()

    def set_on(self, value):
        logger.info("On -> %s", value)
        self._on = value
        self._apply()

    def set_brightness(self, value):
        logger.info("Brightness -> %s", value)
        self._brightness = value
        self._apply()

    def set_hue(self, value):
        logger.info("Hue -> %s", value)
        self._hue = value
        self._apply()

    def set_saturation(self, value):
        logger.info("Saturation -> %s", value)
        self._saturation = value
        self._apply()

    def apply_scene(self, hue, saturation, brightness):
        """Programmatically set the lamp (called by a scene switch) and
        push the new values to HomeKit so the Home app / Control Center
        tile for the lamp reflects the change immediately."""
        self._on = True
        self._hue = hue
        self._saturation = saturation
        self._brightness = brightness
        self._apply()

        self.serv_light.get_characteristic("On").set_value(True)
        self.serv_light.get_characteristic("Hue").set_value(hue)
        self.serv_light.get_characteristic("Saturation").set_value(saturation)
        self.serv_light.get_characteristic("Brightness").set_value(brightness)

    def identify(self):
        """Called when the user taps 'Identify' in the Home app -- blink the lamp."""
        for _ in range(3):
            unicorn.set_all(255, 255, 255)
            unicorn.show()
            import time

            time.sleep(0.3)
            unicorn.off()
            time.sleep(0.3)
        self._apply()

    def stop(self):
        unicorn.off()
        super().stop()


class SceneSwitch(Accessory):
    """A momentary switch that applies a lamp preset, then auto-resets
    to off after ~1s so it reads as a scene button rather than a toggle."""

    category = CATEGORY_SWITCH

    def __init__(self, *args, lamp, hue, saturation, brightness, **kwargs):
        super().__init__(*args, **kwargs)
        self.lamp = lamp
        self.hue = hue
        self.saturation = saturation
        self.brightness = brightness

        serv_switch = self.add_preload_service("Switch", chars=["On"])
        serv_switch.configure_char("On", setter_callback=self.set_on)
        self.serv_switch = serv_switch

    def set_on(self, value):
        if not value:
            return
        logger.info("Scene '%s' triggered", self.display_name)
        self.lamp.apply_scene(self.hue, self.saturation, self.brightness)

        # Flip the switch back off shortly after, so it behaves like a
        # scene button instead of a persistent toggle.
        def reset():
            self.serv_switch.get_characteristic("On").set_value(False)

        threading.Timer(1.0, reset).start()


def build_bridge(driver):
    bridge = Bridge(driver, "Diamond Lamp Bridge")

    lamp = UnicornLamp(driver, "Diamond Lamp")
    bridge.add_accessory(lamp)

    for name, (hue, sat, bri) in SCENES.items():
        bridge.add_accessory(
            SceneSwitch(
                driver, name, lamp=lamp, hue=hue, saturation=sat, brightness=bri
            )
        )

    return bridge


def main():
    driver = AccessoryDriver(
        port=51826,
        persist_file="/var/lib/unicorn-lamp/accessory.state",
    )
    driver.add_accessory(accessory=build_bridge(driver))
    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()


if __name__ == "__main__":
    main()
