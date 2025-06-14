# 棚割軸 小売業ダッシュボード PoC

## 概要
小売業向けの棚割分析ダッシュボードアプリケーションです。ID-POSデータ（売上データ）と棚割データ（陳列データ）を統合し、売上分析や占有率分析を提供します。

## 機能
- **売上分析**: 店舗別・期間別の売上トレンド
- **占有率分析**: 商品の棚占有率と売上の関係
- **期間比較**: 前年同期比や前月比の分析
- **可視化**: インタラクティブなグラフとチャート

## 技術スタック
- **フレームワーク**: Streamlit
- **データ処理**: Pandas, NumPy
- **可視化**: Plotly
- **データベース**: Google BigQuery (pandas-gbq)

## セットアップ

### 必要な環境
- Python 3.8以上
- pip

### インストール
```bash
# 依存関係のインストール
pip install -r dashboard_app/requirements.txt

# アプリケーションの起動
cd dashboard_app
streamlit run dashboard_app.py
```

### アクセス
アプリケーションは `http://localhost:8501` でアクセスできます。

## データファイル
- `df_idpos_per_store_day.csv`: 売上データ（店舗別・日別）
- `df_demo_occupied.csv`: 棚割データ（商品陳列情報）

## ライセンス
MIT License 