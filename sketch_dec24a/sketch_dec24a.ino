#include <Servo.h>

Servo servo;
const int trigPin = 9;
const int echoPin = 10;
const int servoPin = 3;

void setup() {
  Serial.begin(9600);
  servo.attach(servoPin);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
}

void loop() {
  // Sweep 0 to 180
  for (int angle = 0; angle <= 180; angle += 1) {
    servo.write(angle);
    delay(40);
    int distance = getDistance();
    Serial.print(angle);
    Serial.print(",");
    Serial.print(distance);
    Serial.println(".");
  }
  
  // Sweep 180 back to 0
  for (int angle = 180; angle >= 0; angle -= 1) {
    servo.write(angle);
    delay(40);
    int distance = getDistance();
    Serial.print(angle);
    Serial.print(",");
    Serial.print(distance);
    Serial.println(".");
  }
}

int getDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) {
    return 0;
  }
  int distance = duration * 0.034 / 2;
  return constrain(distance, 0, 100);
}
