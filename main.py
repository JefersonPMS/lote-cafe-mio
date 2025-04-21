import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
import io
import base64
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

# URLs e colunas
SHEET_ID = "1yZWlkb8sKZ5PKQiVk5buOhd2pwPdIW2zLG60Z9h18wQ"
GID_RADAR = "1027109383"
GID_INFO = "1373368181"  # <- supondo que seja outro GID com os dados da tabela
URL_RADAR = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_RADAR}"
URL_INFO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_INFO}"

CATEGORIES = ["Fragrance", "Flavor", "Aftertaste", "Acidity", "Body", "Uniformity", "Clean Cup", "Sweetness", "Balance", "Overall"]
INFO_COLS = ["lote_prova", "data", "fazenda", "talhao", "variedade", "repassada", "tipo_de_cafe", "processo_fermentacao", "peso"]

def load_data():
    radar_df = pd.read_csv(URL_RADAR)
    info_df = pd.read_csv(URL_INFO)
    return radar_df, info_df

def prepare_lote(df, lote):
    df_l = df[df["Lote"] == lote]
    if df_l.empty:
        return None
    return df_l[CATEGORIES].mean()

def get_info_row(info_df, lote):
    return info_df[info_df["lote_prova"] == lote]

def create_pdf_with_table(radar_data, info_row, lote):
    values = radar_data.tolist()
    N = len(values)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig = plt.figure(figsize=(8.5, 11))  # tamanho padrão de uma folha A4
    gs = gridspec.GridSpec(2, 1, height_ratios=[2, 1])

    ax1 = fig.add_subplot(gs[0], polar=True)
    ax1.plot(angles, values, linewidth=2)
    ax1.fill(angles, values, alpha=0.25)
    ax1.set_thetagrids(np.degrees(angles[:-1]), CATEGORIES)
    ax1.set_title(f"Radar Sensory – {lote}", y=1.08)
    ax1.grid(True)

    ax2 = fig.add_subplot(gs[1])
    ax2.axis("off")

    table_data = [INFO_COLS] + info_row[INFO_COLS].values.tolist()
    table = ax2.table(cellText=table_data, colLabels=None, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 2.5)

    return fig

@app.get("/radar")
async def radar_pdf(lote: str = Query(..., description="Nome do lote (ex.: 'Lote - 1')")):
    radar_df, info_df = load_data()

    radar_series = prepare_lote(radar_df, lote)
    if radar_series is None:
        raise HTTPException(status_code=404, detail=f"Lote '{lote}' não encontrado")

    info_row = get_info_row(info_df, lote)
    if info_row.empty:
        raise HTTPException(status_code=404, detail=f"Informações adicionais do lote '{lote}' não encontradas")

    fig = create_pdf_with_table(radar_series, info_row, lote)

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    encoded_pdf = base64.b64encode(buf.getvalue()).decode("utf-8")
    return {
        "fileName": f"{lote}_radar.pdf",
        "pdf_base64": encoded_pdf,
        "mimetype": "application/pdf"
    }
