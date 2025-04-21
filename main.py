from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

app = FastAPI()

# URLs das planilhas
SHEET_ID = "1yZWlkb8sKZ5PKQiVk5buOhd2pwPdIW2zLG60Z9h18wQ"
GID_RADAR = "1027109383"  # aba com as notas sensoriais
GID_TABELA = "0"          # aba fato_tipo_de_cafe
RADAR_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_RADAR}"
TABELA_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_TABELA}"

CATEGORIES = [
    "Fragrance", "Flavor", "Aftertaste", "Acidity", "Body",
    "Uniformity", "Clean Cup", "Sweetness", "Balance", "Overall"
]

def load_data_radar() -> pd.DataFrame:
    return pd.read_csv(RADAR_URL)

def load_data_tabela() -> pd.DataFrame:
    return pd.read_csv(TABELA_URL)

def prepare_lote(df: pd.DataFrame, lote: str) -> pd.Series | None:
    df_l = df[df["Lote"] == lote]
    if df_l.empty:
        return None
    return df_l[CATEGORIES].mean()

def create_combined_figure(radar_data: pd.Series, tabela_info: pd.Series, lote: str) -> plt.Figure:
    fig = plt.figure(figsize=(8.27, 11.69))  # A4 em polegadas
    gs = fig.add_gridspec(2, 1, height_ratios=[2, 1])

    # Radar Plot
    ax_radar = fig.add_subplot(gs[0], polar=True)
    values = radar_data.tolist()
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(CATEGORIES), endpoint=False).tolist()
    angles += angles[:1]

    ax_radar.plot(angles, values, linewidth=2)
    ax_radar.fill(angles, values, alpha=0.25)
    ax_radar.set_thetagrids(np.degrees(angles[:-1]), CATEGORIES)
    ax_radar.set_title(f"Radar Sensorial – {lote}", y=1.08, fontsize=16)
    ax_radar.grid(True)

    # Tabela
    ax_table = fig.add_subplot(gs[1])
    ax_table.axis("off")
    df_table = tabela_info.to_frame().T
    table = ax_table.table(
        cellText=df_table.values,
        colLabels=df_table.columns,
        cellLoc="center",
        loc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.5)

    fig.subplots_adjust(hspace=0.5)
    return fig

@app.get("/radar")
async def radar_pdf(lote: str = Query(..., description="Nome do lote (ex.: 'Lote - 1')")):
    df_radar = load_data_radar()
    df_tabela = load_data_tabela()

    radar_series = prepare_lote(df_radar, lote)
    if radar_series is None:
        raise HTTPException(status_code=404, detail=f"Lote '{lote}' não encontrado na aba sensorial")

    tabela_row = df_tabela[df_tabela["lote_prova"] == lote]
    if tabela_row.empty:
        raise HTTPException(status_code=404, detail=f"Lote '{lote}' não encontrado na aba fato_tipo_de_cafe")

    fig = create_combined_figure(radar_series, tabela_row.iloc[0], lote)

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    pdf_bytes = buf.getvalue()
    encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    return {
        "fileName": f"{lote}_radar_tabela.pdf",
        "pdf_base64": encoded_pdf,
        "mimetype": "application/pdf"
    }

