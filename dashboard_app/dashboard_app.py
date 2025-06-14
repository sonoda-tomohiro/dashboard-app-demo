import streamlit as st
import pandas as pd
import os # ファイルの存在確認用
from datetime import datetime
import numpy as np # 占有率の切り捨てに使用
import plotly.express as px
import plotly.graph_objects as go # 累計グラフの追加に必要

# --- アプリの基本設定 ---
st.set_page_config(layout="wide", page_title="棚割軸 小売業ダッシュボード PoC")

# Custom CSS for font size adjustment, margin reduction, and sidebar width
st.markdown("""
    <style>
    /* 全体的な文字サイズを小さくする */
    html, body, .stMarkdown, .stSelectbox, .stButton, .stWarning, .stInfo, .stError, .stText {
        font-size: 0.8em; /* デフォルトよりさらに小さく */
    }
    /* ヘッダーの文字サイズをさらに調整 */
    h1, h2, h3, h4, h5, h6 {
        font-size: 1.2rem; /* h1, h2, h3 などの相対サイズを調整 */
    }
    /* st.header (h2) のサイズを調整 */
    .st-emotion-cache-16txto3 { /* st.header の具体的なクラスをターゲット (バージョンによって変わる可能性あり) */
        font-size: 2.2rem !important; /* タイトルのサイズを少し大きく */
    }
    /* st.dataframe のヘッダーとコンテンツのフォントサイズも調整 */
    .stDataFrame .data-grid-container {
        font-size: 0.8em;
    }
    .stDataFrame .header-cell {
        font-size: 0.85em; /* ヘッダーのフォントサイズを少し大きく */
    }

    /* サイドバーの横幅を小さくする */
    section[data-testid="stSidebar"] {
        width: 250px !important; /* 希望の幅に調整してください */
        max-width: 250px !important; /* 必要に応じて最大幅も設定 */
    }
    section[data-testid="stSidebarContent"] {
        width: 250px !important; /* サイドバーコンテンツの幅も合わせる */
        max-width: 250px !important;
    }
    </style>
    """, unsafe_allow_html=True)


# --- データファイルの読み込み ---
@st.cache_data # データをキャッシュし、変更がない限り再読み込みしないようにする
def load_data():
    # スクリプトのディレクトリを取得して絶対パスでファイルを指定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    idpos_file = os.path.join(script_dir, 'df_idpos_per_store_day.csv')
    planogram_file = os.path.join(script_dir, 'df_demo_occupied.csv')

    df_idpos = None
    df_planogram = None

    # ID-POSデータの読み込みとカラム名変換
    if os.path.exists(idpos_file):
        try:
            df_idpos_raw = pd.read_csv(idpos_file) # まずはそのまま読み込む
            idpos_columns = ['売上日', '店舗CD', 'JAN', '商品名', 'ディビジョン', 'ID数', 'レシート枚数', '売上金額', '売上数量']
            
            # カラム数が一致する場合のみカラム名を変換
            if len(df_idpos_raw.columns) == len(idpos_columns):
                df_idpos = df_idpos_raw.copy() # copy()して元のデータに影響を与えないようにする
                df_idpos.columns = idpos_columns
            else:
                st.error(f"エラー: '{idpos_file}' のカラム数 ({len(df_idpos_raw.columns)}) が、期待されるカラム数 ({len(idpos_columns)}) と一致しません。カラム名の変換に失敗しました。")
                df_idpos = None # カラム変換失敗時はDataFrameをNoneにする
        except Exception as e:
            st.error(f"'{idpos_file}' の読み込みまたはカラム名変換中にエラーが発生しました: {e}")
            df_idpos = None # エラー発生時はDataFrameをNoneにする
    else:
        st.error(f"エラー: '{idpos_file}' が見つかりません。")
        df_idpos = None

    # ID-POSデータが正常にロードされた場合のみ、日付とJANの型変換を行う
    if df_idpos is not None:
        if '売上日' in df_idpos.columns:
            df_idpos['売上日'] = pd.to_datetime(df_idpos['売上日'])
        else:
            st.warning(f"'{idpos_file}' に '売上日' カラムが見つかりませんでした。日付変換をスキップします。")
        
        if 'JAN' in df_idpos.columns:
            df_idpos['JAN'] = df_idpos['JAN'].astype(str)
        else:
            st.warning(f"'{idpos_file}' に 'JAN' カラムが見つかりませんでした。JANの文字列変換をスキップします。")

    # 棚割データの読み込みとカラム名変換
    if os.path.exists(planogram_file):
        try:
            df_planogram_raw = pd.read_csv(planogram_file) # まずはそのまま読み込む
            planogram_columns = ['テーマ名', 'テーマタイプ', '店舗CD', '店舗名', '展開開始日', '展開終了日', '棚番号', 'JAN', '商品名', '陳列面積', '陳列数量', '占有率']
            
            # カラム数が一致する場合のみカラム名を変換
            if len(df_planogram_raw.columns) == len(planogram_columns):
                df_planogram = df_planogram_raw.copy() # copy()して元のデータに影響を与えないようにする
                df_planogram.columns = planogram_columns
            else:
                st.error(f"エラー: '{planogram_file}' のカラム数 ({len(df_planogram_raw.columns)}) が、期待されるカラム数 ({len(planogram_columns)}) と一致しません。カラム名の変換に失敗しました。")
                df_planogram = None # カラム変換失敗時はDataFrameをNoneにする
        except Exception as e:
            st.error(f"'{planogram_file}' の読み込みまたはカラム名変換中にエラーが発生しました: {e}")
            df_planogram = None # エラー発生時はDataFrameをNoneにする
    else:
        st.error(f"エラー: '{planogram_file}' が見つかりません。")
        df_planogram = None

    # 棚割データが正常にロードされた場合のみ、日付とJANの型変換を行う
    if df_planogram is not None:
        if '展開開始日' in df_planogram.columns and '展開終了日' in df_planogram.columns:
            df_planogram['展開開始日'] = pd.to_datetime(df_planogram['展開開始日'])
            df_planogram['展開終了日'] = pd.to_datetime(df_planogram['展開終了日'])
        else:
            st.warning(f"'{planogram_file}' に '展開開始日' または '展開終了日' カラムが見つかりませんでした。日付変換をスキップします。")
        
        if 'JAN' in df_planogram.columns:
            df_planogram['JAN'] = df_planogram['JAN'].astype(str)
        else:
            st.warning(f"'{planogram_file}' に 'JAN' カラムが見つかりませんでした。JANの文字列変換をスキップします。")

    return df_idpos, df_planogram

