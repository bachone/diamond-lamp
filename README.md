# Diamond Lamp — HomeKit-native Unicorn HAT lamp

Replaces the old Homebridge + Flask stack with a single Python process
(HAP-python) that talks directly to Apple Home. No Node.js, no bridge.

## 1. Flash the Pi

Pi Zero W is armv6 — use **Raspberry Pi OS Lite (32-bit), Bookworm**, not
64-bit (64-bit dropped armv6/Zero W support). In Raspberry Pi Imager, use
the gear icon to pre-configure hostname, SSH, and Wi-Fi before flashing.

## 2. Avoid the audio/PWM conflict

The Unicorn HAT and the Pi's onboard analog audio share the same PWM
hardware, which causes flicker/random colors. Disable onboard audio:

```
sudo nano /boot/firmware/config.txt
```

Add:

```
dtparam=audio=off
```

Reboot.

## 3. Install dependencies

```
sudo apt update
sudo apt install -y python3-venv python3-dev git
sudo mkdir -p /var/unicorn-lamp /var/lib/unicorn-lamp
sudo chown $USER:$USER /var/unicorn-lamp /var/lib/unicorn-lamp
cd /var/unicorn-lamp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If `pip install unicornhat` fails to find a package (the Pimoroni repo is
archived, so it's occasionally pulled from PyPI in older Pi OS images but
still installs fine as of writing), install it straight from source
instead:

```
pip install git+https://github.com/pimoroni/unicorn-hat.git#subdirectory=library/UnicornHat
```

## 4. Copy the files onto the Pi

Copy `unicorn_lamp.py` into `/var/unicorn-lamp/`, and
`unicorn-lamp.service` into `/etc/systemd/system/`.

## 5. Test it manually first

```
sudo /var/unicorn-lamp/venv/bin/python3 /var/unicorn-lamp/unicorn_lamp.py
```

Root is required — the LED driver needs direct DMA/PWM access. Watch the
console: HAP-python will log a setup code (default `031-45-154` unless
you change it) and it should also print a pairing QR code if you have the
`qrcode` extra installed. Ctrl+C to stop once you've confirmed it starts
without errors.

## 6. Install as a service

```
sudo systemctl daemon-reload
sudo systemctl enable --now unicorn-lamp.service
sudo systemctl status unicorn-lamp.service
```

## 7. Pair with Apple Home

1. Open the **Home** app on your iPhone (same Wi-Fi network as the Pi).
2. Tap **+** → **Add Accessory** → **More options...**
3. "Diamond Lamp" should appear. Tap it, enter the setup code from the
   logs (`sudo journalctl -u unicorn-lamp -n 50`), and finish setup.
4. In the accessory's settings, add it to **Favorites** so it shows up
   in Control Center.

> If you'd previously paired the bridge version (with separate scene
> switches), remove that old "Diamond Lamp Bridge" pairing from Home
> first, and delete `/var/lib/unicorn-lamp/accessory.state` on the Pi
> before starting the service again — otherwise HomeKit gets confused
> about the accessory's identity.

## 8. Get it into Control Center

With it marked as a Favorite, it'll appear in the Home tile in iOS
Control Center. Press and hold that tile to get quick on/off plus a full
color wheel for the lamp — no need to open the Home app or use Siri.

## Ore color presets, done right

Earlier this project tried presets as separate HomeKit Switch
accessories, but Switches always require opening the accessory and
toggling it — clunky. The better fit is HomeKit's native **Scenes**
feature: a one-tap tile, right on the Home screen or in Control Center,
that snapshots an accessory's state. No drilling in, no toggle to reset.

To set one up:

1. In the Home app, tap the Diamond Lamp tile and use the color wheel +
   brightness slider to dial in a color (see the table below for a
   starting point — hue is the wheel position, saturation is how far
   from center, brightness is the slider).
2. Tap **Done**, then from the Home app's main screen tap **+** → **Add
   Scene** (or, on newer versions, **+** → **Scene**).
3. Choose **Custom**, select the Diamond Lamp, and Home will offer to
   capture its *current* state — so set the color first (step 1), then
   create the scene right after.
4. Name it after the ore (e.g. "Diamond Ore") and save.
5. Repeat per ore. Each saved Scene becomes its own one-tap tile you can
   favorite for Control Center, exactly like a real accessory.

Approximate color targets (hue / saturation / brightness — the Home
app's color wheel doesn't show raw numbers, but hue is roughly the
angle around the wheel and saturation is distance from center):

| Ore | Hue | Saturation | Brightness | Feel |
|---|---|---|---|---|
| Diamond Ore | 190° | 55% | 100% | icy cyan-blue |
| Emerald Ore | 140° | 75% | 90% | rich green |
| Gold Ore | 45° | 80% | 90% | warm yellow-gold |
| Redstone Ore | 355° | 90% | 90% | deep red |
| Lapis Ore | 222° | 85% | 85% | dark blue |
| Copper Ore | 25° | 65% | 80% | burnt orange |
| Iron Ore | 30° | 20% | 75% | pale peach/tan |
| Coal Ore | 0° | 0% | 12% | near-black, dim |
| Night Light | 30° | 60% | 12% | dim warm amber |

## Notes

- The lamp fills all 64 LEDs with one solid color (fits how light diffuses
  through the printed shade) rather than replicating pixel art.
- If you have the smaller Unicorn **pHAT** instead of the full HAT,
  uncomment the `unicorn.set_layout(unicorn.PHAT)` line near the top of
  `unicorn_lamp.py`.
- State (on/off, last color) persists across reboots via
  `/var/lib/unicorn-lamp/accessory.state`.
