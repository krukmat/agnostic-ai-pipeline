from training.steps.cot_generator import ChainOfThoughtGenerator


def test_cot_split_reasoning_answer():
    gen = ChainOfThoughtGenerator()
    out = gen.format_output("Reasoning: paso 1 y paso 2\nAnswer: respuesta final")
    assert out["reasoning"] == "paso 1 y paso 2"
    assert out["output"] == "respuesta final"


def test_cot_fallback_when_no_format():
    gen = ChainOfThoughtGenerator()
    out = gen.format_output("solo respuesta")
    assert out["reasoning"] == ""
    assert out["output"] == "solo respuesta"
