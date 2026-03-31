import pandas as pd

from src.preprocessing import CampaignPreprocessingService


def test_preprocess_normalizes_strings_dates_and_sort_order():
    dataframe = pd.DataFrame(
        [
            {
                "campaign_name": "  Launch B  ",
                "date": "03/02/2026",
                "channel": "  Social  ",
                "spend": "100.5",
            },
            {
                "campaign_name": " Launch A",
                "date": "2026-03-01",
                "channel": " Email ",
                "spend": "50",
            },
        ]
    )

    result = CampaignPreprocessingService().preprocess(dataframe)

    assert result.applied_steps == (
        "normalize_strings",
        "coerce_numeric_columns",
        "normalize_dates",
        "sort_rows",
    )
    assert result.row_count_before == 2
    assert result.row_count_after == 2
    assert result.dataframe["campaign_name"].tolist() == ["Launch A", "Launch B"]
    assert result.dataframe["channel"].tolist() == ["Email", "Social"]
    assert result.dataframe["date"].tolist() == ["2026-03-01", "2026-03-02"]
    assert result.dataframe["spend"].tolist() == [50.0, 100.5]
