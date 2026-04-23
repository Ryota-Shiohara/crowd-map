int sensorPin0 = A0;  // センサー1
int sensorPin1 = A1;  // センサー2
int sensorPin2 = A2;  // センサー3
int sensorPin3 = A3;  // センサー4

void setup() {
  Serial.begin(115200);  // シリアル通信開始
}

void loop() {
  int sensorValue0 = analogRead(sensorPin0);  // 0〜1023
  int sensorValue1 = analogRead(sensorPin1);  // 0〜1023
  int sensorValue2 = analogRead(sensorPin2);  // 0〜1023
  int sensorValue3 = analogRead(sensorPin3);  // 0〜1023

  // 例: 123,456,789,234
  Serial.print(sensorValue0);
  Serial.print(",");
  Serial.print(sensorValue1);
  Serial.print(",");
  Serial.print(sensorValue2);
  Serial.print(",");
  Serial.println(sensorValue3);

  delay(100);  // 0.1秒ごと
}