df_idpos, df_planogram = load_data()


# ヘルパー関数: 指定期間のID-POSデータを集計する
def get_period_total_metrics(df_idpos_data, store_cd, start_date_dt, end_date_dt):
    if df_idpos_data is None or store_cd is None or start_date_dt is None or end_date_dt is None:
        return 0.0, 0.0, 0.0, 0.0 

    period_data = df_idpos_data[
        (df_idpos_data['店舗CD'] == store_cd) &
        (df_idpos_data['売上日'].dt.date >= start_date_dt.date()) &
        (df_idpos_data['売上日'].dt.date <= end_date_dt.date())
    ]
    
    sales_amount = float(period_data['売上金額'].sum()) if '売上金額' in period_data.columns else 0.0
    sales_quantity = float(period_data['売上数量'].sum()) if '売上数量' in period_data.columns else 0.0
    id_count = float(period_data['ID数'].sum()) if 'ID数' in period_data.columns else 0.0
    receipt_count = float(period_data['レシート枚数'].sum()) if 'レシート枚数' in period_data.columns else 0.0

    return sales_amount, sales_quantity, id_count, receipt_count

# ヘルパー関数: 日次平均の増減率を計算し、色付き文字列で返す
def calculate_daily_change_percentage_str(current_total, current_start, current_end, prev_total, prev_start, prev_end):
    # current_start, current_end, prev_start, prev_endがdatetimeオブジェクトであることを確認
    if not (isinstance(current_start, datetime) and isinstance(current_end, datetime) and \
            isinstance(prev_start, datetime) and isinstance(prev_end, datetime)):
        return "N/A"

    # 現在期間の日数を計算
    days_current = (current_end.date() - current_start.date()).days + 1
    # 前期間の日数を計算
    days_prev = (prev_end.date() - prev_start.date()).days + 1

    current_daily_avg = current_total / days_current if days_current > 0 else 0.0
    prev_daily_avg = prev_total / days_prev if days_prev > 0 else 0.0

    if prev_daily_avg == 0.0:
        if current_daily_avg > 0.0:
            return "<span style='font-size: 1.0em; color: red;'>+∞%</span>" 
        else:
            return "N/A" 
    
    change_percent = ((current_daily_avg - prev_daily_avg) / prev_daily_avg) * 100

    if change_percent > 0:
        return f"<span style='font-size: 1.0em; color: red;'>+{change_percent:.1f}%</span>" 
    elif change_percent < 0:
        return f"<span style='font-size: 1.0em; color: blue;'>{change_percent:.1f}%</span>" 
    else:
        return "<span style='font-size: 1.0em;'>0.0%</span>" 

