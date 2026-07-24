PYTHON ?= python3
ENV = PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1

.PHONY: demo test lint reproduce-model-comparison reproduce-replay

demo:
	$(ENV) $(PYTHON) -m terrarium demo --output docs/demo/index.html

test:
	$(ENV) $(PYTHON) -m unittest discover -s tests -v

lint:
	$(ENV) $(PYTHON) scripts/lint.py

reproduce-model-comparison:
	$(ENV) $(PYTHON) -m terrarium demo --output docs/demo/index.html --json-output docs/demo/model-comparison.json

reproduce-replay:
	$(ENV) $(PYTHON) -m terrarium replay examples/recorded/inbox-triage-flash.json --output docs/demo/replay.html

