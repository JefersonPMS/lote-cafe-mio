from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io

app = FastAPI()

# ID e GID da planilha/aba
SHEET_ID = "1yZWlkb8sKZ5PKQiVk5buOhd2pwPdIW2zLG60Z9h18wQ"
GID = "1027109383"
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{SHEET_ID}/export?format=csv&gid={GID}"
)

# Colunas a plotar no radar
CATEGORIES = [
    "Fragrance", "Flavor", "Aftertaste", "Acidity", "Body",
    "Uniformity", "Clean Cup", "Sweetness", "Balance", "Overall"
]

def load_data() -> pd.DataFrame:
    return pd.read_csv(CSV_URL)

def prepare_lote(df: pd.DataFrame, lote: str) -> pd.Series | None:
    df_l = df[df["Lote"] == lote]
    if df_l.empty:
        return None
    return df_l[CATEGORIES].mean()

def create_radar(data: pd.Series, lote: str) -> plt.Figure:
    values = data.tolist()
    N = len(values)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    # fecha o gráfico
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(6,6))
    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), CATEGORIES)
    ax.set_title(f"Radar Sensory – {lote}", y=1.08)
    ax.grid(True)
    return fig

@app.get("/radar", response_class=StreamingResponse)
async def radar_pdf(lote: str = Query(..., description="Nome do lote (ex.: 'Lote - 1')")):
    # 1) carrega os dados
    df = load_data()

    # 2) filtra e calcula média do lote
    series = prepare_lote(df, lote)
    if series is None:
        raise HTTPException(status_code=404, detail=f"Lote '{lote}' não encontrado")

    # 3) gera o radar plot
    fig = create_radar(series, lote)

    # 4) salva em PDF na memória  
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    # 5) retorna o PDF
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{lote}_radar.pdf"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
