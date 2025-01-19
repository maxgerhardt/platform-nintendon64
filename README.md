# ST STM32: development platform for [PlatformIO](https://platformio.org)

[![Build Status](https://github.com/maxgerhardt/platform-nintendon64/workflows/Examples/badge.svg)](https://github.com/maxgerhardt/platform-nintendon64/actions)

The Nintendo 64, released by Nintendo in 1996, is a 64-bit home video game console powered by a custom NEC VR4300 CPU and an SGI-designed Reality Coprocessor, which delivers advanced 3D graphics and audio capabilities for its time. It uses cartridge-based storage for games, enabling fast load times but limiting storage capacity compared to its CD-based competitors.

* [Home](https://registry.platformio.org/platforms/platformio/nintendon64) (home page in the PlatformIO Registry)
* [Documentation](https://docs.platformio.org/page/platforms/nintendon64.html) (advanced usage, packages, boards, frameworks, etc.)

# Usage

1. [Install PlatformIO](https://platformio.org)
2. Create PlatformIO project and configure a platform option in [platformio.ini](https://docs.platformio.org/page/projectconf.html) file:

## Stable version

```ini
[env:stable]
platform = nintendon64
board = ...
...
```

## Development version

```ini
[env:development]
platform = https://github.com/maxgerhardt/platform-nintendon64.git
board = ...
...
```

# Configuration

Please navigate to [documentation](https://docs.platformio.org/page/platforms/nintendon64.html).
