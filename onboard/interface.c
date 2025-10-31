#include "vscope.h"

// Replace this (and the serialSendChar and serialSend32Bit functions) with
// matching implementations from your own project.
#include "serial.h"

#define U32_FROM_MSG(msg, index)                                               \
  (uint32_t)((uint32_t)msg[index] + ((uint32_t)msg[index + 1] << 8) +          \
             ((uint32_t)msg[index + 2] << 16) +                                \
             ((uint32_t)msg[index + 3] << 24))

typedef enum {
  HANDSHAKE = 'h',
  GET_TIMING = 't',
  SET_TIMING = 'T',
  GET_STATE = 's',
  SET_STATE = 'S',
  GET_BUFF = 'b',
  SET_BUFF = 'B',
  GET_FRAME = 'f',
  GET_LABEL = 'l',
  DOWNLOAD = 'd',
} VscopeMessageKeys;

void vscopeProcessMessage(char *msg) {
  uint32_t i = 0U;
  uint32_t j = 0U;

  switch (msg[0]) {
  case HANDSHAKE: {
    serialSendChar((char)(vscope.n_ch));
    serialSendChar((char)(vscope.n_ch >> 8));
    serialSendChar((char)(vscope.buffer_size));
    serialSendChar((char)(vscope.buffer_size >> 8));

    // Send fixed-length device identifier (10 bytes)
    for (i = 0U; i < VSCOPE_DEVICE_NAME_LEN; i += 1U) {
      serialSendChar(vscope.device_name[i]);
    }
    break;
  }

  case GET_TIMING: {
    serialSend32Bit((uint32_t *)&vscope.divider);
    serialSend32Bit((uint32_t *)&vscope.pre_trig);
    break;
  }

  case SET_TIMING: {
    vscope.divider = U32_FROM_MSG(msg, 1);
    vscope.pre_trig = U32_FROM_MSG(msg, 5);
    vscope.acq_time = vscope.buffer_size - vscope.pre_trig;

    serialSendChar(0);
    break;
  }

  case GET_STATE: {
    serialSendChar((char)vscope.state);
    break;
  }

  case SET_STATE: {
    if (msg[8] < (char)VSCOPE_MISCONFIGURED) {
      vscope.request = (VscopeState)msg[8];
      serialSendChar(0);
    } else {
      serialSendChar(1);
    }
    break;
  }

  case GET_BUFF: {
    uint32_t address = U32_FROM_MSG(msg, 5);
    float value = (address < RT_BUFFER_LENGTH)
                      ? vscopeGetRtBuffer((VscopeRtBufferIndexes)address)
                      : 0.0f;
    serialSend32Bit((uint32_t *)&value);
    break;
  }

  case SET_BUFF: {
    uint32_t address = U32_FROM_MSG(msg, 1);
    uint32_t value = U32_FROM_MSG(msg, 5);
    if (address < RT_BUFFER_LENGTH) {
      vscopeSetRtBuffer((VscopeRtBufferIndexes)address, *(float *)(&value));
      serialSendChar(0);
    } else {
      serialSendChar(1);
    }

    break;
  }

  case GET_FRAME: {
    for (i = 0U; i < vscope.n_ch; i += 1U) {
      serialSend32Bit((uint32_t *)vscope.frame[i]);
    }
    break;
  }

  case GET_LABEL: {
    uint32_t label = U32_FROM_MSG(msg, 5);
    if (label < VSCOPE_NUM_CHANNELS) {
      for (i = 0U; (i < VSCOPE_MAX_NAME_LEN) &&
                   (vscope_channel_names[label][i] != '\0');
           i += 1U) {
        serialSendChar(vscope_channel_names[label][i]);
      }

      // terminating the string if we haven't overran
      if (i < VSCOPE_MAX_NAME_LEN) {
        serialSendChar('\0');
      }
    }

    break;
  }

  case DOWNLOAD: {
    for (j = 0U; j < vscope.buffer_size; j += 1U) {
      for (i = 0U; i < vscope.n_ch; i += 1U) {
        serialSend32Bit((uint32_t *)&vscope.buffer[vscope.first_element][i]);
      }

      vscope.first_element += 1U;
      if (vscope.first_element == vscope.buffer_size) {
        vscope.first_element = 0;
      }
    }
    break;
  }
  }
}
