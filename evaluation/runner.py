"""
LangSmith evaluation runner for the Hybrid RAG service.

Runs the "Hybrid-RAG-Evaluation" dataset through the RAG service's
/internal/query endpoint and scores the results with LangSmith's evaluate(),
producing a real Experiment/Run in the "Hybrid-RAG" project (visible under
the dataset in the LangSmith UI).

Usage (CLI):
    python evaluation/runner.py

Usage (imported, e.g. by admin_service):
    from evaluation.runner import run_evaluation
    summary = run_evaluation()

Requires the RAG service to be running (default: http://localhost:8001).
"""

import os

import requests
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langsmith.evaluation import evaluate

load_dotenv()

RAG_URL = os.environ.get("RAG_QUERY_URL", "http://localhost:8001/internal/query")
DATASET_NAME = "Hybrid-RAG-Evaluation"

INTERNAL_HEADERS = {"X-Internal-Secret": os.environ.get("INTERNAL_SERVICE_SECRET", "")}

judge_llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)


def _inputs(obj):
    return obj.get("inputs", {}) if isinstance(obj, dict) else (getattr(obj, "inputs", None) or {})


def _outputs(obj):
    return obj.get("outputs", {}) if isinstance(obj, dict) else (getattr(obj, "outputs", None) or {})


def _judge(prompt: str) -> str:
    return judge_llm.invoke(prompt).content.strip().upper()


