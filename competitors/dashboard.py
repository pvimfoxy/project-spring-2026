"""
Дашборд по конкурентам Tier-4 ЦОД.

Запуск:
    streamlit run dashboard.py

Читает data/competitors.csv (его создаёт parser.py).
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).parent / "data" / "competitors.csv"

st.set_page_config(
    page_title="Конкуренты ЦОД Tier-4 — дашборд",
    layout="wide",
)

st.title("🏢 Анализ конкурентов: рынок коммерческих ЦОД РФ")
st.caption(
    "Источник: TAdviser «Дата-центры (рынок России)» / "
    "iKS-Consulting. Файл данных: data/competitors.csv"
)

if not DATA.exists():
    st.error("Сначала запусти parser.py — он создаст data/competitors.csv")
    st.stop()

df = pd.read_csv(DATA)

# ---------- KPI ----------------------------------------------------------- #
c1, c2, c3, c4 = st.columns(4)
c1.metric("Операторов в выборке", len(df))
c2.metric("Совокупно стойко-мест", f"{df['racks'].sum():,}".replace(",", " "))
c3.metric("Лидер по стойкам", df.loc[df["racks"].idxmax(), "operator"])
c4.metric("Доля топ-3, %",
          f"{df.nlargest(3, 'racks')['market_share_pct'].sum():.1f}")

st.divider()

# ---------- Графики ------------------------------------------------------- #
left, right = st.columns(2)

with left:
    st.subheader("Количество стоек у конкурентов")
    fig = px.bar(
        df.sort_values("racks", ascending=True),
        x="racks", y="operator", orientation="h",
        text="racks", color="racks",
        color_continuous_scale="Blues",
    )
    fig.update_layout(yaxis_title="", xaxis_title="Стойко-мест",
                      height=450, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Доли рынка, %")
    fig = px.pie(
        df, values="market_share_pct", names="operator",
        hole=0.45,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Портреты конкурентов ----------------------------------------- #
st.subheader("👤 Портреты ключевых конкурентов")

picked = st.multiselect(
    "Выбери операторов для сравнения",
    options=df["operator"].tolist(),
    default=df.nlargest(3, "racks")["operator"].tolist(),
)

for op in picked:
    row = df[df["operator"] == op].iloc[0]
    with st.container(border=True):
        st.markdown(f"### {row['operator']}")
        a, b, c = st.columns(3)
        a.metric("Стойко-мест", f"{int(row['racks']):,}".replace(",", " "))
        b.metric("Доля рынка", f"{row['market_share_pct']:.1f} %")
        c.metric("Tier", str(row.get("tier", "—")))
        st.markdown(
            f"**Локация:** {row.get('city', '—')}  \n"
            f"**Основан:** {row.get('founded', '—')}  \n"
            f"**Ключевые клиенты:** {row.get('key_clients', '—')}  \n"
            f"**Особенности:** {row.get('notes', '—')}"
        )

st.divider()

# ---------- Сырые данные -------------------------------------------------- #
with st.expander("📄 Сырые данные (CSV)"):
    st.dataframe(df, use_container_width=True)

st.divider()

# Выводы  
st.subheader("Выводы")

st.markdown(
    """
**Чем мы отличаемся от конкурентов**

- Все основные игроки рынка работают в **Tier III** (отказоустойчивость
  ~99,98 %). Tier **IV** даёт **99,995 %** и зарезервированную
  «fault-tolerant»-архитектуру — это не имеет ни один из топ-10
  операторов в открытых данных.
- Топ-3 (Ростелеком-ЦОД, IXcellerate, Selectel) держат ~**56 % рынка**,
  но это «массовый премиум». Сегмент «mission-critical»
  (банки, биржи, госкритинфраструктура) у них размыт.
- Никто из конкурентов не позиционируется **исключительно** на
  непрерывности — это и есть наша ниша.

**Стратегия выхода на рынок**

1. **Нишевое позиционирование:** «единственный коммерческий Tier IV
   в РФ» — короткое УТП для тендеров банков и госструктур.
2. **Якорные клиенты:** 2–3 ЦБ-поднадзорных финансовых организации
   и один крупный ритейлер — для референса.
3. **Гео-фокус:** Москва (ядро спроса банков) + резервная площадка
   за пределами МКАД для DR (требование 716-П).
4. **Цена:** премия +30–50 % к Tier III оправдывается SLA 99,995 %
   и сертификатом Uptime Institute.
5. **Партнёрства:** интеграторы (КРОК, Softline) как канал продаж
   вместо прямой конкуренции с гипермасштабными операторами.

**Стратегия конкуренции**

- **Не воевать ценой** с Ростелеком-ЦОД и Selectel.
- **Воевать SLA и сертификатами** (Uptime Tier IV, ISO 27001,
  PCI DSS, 152-ФЗ УЗ-1).
- **Закрывать комплаенс-боль** банков (требования ЦБ к
  непрерывности) и госов (постановление 1236, реестр отечественного ПО).
    """
)
