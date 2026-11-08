// src/firmware/abstractSensors/DHT11Adapter.h
#ifndef DHT11_ADAPTER_H
#define DHT11_ADAPTER_H

#include "DHTAdapter.h"

class DHT11Adapter : public DHTAdapter {
public:
    DHT11Adapter(DHT* dht, const char* name) : DHTAdapter(dht, name, DHT11) {}
};

#endif