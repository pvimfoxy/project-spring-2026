"""
dashboard.py
Интерактивный дашборд «Анализ целевой аудитории»
Источники данных: CNews (сегменты) + реестр ЦБ РФ (банки)

Требования:
    pip install dash dash-bootstrap-components plotly pandas

Запуск:
    1) Сначала: python run_parsers.py   (создаёт data/)
    2) Потом:   python dashboard.py
    3) Браузер: http://127.0.0.1:8050
"""

import os
import re
import sys
from collections import Counter
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc



DATA_DIR = "data"


def load_data():
    """Загружает CSV, созданные парсерами. Если файл отсутствует — возвращает пустой DataFrame."""

    news_path  = os.path.join(DATA_DIR, "cnews_segments.csv")
    banks_path = os.path.join(DATA_DIR, "banks_cbr.csv")

    if os.path.exists(news_path):
        df_news = pd.read_csv(news_path, encoding="utf-8-sig")
        print(f"✓ Новости загружены: {len(df_news)} строк")
    else:
        print(f"⚠  {news_path} не найден — запустите run_parsers.py")
        df_news = pd.DataFrame(
            columns=["title", "url", "date", "snippet", "segment", "source"]
        )

    if os.path.exists(banks_path):
        df_banks = pd.read_csv(banks_path, encoding="utf-8-sig")
        print(f"✓ Банки загружены: {len(df_banks)} строк")
    else:
        print(f"⚠  {banks_path} не найден — запустите run_parsers.py")
        df_banks = pd.DataFrame(
            columns=["reg_number", "name", "city", "reg_date", "license_type", "card_url", "source"]
        )

    return df_news, df_banks


RU_STOP = {
    "в", "и", "на", "с", "по", "для", "из", "от", "к", "до", "за", "не",
    "что", "как", "это", "то", "а", "но", "или", "же", "при", "об", "о",
    "со", "во", "все", "они", "он", "их", "его", "её", "мы", "вы", "был",
    "была", "были", "будет", "также", "еще", "уже", "более", "очень",
    "года", "году", "год", "млн", "млрд", "тыс", "руб", "рф", "www",
    "the", "of", "and", "to", "https", "com", "ru",
}


def extract_keywords(titles: pd.Series, top_n: int = 15) -> pd.DataFrame:
    """Считает частоту слов в заголовках новостей."""
    words = []
    for title in titles.dropna():
        tokens = re.findall(r"[а-яёА-ЯЁa-zA-Z]{4,}", title.lower())
        words.extend(t for t in tokens if t not in RU_STOP)
    freq = Counter(words).most_common(top_n)
    return pd.DataFrame(freq, columns=["word", "count"])


def parse_year(series: pd.Series) -> pd.Series:
    """Извлекает год из строк вида 'ДД.ММ.ГГГГ' или 'ГГГГ-ММ-ДД'."""
    def _year(val):
        if pd.isna(val):
            return None
        m = re.search(r"\b(19|20)\d{2}\b", str(val))
        return int(m.group()) if m else None
    return series.map(_year)



df_news, df_banks = load_data()

# — Новости —
seg_counts = (
    df_news["segment"].value_counts()
    .reset_index()
    .rename(columns={"index": "segment", "segment": "count"})
)
seg_counts.columns = ["segment", "count"]

SEGMENTS = sorted(df_news["segment"].dropna().unique().tolist())

SEG_COLORS = {
    "банки":        "#2563eb",
    "ритейлеры":    "#16a34a",
    "госструктуры": "#dc2626",
}

# — Банки —
df_banks["city_clean"] = df_banks["city"].astype(str).str.strip().str.title()
df_banks["year"]       = parse_year(df_banks["reg_date"])

city_top = (
    df_banks["city_clean"].value_counts()
    .reset_index()
    .rename(columns={"city_clean": "city", "count": "count"})
    .head(15)
)
city_top.columns = ["city", "count"]

