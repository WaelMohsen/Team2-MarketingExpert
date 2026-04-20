# tests_2/test_services.py
import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from schemas.analysis_output_schema import AnalysisOutput
from schemas.recommendation_output_schema import RecommendationOutput
from services.base_llm_service import BaseLLMService
from services.llm_analysis_service import LLMAnalysisService
from services.llm_client import LLMClient
from services.llm_orchestrator import LLMOrchestrator
from services.llm_recommendation_service import LLMRecommendationService
from services.prompt_builder import PromptBuilder

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Create a mock LLMClient."""
    return Mock(spec=LLMClient)


@pytest.fixture
def mock_prompt_builder():
    """Create a mock PromptBuilder."""
    mock = Mock(spec=PromptBuilder)
    mock.load.return_value = "System prompt template"
    mock.load_target_prompt.return_value = "Target explanation for revenue"
    return mock


@pytest.fixture
def sample_analysis_output():
    """Sample valid analysis output."""
    return {
        "analysis": "Campaign analysis shows strong performance",
        "key_signals": ["High CTR", "Good conversion rate"],
        "detected_issues": ["Low retention"],
        "root_cause_hypothesis": "Limited retargeting",
        "business_risks": ["Customer churn risk"],
        "confidence_score": 0.85,
    }


@pytest.fixture
def sample_recommendation_cards():
    """Sample recommendation cards (5-8 items as required)."""
    base_card = {
        "id": "rec_{:03d}",
        "title": "Recommendation {}",
        "category": "budget",
        "priority": "high",
        "effort": "low",
        "time_to_see_impact": "2 weeks",
        "confidence": "high",
        "whats_happening": "Performance issue detected",
        "evidence": ["Metric below threshold"],
        "what_you_should_do": [
            {
                "step": "Take action",
                "where": "All channels",
                "how": "Gradual change",
                "guardrails": ["Monitor metrics"],
            }
        ],
        "why_this_matters": "Improve KPI",
        "expected_impact": {
            "primary_kpi": "revenue",
            "direction": "increase",
            "explanation": "Better performance",
        },
        "dependency_or_risk": ["Campaign stability"],
        "measurement_plan": {
            "how_to_measure": "Track metrics",
            "success_criteria": "Increase 15%",
            "check_timing": "Weekly",
            "notes": "Compare to baseline",
        },
        "owner_suggestion": "Marketing Manager",
    }
    return [
        {
            **base_card,
            "id": f"rec_{i:03d}",
            "title": f"Recommendation {i}",
        }
        for i in range(6)  # 6 recommendations (within 5-8 range)
    ]


@pytest.fixture
def mock_analysis_service_response(mock_llm_client, sample_analysis_output):
    """Create mock chat completion response for analysis service."""
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed.dict.return_value = sample_analysis_output
    mock_llm_client.chat_completion.return_value = mock_response
    return mock_response


@pytest.fixture
def mock_recommendation_service_response(mock_llm_client, sample_recommendation_cards):
    """Create mock chat completion response for recommendation service."""
    recommendation_output = {"recommendations": sample_recommendation_cards}
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed.dict.return_value = recommendation_output
    mock_llm_client.chat_completion.return_value = mock_response
    return mock_response


# ============================================================================
# Tests for BaseLLMService
# ============================================================================


class TestBaseLLMService:
    def test_base_service_is_abstract(self):
        """BaseLLMService should not be instantiable."""
        with pytest.raises(TypeError):
            BaseLLMService()

    def test_base_service_requires_run_method(self):
        """Concrete implementation must override run()."""

        class IncompleteService(BaseLLMService):
            def build_system_prompt(self, target):
                pass

            def build_user_prompt(
                self, target, base_context, selected_metrics, analysis_json=None
            ):
                pass

        with pytest.raises(TypeError):
            IncompleteService()

    def test_base_service_requires_prompts(self):
        """Concrete implementation must override prompt builders."""

        class IncompleteService(BaseLLMService):
            def run(self, target, metrics, selected_metrics, analysis_json=None):
                pass

        with pytest.raises(TypeError):
            IncompleteService()


# ============================================================================
# Tests for LLMClient
# ============================================================================


class TestLLMClient:
    def test_llm_client_initialization_with_api_key(self):
        """LLMClient initializes with valid API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            with patch("services.llm_client.OpenAI") as mock_openai:
                client = LLMClient()
                assert client._client is not None
                mock_openai.assert_called_once_with(api_key="sk-test123")

    def test_llm_client_raises_without_api_key(self):
        """LLMClient raises RuntimeError without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="Missing OPENAI_API_KEY"):
                LLMClient()

    def test_chat_completion_calls_openai_api(self):
        """chat_completion() calls OpenAI API with correct parameters."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            with patch("services.llm_client.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client
                mock_client.beta.chat.completions.parse.return_value = {
                    "choices": [{"message": {"parsed": {}}}]
                }

                client = LLMClient()
                client.chat_completion(
                    system_text="You are helpful",
                    user_text="Hello",
                    response_format=AnalysisOutput,
                    model="gpt-4o-mini",
                )

                mock_client.beta.chat.completions.parse.assert_called_once()
                call_args = mock_client.beta.chat.completions.parse.call_args
                assert call_args.kwargs["model"] == "gpt-4o-mini"
                assert call_args.kwargs["temperature"] == 0.2
                assert len(call_args.kwargs["messages"]) == 2

    def test_chat_completion_message_structure(self):
        """chat_completion() creates correct message structure."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            with patch("services.llm_client.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                client = LLMClient()
                client.chat_completion(
                    system_text="System message",
                    user_text="User message",
                    response_format=AnalysisOutput,
                    model="gpt-4o-mini",
                )

                call_args = mock_client.beta.chat.completions.parse.call_args
                messages = call_args.kwargs["messages"]
                assert messages[0]["role"] == "system"
                assert messages[0]["content"] == "System message"
                assert messages[1]["role"] == "user"
                assert messages[1]["content"] == "User message"


# ============================================================================
# Tests for PromptBuilder
# ============================================================================


class TestPromptBuilder:
    def test_prompt_builder_load_existing_file(self, tmp_path):
        """PromptBuilder.load() reads existing file."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "test_prompt.md"
        prompt_file.write_text("Test prompt content")

        pb = PromptBuilder(str(prompts_dir))
        result = pb.load("test_prompt.md")
        assert result == "Test prompt content"

    def test_prompt_builder_load_missing_file_returns_empty(self, tmp_path):
        """PromptBuilder.load() returns empty string for missing file."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        pb = PromptBuilder(str(prompts_dir))
        result = pb.load("nonexistent.md")
        assert result == ""

    def test_prompt_builder_load_target_prompt_revenue(self, tmp_path):
        """PromptBuilder.load_target_prompt() maps targets correctly."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "revenue_growth.md").write_text("Revenue explanation")

        pb = PromptBuilder(str(prompts_dir))
        result = pb.load_target_prompt("revenue")
        assert result == "Revenue explanation"

    def test_prompt_builder_load_target_prompt_acquisition(self, tmp_path):
        """PromptBuilder.load_target_prompt() maps acquisition target."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "customer_acquisition.md").write_text("Acquisition explanation")

        pb = PromptBuilder(str(prompts_dir))
        result = pb.load_target_prompt("acquisition")
        assert result == "Acquisition explanation"

    def test_prompt_builder_load_target_prompt_retention(self, tmp_path):
        """PromptBuilder.load_target_prompt() maps retention target."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "customer_retention.md").write_text("Retention explanation")

        pb = PromptBuilder(str(prompts_dir))
        result = pb.load_target_prompt("retention")
        assert result == "Retention explanation"

    def test_prompt_builder_load_target_prompt_satisfaction(self, tmp_path):
        """PromptBuilder.load_target_prompt() maps satisfaction target."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "customer_satisfaction.md").write_text(
            "Satisfaction explanation"
        )

        pb = PromptBuilder(str(prompts_dir))
        result = pb.load_target_prompt("satisfaction")
        assert result == "Satisfaction explanation"

    def test_prompt_builder_load_target_prompt_unknown_returns_empty(self, tmp_path):
        """PromptBuilder.load_target_prompt() returns empty for unknown target."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        pb = PromptBuilder(str(prompts_dir))
        result = pb.load_target_prompt("unknown_target")
        assert result == ""


