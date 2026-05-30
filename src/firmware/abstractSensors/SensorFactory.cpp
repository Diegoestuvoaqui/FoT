// lib/sensors/SensorFactory.cpp
#include "SensorFactory.h"
#include "DHT22Adapter.h"
#include "SoilMoistureAdapter.h"

ISensor* SensorFactory::create(SensorType type, uint8_t pin, int param1, int param2) {
  switch (type) {
    case SENSOR_DHT22_TEMP:
    case SENSOR_DHT22_HUM:
      return new DHT22Adapter(pin, type);
    case SENSOR_SOIL_CAP:
      return new SoilMoistureAdapter(pin, param1, param2);
    default:
      return nullptr;
  }
}