lic_counts = (
    df_banks["license_type"].value_counts()
    .reset_index()
    .head(8)
)
lic_counts.columns = ["license_type", "count"]
# Обрезаем длинные метки
lic_counts["license_type"] = lic_counts["license_type"].str[:40]

year_counts = (
    df_banks["year"].dropna().astype(int)
    .value_counts().sort_index()
    .reset_index()
)
year_counts.columns = ["year", "count"]
year_counts = year_counts[year_counts["year"] >= 1990]



CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "borderRadius": "12px",
    "padding": "20px 24px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
    "marginBottom": "16px",
    "border": "none",
}

GRAPH_LAYOUT = dict(
    plot_bgcolor="#f8fafc",
    paper_bgcolor="white",
    font=dict(family="Inter, sans-serif", size=12),
    margin=dict(t=44, b=16, l=16, r=16),
)


def kpi_card(icon: str, label: str, value, color: str = "#2563eb"):
    return html.Div(
        [
            html.Div(icon, style={"fontSize": "28px", "marginBottom": "6px"}),
            html.Div(str(value),
                     style={"fontSize": "32px", "fontWeight": "800", "color": color, "lineHeight": "1"}),
            html.Div(label,
                     style={"fontSize": "13px", "color": "#64748b", "marginTop": "4px"}),
        ],
        style=CARD_STYLE | {"textAlign": "center"},
    )



app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap",
    ],
    title="Анализ ЦА | ЦОД",
)

