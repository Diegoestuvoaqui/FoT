#ifndef I_SENSOR_H
#define I_SENSOR_H

#include "SensorType.h"
// avr/pgmspace.h solo existe en el toolchain AVR.
// En el host (tests nativos) ArduinoMock.h ya define los macros equivalentes.
#ifdef ARDUINO
  #include <avr/pgmspace.h>
#endif


class ISensor {
protected:
    bool _enabled = true;   // arranca habilitado (volátil, no persiste)

public:
    virtual float read() = 0;
    virtual bool isValid() = 0;
    virtual SensorType getType() = 0;
    virtual const char* getUnitPGM() = 0;

    // Control de habilitación (para enable/disable desde UI)
    void setEnabled(bool v) { _enabled = v; }
    bool isEnabled() const  { return _enabled; }

    virtual ~ISensor() {}
};

#endif