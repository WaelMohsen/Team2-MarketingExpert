# NOTE: Tests have been split into individual files by schema type
# Import for backward compatibility

from .test_analysis_schema import TestAnalysisSchemaValidation, _analysis_payload
from .test_input_schema import TestCampaignInputSchemaValidation, _campaign_record
from .test_recommendation_schema import (
    TestRecommendationSchemaValidation,
    _recommendation_payload,
)

__all__ = [
    "TestAnalysisSchemaValidation",
    "TestRecommendationSchemaValidation",
    "TestCampaignInputSchemaValidation",
    "_analysis_payload",
    "_recommendation_payload",
    "_campaign_record",
]