app.layout = dbc.Container(
    fluid=True,
    style={"backgroundColor": "#f0f4f8", "minHeight": "100vh", "fontFamily": "Inter, sans-serif"},
    children=[

        #  Шапка 
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.H2("Анализ целевой аудитории",
                                style={"fontWeight": "800", "marginBottom": "4px"}),
                        html.P(
                            "Источники: CNews (новости по сегментам ЦА) · Реестр ЦБ РФ (банковский сектор)",
                            style={"color": "#64748b", "marginBottom": "0"},
                        ),
                        html.Small(
                            f"Данные на: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                            style={"color": "#94a3b8"},
                        ),
                    ],
                    style={"padding": "28px 0 16px"},
                )
            )
        ),

        # KPI-карточки 
        dbc.Row(
            [
                dbc.Col(kpi_card("🎯", "Сегментов ЦА",       len(SEGMENTS),                           "#2563eb"), md=3),
                dbc.Col(kpi_card("📰", "Новостей собрано",    len(df_news),                            "#16a34a"), md=3),
                dbc.Col(kpi_card("🏦", "Банков в реестре ЦБ", len(df_banks),                           "#dc2626"), md=3),
                dbc.Col(kpi_card("🌆", "Городов охвачено",    df_banks["city_clean"].nunique(),         "#9333ea"), md=3),
            ],
            className="mb-2",
        ),

        # 1: новостная активность 
        html.Div(
            html.H5("Новостная активность по сегментам ЦА",
                    style={"fontWeight": "700", "margin": "8px 0 12px"}),
        ),

        dbc.Row(
            [
                # Bar — кол-во новостей
                dbc.Col(
                    html.Div(
                        dcc.Graph(
                            id="news-bar",
                            figure=(
                                px.bar(
                                    seg_counts,
                                    x="segment", y="count",
                                    color="segment",
                                    color_discrete_map=SEG_COLORS,
                                    text="count",
                                    labels={"segment": "Сегмент", "count": "Кол-во новостей"},
                                    title="Количество новостей по сегменту",
                                )
                                .update_traces(textposition="outside")
                                .update_layout(**GRAPH_LAYOUT, showlegend=False)
                            ),
                            config={"displayModeBar": False},
                        ),
                        style=CARD_STYLE,
                    ),
                    md=6,
                ),

                # Donut — доля сегментов
                dbc.Col(
                    html.Div(
                        dcc.Graph(
                            id="news-pie",
                            figure=(
                                px.pie(
                                    seg_counts,
                                    names="segment", values="count",
                                    color="segment",
                                    color_discrete_map=SEG_COLORS,
                                    hole=0.45,
                                    title="Доля сегментов в новостном потоке",
                                )
                                .update_layout(**GRAPH_LAYOUT)
                            ),
                            config={"displayModeBar": False},
                        ),
                        style=CARD_STYLE,
                    ),
                    md=6,
                ),
            ],
            className="mb-2",
        ),

        # ── Раздел 2: анализ сегмента (dropdown) ───────────────────────────
        html.Div(
            html.H5("Ключевые темы и последние публикации по сегменту",
                    style={"fontWeight": "700", "margin": "8px 0 12px"}),
        ),

        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.Label("Выберите сегмент ЦА:",
                                   style={"fontWeight": "600", "fontSize": "13px", "marginBottom": "8px"}),
                        dcc.Dropdown(
                            id="seg-dropdown",
                            options=[{"label": s.capitalize(), "value": s} for s in SEGMENTS],
                            value=SEGMENTS[0] if SEGMENTS else None,
                            clearable=False,
                            style={"maxWidth": "320px"},
                        ),
                    ],
                    style=CARD_STYLE | {"paddingBottom": "12px"},
                ),
                md=12,
            ),
            className="mb-2",
        ),

        dbc.Row(
            [
                # Ключевые слова
                dbc.Col(
                    html.Div(
                        dcc.Graph(id="keywords-bar", config={"displayModeBar": False}),
                        style=CARD_STYLE,
                    ),
                    md=5,
                ),

                # Таблица новостей
                dbc.Col(
                    html.Div(
                        [
                            html.H6("Последние публикации",
                                    style={"fontWeight": "700", "marginBottom": "10px"}),
                            html.Div(id="news-table-div"),
                        ],
                        style=CARD_STYLE,
                    ),
                    md=7,
                ),
            ],
            className="mb-2",
        ),

        # ── Раздел 3: банковский сегмент ────────────────────────────────────
        html.Div(
            html.H5("Банковский сегмент ЦА — реестр ЦБ РФ",
                    style={"fontWeight": "700", "margin": "8px 0 12px"}),
        ),

        dbc.Row(
            [
                # Топ городов
                dbc.Col(
                    html.Div(
                        dcc.Graph(
                            id="city-bar",
                            figure=(
                                px.bar(
                                    city_top,
                                    x="count", y="city",
                                    orientation="h",
                                    color="count",
                                    color_continuous_scale="Blues",
                                    text="count",
                                    labels={"city": "Город", "count": "Банков"},
                                    title="Топ-15 городов по количеству банков",
                                )
                                .update_traces(textposition="outside")
                                .update_layout(
                                    **GRAPH_LAYOUT,
                                    yaxis=dict(autorange="reversed"),
                                    coloraxis_showscale=False,
                                    margin=dict(t=44, b=16, l=130, r=30),
                                )
                            ),
                            config={"displayModeBar": False},
                        ),
                        style=CARD_STYLE,
                    ),
                    md=6,
                ),

                # Типы лицензий
                dbc.Col(
                    html.Div(
                        dcc.Graph(
                            id="license-pie",
                            figure=(
                                px.pie(
                                    lic_counts,
                                    names="license_type", values="count",
                                    hole=0.4,
                                    title="Типы банковских лицензий",
                                    color_discrete_sequence=px.colors.qualitative.Set2,
                                )
                                .update_layout(**GRAPH_LAYOUT)
                            ),
                            config={"displayModeBar": False},
                        ),
                        style=CARD_STYLE,
                    ),
                    md=6,
                ),
            ],
            className="mb-2",
        ),

        # Динамика регистрации
        dbc.Row(
            dbc.Col(
                html.Div(
                    dcc.Graph(
                        id="year-area",
                        figure=(
                            px.area(
                                year_counts,
                                x="year", y="count",
                                labels={"year": "Год", "count": "Банков зарегистрировано"},
                                title="Динамика регистрации банков (с 1990 г.)",
                                color_discrete_sequence=["#2563eb"],
                            )
                            .update_layout(**GRAPH_LAYOUT)
                        ),
                        config={"displayModeBar": False},
                    ),
                    style=CARD_STYLE,
                ),
                md=12,
            ),
            className="mb-4",
        ),

        # Футер
        html.Div(
            "Данные: CNews.ru · Банк России (cbr.ru)  |  Только для внутреннего использования",
            style={"textAlign": "center", "color": "#94a3b8", "fontSize": "12px", "paddingBottom": "24px"},
        ),
    ],
)