# ============================================================================
# Tests for LLMAnalysisService
# ============================================================================


class TestLLMAnalysisService:
    def test_analysis_service_build_system_prompt(
        self, mock_llm_client, mock_prompt_builder
    ):
        """LLMAnalysisService.build_system_prompt() formats correctly."""
        service = LLMAnalysisService(mock_llm_client, mock_prompt_builder)
        prompt = service.build_system_prompt("revenue")

        assert "System prompt template" in prompt
        assert "TARGET: revenue" in prompt
        assert "Target explanation for revenue" in prompt
        mock_prompt_builder.load.assert_called_with("analysis_prompt.md")
        mock_prompt_builder.load_target_prompt.assert_called_with("revenue")

    def test_analysis_service_build_user_prompt(
        self, mock_llm_client, mock_prompt_builder
    ):
        """LLMAnalysisService.build_user_prompt() formats correctly."""
        service = LLMAnalysisService(mock_llm_client, mock_prompt_builder)
        base_context = "Campaign performed well"
        selected_metrics = '{"ctr": 5.0, "roas": 2.0}'

        prompt = service.build_user_prompt(
            "acquisition", base_context, selected_metrics
        )

        assert "Step 1 (Analysis Only)" in prompt
        assert "TARGET: acquisition" in prompt
        assert "BASE CONTEXT:" in prompt
        assert base_context in prompt
        assert "TARGET METRICS:" in prompt
        assert selected_metrics in prompt

    def test_analysis_service_run_returns_dict_with_model_and_json(
        self,
        mock_llm_client,
        mock_prompt_builder,
        mock_analysis_service_response,
        sample_analysis_output,
    ):
        """LLMAnalysisService.run() returns dict with model and JSON."""
        service = LLMAnalysisService(mock_llm_client, mock_prompt_builder)

        result = service.run("revenue", "Context", '{"metric": "value"}')

        assert isinstance(result, dict)
        assert "model" in result
        assert "json" in result
        assert isinstance(result["model"], AnalysisOutput)
        assert isinstance(result["json"], str)
        json_data = json.loads(result["json"])
        assert json_data["analysis"] == sample_analysis_output["analysis"]

    def test_analysis_service_client_called_correctly(
        self, mock_llm_client, mock_prompt_builder, mock_analysis_service_response
    ):
        """LLMAnalysisService.run() calls client with model gpt-4o-mini."""
        service = LLMAnalysisService(mock_llm_client, mock_prompt_builder)
        service.run("revenue", "Context", '{"metric": "value"}')

        mock_llm_client.chat_completion.assert_called_once()
        call_args = mock_llm_client.chat_completion.call_args
        # response_format is the third positional argument
        assert call_args[0][2] == AnalysisOutput
        assert call_args.kwargs["model"] == "gpt-4o-mini"


