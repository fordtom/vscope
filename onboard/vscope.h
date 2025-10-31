#ifndef VSCOPE_H
#define VSCOPE_H

#include <stdint.h>

#define VSCOPE_MEMORY 10501
#define VSCOPE_DEFAULT_BUFFER_SIZE 1000
#define VSCOPE_NUM_CHANNELS 10
#define VSCOPE_MAX_NAME_LEN 40
// Length of the fixed device identifier/name returned during handshake
#define VSCOPE_DEVICE_NAME_LEN 10

typedef enum {
  VSCOPE_HALTED = 0,
  VSCOPE_RUNNING = 1,
  VSCOPE_ACQUIRING = 2,
  VSCOPE_MISCONFIGURED = 3,
} VscopeState;

typedef enum {
  TRG_THRESHOLD = 0,
  TRG_CHANNEL = 1,
  TRG_MODE = 2,

  RT_BUFFER_LENGTH = 16,
} VscopeRtBufferIndexes;

typedef enum {
  VSCOPE_TRG_DISABLED = 0,
  VSCOPE_TRG_RISING = 1,
  VSCOPE_TRG_FALLING = 2,
  VSCOPE_TRG_BOTH = 3,
} VscopeTriggerMode;

typedef struct {
  VscopeState state;
  VscopeState request;

  float *frame[VSCOPE_NUM_CHANNELS];
  float buffer[VSCOPE_DEFAULT_BUFFER_SIZE][VSCOPE_NUM_CHANNELS];

  uint32_t buffer_size;
  uint32_t n_ch;
  uint32_t divider;
  uint32_t pre_trig;
  uint32_t acq_time;
  uint32_t index;
  uint32_t first_element;

  // Fixed-length device identifier returned in handshake (user should populate)
  char device_name[VSCOPE_DEVICE_NAME_LEN];
} VscopeStruct;

extern VscopeStruct vscope;
extern char vscope_channel_names[VSCOPE_NUM_CHANNELS][VSCOPE_MAX_NAME_LEN];

/**
 * @brief This function intialises the vscope module.
 **/
void vscopeInit(void);

/**
 * @brief This function is used to store data in the vscope buffer when the
 *scope is running/triggered.
 **/
void vscopeAcquire(void);

/**
 * @brief Triggers the vscope if the state is 'running'.
 */
void vscopeTrigger(void);

/**
 * @brief Handles an incoming serial request.
 * @param msg a pointer to a char buffer. The function assumes the correct
 * length of 9 bytes.
 */
void vscopeProcessMessage(char *msg);

/**
 * @brief Gets a given index.
 * @param index The index.
 * @return The value.
 */
float vscopeGetRtBuffer(VscopeRtBufferIndexes index);

/**
 * @brief Sets a given index to a given value.
 * @param index The index.
 * @param value The value.
 */
void vscopeSetRtBuffer(VscopeRtBufferIndexes index, float value);

void vscopeSetTriggerThreshold(float threshold);

void vscopeSetTriggerChannel(uint32_t channel);

void vscopeSetTriggerMode(VscopeTriggerMode mode);

#endif // VSCOPE_H
