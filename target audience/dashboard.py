"""
dashboard.py — интерактивный дашборд «Анализ ЦА для ЦОД Tier 4».
pip install dash dash-bootstrap-components plotly pandas
"""
import os, re
from collections import Counter
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

DATA_DIR = "data"

def load_data():
    np_, bp_ = os.path.join(DATA_DIR,"cnews_segments.csv"), os.path.join(DATA_DIR,"banks_cbr.csv")
    df_news  = pd.read_csv(np_, encoding="utf-8-sig") if os.path.exists(np_)  else pd.DataFrame(columns=["title","url","date","snippet","segment","source"])
    df_banks = pd.read_csv(bp_, encoding="utf-8-sig") if os.path.exists(bp_) else pd.DataFrame(columns=["reg_number","name","city","reg_date","license_type","card_url","source"])
    print(f"✓ Новости: {len(df_news)} | Банки: {len(df_banks)}")
    return df_news, df_banks

RU_STOP = {"в","и","на","с","по","для","из","от","к","до","за","не","что","как","это","то","а","но","или",
           "же","при","об","о","со","во","все","они","он","их","его","её","мы","вы","был","была","были",
           "будет","также","еще","уже","более","очень","года","году","год","млн","млрд","тыс","руб","рф",
           "www","the","of","and","to","https","com","ru","быть","есть","свой","свою","после","перед",
           "между","через","чтобы","который","которая","которое"}

def extract_keywords(titles, top_n=15):
    words = []
    for t in titles.dropna():
        words.extend(w for w in re.findall(r"[а-яёА-ЯЁa-zA-Z]{4,}", str(t).lower())
                     if w not in RU_STOP)
    return pd.DataFrame(Counter(words).most_common(top_n), columns=["word","count"])

def parse_year(s):
    def _y(v):
        if pd.isna(v): return None
        m = re.search(r"\b(19|20)\d{2}\b", str(v))
        return int(m.group()) if m else None
    return s.map(_y)

def safe_value_counts(series, top=None, col_name="value"):
    if series is None or series.empty: return pd.DataFrame(columns=[col_name,"count"])
    vc = series.dropna().astype(str).str.strip()
    vc = vc[vc!=""].value_counts()
    if top: vc = vc.head(top)
    return vc.rename_axis(col_name).reset_index(name="count")


df_news, df_banks = load_data()

seg_counts = safe_value_counts(df_news["segment"] if "segment" in df_news else pd.Series(dtype=str),
                               col_name="segment")
SEGMENTS = sorted(df_news["segment"].dropna().unique().tolist()) if not df_news.empty else []
SEG_COLORS = {"банки":"#2563eb","ритейлеры":"#16a34a","госструктуры":"#dc2626"}

if not df_banks.empty:
    df_banks["city_clean"] = df_banks["city"].astype(str).str.strip().str.title()
    df_banks["year"]       = parse_year(df_banks["reg_date"])
else:
    df_banks["city_clean"] = pd.Series(dtype=str); df_banks["year"] = pd.Series(dtype="Int64")

city_top   = safe_value_counts(df_banks["city_clean"], top=15, col_name="city")
lic_counts = safe_value_counts(df_banks["license_type"], top=8, col_name="license_type")
if not lic_counts.empty:
    lic_counts["license_type"] = lic_counts["license_type"].str[:40]

year_counts = safe_value_counts(df_banks["year"].dropna().astype("Int64").astype(str)
                                if not df_banks.empty else pd.Series(dtype=str),
                                col_name="year")
if not year_counts.empty:
    year_counts["year"] = year_counts["year"].astype(int)
    year_counts = year_counts[year_counts["year"] >= 1990].sort_values("year")