# ヘルパー関数: 日次・累計グラフを作成する
def create_daily_cumulative_graph(daily_data, metric_name, unit, title, color_daily, color_cumulative):
    fig = go.Figure()
    
    # 累計 (棒グラフ) - 右軸
    fig.add_trace(go.Bar(x=daily_data['売上日'], y=daily_data[f'累計{metric_name}'],
                        name=f'累計{metric_name}', yaxis='y2', marker_color=color_cumulative,
                        hovertemplate=f'売上日: %{{x|%Y-%m-%d}}<br>累計{metric_name}: %{{y:,.0f}}{unit}<extra></extra>',
                        visible=True)) 

    # 日次 (折れ線グラフ) - 左軸
    fig.add_trace(go.Scatter(x=daily_data['売上日'], y=daily_data[f'日次{metric_name}'],
                            mode='lines+markers', name=f'日次{metric_name}', yaxis='y1',
                            line=dict(color=color_daily, width=2), marker=dict(size=4),
                            hovertemplate=f'売上日: %{{x|%Y-%m-%d}}<br>日次{metric_name}: %{{y:,.0f}}{unit}<extra></extra>'))
    
    fig.update_layout(
        title_text=title,
        xaxis_title='売上日',
        yaxis=dict(
            title=f'日次{metric_name} ({unit})',
            titlefont=dict(color=color_daily),
            tickfont=dict(color=color_daily)
        ),
        yaxis2=dict(
            title=f'累計{metric_name} ({unit})',
            titlefont=dict(color=color_cumulative),
            tickfont=dict(color=color_cumulative),
            overlaying='y',
            side='right'
        ),
        hovermode="x unified",
        legend_title_text='',
        height=350, # 高さを調整
        legend=dict(orientation="h", yanchor="top", y=1.1, xanchor="center", x=0.5) # 凡例をグラフの上に中央揃えで配置
    )
    return fig

# --- タイトルをサイドバーへ移動 ---
with st.sidebar:
    st.header("Dashboard PoC") # サイドバーのタイトルを大きめに


# --- サイドバーにフィルターを配置 ---
st.sidebar.header("データ絞り込みオプション")

# 店舗名選択: df_demo_occupied.csvの「店舗名」カラムのユニーク値を使用
store_names = []
if df_planogram is not None and '店舗名' in df_planogram.columns:
    store_names = sorted(df_planogram['店舗名'].unique().tolist())
selected_store_name = st.sidebar.selectbox("店舗名を選択してください", [''] + store_names, index=0)

# テーマ名選択: df_demo_occupied.csvの「テーマ名」カラムのユニーク値を使用
theme_names = []
if df_planogram is not None and selected_store_name and '店舗名' in df_planogram.columns and 'テーマ名' in df_planogram.columns:
    theme_names = sorted(df_planogram[df_planogram['店舗名'] == selected_store_name]['テーマ名'].unique().tolist())
elif df_planogram is not None and 'テーマ名' in df_planogram.columns:
    theme_names = sorted(df_planogram['テーマ名'].unique().tolist())
selected_theme_name = st.sidebar.selectbox("テーマ名を選択してください", [''] + theme_names, index=0)

# --- 展開期間ナビゲーション (ドロップダウンに変更) ---
st.sidebar.header("展開期間選択")
selected_start_date = None # 初期値をNoneに設定
current_end_date_dt = None # 現在の展開終了日

# 条件が設定されている場合のみ、展開開始日の選択肢を生成
if df_planogram is not None and selected_store_name and selected_theme_name:
    # 店舗名とテーマ名でフィルタリング
    if '店舗名' in df_planogram.columns and 'テーマ名' in df_planogram.columns:
        filtered_by_store_theme = df_planogram[
            (df_planogram['店舗名'] == selected_store_name) &
            (df_planogram['テーマ名'] == selected_theme_name)
        ].copy()
    else:
        filtered_by_store_theme = pd.DataFrame() # 空のDataFrameを設定

    if not filtered_by_store_theme.empty:
        # このブロックに入る前に filtered_by_store_theme が空でないことを確認済み
        # filtered_by_store_theme.columns を直接参照してエラーを避ける
        if '展開開始日' in filtered_by_store_theme.columns: 
            unique_start_dates = sorted(filtered_by_store_theme['展開開始日'].unique().tolist())
            formatted_dates = [''] + [d.strftime('%Y-%m-%d') for d in unique_start_dates]
            
            selected_formatted_date = st.sidebar.selectbox(
                "展開開始日を選択してください",
                formatted_dates,
                index=0
            )
            if selected_formatted_date:
                selected_start_date = datetime.strptime(selected_formatted_date, '%Y-%m-%d')
                matching_planogram = filtered_by_store_theme[filtered_by_store_theme['展開開始日'] == selected_start_date]
                if not matching_planogram.empty and '展開終了日' in matching_planogram.columns:
                    current_end_date_dt = matching_planogram['展開終了日'].iloc[0]
        else:
            st.sidebar.warning("フィルタリングされた棚割データに '展開開始日' カラムが見つかりませんでした。")
    else:
        st.sidebar.warning("選択された店舗名とテーマ名に一致する棚割データが見つかりませんでした。")
