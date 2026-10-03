# Manually reviewed experiment dataset v1

This folder contains new experiment inputs. 

Removed question IDs: Q0485, Q0488, Q0491, Q0494, Q0497, Q0503, Q0515, Q0521, Q0527, Q0529. The first nine ask whether a named module has a module examination; a separate study-plan chunk independently supports the same answer as the existing gold chunk. Q0529 was removed because the formal appendix and exemplary study plan give conflicting SWS values and the question does not specify which source to use.

The folder contains the remaining question set, `gold_with_split.jsonl`, and the three split-ID files. Shared chunks are in `data/frozen/PO_25_CL_chunks.jsonl`. These are the inputs of `configs/manual_review_v1.json`.

The development, validation, and test assignments use a seeded random split at the individual-question level (seed 42; 60/20/20). No question groups or answer-level stratification are used, so questions with identical gold evidence may appear in different splits.
