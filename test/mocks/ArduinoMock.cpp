#include "ArduinoMock.h"

unsigned long _mockMillis   = 0;
uint8_t       _pinState[14] = {};
uint8_t       _pinMode[14]  = {};
FakeSerial    Serial;