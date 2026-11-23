====================================================================================================
RAG ANSWER EVALUATION
====================================================================================================
Provider: groq  |  Top-K: 5
Live pipeline evaluation requiring configured Gemini, Neon, and LLM credentials.
----------------------------------------------------------------------------------------------------
Loaded 7 stored chunks from database.

Evaluating 10 questions...

2026-11-23 21:31:01,284 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:31:01,290 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=962.17 task_type=RETRIEVAL_QUERY dimensions=768 text_length=48
2026-11-23 21:31:07,093 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5802.29 results=7 limit=20 filtered=False
2026-11-23 21:31:15,253 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=8159.33 results=7 limit=20 filtered=False
2026-11-23 21:31:15,253 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=c992a4cb provider=groq results=7 pool=10 latency_ms=15253.90
2026-11-23 21:31:15,255 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=4 top_k=5 latency_ms=0.98
2026-11-23 21:31:15,255 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=c992a4cb provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.28
2026-11-23 21:31:15,444 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1694 max_tokens=2000 latency_ms=188.95
2026-11-23 21:31:15,444 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=c992a4cb provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=189.19
2026-11-23 21:31:16,966 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:31:16,973 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1461.40 input_tokens=2205 output_tokens=287 total_tokens=2492
2026-11-23 21:31:16,974 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=4 context_tokens=1694 latency_ms=1461.40
2026-11-23 21:31:16,974 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=c992a4cb provider=groq latency_ms=1529.36 attempts=1 context_chunks=4 context_tokens=1694 abstained=False
2026-11-23 21:31:17,494 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:31:17,498 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=523.56 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-23 21:31:23,320 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5818.50 results=7 limit=20 filtered=False
2026-11-23 21:31:29,330 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6009.28 results=7 limit=20 filtered=False
2026-11-23 21:31:29,330 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=6e3b3f8b provider=groq results=7 pool=10 latency_ms=12355.94
2026-11-23 21:31:29,331 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=4 top_k=5 latency_ms=0.96
2026-11-23 21:31:29,332 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=6e3b3f8b provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.20
2026-11-23 21:31:29,333 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1858 max_tokens=2000 latency_ms=1.08
2026-11-23 21:31:29,333 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=6e3b3f8b provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.35
2026-11-23 21:31:31,040 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:31:31,042 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1708.06 input_tokens=2365 output_tokens=385 total_tokens=2750
2026-11-23 21:31:31,042 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=2 context_chunks=4 context_tokens=1858 latency_ms=1708.06
2026-11-23 21:31:31,042 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=6e3b3f8b provider=groq latency_ms=1708.98 attempts=1 context_chunks=4 context_tokens=1858 abstained=False
2026-11-23 21:31:31,901 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:31:31,903 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=860.51 task_type=RETRIEVAL_QUERY dimensions=768 text_length=54
2026-11-23 21:31:37,588 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5684.70 results=7 limit=20 filtered=False
2026-11-23 21:31:43,464 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5875.43 results=7 limit=20 filtered=False
2026-11-23 21:31:43,464 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=89c4fe5b provider=groq results=7 pool=10 latency_ms=12421.66
2026-11-23 21:31:43,466 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=5 top_k=5 latency_ms=0.95
2026-11-23 21:31:43,466 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=89c4fe5b provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.14
2026-11-23 21:31:43,467 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1858 max_tokens=2000 latency_ms=1.19
2026-11-23 21:31:43,468 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=89c4fe5b provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.56
2026-11-23 21:31:44,631 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:31:44,632 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1163.84 input_tokens=2365 output_tokens=251 total_tokens=2616
2026-11-23 21:31:44,633 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=2 context_chunks=4 context_tokens=1858 latency_ms=1163.84
2026-11-23 21:31:44,633 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=89c4fe5b provider=groq latency_ms=1164.47 attempts=1 context_chunks=4 context_tokens=1858 abstained=False
2026-11-23 21:31:45,459 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:31:45,461 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=828.11 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-23 21:31:51,480 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6018.14 results=7 limit=20 filtered=False
2026-11-23 21:31:57,303 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5822.53 results=7 limit=20 filtered=False
2026-11-23 21:31:57,304 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=2467574a provider=groq results=7 pool=10 latency_ms=12670.28
2026-11-23 21:31:57,305 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=3 top_k=5 latency_ms=1.00
2026-11-23 21:31:57,305 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=2467574a provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.22
2026-11-23 21:31:57,306 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1693 max_tokens=2000 latency_ms=1.12
2026-11-23 21:31:57,306 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=2467574a provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.31
2026-11-23 21:31:58,639 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:31:58,641 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1334.00 input_tokens=2196 output_tokens=348 total_tokens=2544
2026-11-23 21:31:58,641 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=4 context_tokens=1693 latency_ms=1334.00
2026-11-23 21:31:58,641 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=2467574a provider=groq latency_ms=1334.51 attempts=1 context_chunks=4 context_tokens=1693 abstained=False
2026-11-23 21:31:59,138 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:31:59,140 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=498.43 task_type=RETRIEVAL_QUERY dimensions=768 text_length=42
2026-11-23 21:32:05,032 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5891.27 results=7 limit=20 filtered=False
2026-11-23 21:32:10,670 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5637.48 results=3 limit=20 filtered=False
2026-11-23 21:32:10,671 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=5ee7e804 provider=groq results=7 pool=10 latency_ms=12029.37
2026-11-23 21:32:10,672 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=3 top_k=5 latency_ms=0.97
2026-11-23 21:32:10,673 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=5ee7e804 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.71
2026-11-23 21:32:10,674 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1859 max_tokens=2000 latency_ms=1.21
2026-11-23 21:32:10,675 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=5ee7e804 provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.55
2026-11-23 21:32:13,640 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:32:13,642 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=2966.21 input_tokens=2369 output_tokens=283 total_tokens=2652
2026-11-23 21:32:13,642 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=4 context_tokens=1859 latency_ms=2966.21
2026-11-23 21:32:13,643 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=5ee7e804 provider=groq latency_ms=2966.97 attempts=1 context_chunks=4 context_tokens=1859 abstained=False
2026-11-23 21:32:14,492 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:32:14,495 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=852.04 task_type=RETRIEVAL_QUERY dimensions=768 text_length=32
2026-11-23 21:32:20,313 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5817.27 results=7 limit=20 filtered=False
2026-11-23 21:32:26,140 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5826.92 results=7 limit=20 filtered=False
2026-11-23 21:32:26,140 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=bd693606 provider=groq results=7 pool=10 latency_ms=12497.49
2026-11-23 21:32:26,142 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=3 top_k=5 latency_ms=0.94
2026-11-23 21:32:26,142 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=bd693606 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.14
2026-11-23 21:32:26,143 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=5 duplicates_removed=0 truncated=False total_tokens=1767 max_tokens=2000 latency_ms=0.93
2026-11-23 21:32:26,143 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=bd693606 provider=groq candidates_in=5 included=5 duplicates_removed=0 truncated=False latency_ms=1.11
2026-11-23 21:32:27,717 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:32:27,718 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1575.00 input_tokens=2290 output_tokens=429 total_tokens=2719
2026-11-23 21:32:27,719 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=2 context_chunks=5 context_tokens=1767 latency_ms=1575.00
2026-11-23 21:32:27,719 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=bd693606 provider=groq latency_ms=1575.55 attempts=1 context_chunks=5 context_tokens=1767 abstained=False
2026-11-23 21:32:28,223 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:32:28,226 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=506.81 task_type=RETRIEVAL_QUERY dimensions=768 text_length=40
2026-11-23 21:32:34,023 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5791.18 results=7 limit=20 filtered=False
2026-11-23 21:32:39,716 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5692.20 results=7 limit=20 filtered=False
2026-11-23 21:32:39,716 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=21711d39 provider=groq results=7 pool=10 latency_ms=11997.32
2026-11-23 21:32:39,718 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=3 top_k=5 latency_ms=0.92
2026-11-23 21:32:39,718 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=21711d39 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.13
2026-11-23 21:32:39,719 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=5 duplicates_removed=0 truncated=False total_tokens=1767 max_tokens=2000 latency_ms=0.94
2026-11-23 21:32:39,719 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=21711d39 provider=groq candidates_in=5 included=5 duplicates_removed=0 truncated=False latency_ms=1.15
2026-11-23 21:32:41,345 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:32:41,347 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1627.47 input_tokens=2297 output_tokens=356 total_tokens=2653
2026-11-23 21:32:41,347 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=2 context_chunks=5 context_tokens=1767 latency_ms=1627.47
2026-11-23 21:32:41,347 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=21711d39 provider=groq latency_ms=1627.93 attempts=1 context_chunks=5 context_tokens=1767 abstained=False
2026-11-23 21:32:42,206 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:32:42,209 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=861.89 task_type=RETRIEVAL_QUERY dimensions=768 text_length=55
2026-11-23 21:32:48,053 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5843.78 results=7 limit=20 filtered=False
2026-11-23 21:32:53,920 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5866.69 results=7 limit=20 filtered=False
2026-11-23 21:32:53,921 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=1ad18d46 provider=groq results=7 pool=10 latency_ms=12573.36
2026-11-23 21:32:53,922 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=6 top_k=5 latency_ms=0.93
2026-11-23 21:32:53,922 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=1ad18d46 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.15
2026-11-23 21:32:53,923 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=5 duplicates_removed=0 truncated=False total_tokens=1932 max_tokens=2000 latency_ms=1.00
2026-11-23 21:32:53,924 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=1ad18d46 provider=groq candidates_in=5 included=5 duplicates_removed=0 truncated=False latency_ms=1.21
2026-11-23 21:32:54,903 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:32:54,905 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=980.76 input_tokens=2462 output_tokens=184 total_tokens=2646
2026-11-23 21:32:54,905 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=5 context_tokens=1932 latency_ms=980.76
2026-11-23 21:32:54,905 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=1ad18d46 provider=groq latency_ms=981.52 attempts=1 context_chunks=5 context_tokens=1932 abstained=False
2026-11-23 21:32:55,740 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:32:55,742 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=836.37 task_type=RETRIEVAL_QUERY dimensions=768 text_length=47
2026-11-23 21:33:01,671 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5928.20 results=7 limit=20 filtered=False
2026-11-23 21:33:07,392 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5720.75 results=7 limit=20 filtered=False
2026-11-23 21:33:07,392 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=6fc588d8 provider=groq results=7 pool=10 latency_ms=12486.50
2026-11-23 21:33:07,393 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=5 top_k=5 latency_ms=0.95
2026-11-23 21:33:07,394 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=6fc588d8 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.22
2026-11-23 21:33:07,395 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1694 max_tokens=2000 latency_ms=1.13
2026-11-23 21:33:07,395 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=6fc588d8 provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.41
2026-11-23 21:33:07,514 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
2026-11-23 21:33:07,515 INFO [groq._base_client] Retrying request to /openai/v1/chat/completions in 5.000000 seconds
2026-11-23 21:33:13,408 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:33:13,409 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=6013.02 input_tokens=2199 output_tokens=161 total_tokens=2360
2026-11-23 21:33:13,409 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=4 context_tokens=1694 latency_ms=6013.02
2026-11-23 21:33:13,409 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=6fc588d8 provider=groq latency_ms=6013.79 attempts=1 context_chunks=4 context_tokens=1694 abstained=False
2026-11-23 21:33:14,236 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 21:33:14,241 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=830.09 task_type=RETRIEVAL_QUERY dimensions=768 text_length=34
2026-11-23 21:33:20,130 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5885.12 results=7 limit=20 filtered=False
2026-11-23 21:33:25,942 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5811.72 results=7 limit=20 filtered=False
2026-11-23 21:33:25,970 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=7188ec3f provider=groq results=7 pool=10 latency_ms=12559.87
2026-11-23 21:33:25,982 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=4 top_k=5 latency_ms=1.96
2026-11-23 21:33:25,984 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=7188ec3f provider=groq enabled=True results_in=7 results_out=5 latency_ms=3.21
2026-11-23 21:33:25,995 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1693 max_tokens=2000 latency_ms=2.71
2026-11-23 21:33:25,995 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=7188ec3f provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=3.31
2026-11-23 21:33:26,195 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
2026-11-23 21:33:26,196 INFO [groq._base_client] Retrying request to /openai/v1/chat/completions in 4.000000 seconds
2026-11-23 21:33:31,913 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 21:33:31,915 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=5912.61 input_tokens=2194 output_tokens=635 total_tokens=2829
2026-11-23 21:33:31,915 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=3 context_chunks=4 context_tokens=1693 latency_ms=5912.61
2026-11-23 21:33:31,916 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=7188ec3f provider=groq latency_ms=5913.76 attempts=1 context_chunks=4 context_tokens=1693 abstained=False
 # | question                                      | answer                                 |  cov |  abs |     cit |   prec |  lat(ms)