PERSONAS = [
    {"icon":"🏦","color":"#2563eb","title":"Банк (Tier-1 / Tier-2)",
     "company":"Топ-50 банков из реестра ЦБ РФ (универсальная лицензия)",
     "decision_maker":"CIO / CTO / Директор по IT-инфраструктуре",
     "goals":["обеспечить SLA 99,995% по критичным системам (АБС, процессинг)",
              "выполнить требования ЦБ и ФСТЭК по защите данных",
              "снизить CAPEX на собственный ЦОД, перейти на OPEX"],
     "problems":["простой АБС = прямой финансовый ущерб (млн руб./час)",
                 "штрафы ЦБ за инциденты и недоступность",
                 "регуляторные требования к геораспределённому DR"],
     "budget":"от 8 до 25 млн руб./год за стойку 10–20 кВт с резервированием"},
    {"icon":"🛒","color":"#16a34a","title":"Крупный ритейлер / e-commerce",
     "company":"X5, Магнит, Wildberries, Ozon, Lenta",
     "decision_maker":"CIO / Head of E-commerce / Директор по логистике",
     "goals":["выдержать пики нагрузки (Black Friday, новогодние распродажи)",
              "обеспечить непрерывность онлайн-заказов и омниканальности",
              "сократить время отклика касс, ERP и WMS"],
     "problems":["1 час простоя интернет-магазина = десятки млн руб. потерь",
                 "ограниченная команда DevOps для эксплуатации своего ЦОД",
                 "необходимость географического резервирования к складам"],
     "budget":"от 5 до 18 млн руб./год за стойку, плюс трафик"},
    {"icon":"🏛️","color":"#dc2626","title":"Госструктура / Госкорпорация",
     "company":"ФНС, Госуслуги, региональные МФЦ, ГК уровня Ростех",
     "decision_maker":"Замдиректора по цифровизации / руководитель ИТ-департамента",
     "goals":["соответствовать 152-ФЗ, 187-ФЗ (КИИ), требованиям ФСТЭК",
              "разместить ГИС в аттестованном ЦОД",
              "обеспечить отказоустойчивость социально значимых сервисов"],
     "problems":["штатный простой Госуслуг или ФНС = политический риск",
                 "длинный цикл закупки → выгоднее аренда по 44/223-ФЗ, чем стройка",
                 "требование локализации данных в РФ"],
     "budget":"от 6 до 20 млн руб./год за стойку (через тендер)"},
]

CARD_STYLE = {"backgroundColor":"#ffffff","borderRadius":"12px","padding":"20px 24px",
              "boxShadow":"0 2px 8px rgba(0,0,0,0.08)","marginBottom":"16px","border":"none"}
GRAPH_LAYOUT = dict(plot_bgcolor="#f8fafc", paper_bgcolor="white",
                    font=dict(family="Inter, sans-serif", size=12),
                    margin=dict(t=44, b=16, l=16, r=16))

def kpi_card(icon, label, value, color="#2563eb"):
    return html.Div([
        html.Div(icon, style={"fontSize":"28px","marginBottom":"6px"}),
        html.Div(str(value), style={"fontSize":"32px","fontWeight":"800","color":color,"lineHeight":"1"}),
        html.Div(label, style={"fontSize":"13px","color":"#64748b","marginTop":"4px"}),
    ], style={**CARD_STYLE,"textAlign":"center"})

