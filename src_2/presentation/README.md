# Presentation Adapters

The Streamlit adapter calls the completed-cycle application use case and renders
its returned contracts. KPI, assessment, and budget calculations remain outside
the UI.

Run from the repository root:

```bash
python -m streamlit run app_v2.py
```

The report works without an API key. Add `OPENAI_API_KEY` to `.env` only to
enable the optional structured campaign narrative in the deep-dive view.