# ============================================================================
# Tests for LLMRecommendationService
# ============================================================================


class TestLLMRecommendationService:
    def test_recommendation_service_build_system_prompt(
        self, mock_llm_client, mock_prompt_builder
    ):
        """LLMRecommendationService.build_system_prompt() formats correctly."""
        service = LLMRecommendationService(mock_llm_client, mock_prompt_builder)
        prompt = service.build_system_prompt("revenue")

        assert "System prompt template" in prompt
        assert "TARGET: revenue" in prompt
        assert "Target explanation for revenue" in prompt
        mock_prompt_builder.load.assert_called_with("recommendation_prompt.md")

    def test_recommendation_service_build_user_prompt_with_analysis(
        self, mock_llm_client, mock_prompt_builder
    ):
        """LLMRecommendationService.build_user_prompt() includes analysis JSON."""
        service = LLMRecommendationService(mock_llm_client, mock_prompt_builder)
        base_context = "Campaign context"
        selected_metrics = '{"metric": "value"}'
        analysis_json = '{"analysis": "data"}'

        prompt = service.build_user_prompt(
            "acquisition", base_context, selected_metrics, analysis_json
        )

        assert "Step 2 (Recommendations)" in prompt
        assert "TARGET: acquisition" in prompt
        assert "STEP 1 ANALYSIS:" in prompt
        assert '{"analysis": "data"}' in prompt

    def test_recommendation_service_build_user_prompt_without_analysis(
        self, mock_llm_client, mock_prompt_builder
    ):
        """LLMRecommendationService.build_user_prompt() handles None analysis."""
        service = LLMRecommendationService(mock_llm_client, mock_prompt_builder)

        prompt = service.build_user_prompt("revenue", "Context", '{"m": "v"}')

        assert "STEP 1 ANALYSIS:" in prompt
        assert "None" in prompt

    def test_recommendation_service_run_returns_recommendation_output(
        self,
        mock_llm_client,
        mock_prompt_builder,
        mock_recommendation_service_response,
    ):
        """LLMRecommendationService.run() returns RecommendationOutput."""
        service = LLMRecommendationService(mock_llm_client, mock_prompt_builder)

        result = service.run(
            "revenue", "Context", '{"metric": "value"}', '{"analysis": "data"}'
        )

        assert isinstance(result, RecommendationOutput)
        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0

    def test_recommendation_service_client_called_with_gpt4o(
        self,
        mock_llm_client,
        mock_prompt_builder,
        mock_recommendation_service_response,
    ):
        """LLMRecommendationService.run() calls client with model gpt-4o."""
        service = LLMRecommendationService(mock_llm_client, mock_prompt_builder)
        service.run("revenue", "Context", '{"metric": "value"}')

        call_args = mock_llm_client.chat_completion.call_args
        assert call_args.kwargs["model"] == "gpt-4o"
        # response_format is the third positional argument
        assert call_args[0][2] == RecommendationOutput


