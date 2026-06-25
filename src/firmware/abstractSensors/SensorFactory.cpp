// lib/sensors/SensorFactory.cpp
#include "SensorFactory.h"
#include "DHT11Adapter.h"
#include "SoilMoistureAdapter.h"

ISensor *SensorFactory::create(SensorType type, uint8_t pin, int param1, int param2) {
  switch (type) {
    case SENSOR_DHT11_TEMP:
    case SENSOR_DHT11_HUM:
      return new DHT11Adapter(pin, type);
    case SENSOR_SOIL_CAP:
      return new SoilMoistureAdapter(pin, param1, param2);
    default:
      return nullptr;
  }
}
