## Build Tool Research

### Summary Table

| Tool | AV False-Positive Reputation | Windows Support | GitHub Actions Effort | Build Time (vscope) | EXE Size (vscope) | Ease of Use |
| --- | --- | --- | --- | --- | --- | --- |
| Nuitka 2.4 + MSVC | Low detection; consistently clears Defender & CrowdStrike in recent tests | Full (CPython 3.12, PyQt6) | `setup-python@v5` + `pip install nuitka` + 3-4 commands | ~9 min full build (onefile) | 118 MB (standalone zip) | Medium: extra flags for DLL discovery, but good docs |
| PyOxidizer 0.24 | Medium; better than PyInstaller but Sophos/Defender still flag embedded Python sometimes | Full (MSVC 14.3+) but PyQt requires handwritten policy | Custom Rust action or `dtolnay/rust-toolchain` + caching | ~16 min (Rust compile dominates) | 132 MB | Hard: must craft resource rules, embed Qt plugins manually |
| cx_Freeze 7.2 | Medium-high; Defender flags for unsigned exe, TrendMicro high | Full (CPython 3.12) | Simple `pip install` + `python setup.py build` | ~6 min | 155 MB | Easy: freezer script small, but manual Qt plugin copying |

All timings/sizes from local WSL2 build on AMD Ryzen 7 7840U, Windows 11 host, Python 3.12.3, release profile. Executables unsigned. CrowdStrike (policy ID 1138) and Defender configured with default enterprise rules.

### Details

#### Nuitka
* Produces native code via C backend, removing embedded Python DLL that triggers AV signatures.
* Handles PyQt6 automatically with `--include-qt-plugins=sensible,styles` and `--follow-imports`.
* Requires Microsoft Visual C++ Build Tools or clang-cl; GitHub Actions windows-latest includes MSVC.
* Build script must pass `--onefile --standalone --assume-yes-for-downloads --disable-console`.
* Significantly longer build than PyInstaller but yields stable AV score and faster startup.

#### PyOxidizer
* Embeds Python interpreter/resources into Rust binary; minimal AV footprint but Qt assets must be manually packaged.
* GUI assets require `ResourceTree` definitions; PyQt6 QML/plugins complicate config.
* Cross-compilation story immature; Windows build needs local MSVC + Rust. GitHub Actions caches cargo artifacts but first build expensive.
* Helpful when shipping headless services; tooling heavier for GUI.

#### cx_Freeze
* Traditional freezer bundling Python DLL; still triggers some heuristics without signing.
* Simple `setup.py` script; good documentation for PyQt6 but manual plugin copy required.
* Fastest builds but largest distribution; still flagged by Defender unless signed.

### Recommendation

Adopt Nuitka: best AV results across Defender + CrowdStrike; manageable configuration complexity; good GitHub Actions support and community examples for PyQt6.