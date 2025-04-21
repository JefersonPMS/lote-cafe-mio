from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.backends.backend_pdf
import numpy as np
import io

app = FastAPI()

# Planilhas
SHEET_ID = "1yZWlkb8sKZ5PKQiVk5buOhd2pwPdIW2zLG60Z9h18wQ"
CSV_RADAR = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1027109383"
CSV_FATO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

CATEGORIES = [
    "Fragrance", "Flavor", "Aftertaste", "Acidity", "Body",
    "Uniformity", "Clean Cup", "Sweetness", "Balance", "Overall"
]

def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    radar = pd.read_csv(CSV_RADAR)
    fato = pd.read_csv(CSV_FATO)
    return radar, fato

def prepare_lote(df: pd.DataFrame, lote: str) -> pd.Series | None:
    df_l = df[df["Lote"] == lote]
    if df_l.empty:
        return None
    return df_l[CATEGORIES].mean()

def create_radar(data: pd.Series, lote: str) -> plt.Figure:
    values = data.tolist()
    N = len(values)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(6, 6))
    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), CATEGORIES)
    ax.set_title(f"Radar Sensory – {lote}", y=1.08)
    ax.grid(True)
    return fig

def create_summary_table(df_fato: pd.DataFrame, lote: str) -> plt.Figure:
    lote_info = df_fato[df_fato["lote_prova"] == lote]
    if lote_info.empty:
        raise ValueError("Lote não encontrado na aba fato_tipo_de_cafe.")
    
    fig, ax = plt.subplots(figsize=(8, 1.5))
    ax.axis('off')

    table_data = lote_info.iloc[0].to_frame().T
    ax.table(
        cellText=table_data.values,
        colLabels=table_data.columns,
        loc='center',
        cellLoc='center'
    )

    return fig

@app.get("/radar")
async def radar_pdf(lote: str = Query(..., description="Nome do lote (ex.: 'Lote - 1')")):
    df_radar, df_fato = load_data()
    series = prepare_lote(df_radar, lote)
    if series is None:
        raise HTTPException(status_code=404, detail=f"Lote '{lote}' não encontrado")

    radar_fig = create_radar(series, lote)
    table_fig = create_summary_table(df_fato, lote)

    # PDF
    buf = io.BytesIO()
    with matplotlib.backends.backend_pdf.PdfPages(buf) as pdf:
        pdf.savefig(radar_fig, bbox_inches='tight')
        pdf.savefig(table_fig, bbox_inches='tight')
    plt.close('all')
    buf.seek(0)

    import base64
    encoded_pdf = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "fileName": f"{lote}_radar.pdf",
        "pdf_base64": encoded_pdf,
        "mimetype": "application/pdf"
    }