def target(inputs: dict) -> dict:
    response = requests.post(
        RAG_URL,
        json={"question": inputs["question"]},
        headers=INTERNAL_HEADERS,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def answer_correctness(run, example):
    actual_answer = _outputs(run).get("answer", "")
    expected_answer = _outputs(example).get("expected_answer", "")

    prompt = f"""
You are evaluating the answer produced by a RAG system.

Compare the ACTUAL ANSWER against the EXPECTED ANSWER.

EXPECTED ANSWER:
{expected_answer}

ACTUAL ANSWER:
{actual_answer}

Determine whether the actual answer is factually consistent with
the expected answer.

Important:
- Different wording is acceptable.
- Additional correct explanation is acceptable.
- Do not require exact wording.
- If the actual answer contradicts the expected answer, mark it incorrect.
- If the actual answer contains the expected information but is more detailed,
  mark it correct.
- For "not available in the provided documents" questions, the answer should
  correctly indicate that the requested information is unavailable.

Return ONLY one of these:
CORRECT
INCORRECT
"""
    verdict = _judge(prompt)
    return {"key": "answer_correctness", "score": 1 if verdict == "CORRECT" else 0, "comment": verdict}


def faithfulness(run, example):
    actual_answer = _outputs(run).get("answer", "")
    context = _outputs(run).get("context", [])
    context_text = "\n\n--- DOCUMENT ---\n\n".join(context)
    question = _inputs(example).get("question", "")

    prompt = f"""
You are evaluating the faithfulness of a RAG system's answer.

QUESTION:
{question}

RETRIEVED CONTEXT:
{context_text}

ANSWER:
{actual_answer}

Determine whether the ANSWER is fully supported by the RETRIEVED CONTEXT.

Rules:
- The answer must be supported by the retrieved context.
- Do not use outside knowledge.
- If the answer contains claims that are not supported by the context,
  mark it INCORRECT.
- If the answer is fully supported by the context, mark it CORRECT.
- Different wording is acceptable.
- For an answer saying information is unavailable, check whether the
  retrieved context actually supports that conclusion.

Return ONLY:
CORRECT
or
INCORRECT
"""
    verdict = _judge(prompt)
    return {"key": "faithfulness", "score": 1 if verdict == "CORRECT" else 0, "comment": verdict}


def answer_relevance(run, example):
    actual_answer = _outputs(run).get("answer", "")
    question = _inputs(example).get("question", "")

    prompt = f"""
You are evaluating the relevance of a RAG system's answer.

QUESTION:
{question}

ANSWER:
{actual_answer}

Determine whether the answer directly addresses the user's question.

Rules:
- The answer should directly address what was asked.
- Do not judge factual correctness here.
- Focus only on whether the answer is relevant to the question.
- Concise answers are acceptable.
- Additional relevant explanation is acceptable.
- If the answer discusses unrelated information, mark it INCORRECT.
- For questions whose information is unavailable in the documents,
  an appropriate response stating that the information is unavailable
  is considered relevant.

Return ONLY:
CORRECT
or
INCORRECT
"""
    verdict = _judge(prompt)
    return {"key": "answer_relevance", "score": 1 if verdict == "CORRECT" else 0, "comment": verdict}


def retrieval_quality(run, example):
    """Only meaningful for in-context questions — out-of-context ones are
    scored separately by `abstention` since "no relevant chunks" is the
    correct retrieval outcome there, not a retrieval failure."""
    if _inputs(example).get("question_type") == "out_of_context":
        # LangSmith's evaluate() treats a bare `None`/`[]`/`{}` return as a
        # crashed evaluator (raises ValueError), not "no feedback for this
        # example" — a non-empty dict with an empty results list is the
        # actual way to skip scoring here.
        return {"results": []}

    question = _inputs(example).get("question", "")
    context = _outputs(run).get("context", [])
    context_text = "\n\n--- DOCUMENT ---\n\n".join(context)

    prompt = f"""
You are evaluating the retrieval quality of a RAG system.

QUESTION:
{question}

RETRIEVED DOCUMENTS:
{context_text}

Determine whether the retrieved documents contain the information
necessary to answer the question.

Rules:
- If the retrieved context contains sufficient information to answer
  the question, return CORRECT.
- If important information needed to answer the question is missing,
  return INCORRECT.
- The documents do not need to contain the exact wording of the answer.
- Semantic equivalence is acceptable.

Return ONLY:
CORRECT
or
INCORRECT
"""
    verdict = _judge(prompt)
    return {"key": "retrieval_quality", "score": 1 if verdict == "CORRECT" else 0, "comment": verdict}


def abstention(run, example):
    """Only meaningful for out-of-context questions — checks the system
    declines to answer rather than hallucinating a fact not grounded in the
    retrieved context."""
    if _inputs(example).get("question_type") != "out_of_context":
        return {"results": []}

    question = _inputs(example).get("question", "")
    actual_answer = _outputs(run).get("answer", "")
    context = _outputs(run).get("context", [])
    context_text = "\n\n--- DOCUMENT ---\n\n".join(context)

    prompt = f"""
You are evaluating whether a RAG system correctly abstains on a question
that cannot be answered from the knowledge base.

QUESTION (not answerable from the documents):
{question}

RETRIEVED CONTEXT:
{context_text}

ANSWER:
{actual_answer}

Determine whether the ANSWER correctly declines to answer / states that the
information is not available, rather than hallucinating an answer using
outside knowledge or fabricating details not present in the retrieved context.

Rules:
- If the answer clearly states the information is unavailable or not found
  in the documents (in any phrasing), mark it CORRECT.
- If the answer supplies a specific fact, figure, name, or claim that is not
  grounded in the retrieved context, mark it INCORRECT — this is a
  hallucination, even if the fact happens to be true in the real world.
- A partial hedge that still asserts unsupported specifics is INCORRECT.

Return ONLY:
CORRECT
or
INCORRECT
"""
    verdict = _judge(prompt)
    return {"key": "abstention", "score": 1 if verdict == "CORRECT" else 0, "comment": verdict}


EVALUATORS = [
    answer_correctness,
    faithfulness,
    answer_relevance,
    retrieval_quality,
    abstention,
]


def run_evaluation() -> dict:
    """Run the full evaluation dataset through the RAG service and LangSmith
    evaluators, then aggregate per-metric pass/fail counts.

    Returns a dict shaped like:
        {
            "run_id": "hybrid-rag-eval-...",
            "total_examples": 35,
            "metrics": {
                "answer_correctness": {"score": 97.14, "total_examples": 35,
                                        "passed_examples": 34, "failed_examples": 1},
                ...
            },
        }
    """
    results = evaluate(
        target,
        data=DATASET_NAME,
        evaluators=EVALUATORS,
        experiment_prefix="hybrid-rag-eval",
        max_concurrency=3,
    )

    tallies = {}
    examples_seen = 0

    for row in results:
        examples_seen += 1

        eval_results = (row.get("evaluation_results") or {}).get("results", [])

        for evaluation_result in eval_results:
            if evaluation_result is None:
                continue

            key = getattr(evaluation_result, "key", None)
            score = getattr(evaluation_result, "score", None)

            if key is None or score is None:
                continue

            passed, total = tallies.get(key, (0, 0))
            tallies[key] = (passed + (1 if score else 0), total + 1)

    metrics = {
        key: {
            "score": round((passed / total) * 100, 2) if total else 0.0,
            "total_examples": total,
            "passed_examples": passed,
            "failed_examples": total - passed,
        }
        for key, (passed, total) in tallies.items()
    }

    return {
        "run_id": results.experiment_name,
        "url": results.url,
        "total_examples": examples_seen,
        "metrics": metrics,
    }


if __name__ == "__main__":
    summary = run_evaluation()
    print(summary)
