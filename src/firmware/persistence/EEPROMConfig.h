#ifndef EEPROM_CONFIG_H
#define EEPROM_CONFIG_H

#include <stdint.h>

struct ConfigData {
    float humidityThresholdMin; // % — umbral para activar riego
    float humidityThresholdMax; // % — umbral de saturación
    uint16_t irrigationTimeoutSec; // segundos máximos de riego continuo
    uint16_t monitoringIntervalSec; // segundos entre lecturas en auto
    uint8_t startInAutoMode; // 0 = Idle al arrancar, 1 = Monitoring
    uint8_t checksum; // XOR de todos los bytes anteriores
};

class EEPROMConfig {
public:
    static void save(const ConfigData &cfg);

    static bool load(ConfigData &cfg);

    static void writeDefaults(ConfigData &cfg);

private:
    static uint8_t calcChecksum(const ConfigData &cfg);

    static const uint16_t BASE_ADDRESS = 0;
};

#endif
