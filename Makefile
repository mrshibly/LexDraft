.PHONY: install run run-ui eval demo seed clean

install:
	pip install -r requirements.txt
	python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

run:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run-ui:
	streamlit run ui/app.py

seed:
	python scripts/seed_sample_docs.py

demo:
	python scripts/demo_feedback_loop.py

eval:
	python evaluation/eval_retrieval.py
	python evaluation/eval_grounding.py
	python evaluation/eval_feedback.py

clean:
	rm -rf data/chroma_db/*
	rm -f data/lexdraft.db
	rm -rf logs/*
	rm -rf __pycache__ */__pycache__ */*/__pycache__