def persona_card(p):
    return html.Div([
        html.Div([html.Span(p["icon"], style={"fontSize":"32px","marginRight":"10px"}),
                  html.Span(p["title"], style={"fontSize":"18px","fontWeight":"800","color":p["color"]})],
                 style={"marginBottom":"10px"}),
        html.Div([html.B("Кто: "), p["company"]], style={"fontSize":"13px","marginBottom":"4px"}),
        html.Div([html.B("ЛПР: "), p["decision_maker"]], style={"fontSize":"13px","marginBottom":"8px"}),
        html.Div("Цели:", style={"fontWeight":"700","fontSize":"13px","marginTop":"6px"}),
        html.Ul([html.Li(g) for g in p["goals"]],
                style={"fontSize":"12.5px","margin":"2px 0 8px 18px","color":"#334155"}),
        html.Div("Проблемы и боли:", style={"fontWeight":"700","fontSize":"13px"}),
        html.Ul([html.Li(g) for g in p["problems"]],
                style={"fontSize":"12.5px","margin":"2px 0 8px 18px","color":"#334155"}),
        html.Div([html.B("Готов платить: "),
                  html.Span(p["budget"], style={"color":p["color"],"fontWeight":"700"})],
                 style={"fontSize":"13px","marginTop":"4px","padding":"8px 10px",
                        "backgroundColor":"#f1f5f9","borderRadius":"8px"}),
    ], style={**CARD_STYLE,"borderTop":f"4px solid {p['color']}"})

def fig_segments_bar():
    if seg_counts.empty: return go.Figure().update_layout(**GRAPH_LAYOUT, title="Нет данных")
    return (px.bar(seg_counts, x="segment", y="count", color="segment",
                   color_discrete_map=SEG_COLORS, text="count",
                   labels={"segment":"Сегмент","count":"Кол-во новостей"},
                   title="Количество новостей по сегменту ЦА")
            .update_traces(textposition="outside")
            .update_layout(**GRAPH_LAYOUT, showlegend=False))

def fig_segments_pie():
    if seg_counts.empty: return go.Figure().update_layout(**GRAPH_LAYOUT, title="Нет данных")
    return (px.pie(seg_counts, names="segment", values="count", color="segment",
                   color_discrete_map=SEG_COLORS, hole=0.45,
                   title="Доля сегментов в новостном потоке")
            .update_layout(**GRAPH_LAYOUT))

def fig_city_bar():
    if city_top.empty:
        return go.Figure().update_layout(**GRAPH_LAYOUT, title="Нет данных")

    layout = {
        **GRAPH_LAYOUT,
        "yaxis": dict(autorange="reversed"),
        "coloraxis_showscale": False,
        "margin": dict(t=44, b=16, l=150, r=30),   # перебивает margin из GRAPH_LAYOUT
    }

    return (px.bar(city_top, x="count", y="city", orientation="h",
                   color="count", color_continuous_scale="Blues", text="count",
                   labels={"city": "Город", "count": "Банков"},
                   title="Топ-15 городов по концентрации банков")
            .update_traces(textposition="outside")
            .update_layout(**layout))


def fig_license_pie():
    if lic_counts.empty: return go.Figure().update_layout(**GRAPH_LAYOUT, title="Нет данных")
    return (px.pie(lic_counts, names="license_type", values="count", hole=0.4,
                   title="Типы банковских лицензий",
                   color_discrete_sequence=px.colors.qualitative.Set2)
            .update_layout(**GRAPH_LAYOUT))

def fig_year_area():
    if year_counts.empty: return go.Figure().update_layout(**GRAPH_LAYOUT, title="Нет данных")
    return (px.area(year_counts, x="year", y="count",
                    labels={"year":"Год","count":"Банков зарегистрировано"},
                    title="Динамика регистрации банков (с 1990 г.)",
                    color_discrete_sequence=["#2563eb"])
            .update_layout(**GRAPH_LAYOUT))

def fig_budget_compare():
    data = pd.DataFrame([{"segment":"банки","low":8,"high":25},
                         {"segment":"ритейлеры","low":5,"high":18},
                         {"segment":"госструктуры","low":6,"high":20}])
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Минимум", x=data["segment"], y=data["low"],
                         marker_color="#94a3b8", text=data["low"], textposition="auto"))
    fig.add_trace(go.Bar(name="Максимум", x=data["segment"], y=data["high"]-data["low"],
                         base=data["low"], marker_color=[SEG_COLORS[s] for s in data["segment"]],
                         text=data["high"], textposition="outside"))
    fig.update_layout(**GRAPH_LAYOUT, barmode="stack",
                      title="Платёжеспособность ЦА: бюджет на аренду стойки, млн руб./год",
                      yaxis_title="млн руб./год", showlegend=False)
    return fig


