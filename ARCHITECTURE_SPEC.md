# Crowd Map 構成仕様書

最終更新: 2026-04-24
対象構成: Arduino + このPC(Windows) + Docker + Cloudflare Tunnel + Vercel

## 1. 目的

この仕様書は、部屋混雑度可視化ページ Crowd Map を「Arduino を USB 接続しているこのPCを中継サーバーとして使う」前提で運用するための標準設計を定義する。

- センサー入力: Arduino
- 中継処理・配信: このPC上の Python API
- コンテナ実行: Docker (主に cloudflared)
- 外部公開: Cloudflare Tunnel
- Web フロント: Vercel (Next.js)

## 2. 全体アーキテクチャ

1. Arduino がセンサーデータを USB シリアルでこのPCへ送信する。
2. このPC上の Python アプリがデータを解釈し、室内人数状態を更新する。
3. このPC上の FastAPI が以下を配信する。
   - 現在状態 API: /api/occupancy
   - SSE API: /api/occupancy/sse
4. cloudflared が FastAPI を Cloudflare 経由で HTTPS 公開する。
5. Vercel 上の crowd-map ページが公開 API を参照し、初期取得 + SSE で表示更新する。

## 3. 論理コンポーネント

### 3.1 Arduino ノード

責務:
- A0-A4 センサー値の取得
- 規定周期で CSV 送信

想定出力フォーマット:
- sensor_distance,sensor_photo_slide,sensor_photo,sensor_light,sensor_pyro

通信:
- USB Serial 115200 bps

### 3.2 PC 中継ノード

責務:
- COM ポートからのシリアル受信
- 入退室推定ロジック実行
- 現在人数状態の保持
- API/SSE 配信
- ログ保存 (任意)

実行環境:
- Windows 10/11
- Python 3.10+
- Docker Desktop (cloudflared 用)

### 3.3 Cloudflare Tunnel

責務:
- このPC内部の FastAPI を外部 HTTPS へ公開
- ポート開放不要化
- 公開ドメイン固定化

### 3.4 Vercel (Next.js)

責務:
- crowd-map UI の配信
- API の初期取得と SSE 受信
- リアルタイム表示

設定:
- NEXT_PUBLIC_CROWD_MAP_BASE_URL に公開 API ドメインを設定

## 4. ネットワーク設計

### 4.1 ローカル通信

- Arduino -> PC: USB シリアル (例: COM3)
- PC 内部: FastAPI (127.0.0.1:8000)

### 4.2 外部通信

- Browser -> Vercel: HTTPS
- Browser -> Cloudflare 公開 API: HTTPS

推奨公開 URL 例:
- https://crowd-api.example.com/api/occupancy
- https://crowd-api.example.com/api/occupancy/sse

## 5. API 契約

### 5.1 GET /api/occupancy

用途:
- 画面初期表示用の最新スナップショット取得

レスポンス例:
{
  "room_counts": { "K": 0, "E": 1, "I": 2, "O": 7 },
  "last_event": {
    "event_label": "io_in_move_confirmed",
    "from_room": "O",
    "to_room": "I",
    "timestamp": "2026-04-24T12:34:56"
  },
  "updated_at": "2026-04-24T12:34:56",
  "sequence": 42
}

### 5.2 GET /api/occupancy/sse

用途:
- 状態更新イベントのリアルタイム配信

レスポンス:
- Content-Type: text/event-stream
- data: で JSON 形式の最新状態を送信

運用要件:
- 切断時にクライアントが再接続できること
- keep-alive イベントまたは更新イベントを継続送信できること

## 6. Docker 構成

### 6.1 標準構成 (Windows推奨)

1. api はホスト実行
- 理由: Windows + Docker Desktop + USB COM の取り回しが複雑なため
- FastAPI とシリアル処理をホスト Python で実行

2. tunnel は Docker 実行
- cloudflared コンテナで公開
- 転送先は host.docker.internal:8000

### 6.2 代替構成 (上級)

1. api も Docker 実行
- Linux ベース環境では可能
- Windows では COM デバイスマウントが難しく非推奨

### 6.3 必須設定項目

- restart: unless-stopped
- healthcheck の定義
- タイムゾーン設定
- ログローテーション

## 7. Cloudflare Tunnel 設計

### 7.1 ルーティング

公開ホスト名:
- crowd-api.example.com

転送先:
- 標準構成: http://host.docker.internal:8000
- 代替構成: http://api:8000

### 7.2 セキュリティ

最低限の対策:
1. 読み取り API でもトークン検証を導入
2. Cloudflare Access か共有シークレットの適用
3. ドメイン制限・レート制限の設定

## 8. Vercel 設計

### 8.1 環境変数

本番:
- NEXT_PUBLIC_CROWD_MAP_BASE_URL=https://crowd-api.example.com

開発:
- NEXT_PUBLIC_CROWD_MAP_BASE_URL=http://127.0.0.1:8000

### 8.2 クライアント通信方針

- 初期表示: /api/occupancy を fetch
- 追従更新: /api/occupancy/sse を EventSource で購読
- 切断時: 3 秒後再接続

## 9. 非機能要件

### 9.1 可用性

- PC 再起動後に自動復帰すること
- cloudflared コンテナが自動起動すること
- FastAPI が自動起動すること (タスクスケジューラまたはサービス化)
- SSE 切断時にクライアント側再接続できること

### 9.2 性能

- 表示更新遅延: 通常 1 秒未満を目標
- 同時閲覧端末: 10 台程度を初期目標

### 9.3 保守性

- 構成は .env で切替可能
- ログを時刻付きで追跡可能
- API ヘルスチェックを提供

## 10. デプロイ手順 (標準)

### 10.1 このPC 側

1. Arduino を USB 接続し、COM ポート確認
2. Python 仮想環境を作成し依存を導入
3. FastAPI を 127.0.0.1:8000 で起動
4. /health で疎通確認
5. シリアル受信と occupancy 更新を確認

### 10.2 Cloudflare 側

1. Tunnel 作成
2. 認証情報をこのPCに配置
3. 公開ホスト名を設定
4. crowd-api.example.com で API 応答確認

### 10.3 Vercel 側

1. プロジェクトをデプロイ
2. NEXT_PUBLIC_CROWD_MAP_BASE_URL を設定
3. crowd-map ページアクセス
4. 初期取得と SSE 更新を確認

## 11. 監視・運用

### 11.1 最低監視項目

- API 稼働 (/health)
- SSE 接続エラー率
- 最終更新時刻の遅延
- PC の CPU/メモリ

### 11.2 障害時切り分け

1. Arduino 送信有無
2. COM ポート認識状態
3. FastAPI ログ
4. cloudflared ログ
5. ブラウザコンソール (SSE 接続状態)

## 12. 既知の制約

- PC の電源オフ・スリープ時は配信停止
- Windows 更新再起動で一時停止しうる
- Arduino COM 番号が変わる場合がある
- インターネット品質により SSE 安定性が影響を受ける

## 13. 将来拡張

1. API 認証強化 (JWT, Access)
2. DB 保存 (SQLite/PostgreSQL)
3. イベント履歴 API の追加
4. 異常検知アラート通知
5. Raspberry Pi など常時稼働機への移行