---------------------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | Customers typically have 30 days from… |    1 |    0 |     1/1 |   1.00 | 16974.74
 2 | What makes a returned unit unsellable?        | A returned unit is deemed unsellable … |    1 |    0 |     2/2 |   1.00 | 14068.62
 3 | When does Amazon reimburse sellers for retur… | Amazon reimburses sellers for eligibl… |    1 |    0 |     2/2 |   1.00 | 13590.37
 4 | How do I issue a refund to a customer?        | To issue a refund, locate the order y… |    1 |    0 |     1/1 |   1.00 | 14008.08
 5 | What is an RMA number and when is it used?    | An RMA number is a Return Merchandise… |    1 |    0 |     1/1 |   1.00 | 15001.51
 6 | How do I close a return request?              | In the Manage Returns tool, select th… |    1 |    0 |     2/2 |   1.00 | 14076.00
 7 | How do I contact a buyer about a return?      | You can contact the buyer by using th… |    1 |    0 |     1/2 |   0.50 | 13628.27
 8 | Are return labels prepaid for seller-fulfill… | No, by default return labels for sell… |    1 |    0 |     1/1 |   1.00 | 13558.24
 9 | How quickly must I respond to a return reque… | You should respond to return requests… |    1 |    0 |     1/1 |   1.00 | 18504.69
10 | How are FBA order returns handled?            | For Fulfilment by Amazon (FBA) orders… |    1 |    0 |     1/3 |   0.33 | 18505.64

====================================================================================================
AGGREGATE SUMMARY
====================================================================================================
Provider: groq  |  Top-K: 5  |  Questions: 10
----------------------------------------------------------------------------------------------------
Metric                                   |           Value
----------------------------------------------------------
Evidence phrase coverage rate            |           1.000
Abstention rate                          |           0.000
Mean citation precision                  |           0.883
Fraction with >=1 expected citation      |           1.000
Mean latency (ms)                        |        15191.62
====================================================================================================
NOTE: Evidence phrase coverage is a heuristic, not a measure of factual faithfulness.
====================================================================================================

====================================================================================================
EVALUATION COMPLETE
====================================================================================================