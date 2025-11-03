# 07 - Metrics and common helpers

Create the file `dspy/config/metrics.py` that defines two functions:

1. `requirements_metric(example, prediction) -> float`
   - example: dict
   - prediction: object/dict with the model output
   - scoring idea:
     - +0.4 if non-empty text
     - +0.3 if it contains the word "epic" or "story"
     - +0.3 if length is above a minimal threshold
     - cap at 1.0

2. `qa_metric(example, prediction) -> float`
   - reward presence of both "happy" and "negative" or "unhappy"
   - reward list/numbering
   - return a float in [0,1]

Also create `dspy/modules/common.py` with:
- `tiny_trainset_ba()` returning 3-5 tiny examples as a list[dict]
- `tiny_trainset_qa()` returning 3-5 tiny examples
- placeholder YAML validator with a TODO