@app.callback(
    Output("keywords-bar",   "figure"),
    Output("news-table-div", "children"),
    Input("seg-dropdown",    "value"),
)
def update_segment_view(segment: str):
    """Обновляет график ключевых слов и таблицу новостей при смене сегмента."""

    if not segment or df_news.empty:
        fig = go.Figure().update_layout(**GRAPH_LAYOUT)
        return fig, html.P("Нет данных. Запустите run_parsers.py",
                           style={"color": "#94a3b8", "textAlign": "center"})

    seg_df = df_news[df_news["segment"] == segment].copy()

    # График ключевых слов 
    kw_df = extract_keywords(seg_df["title"], top_n=15)

    if kw_df.empty:
        kw_fig = go.Figure().update_layout(**GRAPH_LAYOUT,
                                           title=f"Нет данных — {segment.capitalize()}")
    else:
        kw_fig = (
            px.bar(
                kw_df,
                x="count", y="word",
                orientation="h",
                color="count",
                color_continuous_scale="Greens",
                text="count",
                labels={"word": "Слово", "count": "Частота"},
                title=f"Топ слов в заголовках — {segment.capitalize()}",
            )
            .update_traces(textposition="outside")
            .update_layout(
                **GRAPH_LAYOUT,
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False,
                margin=dict(t=44, b=16, l=110, r=30),
            )
        )

    # Таблица последних новостей 
    display_df = seg_df[["title", "date", "url"]].head(12).copy()
    display_df["title"] = display_df["title"].str[:90].fillna("—")
    display_df["date"]  = display_df["date"].fillna("—")

    table = dash_table.DataTable(
        data=display_df.to_dict("records"),
        columns=[
            {"name": "Заголовок", "id": "title", "presentation": "markdown"},
            {"name": "Дата",      "id": "date"},
        ],
        style_cell={
            "textAlign":    "left",
            "padding":      "8px 10px",
            "fontSize":     "12px",
            "whiteSpace":   "normal",
            "height":       "auto",
            "border":       "none",
            "fontFamily":   "Inter, sans-serif",
        },
        style_header={
            "backgroundColor": SEG_COLORS.get(segment, "#2563eb"),
            "color":           "white",
            "fontWeight":      "700",
            "fontSize":        "12px",
            "border":          "none",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8fafc"},
        ],
        style_table={"overflowX": "auto"},
        page_size=10,
    )

    return kw_fig, table


#  запуск
if __name__ == "__main__":
    # Если данных нет — запускаем парсеры автоматически
    news_missing  = not os.path.exists(os.path.join(DATA_DIR, "cnews_segments.csv"))
    banks_missing = not os.path.exists(os.path.join(DATA_DIR, "banks_cbr.csv"))

    if news_missing or banks_missing:
        print("⚠  Файлы данных не найдены — запускаю парсеры...")
        try:
            import run_parsers
            run_parsers.run()
            # Перезагружаем данные
            df_news, df_banks = load_data()
        except Exception as e:
            print(f"✗ Не удалось запустить парсеры: {e}")
            print("  Запустите вручную: python run_parsers.py")

    print("\n Дашборд запущен → http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)
