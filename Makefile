NAME := src
VENV := .venv
PYTHON := $(VENV)/bin/python
FLAKE8 := $(VENV)/bin/flake8
MYPY := $(VENV)/bin/mypy

ARGV=
MAX_CHUNK_SIZE=2000
K=10
QUERY="What is the type hint for the kv_range_for_decode parameter in the _attention_with_mask method?"


ECHO    := echo -e

install:
	uv sync

run: install
	$(PYTHON) -m $(NAME) $(ARGV)

lint: install
	$(PYTHON) -m flake8 src
	$(PYTHON) -m mypy src --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: install
	$(PYTHON) -m flake8 src
	$(PYTHON) -m mypy src --strict

debug: install
	$(PYTHON) -m pdb -m src

clean:
	rm -rf data/processed/*
	rm -rf data/output/search_results/*
	rm -rf data/output/search_results_and_answer/*


index: install
	clear
	$(PYTHON) -m $(NAME) index --max_chunk_size $(MAX_CHUNK_SIZE)

search: install
	uv run python -m src search $(QUERY) --k $(K)

search_dataset: install
	uv run python -m src search_dataset --dataset_path 'data/datasets/UnansweredQuestions/dataset_code_public.json' --k $(K) --save_directory data/output/search_results/UnansweredQuestions
	uv run python -m src search_dataset --dataset_path 'data/datasets/UnansweredQuestions/dataset_docs_public.json' --k $(K) --save_directory data/output/search_results/UnansweredQuestions

answer: install
	uv run python -m src answer $(QUERY)

answer-dataset: install
	uv run python -m src answer_dataset --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_code_public.json --save_directory data/output/search_results_and_answer/AnsweredQuestions


moulinette-code: install
	uv run python -m src search_dataset --dataset_path 'data/datasets/UnansweredQuestions/dataset_code_public.json' --k $(K) --save_directory data/output/search_results/UnansweredQuestions
	./moulinette/moulinette-ubuntu evaluate_student_search_results 'data/output/search_results/UnansweredQuestions/dataset_code_public.json' 'data/datasets/AnsweredQuestions/dataset_code_public.json' --k $(K)

moulinette-docs: install
	uv run python -m src search_dataset --dataset_path 'data/datasets/UnansweredQuestions/dataset_docs_public.json' --k $(K) --save_directory data/output/search_results/UnansweredQuestions
	./moulinette/moulinette-ubuntu evaluate_student_search_results 'data/output/search_results/UnansweredQuestions/dataset_docs_public.json' 'data/datasets/AnsweredQuestions/dataset_docs_public.json' --k $(K)

evaluate: install
	uv run python -m src evaluate data/output/search_results/UnansweredQuestions/dataset_code_public.json data/datasets/AnsweredQuestions/dataset_code_public.json --k 10
	uv run python -m src evaluate data/output/search_results/UnansweredQuestions/dataset_docs_public.json data/datasets/AnsweredQuestions/dataset_docs_public.json --k 10


start-api: install
	uv run uvicorn api.api:app --reload
