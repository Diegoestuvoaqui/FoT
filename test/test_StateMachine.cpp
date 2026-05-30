#include <unity.h>
#include "StateMachine.h"
#include "StateIdle.h"
#include "StateMonitoring.h"
#include "StateIrrigating.h"
#include "StateFault.h"
#include "MockSensor.h"

// ─── fixtures ────────────────────────────────────────────────────────────────

StateMachine* fsm        = nullptr;
MockSensor*   soilSensor = nullptr;
MockSensor*   tempSensor = nullptr;

void setUp(void) {
    fsm        = new StateMachine();
    soilSensor = new MockSensor(SENSOR_SOIL_CAP);
    tempSensor = new MockSensor(SENSOR_DHT22_TEMP);
    fsm->addSensor(soilSensor);
    fsm->addSensor(tempSensor);
    fsm->applyStartupState();
}

void tearDown(void) {
    delete fsm;
    delete soilSensor;
    delete tempSensor;
    fsm = soilSensor = tempSensor = nullptr;
}

// ─── 1.2 FSM tests ───────────────────────────────────────────────────────────

void test_initial_state_is_idle() {
    TEST_ASSERT_EQUAL_STRING("Idle", fsm->getCurrentStateName());
}

void test_idle_to_irrigating_via_command() {
    fsm->dispatchCommand("irrigate");
    fsm->tick();
    TEST_ASSERT_EQUAL_STRING("Irrigating", fsm->getCurrentStateName());
}

void test_irrigating_stop_returns_to_idle_when_manual() {
    fsm->dispatchCommand("irrigate");
    fsm->tick();
    fsm->dispatchCommand("stop");
    fsm->tick();
    TEST_ASSERT_EQUAL_STRING("Idle", fsm->getCurrentStateName());
}

void test_irrigating_timeout_goes_to_fault() {
    TEST_IGNORE_MESSAGE("Requiere mock de tiempo");
}

void test_idle_to_monitoring() {
    fsm->dispatchCommand("set_mode_auto");
    fsm->tick();
    TEST_ASSERT_EQUAL_STRING("Monitoring", fsm->getCurrentStateName());
}

void test_monitoring_irrigates_when_below_threshold() {
    fsm->dispatchCommand("set_mode_auto");
    fsm->tick();
    soilSensor->setValue(10.0f); // debajo del umbral mínimo (20)
    fsm->updateSensors();
    fsm->tick();
    TEST_ASSERT_EQUAL_STRING("Irrigating", fsm->getCurrentStateName());
}

void test_sensor_fault_three_invalid_readings() {
    soilSensor->setValid(false);
    for (int i = 0; i < 3; i++) {
        fsm->updateSensors();
        fsm->tick();
    }
    TEST_ASSERT_EQUAL_STRING("Fault", fsm->getCurrentStateName());
}

void test_fault_reset_returns_to_idle() {
    soilSensor->setValid(false);
    for (int i = 0; i < 3; i++) {
        fsm->updateSensors();
        fsm->tick();
    }
    fsm->dispatchCommand("reset_fault");
    fsm->tick();
    TEST_ASSERT_EQUAL_STRING("Idle", fsm->getCurrentStateName());
}

// ─── 1.1 Sensor abstraction tests ────────────────────────────────────────────

void test_mock_sensor_default_valid() {
    MockSensor s(SENSOR_SOIL_CAP);
    TEST_ASSERT_TRUE(s.isValid());
}

void test_mock_sensor_set_invalid() {
    MockSensor s(SENSOR_SOIL_CAP);
    s.setValid(false);
    TEST_ASSERT_FALSE(s.isValid());
}

void test_mock_sensor_read_value() {
    MockSensor s(SENSOR_DHT22_TEMP);
    s.setValue(25.5f);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 25.5f, s.read());
}

void test_mock_sensor_type() {
    MockSensor s(SENSOR_DHT22_HUM);
    TEST_ASSERT_EQUAL(SENSOR_DHT22_HUM, s.getType());
}

void test_fsm_sensor_disabled_ignored_in_fault_check() {
    soilSensor->setValid(false);
    fsm->setSensorEnabled(SENSOR_SOIL_CAP, false);
    for (int i = 0; i < 3; i++) {
        fsm->updateSensors();
        fsm->tick();
    }
    // sensor deshabilitado no debe causar Fault
    TEST_ASSERT_EQUAL_STRING("Idle", fsm->getCurrentStateName());
}

void test_fsm_thresholds_update() {
    fsm->updateThresholds(30.0f, 80.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 30.0f, fsm->getThresholdMin());
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 80.0f, fsm->getThresholdMax());
}

// ─── runner ──────────────────────────────────────────────────────────────────

int main(int argc, char** argv) {
    UNITY_BEGIN();

    // 1.1 Abstracción de sensores
    RUN_TEST(test_mock_sensor_default_valid);
    RUN_TEST(test_mock_sensor_set_invalid);
    RUN_TEST(test_mock_sensor_read_value);
    RUN_TEST(test_mock_sensor_type);
    RUN_TEST(test_fsm_sensor_disabled_ignored_in_fault_check);
    RUN_TEST(test_fsm_thresholds_update);

    // 1.2 FSM
    RUN_TEST(test_initial_state_is_idle);
    RUN_TEST(test_idle_to_irrigating_via_command);
    RUN_TEST(test_irrigating_stop_returns_to_idle_when_manual);
    RUN_TEST(test_irrigating_timeout_goes_to_fault);
    RUN_TEST(test_idle_to_monitoring);
    RUN_TEST(test_monitoring_irrigates_when_below_threshold);
    RUN_TEST(test_sensor_fault_three_invalid_readings);
    RUN_TEST(test_fault_reset_returns_to_idle);

    return UNITY_END();
}