app = Dash(__name__,
           external_stylesheets=[dbc.themes.FLATLY,
               "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap"],
           title="ЦА | ЦОД Tier 4")

app.layout = dbc.Container(fluid=True,
    style={"backgroundColor":"#f0f4f8","minHeight":"100vh",
           "fontFamily":"Inter, sans-serif","padding":"0 24px"},
    children=[
        dbc.Row(dbc.Col(html.Div([
            html.H2("Анализ целевой аудитории · ЦОД Tier 4",
                    style={"fontWeight":"800","marginBottom":"4px"}),
            html.P("B2B / B2G · банки, крупный ритейл, госструктуры. Источники: CNews + реестр ЦБ РФ.",
                   style={"color":"#64748b","marginBottom":"0"}),
            html.Small(f"Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                       style={"color":"#94a3b8"}),
        ], style={"padding":"28px 0 16px"}))),

        dbc.Row([
            dbc.Col(kpi_card("🎯","Сегментов ЦА",   len(SEGMENTS) or 3,"#2563eb"), md=3),
            dbc.Col(kpi_card("📰","Новостей",       len(df_news),     "#16a34a"), md=3),
            dbc.Col(kpi_card("🏦","Банков в реестре",len(df_banks),   "#dc2626"), md=3),
            dbc.Col(kpi_card("🌆","Городов",
                df_banks["city_clean"].nunique() if not df_banks.empty else 0, "#9333ea"), md=3),
        ], className="mb-2"),

        html.H5("Портреты целевой аудитории", style={"fontWeight":"700","margin":"16px 0 12px"}),
        dbc.Row([dbc.Col(persona_card(p), md=4) for p in PERSONAS], className="mb-2"),

        html.H5("Платёжеспособность сегментов", style={"fontWeight":"700","margin":"16px 0 12px"}),
        dbc.Row(dbc.Col(html.Div(dcc.Graph(figure=fig_budget_compare(),
                                           config={"displayModeBar":False}),
                                 style=CARD_STYLE), md=12), className="mb-2"),

        html.H5("Новостная активность по сегментам", style={"fontWeight":"700","margin":"16px 0 12px"}),
        dbc.Row([
            dbc.Col(html.Div(dcc.Graph(figure=fig_segments_bar(), config={"displayModeBar":False}),
                             style=CARD_STYLE), md=6),
            dbc.Col(html.Div(dcc.Graph(figure=fig_segments_pie(), config={"displayModeBar":False}),
                             style=CARD_STYLE), md=6),
        ], className="mb-2"),

        html.H5("Ключевые темы и публикации по сегменту",
                style={"fontWeight":"700","margin":"16px 0 12px"}),
        dbc.Row(dbc.Col(html.Div([
            html.Label("Сегмент ЦА:",
                       style={"fontWeight":"600","fontSize":"13px","marginBottom":"8px"}),
            dcc.Dropdown(id="seg-dropdown",
                options=[{"label":s.capitalize(),"value":s} for s in SEGMENTS],
                value=SEGMENTS[0] if SEGMENTS else None,
                clearable=False, style={"maxWidth":"320px"}),
        ], style={**CARD_STYLE,"paddingBottom":"12px"}), md=12), className="mb-2"),

        dbc.Row([
            dbc.Col(html.Div(dcc.Graph(id="keywords-bar", config={"displayModeBar":False}),
                             style=CARD_STYLE), md=5),
            dbc.Col(html.Div([
                html.H6("Последние публикации", style={"fontWeight":"700","marginBottom":"10px"}),
                html.Div(id="news-table-div"),
            ], style=CARD_STYLE), md=7),
        ], className="mb-2"),

        html.H5("Банковский сегмент — реестр ЦБ РФ", style={"fontWeight":"700","margin":"16px 0 12px"}),
        dbc.Row([
            dbc.Col(html.Div(dcc.Graph(figure=fig_city_bar(), config={"displayModeBar":False}),
                             style=CARD_STYLE), md=6),
            dbc.Col(html.Div(dcc.Graph(figure=fig_license_pie(), config={"displayModeBar":False}),
                             style=CARD_STYLE), md=6),
        ], className="mb-2"),

        dbc.Row(dbc.Col(html.Div(dcc.Graph(figure=fig_year_area(), config={"displayModeBar":False}),
                                 style=CARD_STYLE), md=12), className="mb-4"),

        html.Div("Источники: CNews.ru · cbr.ru | Учебный проект",
                 style={"textAlign":"center","color":"#94a3b8","fontSize":"12px","paddingBottom":"24px"}),
    ])


@app.callback(Output("keywords-bar","figure"),
              Output("news-table-div","children"),
              Input("seg-dropdown","value"))
def update_segment_view(segment):
    if not segment or df_news.empty:
        return (go.Figure().update_layout(**GRAPH_LAYOUT, title="Нет данных"),
                html.P("Нет данных. Запустите run_parsers.py",
                       style={"color":"#94a3b8","textAlign":"center"}))

    seg_df = df_news[df_news["segment"]==segment].copy()
    kw_df  = extract_keywords(seg_df["title"], top_n=15)

    if kw_df.empty:
        kw_fig = go.Figure().update_layout(**GRAPH_LAYOUT,
            title=f"Нет ключевых слов — {segment.capitalize()}")
    else:
        kw_fig = (px.bar(kw_df, x="count", y="word", orientation="h",
                         color="count", color_continuous_scale="Greens", text="count",
                         labels={"word":"Слово","count":"Частота"},
                         title=f"Топ слов в заголовках — {segment.capitalize()}")
                  .update_traces(textposition="outside")
                  .update_layout(**GRAPH_LAYOUT, yaxis=dict(autorange="reversed"),
                                 coloraxis_showscale=False,
                                 margin=dict(t=44,b=16,l=110,r=30)))

    disp = seg_df[["title","date","url"]].head(12).copy()
    disp["title"] = disp["title"].astype(str).str[:90].fillna("—")
    disp["date"]  = disp["date"].fillna("—")
    disp["title"] = disp.apply(
        lambda r: f"[{r['title']}]({r['url']})" if isinstance(r["url"],str) and r["url"] else r["title"],
        axis=1)

    table = dash_table.DataTable(
        data=disp[["title","date"]].to_dict("records"),
        columns=[{"name":"Заголовок","id":"title","presentation":"markdown"},
                 {"name":"Дата","id":"date"}],
        style_cell={"textAlign":"left","padding":"8px 10px","fontSize":"12px",
                    "whiteSpace":"normal","height":"auto","border":"none",
                    "fontFamily":"Inter, sans-serif"},
        style_header={"backgroundColor":SEG_COLORS.get(segment,"#2563eb"),
                      "color":"white","fontWeight":"700","fontSize":"12px","border":"none"},
        style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#f8fafc"}],
        style_table={"overflowX":"auto"}, page_size=10)
    return kw_fig, table


if __name__ == "__main__":
    if (not os.path.exists(os.path.join(DATA_DIR,"cnews_segments.csv"))
            or not os.path.exists(os.path.join(DATA_DIR,"banks_cbr.csv"))):
        print("⚠ Файлы данных не найдены — запускаю парсеры…")
        try:
            from run_parsers import run as run_parsers_fn
            run_parsers_fn()
            df_news, df_banks = load_data()
        except Exception as e:
            print(f"✗ Парсеры не отработали: {e}")
            print("  Запустите вручную: python run_parsers.py")
    print("\n>>> Дашборд: http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)