else:
    st.sidebar.info("店舗名とテーマ名を選択すると、展開開始日が表示されます。")


# --- ダッシュボード本体 ---
# フィルターが選択されていない場合は情報メッセージを表示し、それ以上は処理しない
if not (selected_store_name and selected_theme_name and selected_start_date):
    st.info("左側のサイドバーで「店舗名」と「テーマ名」、そして「展開開始日」を選択してください。")
else:
    # データを再フィルタリングして使用
    # df_planogramがNoneでないことを確認した上でfiltered_by_store_theme_mainを生成
    if df_planogram is not None and '店舗名' in df_planogram.columns and 'テーマ名' in df_planogram.columns:
        filtered_by_store_theme_main = df_planogram[
            (df_planogram['店舗名'] == selected_store_name) &
            (df_planogram['テーマ名'] == selected_theme_name)
        ].copy()
    else:
        # df_planogramがNoneの場合や必須カラムがない場合は空のDataFrameを設定
        filtered_by_store_theme_main = pd.DataFrame()
        st.error("棚割データが利用できないため、メインダッシュボードを表示できません。")
        
    if not filtered_by_store_theme_main.empty: # filtered_by_store_theme_mainが空でないことを確認
        planogram_data_for_display = filtered_by_store_theme_main[
            filtered_by_store_theme_main['展開開始日'] == selected_start_date
        ].copy()

        if not planogram_data_for_display.empty:
            end_date_for_display_str = current_end_date_dt.strftime('%Y-%m-%d') if current_end_date_dt else "N/A"
            
            st.write(f"### {selected_store_name}/{selected_theme_name} <small style='font-size: 0.8em; color: grey;'>({selected_start_date.strftime('%Y-%m-%d')}〜{end_date_for_display_str})</small>", unsafe_allow_html=True)


            # --- ID-POSデータを結合し、売上金額と売上数量などを追加 ---
            if df_idpos is not None:
                required_cols_planogram = ['店舗CD', 'JAN', '展開開始日', '展開終了日']
                required_cols_idpos = ['店舗CD', 'JAN', '売上日', '売上金額', '売上数量', 'ID数', 'レシート枚数']

                if all(col in planogram_data_for_display.columns for col in required_cols_planogram) and \
                   all(col in df_idpos.columns for col in required_cols_idpos):

                    merged_df_for_idpos = pd.merge(
                        planogram_data_for_display,
                        df_idpos,
                        on=['店舗CD', 'JAN'],
                        how='left',
                        suffixes=('_planogram', '_idpos')
                    )
                    
                    groupby_cols_original = planogram_data_for_display.columns.tolist()
                    actual_groupby_keys = []
                    for col in groupby_cols_original:
                        if f"{col}_planogram" in merged_df_for_idpos.columns:
                            actual_groupby_keys.append(f"{col}_planogram")
                        elif col in merged_df_for_idpos.columns:
                            actual_groupby_keys.append(col)

                    merged_df_for_idpos = merged_df_for_idpos[
                        (merged_df_for_idpos['売上日'].notna()) &
                        (merged_df_for_idpos['展開開始日'].notna()) &
                        (merged_df_for_idpos['展開終了日'].notna()) &
                        (merged_df_for_idpos['売上日'].dt.date >= merged_df_for_idpos['展開開始日'].dt.date) &
                        (merged_df_for_idpos['売上日'].dt.date <= merged_df_for_idpos['展開終了日'].dt.date)
                    ]
                    
                    aggregated_idpos = merged_df_for_idpos.groupby(
                        actual_groupby_keys, as_index=False
                    )[['売上金額', '売上数量', 'ID数', 'レシート枚数']].sum()
                    
                    rename_map = {f"{col}_planogram": col for col in groupby_cols_original if f"{col}_planogram" in aggregated_idpos.columns}
                    aggregated_idpos_renamed = aggregated_idpos.rename(columns=rename_map)

                    final_display_df = pd.merge(
                        planogram_data_for_display,
                        aggregated_idpos_renamed,
                        on=groupby_cols_original,
                        how='left'
                    ).fillna({
                        '売上金額': 0.0,
                        '売上数量': 0.0,
                        'ID数': 0.0,
                        'レシート枚数': 0.0
                    })
                    
                else:
                    st.warning("ID-POSデータとの結合に必要なカラムが不足しているか、名前が一致しません。棚割データのみを表示します。")
                    final_display_df = planogram_data_for_display.copy()
            else:
                st.info("ID-POSデータファイルが読み込まれていません。棚割データのみを表示します。")
                final_display_df = planogram_data_for_display.copy()

            # 占有率を数値に変換し、棚効率を計算
            if '占有率' in final_display_df.columns and '売上数量' in final_display_df.columns:
                final_display_df['占有率_数値'] = pd.to_numeric(final_display_df['占有率'], errors='coerce').fillna(0)
                final_display_df['棚効率'] = np.where(
                    final_display_df['占有率_数値'] > 0,
                    final_display_df['売上数量'] / final_display_df['占有率_数値'],
                    0
                )
                final_display_df['棚効率'] = final_display_df['棚効率'].apply(lambda x: np.ceil(x * 100) / 100 if x > 0 else 0)
            else:
                st.warning("棚効率の計算に必要な'占有率'または'売上数量'カラムが見つかりません。")
                final_display_df['棚効率'] = 0.0

            # 棚判定の追加
            if '棚効率' in final_display_df.columns:
                shelf_efficiency_values = final_display_df['棚効率'].dropna()
                if not shelf_efficiency_values.empty:
                    q1 = shelf_efficiency_values.quantile(0.25)
                    q3 = shelf_efficiency_values.quantile(0.75)

                    conditions = [
                        final_display_df['棚効率'] <= q1,
                        (final_display_df['棚効率'] > q1) & (final_display_df['棚効率'] <= q3),
                        final_display_df['棚効率'] > q3
                    ]
                    choices = ['いまいち...', 'ふつう', '好調！']
                    final_display_df['棚判定'] = np.select(conditions, choices, default='N/A')
                else:
                    final_display_df['棚判定'] = 'データなし'
                    st.info("棚効率データが空のため、棚判定を計算できませんでした。")
            else:
                final_display_df['棚判定'] = '棚効率なし'
                st.warning("棚判定の計算に必要な'棚効率'カラムが見つかりません。")

            # 展開開始日と展開終了日をYYYY-MM-DD形式に変換 (表示用)
            if '展開開始日' in final_display_df.columns:
                final_display_df['展開開始日'] = final_display_df['展開開始日'].dt.strftime('%Y-%m-%d')
            if '展開終了日' in final_display_df.columns:
                final_display_df['展開終了日'] = final_display_df['展開終了日'].dt.strftime('%Y-%m-%d')

            # 占有率を小数点第一桁までで切り捨てて％を末尾につける (棚効率計算後に行う)
            if '占有率' in final_display_df.columns:
                final_display_df['占有率'] = pd.to_numeric(final_display_df['占有率'], errors='coerce')
                final_display_df['占有率'] = final_display_df['占有率'].fillna(0)
                final_display_df['占有率'] = final_display_df['占有率'].apply(lambda x: f"{np.floor(x * 10) / 10:.1f}%")

            # --- 累計実績カードの表示 ---
            col1, col2, col3, col4 = st.columns(4)

            current_sales_amount = float(final_display_df['売上金額'].sum()) if '売上金額' in final_display_df.columns else 0.0
            current_sales_quantity = float(final_display_df['売上数量'].sum()) if '売上数量' in final_display_df.columns else 0.0
            current_id_count = float(final_display_df['ID数'].sum()) if 'ID数' in final_display_df.columns else 0.0
            current_receipt_count = float(final_display_df['レシート枚数'].sum()) if 'レシート枚数' in final_display_df.columns else 0.0
            
            selected_store_cd_for_comparison = df_planogram[df_planogram['店舗名'] == selected_store_name]['店舗CD'].iloc[0]

            unique_start_dates_all = sorted(filtered_by_store_theme_main['展開開始日'].unique().tolist())
            current_date_index_in_all = unique_start_dates_all.index(selected_start_date)

            prev_start_date_dt = None
            prev_end_date_dt = None
            if current_date_index_in_all > 0:
                prev_start_date_dt = unique_start_dates_all[current_date_index_in_all - 1]
                prev_planogram_data_for_end = df_planogram[
                    (df_planogram['店舗名'] == selected_store_name) &
                    (df_planogram['テーマ名'] == selected_theme_name) &
                    (df_planogram['展開開始日'] == prev_start_date_dt)
                ]
                if not prev_planogram_data_for_end.empty and '展開終了日' in prev_planogram_data_for_end.columns:
                    prev_end_date_dt = prev_planogram_data_for_end['展開終了日'].iloc[0]
            
            prev_sales_amount, prev_sales_quantity, prev_id_count, prev_receipt_count = \
                get_period_total_metrics(df_idpos, selected_store_cd_for_comparison, prev_start_date_dt, prev_end_date_dt)

            change_sales_amount_str = calculate_daily_change_percentage_str(current_sales_amount, selected_start_date, current_end_date_dt, prev_sales_amount, prev_start_date_dt, prev_end_date_dt)
            change_sales_quantity_str = calculate_daily_change_percentage_str(current_sales_quantity, selected_start_date, current_end_date_dt, prev_sales_quantity, prev_start_date_dt, prev_end_date_dt)
            change_id_count_str = calculate_daily_change_percentage_str(current_id_count, selected_start_date, current_end_date_dt, prev_id_count, prev_start_date_dt, prev_end_date_dt)
            change_receipt_count_str = calculate_daily_change_percentage_str(current_receipt_count, selected_start_date, current_end_date_dt, prev_receipt_count, prev_start_date_dt, prev_end_date_dt)

            with col1:
                st.markdown(f"<div style='text-align: center;'>"
                            f"<div style='font-size: 1.2em; color: gray; margin-bottom: 0.2em; font-weight: bold;'>売上金額</div>"
                            f"<div style='font-size: 1.5em; font-weight: bold; margin-bottom: 0.1em;'>¥{int(current_sales_amount):,}</div>"
                            f"<div style='font-size: 1.1em; margin-top: 0.1em;'>({change_sales_amount_str})</div>"
                            f"</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='text-align: center;'>"
                            f"<div style='font-size: 1.2em; color: gray; margin-bottom: 0.2em; font-weight: bold;'>売上数量</div>"
                            f"<div style='font-size: 1.5em; font-weight: bold; margin-bottom: 0.1em;'>{int(current_sales_quantity):,}個</div>"
                            f"<div style='font-size: 1.1em; margin-top: 0.1em;'>({change_sales_quantity_str})</div>"
                            f"</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div style='text-align: center;'>"
                            f"<div style='font-size: 1.2em; color: gray; margin-bottom: 0.2em; font-weight: bold;'>ID数</div>"
                            f"<div style='font-size: 1.5em; font-weight: bold; margin-bottom: 0.1em;'>{int(current_id_count):,}</div>"
                            f"<div style='font-size: 1.1em; margin-top: 0.1em;'>({change_id_count_str})</div>"
                            f"</div>", unsafe_allow_html=True)
            with col4:
                st.markdown(f"<div style='text-align: center;'>"
                            f"<div style='font-size: 1.2em; color: gray; margin-bottom: 0.2em; font-weight: bold;'>レシート枚数</div>"
                            f"<div style='font-size: 1.5em; font-weight: bold; margin-bottom: 0.1em;'>{int(current_receipt_count):,}</div>"
                            f"<div style='font-size: 1.1em; margin-top: 0.1em;'>({change_receipt_count_str})</div>"
                            f"</div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='margin-top: 0.5em; margin-bottom: 0.5em;'>", unsafe_allow_html=True)


            # 表示するカラムと順序を指定 (棚効率と棚判定を追加)
            display_columns = ['棚番号', 'JAN', '商品名', '陳列数量', '占有率', '売上金額', '売上数量', 'ID数', 'レシート枚数', '棚効率', '棚判定']
            available_columns = [col for col in display_columns if col in final_display_df.columns]

            if available_columns:
                styled_df = final_display_df[available_columns].style.set_properties(
                    **{'text-align': 'center'}, subset=[col for col in available_columns if col != '商品名']
                ).set_properties(
                    **{'text-align': 'left'}, subset=['商品名']
                ).format({
                    '売上金額': '{:,.0f}', '売上数量': '{:,.0f}', 'ID数': '{:,.0f}', 'レシート枚数': '{:,.0f}', '棚効率': '{:,.2f}'
                })

                def highlight_imaima_rows(row):
                    return ['background-color: #ffe6e6'] * len(row) if '棚判定' in row.index and row['棚判定'] == 'いまいち...' else [''] * len(row)
                
                styled_df = styled_df.apply(highlight_imaima_rows, axis=1)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            else:
                st.warning("指定された表示カラムがデータに見つかりませんでした。")
            
            st.markdown("<hr style='margin-top: 0.5em; margin-bottom: 0.5em;'>", unsafe_allow_html=True)

            # --- グラフの表示 ---
            
            chart_metric_options_dict = {
                "売上金額": {"daily_col": "日次売上金額", "cumulative_col": "累計売上金額", "unit": "円", "daily_color": "royalblue", "cumulative_color": "lightcoral"},
                "売上数量": {"daily_col": "日次売上数量", "cumulative_col": "累計売上数量", "unit": "個", "daily_color": "forestgreen", "cumulative_color": "lightseagreen"},
                "ID数": {"daily_col": "日次ID数", "cumulative_col": "累計ID数", "unit": "", "daily_color": "purple", "cumulative_color": "darkorange"},
                "レシート枚数": {"daily_col": "日次レシート枚数", "cumulative_col": "累計レシート枚数", "unit": "", "daily_color": "teal", "cumulative_color": "darkblue"}
            }
            
            metric_options_list = list(chart_metric_options_dict.keys())
            selected_chart_metric_index = metric_options_list.index("売上金額") if "売上金額" in metric_options_list else 0
            
            graph_row1_col1, graph_row1_col2 = st.columns(2)
            graph_row2_col1, graph_row2_col2 = st.columns(2)

            selected_store_cd_for_graph = df_planogram[df_planogram['店舗名'] == selected_store_name]['店舗CD'].iloc[0]

            idpos_for_graphs = df_idpos[
                (df_idpos['店舗CD'] == selected_store_cd_for_graph) &
                (df_idpos['売上日'].dt.date >= selected_start_date.date()) &
                (df_idpos['売上日'].dt.date <= datetime.strptime(end_date_for_display_str, '%Y-%m-%d').date())
            ].copy()

            if 'JAN' in planogram_data_for_display.columns:
                jancodes_in_planogram = planogram_data_for_display['JAN'].unique().tolist()
                idpos_for_graphs_filtered_by_planogram_jan = idpos_for_graphs[idpos_for_graphs['JAN'].isin(jancodes_in_planogram)].copy()
            else:
                idpos_for_graphs_filtered_by_planogram_jan = pd.DataFrame()


            if not idpos_for_graphs_filtered_by_planogram_jan.empty:
                daily_data = idpos_for_graphs_filtered_by_planogram_jan.groupby('売上日').agg(
                    日次売上金額=('売上金額', 'sum'), 日次売上数量=('売上数量', 'sum'),
                    日次ID数=('ID数', 'sum'), 日次レシート枚数=('レシート枚数', 'sum')
                ).reset_index().sort_values('売上日')

                daily_data['累計売上金額'] = daily_data['日次売上金額'].cumsum()
                daily_data['累計売上数量'] = daily_data['日次売上数量'].cumsum()
                daily_data['累計ID数'] = daily_data['日次ID数'].cumsum()
                daily_data['累計レシート枚数'] = daily_data['日次レシート枚数'].cumsum()
                
                with graph_row1_col1: # 左上のグラフ: 日次・累計推移グラフのコンテナ
                    selected_chart_metric = st.selectbox(
                        "表示する指標を選択してください", list(chart_metric_options_dict.keys()), index=0, key="main_chart_metric_select"
                    )
                    chart_info = chart_metric_options_dict.get(selected_chart_metric, {})

                    fig = create_daily_cumulative_graph(
                        daily_data, selected_chart_metric, chart_info["unit"], f'{selected_chart_metric}推移', chart_info["daily_color"], chart_info["cumulative_color"]
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with graph_row1_col2: # 右上のグラフ: 商品別売上推移グラフのコンテナ
                    # JANと商品名を結合した選択肢を作成
                    if 'JAN' in planogram_data_for_display.columns and '商品名' in planogram_data_for_display.columns:
                        planogram_data_for_display['JAN_商品名'] = planogram_data_for_display.apply(
                            lambda row: f"{row['JAN']} ({row['商品名']})" if pd.notna(row['商品名']) else str(row['JAN']), axis=1
                        )
                        product_jan_names_dropdown = ['全て'] + sorted(planogram_data_for_display['JAN_商品名'].unique().tolist())
                    else:
                        product_jan_names_dropdown = ['全て']

                    selected_product_for_product_trend_graph = st.selectbox(
                        "商品名を選択してください", product_jan_names_dropdown, index=0, key="product_trend_select"
                    )
                    
                    data_for_product_trend_graph = pd.DataFrame()
                    title_suffix = ""
                    
                    selected_jan_for_trend = None
                    if selected_product_for_product_trend_graph != '全て':
                        if '(' in selected_product_for_product_trend_graph and ')' in selected_product_for_product_trend_graph:
                            selected_jan_for_trend = selected_product_for_product_trend_graph.split('(')[0].strip()
                        else:
                            selected_jan_for_trend = selected_product_for_product_trend_graph.strip()

                    if selected_product_for_product_trend_graph == '全て':
                        if not daily_data.empty:
                            data_for_product_trend_graph = daily_data[['売上日', '日次売上金額']].copy()
                            title_suffix = " (全商品)"
                    elif selected_jan_for_trend and 'JAN' in idpos_for_graphs_filtered_by_planogram_jan.columns and '売上日' in idpos_for_graphs_filtered_by_planogram_jan.columns and '売上金額' in idpos_for_graphs_filtered_by_planogram_jan.columns:
                        filtered_idpos_by_product = idpos_for_graphs_filtered_by_planogram_jan[idpos_for_graphs_filtered_by_planogram_jan['JAN'] == selected_jan_for_trend].copy()
                        if not filtered_idpos_by_product.empty:
                            data_for_product_trend_graph = filtered_idpos_by_product.groupby('売上日')['売上金額'].sum().reset_index().sort_values('売上日')
                            original_product_name = planogram_data_for_display[planogram_data_for_display['JAN'] == selected_jan_for_trend]['商品名'].iloc[0] if not planogram_data_for_display[planogram_data_for_display['JAN'] == selected_jan_for_trend].empty and '商品名' in planogram_data_for_display.columns else selected_jan_for_trend
                            title_suffix = f" ({original_product_name})"
                        
                    if not data_for_product_trend_graph.empty and '売上金額' in data_for_product_trend_graph.columns:
                        fig_product_sales_trend = go.Figure()
                        fig_product_sales_trend.add_trace(go.Scatter(x=data_for_product_trend_graph['売上日'], y=data_for_product_trend_graph['売上金額'],
                                                                    mode='lines+markers', name='日次売上金額',
                                                                    line=dict(color='orange', width=2), marker=dict(size=4),
                                                                    hovertemplate='売上日: %{x|%Y-%m-%d}<br>売上金額: ¥%{y:,.0f}<extra></extra>'))
                        fig_product_sales_trend.update_layout(
                            title_text=f'商品別売上推移{title_suffix}',
                            xaxis_title='売上日', yaxis_title='売上金額 (円)', hovermode="x unified", height=350,
                            legend=dict(orientation="h", yanchor="top", y=1.1, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig_product_sales_trend, use_container_width=True)
                    else:
                        st.info("商品選択に基づいた売上推移グラフを表示できません。")


                with graph_row2_col1: # 左下: ドーナツグラフ
                    donut_target_column = selected_chart_metric
                    if donut_target_column in idpos_for_graphs_filtered_by_planogram_jan.columns and '商品名' in idpos_for_graphs_filtered_by_planogram_jan.columns:
                        product_breakdown = idpos_for_graphs_filtered_by_planogram_jan.groupby('商品名')[donut_target_column].sum().reset_index()
                        
                        if not product_breakdown.empty:
                            fig_donut = go.Figure(data=[go.Pie(
                                labels=product_breakdown['商品名'], values=product_breakdown[donut_target_column],
                                hole=.3, hoverinfo='label+percent+value',
                                hovertemplate=f'商品名: %{{label}}<br>{selected_chart_metric}: %{{value:,.0f}}{chart_info["unit"]}<br>構成比: %{{percent}}<extra></extra>',
                                textinfo='percent', marker=dict(colors=px.colors.qualitative.Pastel)
                            )])
                            fig_donut.update_layout(
                                title_text=f'商品ごとの{selected_chart_metric}内訳', title_x=0, showlegend=False, height=350,
                            )
                            st.plotly_chart(fig_donut, use_container_width=True)
                        else:
                            st.info(f"商品ごとの{selected_chart_metric}データがありません。")
                    else:
                        st.warning(f"ドーナツグラフの作成に必要な'商品名'または'{selected_chart_metric}'カラムが見つかりません。")

                with graph_row2_col2: # 右下: 散布図
                    temp_df_for_scatter = final_display_df.copy()
                    if '占有率_数値' in temp_df_for_scatter.columns and '売上金額' in temp_df_for_scatter.columns and '商品名' in temp_df_for_scatter.columns:
                        fig_scatter = px.scatter(temp_df_for_scatter, x='占有率_数値', y='売上金額',
                                                 text='商品名', title='占有率 vs 売上金額 (商品別)',
                                                 labels={'占有率_数値': '占有率 (%)', '売上金額': '売上金額 (円)'},
                                                 height=350)
                        
                        fig_scatter.update_traces(textposition='top center')
                        fig_scatter.update_xaxes(tickformat=".1f")
                        fig_scatter.update_yaxes(tickformat=",.0f")
                        fig_scatter.update_layout(hovermode="closest", height=350)
                        st.plotly_chart(fig_scatter, use_container_width=True)
                    else:
                        st.warning("散布図の作成に必要なカラムが見つかりません。")

            else: # ID-POSデータが空の場合
                st.info("選択された店舗と期間に一致するID-POSデータがありませんでした。グラフは表示されません。")
                
        else: # 絞り込まれた棚割データが空の場合
            st.warning("選択された条件に一致する棚割データが見つかりませんでした。")
            st.info("左側のサイドバーで「店舗名」と「テーマ名」、そして「展開開始日」を選択してください。")

# Copyright notice at the very bottom of the sidebar
st.sidebar.markdown("© 2025 Retail Dashboard PoC")

