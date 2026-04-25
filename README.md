# マルチセンサー入退室計測システム

## 0. ディレクトリ構成

```text
crowd-map/
├─ README.md
├─ ARCHITECTURE_SPEC.md
├─ apps/
│  ├─ api/
│  │  ├─ src/
│  │  │  ├─ main.py
│  │  │  ├─ serial_worker.py
│  │  │  ├─ config.py
│  │  │  ├─ api/
│  │  │  ├─ domain/
│  │  │  ├─ infra/
│  │  │  └─ sensors/
│  │  ├─ requirements.txt
│  │  └─ .env.example
├─ arduino/
│  └─ monita_test.ino
├─ infra/
│  ├─ docker/
│  │  ├─ docker-compose.tunnel.yml
│  │  └─ cloudflared/config.yml
├─ data/
│  └─ logs/
└─ README.md
```

起動エントリ：
- `apps/api/src/main.py`（FastAPI + シリアル受信ワーカー）

主要ディレクトリ：
- `apps/api`: このPC上で動く API/推定/配信
- `infra/docker`: Cloudflare Tunnel 用 Docker 構成
- `data/logs`: `sensor_log.csv`, `event_log.csv` の保存先

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
- PCアプリ: Python (FastAPI + pyserial)
- ログ: CSV (ローカル保存)

### 2.1 部屋構成 (4部屋)
- 部屋名: K, E, I, O
- 中心部屋: I
- 接続関係: K-I-O と E-I-O
- IとOの間: 出入口が2つあり、それぞれ一方通行
- IとOはそれぞれ1部屋で、K/Eより広い想定

配置イメージ:

```text
+-----------------+----------------------+----------------------+
|        K        |                      |  フォトリフレクタ   |
|       光        |          I           |          O           |
+-----------------+                      |                      |
|        E        |   測距        加速度  |                      |
+-----------------+----------------------+----------------------+

黄色ラベル = センサー位置
```

I-O間の一方通行ゲート:
- O_to_I: O -> I 専用
- I_to_O: I -> O 専用

センサー配置:
- 光センサー: K室内
- 測距センサー: E-I境界付近
- 加速度センサー: I-O境界付近
- フォトリフレクター: O側上部 (I-O側)
- 焦電センサー (A4): 追加センサーとして運用

処理の流れ:
1. ArduinoがA0-A4を100ms周期で読み取る
2. 5列CSVとしてシリアル送信する
3. Pythonが受信してグラフ描画する
4. センサー組み合わせルールでイベント推定する
5. センサーログとイベントログを別CSVで保存する

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
```bash
pip install -r apps/api/requirements.txt
```

## 6. 実行方法

### 6.1 基本的な実行

1. Arduinoを書き込み後、USB接続したままにする
2. `apps/api/.env.example` をコピーして `.env` を作成し、`CROWD_SERIAL_PORT` を設定する
3. API を起動する

```bash
python -m uvicorn apps.api.src.main:app --host 127.0.0.1 --port 8000
```

実行すると、以下が自動で開始されます：
- FastAPI Web サーバーが起動する（http://127.0.0.1:8000）
- CSV ログが出力される

### 6.2 ブラウザでの確認（オプション）

API を確認する場合:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/api/occupancy

シリアル接続エラーが出る場合は、Arduino IDE のシリアルモニタや他の COM 使用アプリを閉じてから再実行してください。

### 6.3 波形を見る場合（オプション）

```bash
cd apps/api
python src/waveform_viewer.py
```

Arduino の生波形を 5 チャネルで表示します。API は起動せず、表示専用です。

### 6.4 出力ログ

実行すると以下のログが生成されます：
- `sensor_log.csv`: 毎サンプルのセンサー値
- `event_log.csv`: イベント発生時のみの人数変化ログ

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

### 7.2 センサーログCSV
ファイル名: sensor_log.csv

列:
- timestamp
- sensor_distance
- sensor_accel
- sensor_photo
- sensor_light
- sensor_pyro

### 7.3 イベントログCSV
ファイル名: event_log.csv

列:
- timestamp
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
- 測距センサー: E-I境界の通過を検出し、EI_DEFAULT_DIRECTION方向へ人数更新
- 加速度センサー: I->O側の一方通行ゲートとして人数更新
- フォトリフレクター: O->I側の一方通行ゲートとして人数更新
- 光/焦電センサー: 通過イベントの確信度補助

### 8.3 部屋間遷移推定
- 測距ラインは E-I の遷移のみを担当します
- I-Oは2つの一方通行ラインを別センサーで担当します
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
  - EI_DEFAULT_DIRECTION が実際の運用方向と一致しているか確認
  - 加速度/フォトリフレクターの設置向きが一方通行方向と一致しているか確認

## 10. 簡易検証条件
- サンプリング周期: 100ms
- 各センサーを単体で反応確認
- 扉開閉 + 通過の組み合わせを複数回試験
- ログCSVの event_label と count_K/count_E/count_I/count_O の整合を確認

## 11. API 配信仕様（最小構成）

このリポジトリは「センサー受信 + 状態推定 + API/SSE配信」に機能を絞っています。
フロントエンド表示は別リポジトリまたは将来追加する Web アプリで行います。

### 11.1 エンドポイント

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/health` | GET | ヘルスチェック |
| `/api/occupancy` | GET | 現在の室別人数（JSON） |
| `/api/occupancy/sse` | GET | SSE ストリーム（text/event-stream） |

### 11.2 SSE データフォーマット

```json
{
  "room_counts": {
    "K": 0,
    "E": 1,
    "I": 2,
    "O": 7
  },
  "last_event": {
    "event_label": "io_in_move_confirmed",
    "from_room": "O",
    "to_room": "I",
    "timestamp": "2026-04-24T12:34:56"
  },
  "updated_at": "2026-04-24T12:34:56",
  "sequence": 42
}
```

## 13. 今後の課題
- センサー型番の確定と特性反映
- 閾値自動調整 (キャリブレーション強化)
- 昼夜・外光変動に対する光センサー補正
- 推定ロジックの高精度化 (時間窓・状態遷移モデル導入)
- WebSocket 導入（ブラウザからセンサー設定変更を可能にする場合）
- データベース化（CSV から SQLite への移行）
