This repo consists of a python GUI for interacting with a debug interface built onto an embedded microcontroller. The application consists of a virtual oscilloscope, referred to as vscope, and some real-time read/write buffers for live control referred to as the rtbuffers. The application should provide a simple, clean one-page control panel for the vscope/rtbuffers (plus helpful information and some simple live stats) and a comprehensive graphing and comparison experience. vscope isn't really a 'real time' scope; the high resolution runs are stored on device and downloaded afterwards, to be saved as 'snapshots' - we plot these against each other at a later date.

The code is formatted using `uv format` (follows black formatting).

## Architecture

The application uses **qasync** to integrate asyncio with Qt's event loop. This keeps the GUI responsive during serial I/O operations (which can take 3+ seconds for snapshot downloads).

Key patterns:
- Qt signal handlers use `asyncio.create_task()` to schedule async operations without blocking
- Periodic samplers are implemented as `async` loop tasks with `asyncio.sleep()`
- Serial I/O remains threaded via `ThreadPoolExecutor` in `core/devices.py`
- The global `_msg_lock` in `send_message()` ensures fan-out/fan-in synchronization across all devices

Never use `asyncio.run()` in GUI code - it will block the Qt event loop.
