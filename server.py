import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import src.llm as llm_handler
import src.metrics_engine as data_processor

app = FastAPI()

class AnalyzeReq(BaseModel):
    category: str

class ChatReq(BaseModel):
    message: str
    analysis: dict | None = None
    recommendations: list | None = None
    category: str | None = None

def _build_by_channel(per_channel: dict) -> list:
    rows = []
    for name, m in per_channel.items():
        rows.append({
            "channel": name,
            "spend": m.get("Total Spend", 0),
            "revenue": m.get("Total Revenue", 0),
            "conversions": m.get("Total Conversions", 0),
            "ctr": float(str(m.get("CTR", 0)).replace("%", "")),
            "cpa": m.get("CPA", 0),
            "roas": m.get("ROAS", 0),
            "bounce": m.get("Average Bounce Rate", 0) or 0,
            "churn": m.get("Churn Rate", 0) or 0,
        })
    return rows

@app.post("/api/analyze")
def analyze(req: AnalyzeReq):
    df = data_processor.load_data()
    metrics = data_processor.calculate_metrics_full(df, req.category)
    response = llm_handler.generate_response(df, req.category, metrics)
    overall = metrics.get("overall", {})
    return {
        "kpis": list(overall.keys()),
        "overall": overall,
        "byChannel": _build_by_channel(metrics.get("per_channel", {})),
        "analysis": response.get("analysis", {}),
        "recommendations": response.get("recommendations", []),
    }

@app.get("/api/campaigns")
def campaigns():
    df = data_processor.load_data()
    if df is None:
        return []
    return json.loads(df.to_json(orient="records"))

@app.get("/api/history")
def history():
    log_dir = Path("output_log")
    if not log_dir.exists():
        return []
    files = sorted(log_dir.glob("pipeline_output_*.json"), reverse=True)
    results = []
    for f in files[:20]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            analysis = data.get("analysis", {})
            recs = data.get("recommendations", [])
            # Infer category from KPIs: presence of specific KPIs hints at category
            kpis = data.get("kpis", [])
            cat = "Analysis"
            if "Engagement Rate" in kpis:
                cat = "Customer Satisfaction"
            elif "Retention Rate" in kpis or "Churn Rate" in kpis:
                cat = "Customer Retention"
            elif "AOV" in kpis or "Marketing ROI" in kpis:
                cat = "Revenue Growth"
            elif "CTR" in kpis:
                cat = "Customer Acquisition"
            results.append({
                "filename": f.name,
                "timestamp": f.name.replace("pipeline_output_", "").replace(".json", ""),
                "category": cat,
                "confidence": analysis.get("confidence_score", 0),
                "recCount": len(recs),
            })
        except Exception:
            continue
    return results

@app.get("/api/history/{filename}")
def history_detail(filename: str):
    path = Path("output_log") / filename
    if not path.exists() or not path.name.startswith("pipeline_output_"):
        return {"error": "not found"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data

@app.post("/api/chat")
def chat(req: ChatReq):
    context = ""
    if req.category:
        context += f"Category: {req.category}\n"
    if req.analysis:
        context += f"Analysis: {json.dumps(req.analysis)}\n"
    if req.recommendations:
        context += f"Recommendations: {json.dumps(req.recommendations)}\n"

    prompt = f"""You are a marketing expert assistant. The user has just reviewed a marketing analysis and has follow-up questions.

Here is the analysis context:
{context}

User question: {req.message}

Answer in plain business language. Be concise and actionable. Avoid marketing abbreviations."""

    response = llm_handler.llm_callable(prompt)
    return {"reply": response}

app.mount("/", StaticFiles(directory="web", html=True), name="web")
