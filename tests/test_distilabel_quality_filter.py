from training.steps.quality_filter import QualityFilterStep


def test_quality_filter_flags_low_quality():
    step = QualityFilterStep(role="ba", min_score=0.9)
    rows = [
        {
            "instruction": "x",
            "input": "y",
            "output": "corto",
            "role": "ba",
            "metadata": {},
        }
    ]
    out = step.process(rows)
    assert out[0]["passed"] is False
    assert out[0]["retry"] is True


def test_quality_filter_passes_good_output():
    step = QualityFilterStep(role="ba", min_score=0.2)
    rows = [
        {
            "instruction": "x",
            "input": "y",
            "output": "Salida suficientemente larga para superar threshold local de score",
            "role": "ba",
            "metadata": {},
        }
    ]
    out = step.process(rows)
    assert out[0]["passed"] is True
