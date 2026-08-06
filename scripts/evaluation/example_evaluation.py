from mapping_evaluator import QAMappingEvaluator


evaluator = QAMappingEvaluator("data/processed/qamappings/qa_mapping_merged.jsonl")
result = evaluator.eval("data/processed/qamappings/qa_mapping_test.jsonl")

summary = result["summary"]

print("Evaluated questions:", summary["evaluated_question_count"])
print("Unanswered questions:", summary["unanswered_question_count"])
print("Coverage:", f'{summary["answer_coverage"]:.1%}')
print("Exact-match rate:", summary["exact_match_rate"])
print("Mean question F1:", summary["mean_question_f1"])
print("Micro F1:", summary["micro_f1"])
print(summary)