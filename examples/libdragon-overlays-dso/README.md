How to build PlatformIO based project
=====================================

1. [Install PlatformIO Core](https://docs.platformio.org/page/core.html)
2. Download [development platform with examples](https://github.com/maxgerhardt/platform-nintendon64/archive/main.zip)
3. Extract ZIP archive
4. Run these commands:

```shell
# Change directory to example
$ cd platform-nintendon64/examples/libdragon-overlays-dso

# Build project
$ pio run

# Upload firmware
$ pio run --target upload

# Upload firmware for the specific environment
$ pio run -e n64 --target upload

# Clean build files
$ pio run --target clean
```
