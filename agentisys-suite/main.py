"""
AgentiSys Suite — point d'entrée unique regroupant les 7 démonstrateurs IA (8 outils) du portfolio.
Auteur : Wajih Jemli — Consultant IA & Transformation Opérationnelle

Pourquoi un seul processus plutôt que 8 apps séparées : un seul outil est utilisé à la fois
pendant une démonstration — faire tourner 8 serveurs sur 8 ports différents n'apporte aucune
valeur et ajoute une charge opérationnelle inutile. Chaque outil reste un module indépendant
(routeur FastAPI dédié dans tools/<outil>/router.py) : il peut être re-séparé en service
distinct plus tard sans réécrire sa logique, si un jour il doit scaler seul.

Structure :
    /                        -> hub (choix de l'outil)
    /<outil>                 -> page de l'outil (ex: /assurbot)
    /api/<outil>/...         -> API de l'outil (ex: /api/assurbot/chat)
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()  # une seule clé GROQ_API_KEY, partagée par les 8 outils

from tools.assurbot.router import router as assurbot_router
from tools.senticlaim.router import router as senticlaim_router
from tools.assurocr.router import router as assurocr_router
from tools.assurmeet.router import router as assurmeet_router
from tools.assurrag.router import router as assurrag_router
from tools.assurtranslate.router import router as assurtranslate_router
from tools.assurvision.router import router as assurvision_router
from tools.assurvoice.router import router as assurvoice_router

TOOLS = [
    "assurbot", "senticlaim", "assurocr", "assurmeet",
    "assurrag", "assurtranslate", "assurvision", "assurvoice",
]

app = FastAPI(title="AgentiSys Suite")

app.include_router(assurbot_router, prefix="/api/assurbot", tags=["AssurBot"])
app.include_router(senticlaim_router, prefix="/api/senticlaim", tags=["SentiClaim"])
app.include_router(assurocr_router, prefix="/api/assurocr", tags=["AssurOCR"])
app.include_router(assurmeet_router, prefix="/api/assurmeet", tags=["AssurMeet"])
app.include_router(assurrag_router, prefix="/api/assurrag", tags=["AssurRAG"])
app.include_router(assurtranslate_router, prefix="/api/assurtranslate", tags=["AssurTranslate"])
app.include_router(assurvision_router, prefix="/api/assurvision", tags=["AssurVision"])
app.include_router(assurvoice_router, prefix="/api/assurvoice", tags=["AssurVoice"])

app.mount("/static", StaticFiles(directory="static"), name="hub-static")
for slug in TOOLS:
    app.mount(f"/{slug}/static", StaticFiles(directory=f"tools/{slug}/static"), name=f"{slug}-static")


@app.get("/")
def hub():
    return FileResponse("static/index.html")


def _make_tool_page(slug: str):
    def page():
        return FileResponse(f"tools/{slug}/static/index.html")
    return page


for slug in TOOLS:
    app.add_api_route(f"/{slug}", _make_tool_page(slug), methods=["GET"])