# ============================================================================
# Tests for LLMOrchestrator
# ============================================================================


class TestLLMOrchestrator:
    def test_orchestrator_initialization_creates_services(self):
        """LLMOrchestrator initializes with analysis and recommendation services."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            with patch("services.llm_orchestrator.LLMClient"):
                with patch("services.llm_orchestrator.PromptBuilder"):
                    orchestrator = LLMOrchestrator()
                    assert isinstance(orchestrator.analysis, LLMAnalysisService)
                    assert isinstance(
                        orchestrator.recommendation, LLMRecommendationService
                    )

    def test_orchestrator_run_calls_analysis_then_recommendation(self):
        """LLMOrchestrator.run() calls analysis first, then recommendation."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            with patch("services.llm_orchestrator.LLMClient"):
                with patch("services.llm_orchestrator.PromptBuilder"):
                    with patch.object(LLMOrchestrator, "_save_output"):  # noqa: F841
                        orchestrator = LLMOrchestrator()
                        orchestrator.analysis = MagicMock()
                        orchestrator.recommendation = MagicMock()

                        orchestrator.analysis.run.return_value = {
                            "model": MagicMock(dict=MagicMock(return_value={})),
                            "json": '{"analysis": "data"}',
                        }
                        orchestrator.recommendation.run.return_value = MagicMock(
                            recommendations=[], dict=MagicMock(return_value={})
                        )

                        orchestrator.run("revenue", "metrics", "selected")

                        orchestrator.analysis.run.assert_called_once_with(
                            "revenue", "metrics", "selected"
                        )
                        orchestrator.recommendation.run.assert_called_once()

    def test_orchestrator_runs_calls_save_output(self):
        """LLMOrchestrator.run() saves combined output."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            with patch("services.llm_orchestrator.LLMClient"):
                with patch("services.llm_orchestrator.PromptBuilder"):
                    with patch.object(LLMOrchestrator, "_save_output") as mock_save:
                        orchestrator = LLMOrchestrator()
                        orchestrator.analysis = MagicMock()
                        orchestrator.recommendation = MagicMock()

                        orchestrator.analysis.run.return_value = {
                            "model": MagicMock(dict=MagicMock(return_value={})),
                            "json": "{}",
                        }
                        orchestrator.recommendation.run.return_value = MagicMock(
                            recommendations=[]
                        )

                        orchestrator.run("revenue", "metrics", "selected")
                        mock_save.assert_called_once()

    def test_orchestrator_save_output_creates_directory(self, tmp_path):
        """LLMOrchestrator._save_output() creates output_log directory if missing."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            with patch("services.llm_orchestrator.LLMClient"):
                with patch("services.llm_orchestrator.PromptBuilder"):
                    output_dir = str(tmp_path / "output_log")
                    orchestrator = LLMOrchestrator(output_log_dir=output_dir)

                    assert not os.path.exists(output_dir)
                    orchestrator._save_output({"test": "data"})
                    assert os.path.exists(output_dir)

    def test_orchestrator_save_output_writes_json_file(self, tmp_path):
        """LLMOrchestrator._save_output() writes valid JSON file."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            with patch("services.llm_orchestrator.LLMClient"):
                with patch("services.llm_orchestrator.PromptBuilder"):
                    output_dir = str(tmp_path / "output_log")
                    orchestrator = LLMOrchestrator(output_log_dir=output_dir)

                    output_data = {"analysis": {"key": "value"}, "recommendations": []}
                    with patch("builtins.print"):
                        orchestrator._save_output(output_data)

                    files = os.listdir(output_dir)
                    assert len(files) == 1
                    output_file = os.path.join(output_dir, files[0])
                    with open(output_file) as f:
                        saved_data = json.load(f)
                    assert saved_data == output_data
