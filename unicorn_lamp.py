"""
HomeKit-controllable lamp for a Raspberry Pi + Pimoroni Unicorn HAT.

Exposes a single Lightbulb accessory (On / Brightness / Hue / Saturation)
directly to Apple Home via HAP-python -- no Homebridge/Node required.

Color presets (Diamond Ore, Emerald Ore, etc.) are NOT built into this
accessory. HomeKit's per-accessory "Switch" scenes require opening the
accessory and toggling it, which is clunky. Instead, use the Home app's
native Scenes feature: set the lamp to a color, then save that as a
Scene. Scenes appear as one-tap tiles on the Home screen and in Control
Center -- no drilling in, no toggling back off. See the README for the
exact hue/saturation/brightness values to dial in per ore, and how to
save each as a Scene.

Run as root (LED driver needs DMA/PWM access):
    sudo /var/unicorn-lamp/venv/bin/python3 /var/unicorn-lamp/unicorn_lamp.py
"""
import colorsys
import logging
import signal

from pyhap.accessory import Accessory
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_LIGHTBULB

import unicornhat as unicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unicorn-lamp")

# If you have the smaller Unicorn pHAT instead of the full Unicorn HAT,
# uncomment the next line:
# unicorn.set_layout(unicorn.PHAT)

unicorn.rotation(0)
unicorn.brightness(1.0)


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


def get_accessory(driver):
    return UnicornLamp(driver, "Diamond Lamp")


def main():
    driver = AccessoryDriver(
        port=51826,
        persist_file="/var/lib/unicorn-lamp/accessory.state",
    )
    driver.add_accessory(accessory=get_accessory(driver))
    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()


if __name__ == "__main__":
    main()
