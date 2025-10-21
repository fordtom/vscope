# VScope

A Python GUI application for interfacing with a custom datalogging module on embedded microcontrollers via serial communication.

## Overview

VScope consists of two integrated components:

### 1. Virtual Oscilloscope

A high-resolution data capture system that logs and stores waveform snapshots on the embedded device and downloads them for analysis. VScope captures data at full resolution on the microcontroller, stores complete buffer snapshots, and then offloads them over serial for analysis and comparison.

**Key Features:**

- Configure sampling rates and pre-trigger capture windows
- Trigger-based acquisition with circular buffering
- Multi-channel (10) support
- Save and compare multiple snapshots
- High-resolution waveform plotting and overlay
- Export snapshot data for further analysis
- low-res live view

### 2. Real-Time Buffers

A live read/write interface for monitoring and adjusting system parameters during runtime. RT buffers provide direct access to float32 variables on the device, enabling real-time control and observation without stopping execution.

**Key Features:**

- Live monitoring of up to 16 parameter values
- Direct parameter adjustment via GUI controls
- Immediate feedback for tuning and debugging

### Parallel monitoring

The VScope can handle multiple devices in parallel. This lets you compare the behaviour of two or more systems provided they both contain an identical copy of the vscope onboard module.

## Protocol

Communication uses a simple 9-byte fixed-format serial protocol. See [`onboard/PROTOCOL.md`](onboard/PROTOCOL.md) for detailed message specifications.

## Usage

The embedded components in `onboard` (`interface.c`, `logger.c`, `vscope.h`) should be integrated into your target firmware:

1. Include the source files in your build
2. Call `vscopeInit()` during startup
3. Configure channels by linking pointers to your variables (for now only f32)
4. Call `vscopeAcquire()` periodically (e.g., in a high-frequency ISR)
5. Call `vscopeTrigger()` conditionally in-code to trigger, or do it by hand in the GUI
6. Periodically process incoming serial commands via `vscopeProcessMessage()`

The Python GUI connects via serial and provides a unified interface for controlling the scope, managing snapshots, and adjusting real-time parameters. You should:

1. Configure the `vscopeAqcuire()` ISR speed and other settings in the GUI, including UART settings.
2. USB VID/PID are required to filter the ports the VScope will try to communicate with; it will attempt to communicate with everything that matches these settings + the regex.

## License

This project is available under the MIT License. See [`LICENSE.md`](LICENSE.md) for details.
