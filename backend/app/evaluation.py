"""
Step 8 — RAGAS Evaluation Script

Runs RAGAS (faithfulness, answer_relevancy, context_precision) against
a labeled eval set and appends each result to eval/results.jsonl.

Usage:
  cd backend
  python -m app.evaluation
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_precision, faithfulness

from app.rag_chain import run_rag

EVAL_SET: List[Dict[str, str]] = [
    {
        "question": "What is the company's policy on annual leave entitlement?",
        "ground_truth": "Employees are entitled to annual leave as defined in the HR policy document.",
    },
    {
        "question": "How many sick days are employees allowed per year?",
        "ground_truth": "The sick leave policy specifies the number of sick days an employee may take per year.",
    },
    {
        "question": "What is the process for requesting a promotion?",
        "ground_truth": "The promotion process involves a formal appraisal and manager recommendation as described in the HR policy.",
    },
    {
        "question": "What is the disciplinary procedure for misconduct?",
        "ground_truth": "The disciplinary procedure includes verbal warning, written warning, and final written warning before dismissal.",
    },
    {
        "question": "How should employees report workplace harassment?",
        "ground_truth": "Employees should report harassment to their HR representative or through the anonymous reporting channel.",
    },
    {
        "question": "What is the remote work policy?",
        "ground_truth": "The remote work policy specifies eligibility criteria and the maximum number of days employees may work from home.",
    },
    {
        "question": "What are the notice period requirements for resignation?",
        "ground_truth": "Notice periods vary by seniority level and are specified in the employment contract and HR policy.",
    },
    {
        "question": "How is overtime compensated?",
        "ground_truth": "Overtime is compensated either as time-off-in-lieu or at a premium rate as defined in the HR policy.",
    },
    {
        "question": "What training and development benefits are available?",
        "ground_truth": "Employees are entitled to a training budget and may request external courses through the HR department.",
    },
    {
        "question": "What is the maternity/paternity leave policy?",
        "ground_truth": "The parental leave policy specifies the duration and pay entitlements for primary and secondary caregivers.",
    },
]

RESULTS_FILE = Path("eval/results.jsonl")
RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def run_evaluation() -> None:
    questions, answers, contexts, ground_truths = [], [], [], []

    print(f"Running RAGAS evaluation on {len(EVAL_SET)} questions …")
    for item in EVAL_SET:
        q = item["question"]
        gt = item["ground_truth"]
        try:
            result = run_rag(q)
            ans = result["answer"]
            ctx = [s["text"] for s in result["sources"]]
        except Exception as exc:
            print(f"  ⚠  Skipping '{q[:60]}…': {exc}")
            continue

        questions.append(q)
        answers.append(ans)
        contexts.append(ctx)
        ground_truths.append(gt)

    if not questions:
        print("No questions answered — is the FAISS index populated?")
        return

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
    )

    scores = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision],
    )

    record: Dict[str, Any] = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "n_questions": len(questions),
        "faithfulness": scores["faithfulness"],
        "answer_relevancy": scores["answer_relevancy"],
        "context_precision": scores["context_precision"],
    }

    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    print("\n── RAGAS Results ─────────────────────────────────")
    print(f"  Faithfulness       : {record['faithfulness']:.4f}")
    print(f"  Answer Relevancy   : {record['answer_relevancy']:.4f}")
    print(f"  Context Precision  : {record['context_precision']:.4f}")
    print(f"\nResults appended to {RESULTS_FILE}")


if __name__ == "__main__":
    run_evaluation()
