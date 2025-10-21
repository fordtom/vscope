#include "vscope.h"
#include "string.h"

#pragma DATA_SECTION(vscope, "VScope");
VscopeStruct vscope;
float rt_buffer[RT_BUFFER_LENGTH];

char vscope_channel_names[VSCOPE_NUM_CHANNELS][VSCOPE_MAX_NAME_LEN];

#define CONFIGURE_CHANNEL(name, ch)                                                 \
    do {                                                                            \
        vscope.frame[ch] = &(name);                                                 \
        strncpy(vscope_channel_names[ch], #name, sizeof(vscope_channel_names[ch])); \
    } while (0)

void vscopeInit(void) {
    memset(&vscope.frame, 0, sizeof(vscope.frame));
    memset(&vscope.buffer, 0, sizeof(vscope.buffer));

    vscope.state = VSCOPE_HALTED;
    vscope.request = VSCOPE_HALTED;

    vscope.buffer_size = VSCOPE_DEFAULT_BUFFER_SIZE;
    vscope.n_ch = VSCOPE_NUM_CHANNELS;
    vscope.pre_trig = 0U;
    vscope.divider = 1U;

    if ((VSCOPE_DEFAULT_BUFFER_SIZE * VSCOPE_NUM_CHANNELS) > VSCOPE_MEMORY) {
        vscope.state = VSCOPE_MISCONFIGURED;
    }

    vscope.acq_time = VSCOPE_DEFAULT_BUFFER_SIZE - vscope.pre_trig;

    // Initialising to default values
    vscopeSetRtBuffer(PI_KP, 0.5f);
    vscopeSetRtBuffer(PI_KI, 0.1f);

    CONFIGURE_CHANNEL(voltage_setpoint, 0);
    CONFIGURE_CHANNEL(voltage_limit, 1);
    CONFIGURE_CHANNEL(voltage_measurement, 2);
    CONFIGURE_CHANNEL(current_measurement, 3);
    CONFIGURE_CHANNEL(voltage_limit, 4);
    CONFIGURE_CHANNEL(temperature, 5);
    CONFIGURE_CHANNEL(frequency, 6);
    CONFIGURE_CHANNEL(duration, 7);
    CONFIGURE_CHANNEL(threshold, 8);
    CONFIGURE_CHANNEL(phase, 9);
}

void saveFrameToBuffer(void) {
    uint16_t i = 0U;
    for (i = 0U; i < VSCOPE_NUM_CHANNELS; i += 1U) {
        vscope.buffer[vscope.index][i] = *vscope.frame[i];
    }

    vscope.index += 1U;

    if (vscope.index == vscope.buffer_size) {
        vscope.index = 0U;
    }
}

void vscopeAcquire(void) {
    static uint16_t divider = 0U;
    static uint16_t run_index = 0U;

    divider += 1U;
    if (divider < vscope.divider) {
        return;
    }
    divider = 0U;

    switch (vscope.state) {
        case VSCOPE_HALTED: {
            vscope.index = 0U;

            if (vscope.request == VSCOPE_RUNNING) {
                vscope.state = VSCOPE_RUNNING;
            }
            break;
        }

        case VSCOPE_RUNNING: {
            if (vscope.request == VSCOPE_HALTED) {
                vscope.state = VSCOPE_HALTED;
            }
            if (vscope.request == VSCOPE_ACQUIRING) {
                if (vscope.acq_time == 0U) {
                    vscope.state = VSCOPE_HALTED;
                    vscope.first_element = vscope.index;
                } else {
                    vscope.state = VSCOPE_ACQUIRING;
                    run_index = 1U;
                }
            }

            saveFrameToBuffer();
            break;
        }

        case VSCOPE_ACQUIRING: {
            if (run_index == vscope.acq_time) {
                vscope.state = VSCOPE_HALTED;
                vscope.first_element = vscope.index;
            } else {
                run_index += 1U;
                saveFrameToBuffer();
            }
            break;
        }

        default: {
            // Do nothing; get stuck here if misconfigured.
            break;
        }
    }
}

void vscopeTrigger(void) {
    if (vscope.state == VSCOPE_RUNNING) {
        vscope.request = VSCOPE_ACQUIRING;
    }
}

float vscopeGetRtBuffer(VscopeRtBufferIndexes index) {
    return rt_buffer[index];
}

void vscopeSetRtBuffer(VscopeRtBufferIndexes index, float value) {
    rt_buffer[index] = value;
}
