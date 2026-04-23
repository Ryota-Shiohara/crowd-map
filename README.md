# マルチセンサー入退室計測システム

## 0. ディレクトリ構成

```text
crowd-map/
├─ README.md
├─ arduino/
│  └─ monita_test.ino
└─ python/
  ├─ room_flow_monitor.py
  └─ sensors/
    ├─ distance_sensor.py
    ├─ accel_sensor.py
    ├─ photo_sensor.py
    ├─ light_sensor.py
    └─ pyro_sensor.py
```

- Arduino側は arduino/monita_test.ino の1ファイルで管理
- Python側は sensors/ 配下でセンサーごとにファイル分割

## 1. 概要・目的
Arduino UNO 1台に複数種類のセンサーを接続し、人の通過イベントと在室人数の推定を行うシステムです。

このリポジトリは以下を対象にします。
- センサー値のリアルタイム取得
- PC側での可視化
- イベント推定ログのCSV保存

現時点では、閾値や一部の判定条件は現地テストで調整する前提です。

## 2. システム構成
- マイコン: Arduino UNO
- 接続センサー: 5種類
- 通信: USBシリアル (115200bps)
- PCアプリ: Python (matplotlib + pyserial)
- ログ: CSV (ローカル保存)

### 2.1 部屋構成 (4部屋)
- 部屋名: K, E, I, O
- 中心部屋: I
- 接続関係: IがK/E/Oと接続
- IとOの間: 出入口が2つあり、それぞれ一方通行

配置イメージ:

```text
          [ K ]
            |
            |
[ E ] ----- [ I ] ----- [ O ]
              ||
              ||
        (I->O gate)  (O->I gate)
```

I-O間の一方通行ゲート:
- O_to_I: O -> I 専用
- I_to_O: I -> O 専用

処理の流れ:
1. ArduinoがA0-A4を100ms周期で読み取る
2. 5列CSVとしてシリアル送信する
3. Pythonが受信してグラフ描画する
4. センサー組み合わせルールでイベント推定する
5. CSVログに保存する

## 3. 使用部品一覧
型番は未確定のため、役割ベースで記載します。

| 種類 | 用途 | 備考 |
|---|---|---|
| 測距センサー | 通過時パルス検出 | 閾値は要調整 |
| 加速度センサー | スライド戸の開閉検知 | X軸を主に利用 |
| フォトリフレクター | 引き戸近傍の開閉変化検知 | 起動時キャリブレーション |
| 光センサー | 在室候補検知 (照明ON相当) | 後で環境補正予定 |
| 焦電センサー | 人体動きの在室補助検知 | A4に接続 |

## 4. 配線表 (ピン割り当て)

| Arduinoピン | センサー |
|---|---|
| A0 | 測距センサー |
| A1 | 加速度センサー (X軸出力) |
| A2 | フォトリフレクター |
| A3 | 光センサー |
| A4 | 焦電センサー |

## 5. セットアップ
### 5.1 Arduino
1. Arduino IDEで arduino/monita_test.ino を開く
2. ボードを Arduino UNO に設定する
3. 正しいシリアルポートを選ぶ
4. スケッチを書き込む

### 5.2 Python
必要ライブラリ:
- pyserial
- matplotlib

インストール例:
```bash
pip install pyserial matplotlib
```

## 6. 実行方法
1. Arduinoを書き込み後、USB接続したままにする
2. python/room_flow_monitor.py の PORT を環境に合わせる (例: COM3)
3. python/room_flow_monitor.py の ACTIVE_GATE を設置ポイントに合わせる
  - 例: IとOの一方通行出口側なら I_to_O
  - 例: IとOの一方通行入口側なら O_to_I
  - K, E側も同様にゲート方向を選択
4. 次を実行する

```bash
python python/room_flow_monitor.py
```

実行すると、5チャネルのリアルタイムグラフが表示され、同時に sensor_log.csv が出力されます。

## 7. データフォーマット
### 7.1 Arduino -> Python (シリアル)
1行5列のCSVです。

例:
```text
512,401,632,220,700
```

列の意味:
1. sensor_distance
2. sensor_accel
3. sensor_photo
4. sensor_light
5. sensor_pyro

### 7.2 PythonログCSV
ファイル名: sensor_log.csv

列:
- timestamp
- sensor_distance
- sensor_accel
- sensor_photo
- sensor_light
- sensor_pyro
- from_room
- to_room
- event_label
- count_K
- count_E
- count_I
- count_O

## 8. 判定ロジック (初期実装)
### 8.1 センサー単体判定
- 測距: 一定閾値以下で通過候補
- 加速度: 基準値からの差分で扉動作候補
- フォトリフレクター: 起動時基準との差分で扉動作候補
- 光: 基準値との差分で在室候補
- 焦電: 閾値以上で在室候補を補強

### 8.2 入退室推定
以下の時系列組み合わせで推定します。
- 扉動作イベントが発生
- 一定時間窓内に通過イベントが発生
- 設置ゲートの方向 (from_room -> to_room) に従って部屋人数を更新
- 光状態を補助情報として確信度を判定

### 8.3 部屋間遷移推定
- 各計測ノードは1つのゲート方向を担当します (ACTIVE_GATE)
- 通過が確定した場合、from_room から to_room へ1人移動します
- from_room の人数が0以下のときは移動を拒否し、event_labelで記録します

注意:
- 閾値は暫定値です。必ず現地で調整してください。
- 現在の推定ロジックは初期版で、誤検知が起きる可能性があります。

## 9. トラブルシュート
- グラフが表示されない:
  - PORT設定が実機と一致しているか確認
  - ボーレートが115200か確認
- Invalid行が多い:
  - Arduino側が5列CSVを送っているか確認
  - ノイズ混入時はGND配線と電源安定性を確認
- 人数推定がずれる:
  - 各閾値を再調整
  - 扉イベント連携時間窓を調整
  - ACTIVE_GATEの方向設定が設置位置と一致しているか確認

## 10. 簡易検証条件
- サンプリング周期: 100ms
- 各センサーを単体で反応確認
- 扉開閉 + 通過の組み合わせを複数回試験
- ログCSVの event_label と count_K/count_E/count_I/count_O の整合を確認

## 11. 今後の課題
- センサー型番の確定と特性反映
- 閾値自動調整 (キャリブレーション強化)
- 昼夜・外光変動に対する光センサー補正
- 推定ロジックの高精度化 (時間窓・状態遷移モデル導入)
