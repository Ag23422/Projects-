Here is the revised `README.md` for your [`embedded_project`](https://github.com/Ag23422/Projects-/tree/main/embedded_project) **with all emojis removed**:

---

````markdown
# Embedded Systems Projects Repository

This repository contains a collection of microcontroller-based embedded systems projects focusing on real-time sensor integration, actuator control, and communication interfaces (I2C, UART, SPI). These projects highlight low-level hardware interaction, efficiency under memory constraints, and reliability in real-time environments.

---

## Contents

| Project Folder       | Description |
|----------------------|-------------|
| `sensor_reading/`        | Real-time acquisition from environmental sensors (DHT11, LDR, MQ-2) with threshold-based alerting. |
| `uart_control/`          | Command-based actuator control using UART interface (via serial terminal). |
| `i2c_display/`           | Real-time sensor feedback visualized on I2C OLED displays (SSD1306/HD44780). |
| `motor_pwm_control/`     | PWM-based motor control for varying speed/direction via potentiometer input. |
| `spi_comm_test/`         | SPI protocol implementation between master-slave devices for reliable byte-level transmission. |

---

## Hardware Used

- Microcontrollers: ATmega328P (Arduino Uno), ESP32, STM32 (as applicable)
- Sensors:
  - DHT11 / DHT22 (Temperature & Humidity)
  - MQ-2 (Gas Sensor)
  - LDR (Light Sensor)
- Actuators: Servo Motor, DC Motor (with L298N Driver)
- Displays: SSD1306 OLED, I2C LCD (16x2 / 20x4)
- Communication: UART, I2C, SPI

---

## Key Features

- Low-level C/C++ code for real-time hardware control
- Interrupt-driven timers for sensor polling & actuator response
- PWM Signal Generation for motor control and brightness modulation
- Embedded Communication Protocols (UART, SPI, I2C)
- Power-efficient loops and debounce logic for mechanical buttons
- Cross-platform Testing using both Arduino and STM32 environments

---

## Sample Code Snippet

```c
// Sample: Read temperature from DHT11 and control fan
#include <DHT.h>
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

void loop() {
    float temp = dht.readTemperature();
    if (temp > 30) {
        digitalWrite(FAN_PIN, HIGH); // Turn on fan
    } else {
        digitalWrite(FAN_PIN, LOW);
    }
}
````

---

## Setup & Deployment

1. Install [Arduino IDE](https://www.arduino.cc/en/software) or PlatformIO (VS Code).
2. Connect your microcontroller to your system via USB.
3. Open the desired `.ino` or `.c/.cpp` file in the folder.
4. Select appropriate board and port.
5. Compile and upload the firmware.

---

## Extension Ideas

* Add Bluetooth/BLE (HC-05 / ESP32) for wireless control.
* Add EEPROM logging for offline sensor data storage.
* Integrate FreeRTOS for task scheduling and concurrency.

---

## Author

**Ansh Sharma**
GitHub: [@Ag23422](https://github.com/Ag23422)

