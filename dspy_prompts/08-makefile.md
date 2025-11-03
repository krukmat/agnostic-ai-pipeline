# 08 - Makefile targets

Open the repository Makefile (or create one if not present) and add these targets:

```make
dspy-ba:
	python -m dspy.scripts.run_ba --concept "New B2B ordering app"

dspy-qa:
	python -m dspy.scripts.run_qa --story-file examples/story.json

dspy-tune-ba:
	python -m dspy.scripts.tune --program ba

dspy-tune-qa:
	python -m dspy.scripts.tune --program qa
```

If the repository uses poetry or another runner, add a TODO to wrap these commands accordingly.

Do not remove existing targets.
