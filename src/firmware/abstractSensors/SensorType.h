#ifndef SENSOR_TYPE_H
#define SENSOR_TYPE_H

#include <stdint.h>

// Enum que reemplaza el uso de String para identificar tipos de sensor.
// Ocupa 1 byte, se almacena en flash, no toca el heap.
enum SensorType : uint8_t {
  SENSOR_DHT22_TEMP = 0,
  SENSOR_DHT22_HUM  = 1,
  SENSOR_SOIL_CAP   = 2
};

#endif