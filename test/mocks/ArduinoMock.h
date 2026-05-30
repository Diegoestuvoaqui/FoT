#ifndef ARDUINO_MOCK_H
#define ARDUINO_MOCK_H

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

// ─── Tiempo ──────────────────────────────────────────────────────────────────
// En los tests controlamos el tiempo manualmente con esta variable.
// Llama a setMillis(n) para simular que pasaron n milisegundos.

extern unsigned long _mockMillis;

inline unsigned long millis()        { return _mockMillis; }
inline void setMillis(unsigned long v) { _mockMillis = v; }
inline void advanceMillis(unsigned long ms) { _mockMillis += ms; }

// ─── GPIO ────────────────────────────────────────────────────────────────────
// Guardamos el último estado escrito en cada pin para poder afirmarlo en tests.

extern uint8_t _pinState[14];
extern uint8_t _pinMode[14];

inline void pinMode(uint8_t pin, uint8_t mode) {
    if (pin < 14) _pinMode[pin] = mode;
}
inline void digitalWrite(uint8_t pin, uint8_t val) {
    if (pin < 14) _pinState[pin] = val;
}
inline uint8_t digitalRead(uint8_t pin) {
    return (pin < 14) ? _pinState[pin] : 0;
}
inline int analogRead(uint8_t) { return 512; } // valor neutro

// ─── Constantes Arduino ───────────────────────────────────────────────────────
#define HIGH      1
#define LOW       0
#define OUTPUT    1
#define INPUT     0
#define INPUT_PULLUP 2

// ─── Serial (stub mínimo) ────────────────────────────────────────────────────
// Solo necesitamos que compile. En tests no nos importa la salida serial
// del firmware, solo los estados de la FSM.

struct FakeSerial {
    void begin(unsigned long) {}
    void print(const char* s)   { fputs(s, stdout); }
    void print(int v)           { printf("%d", v); }
    void print(float v)         { printf("%.2f", v); }
    void println(const char* s) { puts(s); }
    void println(int v)         { printf("%d\n", v); }
    void println(float v)       { printf("%.2f\n", v); }
    void flush() {}
    void write(char c)          { putchar(c); }
};

extern FakeSerial Serial;

// ─── Tipos Arduino ────────────────────────────────────────────────────────────
typedef uint8_t  byte;
typedef uint16_t word;

// ─── PROGMEM (no-op en el host) ───────────────────────────────────────────────
// En el AVR PROGMEM pone strings en flash. En el host no hace nada.
#define PROGMEM
#define pgm_read_byte(addr)   (*(const uint8_t*)(addr))
#define strcpy_P(d, s)        strcpy(d, s)
#define strncmp_P(a, b, n)    strncmp(a, b, n)

// avr/pgmspace.h lo incluye StateMachine.h → ISensor.h, lo reemplazamos aquí
#ifndef PGMSPACE_H
#define PGMSPACE_H
#endif

// ─── NAN (ya viene de math.h pero por si acaso) ───────────────────────────────
#ifndef NAN
#define NAN __builtin_nanf("")
#endif
inline bool isnan(float v) { return v != v; }

#endif // ARDUINO_MOCK_H