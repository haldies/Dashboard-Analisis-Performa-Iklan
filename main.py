"""
Dashboard Analisis Performa Iklan — Google, Meta, TikTok Ads
============================================================
Proyek portofolio: analisis performa kampanye iklan digital multi-platform
dari dataset Kaggle "Global Ads Performance". Semua metrik dihitung langsung
dari data (tidak ada angka karangan).

Jalankan:  streamlit run main.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ----------------------------------------------------------------------------
# Konfigurasi halaman
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Analisis Performa Iklan",
    layout="wide",
)

st.title("Dashboard Analisis Performa Iklan")
st.caption("Google Ads · Meta Ads · TikTok Ads — data kampanye harian tahun 2025")

st.markdown(
    """
    <style>
    /* Rapatkan margin atas konten */
    .block-container { padding-top: 1rem !important; }
    /* Filter jadi navbar: selalu nempel di atas saat scroll */
    div[data-testid="stExpander"] {
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: var(--secondary-background-color, #f0f2f6);
        border-bottom: 1px solid rgba(0, 0, 0, 0.08);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_PATH = "data/global_ads_performance_dataset.csv"
# Fallback: dukung juga file di root proyek (tanpa folder data/)
if not Path(DATA_PATH).exists() and Path("global_ads_performance_dataset.csv").exists():
    DATA_PATH = "global_ads_performance_dataset.csv"


# ----------------------------------------------------------------------------
# Utilitas format angka (nilai sudah dalam Rupiah)
# ----------------------------------------------------------------------------
def fmt_idr(x: float) -> str:
    return "Rp" + f"{x:,.0f}".replace(",", ".")


def fmt_pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def fmt_num(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


# ----------------------------------------------------------------------------
# Load data (di-cache agar tidak dibaca ulang setiap interaksi)
# ----------------------------------------------------------------------------
@st.cache_data
def load_data(file_mtime: float) -> pd.DataFrame:
    # file_mtime menjadi bagian cache-key: cache otomatis basi
    # setiap file CSV berubah, dashboard selalu baca data terbaru.
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    return df


df_all = load_data(Path(DATA_PATH).stat().st_mtime)

# ----------------------------------------------------------------------------
# Filter (di dashboard)
# ----------------------------------------------------------------------------
with st.expander("Filter Data", expanded=True):
    dmin, dmax = df_all["date"].min().date(), df_all["date"].max().date()
    date_range = st.date_input(
        "Rentang tanggal", value=(dmin, dmax), min_value=dmin, max_value=dmax
    )
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        sel_platform = st.multiselect(
            "Platform", sorted(df_all["platform"].unique()),
            default=sorted(df_all["platform"].unique()),
        )
    with f2:
        sel_type = st.multiselect(
            "Tipe campaign", sorted(df_all["campaign_type"].unique()),
            default=sorted(df_all["campaign_type"].unique()),
        )
    with f3:
        sel_industry = st.multiselect(
            "Kategori", sorted(df_all["industry"].unique()),
            default=sorted(df_all["industry"].unique()),
        )
    with f4:
        sel_country = st.multiselect(
            "Kota", sorted(df_all["country"].unique()),
            default=sorted(df_all["country"].unique()),
        )
start_date, end_date = date_range[0], date_range[1]

# Terapkan filter
df = df_all[
    (df_all["date"].dt.date >= start_date)
    & (df_all["date"].dt.date <= end_date)
    & (df_all["platform"].isin(sel_platform))
    & (df_all["campaign_type"].isin(sel_type))
    & (df_all["industry"].isin(sel_industry))
    & (df_all["country"].isin(sel_country))
].copy()

if df.empty:
    st.warning("Tidak ada data untuk kombinasi filter tersebut. Ubah filter di atas.")
    st.stop()

# ----------------------------------------------------------------------------
# Metrik agregat (dihitung dari data, bukan rata-rata kolom)
# ----------------------------------------------------------------------------
def aggregate(d: pd.DataFrame) -> dict:
    spend = d["ad_spend"].sum()
    rev = d["revenue"].sum()
    imp = d["impressions"].sum()
    clk = d["clicks"].sum()
    conv = d["conversions"].sum()
    return {
        "spend": spend,
        "revenue": rev,
        "roas": rev / spend if spend else 0,
        "conversions": conv,
        "ctr": clk / imp if imp else 0,
        "cpc": spend / clk if clk else 0,
        "cpa": spend / conv if conv else 0,
    }


m = aggregate(df)

# ----------------------------------------------------------------------------
# 1. KPI cards
# ----------------------------------------------------------------------------
st.subheader("Ringkasan KPI")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Ad Spend", fmt_idr(m["spend"]))
k2.metric("Total Revenue", fmt_idr(m["revenue"]))
k3.metric("Blended ROAS", f"{m['roas']:.2f}x")
k4.metric("Total Konversi", fmt_num(m["conversions"]))
k5, k6, k7 = st.columns(3)
k5.metric("Rata-rata CTR", fmt_pct(m["ctr"]))
k6.metric("Rata-rata CPC", fmt_idr(m["cpc"]))
k7.metric("Rata-rata CPA", fmt_idr(m["cpa"]))

# ----------------------------------------------------------------------------
# 2. Perbandingan platform
# ----------------------------------------------------------------------------
st.subheader("Perbandingan Platform")

plat = (
    df.groupby("platform")
    .agg(
        spend=("ad_spend", "sum"),
        revenue=("revenue", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        conversions=("conversions", "sum"),
    )
    .reset_index()
)
plat["ROAS"] = plat["revenue"] / plat["spend"]
plat["CTR"] = plat["clicks"] / plat["impressions"]
plat["CTR_pct"] = plat["CTR"] * 100
plat["CPA"] = plat["spend"] / plat["conversions"]

c1, c2, c3 = st.columns(3)
c1.plotly_chart(
    px.bar(plat, x="platform", y="ROAS", color="platform",
           title="ROAS per Platform", text_auto=".2f"),
    width="stretch",
)
c2.plotly_chart(
    px.bar(plat, x="platform", y="CPA", color="platform",
           title="CPA per Platform (Rp)", text_auto=".2f"),
    width="stretch",
)
fig_ctr = px.bar(plat, x="platform", y="CTR_pct", color="platform",
                 title="CTR per Platform (%)", text_auto=".2f",
                 labels={"CTR_pct": "CTR (%)"})
fig_ctr.update_traces(texttemplate="%{y:.2f}%")
c3.plotly_chart(fig_ctr, width="stretch")

st.dataframe(
    plat[["platform", "spend", "revenue", "ROAS", "CPA", "CTR", "conversions"]]
    .rename(columns={
        "platform": "Platform", "spend": "Ad Spend (Rp)",
        "revenue": "Revenue (Rp)", "conversions": "Konversi",
    })
    .style.format({
        "Ad Spend (Rp)": fmt_idr, "Revenue (Rp)": fmt_idr,
        "ROAS": "{:.2f}x", "CPA": fmt_idr, "CTR": "{:.2%}",
        "Konversi": fmt_num,
    }),
    width="stretch", hide_index=True,
)

# ----------------------------------------------------------------------------
# 3. Analisis tipe campaign
# ----------------------------------------------------------------------------
st.subheader("Analisis Tipe Campaign")

ctype = (
    df.groupby("campaign_type")
    .agg(spend=("ad_spend", "sum"), revenue=("revenue", "sum"),
         conversions=("conversions", "sum"))
    .reset_index()
)
ctype["ROAS"] = ctype["revenue"] / ctype["spend"]

c1, c2 = st.columns(2)
c1.plotly_chart(
    px.bar(ctype, x="campaign_type", y="ROAS", color="campaign_type",
           title="ROAS per Tipe Campaign", text_auto=".2f"),
    width="stretch",
)
c2.plotly_chart(
    px.bar(ctype, x="campaign_type", y="conversions", color="campaign_type",
           title="Total Konversi per Tipe Campaign", text_auto=True),
    width="stretch",
)

# ----------------------------------------------------------------------------
# 4. Analisis industri & negara
# ----------------------------------------------------------------------------
st.subheader("Analisis Kategori & Kota")

ind = df.groupby("industry").agg(spend=("ad_spend", "sum"),
                                 revenue=("revenue", "sum")).reset_index()
ind["ROAS"] = ind["revenue"] / ind["spend"]

ctr_ = df.groupby("country").agg(spend=("ad_spend", "sum"),
                                 revenue=("revenue", "sum")).reset_index()
ctr_["ROAS"] = ctr_["revenue"] / ctr_["spend"]

c1, c2 = st.columns(2)
c1.plotly_chart(
    px.bar(ind.sort_values("ROAS"), x="ROAS", y="industry", orientation="h",
           color="ROAS", title="ROAS per Kategori", text_auto=".2f"),
    width="stretch",
)
c2.plotly_chart(
    px.bar(ctr_.sort_values("ROAS"), x="ROAS", y="country", orientation="h",
           color="ROAS", title="ROAS per Kota", text_auto=".2f"),
    width="stretch",
)

# Heatmap industri x negara
pivot = df.groupby(["industry", "country"]).agg(
    spend=("ad_spend", "sum"), revenue=("revenue", "sum"))
pivot["ROAS"] = pivot["revenue"] / pivot["spend"]
heat = pivot["ROAS"].unstack("country")
st.plotly_chart(
    px.imshow(heat, text_auto=".2f", aspect="auto",
              color_continuous_scale="YlGn",
              title="Heatmap ROAS: Kategori × Kota"),
    width="stretch",
)

# ----------------------------------------------------------------------------
# 5. Tren waktu (deteksi ad fatigue)
# ----------------------------------------------------------------------------
st.subheader("Tren Waktu & Deteksi Ad Fatigue")

monthly = (
    df.set_index("date")
    .resample("ME")
    .agg(spend=("ad_spend", "sum"), revenue=("revenue", "sum"),
         impressions=("impressions", "sum"), clicks=("clicks", "sum"))
    .reset_index()
)
monthly["ROAS"] = monthly["revenue"] / monthly["spend"]
monthly["CTR"] = monthly["clicks"] / monthly["impressions"]
monthly["bulan"] = monthly["date"].dt.strftime("%Y-%m")

fig = go.Figure()
fig.add_trace(go.Scatter(x=monthly["bulan"], y=monthly["spend"],
                         name="Ad Spend (Rp)", mode="lines+markers"))
fig.add_trace(go.Scatter(x=monthly["bulan"], y=monthly["revenue"],
                         name="Revenue (Rp)", mode="lines+markers"))
fig.update_layout(title="Ad Spend vs Revenue per Bulan",
                  xaxis_title="Bulan", yaxis_title="Rp")
st.plotly_chart(fig, width="stretch")

st.plotly_chart(
    px.line(monthly, x="bulan", y=["ROAS", "CTR"], markers=True,
            title="Tren ROAS & CTR per Bulan (CTR turun terus = indikasi ad fatigue)"),
    width="stretch",
)

# Cek sederhana tren CTR: bandingkan rata-rata 3 bulan pertama vs 3 bulan terakhir
if len(monthly) >= 6:
    ctr_awal = monthly["CTR"].iloc[:3].mean()
    ctr_akhir = monthly["CTR"].iloc[-3:].mean()
    delta = (ctr_akhir - ctr_awal) / ctr_awal * 100 if ctr_awal else 0
    if delta < -10:
        st.warning(
            f"CTR turun **{abs(delta):.1f}%** dari 3 bulan pertama ke 3 bulan "
            f"terakhir — indikasi ad fatigue. Pertimbangkan refresh materi iklan."
        )
    else:
        st.success(
            f"CTR relatif stabil (perubahan {delta:+.1f}% antara 3 bulan "
            f"pertama vs 3 bulan terakhir)."
        )

# ----------------------------------------------------------------------------
# 6. Funnel konversi
# ----------------------------------------------------------------------------
st.subheader("Funnel Konversi")

imp, clk, conv = df["impressions"].sum(), df["clicks"].sum(), df["conversions"].sum()
click_rate = clk / imp if imp else 0
conv_rate_click = conv / clk if clk else 0
conv_rate_imp = conv / imp if imp else 0

fig_funnel = go.Figure(go.Funnel(
    y=["Impressions", "Clicks", "Conversions"],
    x=[imp, clk, conv],
    textinfo="value+percent initial",
))
fig_funnel.update_layout(title="Funnel: Impressions → Clicks → Conversions")
st.plotly_chart(fig_funnel, width="stretch")

f1, f2, f3 = st.columns(3)
f1.metric("Impressions → Clicks", fmt_pct(click_rate),
          f"drop-off {fmt_pct(1 - click_rate)}")
f2.metric("Clicks → Conversions", fmt_pct(conv_rate_click),
          f"drop-off {fmt_pct(1 - conv_rate_click)}")
f3.metric("Impressions → Conversions", fmt_pct(conv_rate_imp))

# ----------------------------------------------------------------------------
# 7. Matriks Pause / Scale
# ----------------------------------------------------------------------------
st.subheader("Matriks Keputusan: Pause / Scale")

seg = (
    df.groupby(["platform", "campaign_type"])
    .agg(spend=("ad_spend", "sum"), revenue=("revenue", "sum"),
         conversions=("conversions", "sum"))
    .reset_index()
)
seg["ROAS"] = seg["revenue"] / seg["spend"]
seg["segmen"] = seg["platform"] + " · " + seg["campaign_type"]

med_roas = seg["ROAS"].median()
med_spend = seg["spend"].median()


def label_segmen(row):
    if row["ROAS"] >= med_roas and row["spend"] <= med_spend:
        return "SCALE"
    if row["ROAS"] < med_roas and row["spend"] > med_spend:
        return "PAUSE / EVALUASI"
    return "PERTAHANKAN"


seg["keputusan"] = seg.apply(label_segmen, axis=1)

fig_m = px.scatter(
    seg, x="spend", y="ROAS", color="keputusan", size="conversions",
    hover_data=["segmen", "spend", "revenue"],
    title="Segmen Platform × Tipe Campaign (garis = median)",
    labels={"spend": "Ad Spend (Rp)", "ROAS": "ROAS",
            "keputusan": "Keputusan", "conversions": "Konversi"},
    color_discrete_map={"SCALE": "green", "PAUSE / EVALUASI": "red",
                        "PERTAHANKAN": "gold"},
)
fig_m.add_vline(x=med_spend, line_dash="dash", line_color="gray")
fig_m.add_hline(y=med_roas, line_dash="dash", line_color="gray")
st.plotly_chart(fig_m, width="stretch")

st.dataframe(
    seg[["segmen", "spend", "revenue", "ROAS", "conversions", "keputusan"]]
    .sort_values("ROAS", ascending=False)
    .rename(columns={"segmen": "Segmen", "spend": "Ad Spend (Rp)",
                      "revenue": "Revenue (Rp)", "conversions": "Konversi",
                      "keputusan": "Keputusan"})
    .style.format({"Ad Spend (Rp)": fmt_idr, "Revenue (Rp)": fmt_idr,
                   "ROAS": "{:.2f}x", "Konversi": fmt_num}),
    width="stretch", hide_index=True,
)

# ----------------------------------------------------------------------------
# 8. Budget optimizer
# ----------------------------------------------------------------------------
st.subheader("Simulator Alokasi Budget")

budget = st.slider("Total budget (Rp)", min_value=1_000_000,
                   max_value=1_000_000_000, value=100_000_000,
                   step=5_000_000)

roas_p = plat.set_index("platform")["ROAS"]
platforms = list(roas_p.index)

# Alokasi proporsional ROAS
alloc_prop = {p: budget * roas_p[p] / roas_p.sum() for p in platforms}
rev_prop = {p: alloc_prop[p] * roas_p[p] for p in platforms}

# Alokasi merata (pembanding)
alloc_eq = {p: budget / len(platforms) for p in platforms}
rev_eq = {p: alloc_eq[p] * roas_p[p] for p in platforms}

opt_df = pd.DataFrame({
    "Platform": platforms,
    "ROAS": [roas_p[p] for p in platforms],
    "Alokasi Proporsional (Rp)": [alloc_prop[p] for p in platforms],
    "Est. Revenue Proporsional (Rp)": [rev_prop[p] for p in platforms],
    "Alokasi Merata (Rp)": [alloc_eq[p] for p in platforms],
    "Est. Revenue Merata (Rp)": [rev_eq[p] for p in platforms],
})

tot_rev_prop = sum(rev_prop.values())
tot_rev_eq = sum(rev_eq.values())

o1, o2, o3 = st.columns(3)
o1.metric("Est. Revenue (Proporsional)", fmt_idr(tot_rev_prop),
          f"{fmt_idr(tot_rev_prop - tot_rev_eq)} vs merata")
o2.metric("Est. ROAS (Proporsional)", f"{tot_rev_prop / budget:.2f}x")
o3.metric("Est. ROAS (Merata)", f"{tot_rev_eq / budget:.2f}x")

st.dataframe(
    opt_df.style.format({
        "ROAS": "{:.2f}x",
        "Alokasi Proporsional (Rp)": fmt_idr,
        "Est. Revenue Proporsional (Rp)": fmt_idr,
        "Alokasi Merata (Rp)": fmt_idr,
        "Est. Revenue Merata (Rp)": fmt_idr,
    }),
    width="stretch", hide_index=True,
)

st.plotly_chart(
    px.bar(opt_df, x="Platform",
           y=["Alokasi Proporsional (Rp)", "Alokasi Merata (Rp)"],
           barmode="group", title="Perbandingan Alokasi Budget per Platform"),
    width="stretch",
)


