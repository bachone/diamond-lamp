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
3. "Diamond Lamp Bridge" should appear. Tap it, enter the setup code from
   the logs (`sudo journalctl -u unicorn-lamp -n 50`), and finish setup.
4. Pairing the bridge adds the "Diamond Lamp" light plus one scene
   switch per ore (see below). Add whichever ones you want to
   **Favorites** (usually just the lamp itself, but the scene switches
   work too if you want one-tap presets).

## 8. Get it into Control Center

Anything marked as a Favorite appears in the Home tile in iOS Control
Center. Press and hold that tile:
- The **lamp** gives you quick on/off plus a full color wheel.
- Each **scene switch**, if favorited, appears as its own quick-tap
  tile — tapping it applies that preset to the lamp and then resets
  itself off, so it always reads as "ready to trigger" rather than "on".

## Scenes

Presets live in the `SCENES` dict near the top of `unicorn_lamp.py` as
`(hue, saturation, brightness)` tuples — edit values or add more entries
there, then restart the service:

```
sudo systemctl restart unicorn-lamp.service
```

Shipped with one scene per Minecraft ore, tuned to roughly match its
in-game glow, plus a dim "Night Light" preset:
- **Diamond Ore** — icy cyan-blue, full brightness
- **Emerald Ore** — rich green
- **Gold Ore** — warm yellow-gold
- **Redstone Ore** — deep red
- **Lapis Ore** — dark blue
- **Copper Ore** — burnt orange
- **Iron Ore** — pale peach/tan
- **Coal Ore** — near-black, very dim
- **Night Light** — dim warm amber

Note: adding or removing entries from `SCENES` changes how many
accessories the bridge exposes, which HomeKit doesn't always handle
gracefully on existing pairings. If accessories go missing or duplicate
in the Home app after an edit, remove the bridge from Home and re-pair.

## Notes

- The lamp fills all 64 LEDs with one solid color (fits how light diffuses
  through the printed shade) rather than replicating pixel art.
- If you have the smaller Unicorn **pHAT** instead of the full HAT,
  uncomment the `unicorn.set_layout(unicorn.PHAT)` line near the top of
  `unicorn_lamp.py`.
- State (on/off, last color) persists across reboots via
  `/var/lib/unicorn-lamp/accessory.state`.
