import streamlit as st
from dotenv import load_dotenv

from src.core import MarketingExpertError, configure_logging
from src.ingestion import CampaignDataService
from src.pipelines import MarketingPipeline
from src.presentation import (
    apply_page_style,
    initialize_session_state,
    render_analysis_result,
    render_category_selector,
    render_header,
    render_sidebar,
)

load_dotenv()
configure_logging()

data_service = CampaignDataService()
marketing_pipeline = MarketingPipeline(data_service=data_service)


def handle_click_category(category_name: str) -> None:
    st.session_state.selected_category = category_name
    st.session_state.run_analysis = True


def main() -> None:
    apply_page_style()
    render_header()
    render_sidebar(data_service)
    initialize_session_state()
    render_category_selector(handle_click_category)

    if st.session_state.run_analysis and st.session_state.selected_category:
        selected_category = st.session_state.selected_category
        st.markdown(
            f"<h2 style='text-align: center; color: #4338ca;'>Analysis: {selected_category}</h2>",
            unsafe_allow_html=True,
        )

        with st.spinner(f"Generating detailed report for {selected_category}..."):
            try:
                pipeline_result = marketing_pipeline.run(selected_category)
                render_analysis_result(pipeline_result)
            except MarketingExpertError as exc:
                st.error(str(exc))
            except Exception as exc:  # pragma: no cover - UI-only safety net.
                st.error(f"An error occurred: {exc}")

        st.session_state.run_analysis = False


if __name__ == "__main__":
    main()
