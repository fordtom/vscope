# VScope Serial Protocol

All messages follow a fixed 9-byte format: 1 byte message key + 8 bytes payload.

## Message Types

### HANDSHAKE (`h`)

**Request:** `h` + 8 padding bytes  
**Response:**

- 2 bytes: Number of channels (uint16, little-endian)
- 2 bytes: Buffer size (uint16, little-endian)
- 10 bytes: Fixed-length device identifier string

Initiates communication and retrieves device configuration information.

---

### GET_TIMING (`t`)

**Request:** `t` + 8 padding bytes  
**Response:**

- 4 bytes: Divider value (uint32)
- 4 bytes: Pre-trigger sample count (uint32)

Retrieves the current timing configuration. The divider determines the sample rate (samples are taken every nth tick of the base polling rate). Pre-trigger defines how many samples are captured before the trigger event.

---

### SET_TIMING (`T`)

**Request:** `T` + 4 bytes divider (uint32) + 4 bytes pre-trigger (uint32)  
**Response:** 1 byte (0 = success)

Sets the timing configuration. The acquisition time is automatically calculated as `buffer_size - pre_trigger`.

---

### GET_STATE (`s`)

**Request:** `s` + 8 padding bytes  
**Response:** 1 byte state value

- 0 = HALTED
- 1 = RUNNING (circular buffering)
- 2 = ACQUIRING (capturing post-trigger samples)
- 3 = MISCONFIGURED

Retrieves the current operational state of the scope.

---

### SET_STATE (`S`)

**Request:** `S` + 7 padding bytes + 1 byte state (at index 8)  
**Response:** 1 byte (0 = success, 1 = invalid state)

Requests a state transition. Valid states are 0-2. State machine handles transitions via the internal `request` field.

---

### GET_BUFF (`b`)

**Request:** `b` + 4 padding bytes + 4 bytes buffer index (uint32)  
**Response:** 4 bytes float value (IEEE 754 single precision)

Reads a single float32 value from the real-time buffer at the specified index. Used for live parameter monitoring.

---

### SET_BUFF (`B`)

**Request:** `B` + 4 bytes buffer index (uint32) + 4 bytes float32 value  
**Response:** 1 byte (0 = success, 1 = invalid index)

Writes a float32 value to the real-time buffer at the specified index. Used for live parameter adjustment and control.

---

### GET_FRAME (`f`)

**Request:** `f` + 8 padding bytes  
**Response:** N × 4 bytes (N = number of channels)

Returns the current frame data as an array of float32 values, one per channel. Provides a snapshot of the current signal values.

---

### GET_LABEL (`l`)

**Request:** `l` + 4 padding bytes + 4 bytes channel index (uint32)  
**Response:** Variable-length null-terminated string (max 40 characters)

Retrieves the label/name for a specific channel.

---

### DOWNLOAD (`d`)

**Request:** `d` + 8 padding bytes  
**Response:** Buffer_size × N_channels × 4 bytes

Downloads the complete circular buffer contents. Data is transmitted as sequential frames, starting from `first_element` (the trigger/oldest sample point) and wrapping around the circular buffer. Each frame contains all channel values as float32 in channel order.

---
