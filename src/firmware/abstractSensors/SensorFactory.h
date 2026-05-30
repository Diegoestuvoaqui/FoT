#ifndef SENSOR_FACTORY_H
#define SENSOR_FACTORY_H

#include "ISensor.h"

class SensorFactory {
public:
  // Crea un sensor según el tipo. Param1/param2 se usan para SoilMoisture (dry/wet).
  // Retorna nullptr si el tipo no es reconocido.
  static ISensor* create(SensorType type, uint8_t pin, int param1 = 0, int param2 = 1023);
};

#endif