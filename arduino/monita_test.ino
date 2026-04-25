int sensorPin0 = A3;  // 測距センサー
int sensorPin1 = A1;  // フォトリフレクタ (スライド扉)
int sensorPin2 = A2;  // フォトリフレクタ (O->Iゲート)
int sensorPin3 = A0;  // 光センサー
int sensorPin4 = A4;  // 焦電センサー

void setup() {
  Serial.begin(115200);  // シリアル通信開始
}

void loop() {
  int sensorValue0 = analogRead(sensorPin0);  // 0〜1023
  int sensorValue1 = analogRead(sensorPin1);  // 0〜1023
  int sensorValue2 = analogRead(sensorPin2);  // 0〜1023
  int sensorValue3 = analogRead(sensorPin3);  // 0〜1023
  int sensorValue4 = analogRead(sensorPin4);  // 0〜1023

  // 例: 123,456,789,234,512
  Serial.print(sensorValue0);
  Serial.print(",");
  Serial.print(sensorValue1);
  Serial.print(",");
  Serial.print(sensorValue2);
  Serial.print(",");
  Serial.print(sensorValue3);
  Serial.print(",");
  Serial.println(sensorValue4);

  delay(100);  // 0.1秒ごと
}
