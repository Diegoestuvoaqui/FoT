//
// Created by dda on 5/6/26.
//
#include "EEPROMConfig.h"

#ifdef ARDUINO
#include <EEPROM.h>
#endif

// --------------------------------------------------------------------------
// XOR de todos los bytes del struct excepto el campo checksum (último byte)
uint8_t EEPROMConfig::calcChecksum(const ConfigData &cfg) {
    const uint8_t *p = reinterpret_cast<const uint8_t *>(&cfg);
    uint8_t result = 0;
    for (size_t i = 0; i < sizeof(ConfigData) - 1; i++) {
        result ^= p[i];
    }
    return result;
}

// --------------------------------------------------------------------------
void EEPROMConfig::save(const ConfigData &cfg) {
    ConfigData toWrite = cfg;
    toWrite.checksum = calcChecksum(cfg);

    const uint8_t *p = reinterpret_cast<const uint8_t *>(&toWrite);
#ifdef ARDUINO
    for (size_t i = 0; i < sizeof(ConfigData); i++) {
        EEPROM.update(BASE_ADDRESS + i, p[i]);
    }
#endif
}

// --------------------------------------------------------------------------
bool EEPROMConfig::load(ConfigData &cfg) {
#ifdef ARDUINO
    uint8_t *p = reinterpret_cast<uint8_t *>(&cfg);
    for (size_t i = 0; i < sizeof(ConfigData); i++) {
        p[i] = EEPROM.read(BASE_ADDRESS + i);
    }
#endif

    if (cfg.checksum != calcChecksum(cfg)) {
        writeDefaults(cfg);
        return false;
    }
    return true;
}

// --------------------------------------------------------------------------
void EEPROMConfig::writeDefaults(ConfigData &cfg) {
    cfg.humidityThresholdMin = 30.0f;
    cfg.humidityThresholdMax = 70.0f;
    cfg.irrigationTimeoutSec = 300;
    cfg.monitoringIntervalSec = 60;
    cfg.startInAutoMode = 0;
    save(cfg); // persiste los defaults para no repetir esto en cada arranque
}
