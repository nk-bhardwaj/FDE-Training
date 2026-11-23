====================================================================================================
RAG ANSWER EVALUATION
====================================================================================================
Provider: groq  |  Top-K: 5
Live pipeline evaluation requiring configured Gemini, Neon, and LLM credentials.
----------------------------------------------------------------------------------------------------
Loaded 7 stored chunks from database.

Evaluating 10 questions...

2026-11-23 20:09:24,931 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:09:24,940 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=591.78 task_type=RETRIEVAL_QUERY dimensions=768 text_length=48
2026-11-23 20:09:30,827 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5886.70 results=7 limit=20 filtered=False
2026-11-23 20:09:36,691 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5863.21 results=7 limit=20 filtered=False
2026-11-23 20:09:36,692 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=c992a4cb provider=groq results=7 pool=10 latency_ms=12528.09
2026-11-23 20:09:36,696 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=4 top_k=5 latency_ms=3.00
2026-11-23 20:09:36,696 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=c992a4cb provider=groq enabled=True results_in=7 results_out=5 latency_ms=3.65
2026-11-23 20:09:36,857 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1694 max_tokens=2000 latency_ms=160.19
2026-11-23 20:09:36,858 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=c992a4cb provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=160.50
2026-11-23 20:09:38,169 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:09:38,177 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1264.67 input_tokens=2205 output_tokens=239 total_tokens=2444
2026-11-23 20:09:38,178 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=4 context_tokens=1694 latency_ms=1264.67
2026-11-23 20:09:38,178 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=c992a4cb provider=groq latency_ms=1320.20 attempts=1 context_chunks=4 context_tokens=1694 abstained=False
2026-11-23 20:09:38,662 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:09:38,666 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=487.22 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-23 20:09:44,312 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5645.47 results=7 limit=20 filtered=False
2026-11-23 20:09:50,238 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5925.35 results=7 limit=20 filtered=False
2026-11-23 20:09:50,239 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=6e3b3f8b provider=groq results=7 pool=10 latency_ms=12060.43
2026-11-23 20:09:50,243 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=4 top_k=5 latency_ms=3.14
2026-11-23 20:09:50,244 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=6e3b3f8b provider=groq enabled=True results_in=7 results_out=5 latency_ms=3.81
2026-11-23 20:09:50,246 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1858 max_tokens=2000 latency_ms=1.29
2026-11-23 20:09:50,246 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=6e3b3f8b provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.63
2026-11-23 20:09:51,399 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:09:51,402 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1155.43 input_tokens=2365 output_tokens=337 total_tokens=2702
2026-11-23 20:09:51,403 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=2 context_chunks=4 context_tokens=1858 latency_ms=1155.43
2026-11-23 20:09:51,403 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=6e3b3f8b provider=groq latency_ms=1156.97 attempts=1 context_chunks=4 context_tokens=1858 abstained=False
2026-11-23 20:09:52,277 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:09:52,280 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=875.66 task_type=RETRIEVAL_QUERY dimensions=768 text_length=54
2026-11-23 20:09:57,932 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5651.74 results=7 limit=20 filtered=False
2026-11-23 20:10:03,761 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5828.66 results=7 limit=20 filtered=False
2026-11-23 20:10:03,762 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=89c4fe5b provider=groq results=7 pool=10 latency_ms=12358.42
2026-11-23 20:10:03,766 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=5 top_k=5 latency_ms=2.97
2026-11-23 20:10:03,767 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=89c4fe5b provider=groq enabled=True results_in=7 results_out=5 latency_ms=3.60
2026-11-23 20:10:03,769 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1858 max_tokens=2000 latency_ms=1.42
2026-11-23 20:10:03,769 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=89c4fe5b provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.78
2026-11-23 20:10:05,090 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:10:05,093 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1323.84 input_tokens=2365 output_tokens=351 total_tokens=2716
2026-11-23 20:10:05,094 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=2 context_chunks=4 context_tokens=1858 latency_ms=1323.84
2026-11-23 20:10:05,095 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=89c4fe5b provider=groq latency_ms=1325.36 attempts=1 context_chunks=4 context_tokens=1858 abstained=False
2026-11-23 20:10:05,610 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:10:05,615 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=519.82 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-23 20:10:11,468 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5852.67 results=7 limit=20 filtered=False
2026-11-23 20:10:17,230 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5761.71 results=7 limit=20 filtered=False
2026-11-23 20:10:17,233 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=2467574a provider=groq results=7 pool=10 latency_ms=12137.54
2026-11-23 20:10:17,236 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=3 top_k=5 latency_ms=2.86
2026-11-23 20:10:17,237 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=2467574a provider=groq enabled=True results_in=7 results_out=5 latency_ms=3.50
2026-11-23 20:10:17,242 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1693 max_tokens=2000 latency_ms=4.38
2026-11-23 20:10:17,243 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=2467574a provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=5.17
2026-11-23 20:10:20,572 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:10:20,574 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=3330.70 input_tokens=2196 output_tokens=426 total_tokens=2622
2026-11-23 20:10:20,575 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=4 context_tokens=1693 latency_ms=3330.70
2026-11-23 20:10:20,575 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=2467574a provider=groq latency_ms=3331.88 attempts=1 context_chunks=4 context_tokens=1693 abstained=False
2026-11-23 20:10:21,080 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:10:21,085 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=509.64 task_type=RETRIEVAL_QUERY dimensions=768 text_length=42
2026-11-23 20:10:26,778 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5692.00 results=7 limit=20 filtered=False
2026-11-23 20:10:32,229 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5449.95 results=3 limit=20 filtered=False
2026-11-23 20:10:32,230 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=5ee7e804 provider=groq results=7 pool=10 latency_ms=11654.13
2026-11-23 20:10:32,234 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=3 top_k=5 latency_ms=3.15
2026-11-23 20:10:32,235 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=5ee7e804 provider=groq enabled=True results_in=7 results_out=5 latency_ms=4.29
2026-11-23 20:10:32,237 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1859 max_tokens=2000 latency_ms=1.36
2026-11-23 20:10:32,238 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=5ee7e804 provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.82
2026-11-23 20:10:33,814 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:10:33,816 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1578.05 input_tokens=2369 output_tokens=351 total_tokens=2720
2026-11-23 20:10:33,816 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=4 context_tokens=1859 latency_ms=1578.05
2026-11-23 20:10:33,817 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=5ee7e804 provider=groq latency_ms=1578.65 attempts=1 context_chunks=4 context_tokens=1859 abstained=False
2026-11-23 20:10:34,314 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:10:34,320 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=503.28 task_type=RETRIEVAL_QUERY dimensions=768 text_length=32
2026-11-23 20:10:40,057 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5736.44 results=7 limit=20 filtered=False
2026-11-23 20:10:45,709 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5651.41 results=7 limit=20 filtered=False
2026-11-23 20:10:45,710 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=bd693606 provider=groq results=7 pool=10 latency_ms=11892.79
2026-11-23 20:10:45,711 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=3 top_k=5 latency_ms=1.14
2026-11-23 20:10:45,711 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=bd693606 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.43
2026-11-23 20:10:45,713 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=5 duplicates_removed=0 truncated=False total_tokens=1767 max_tokens=2000 latency_ms=0.92
2026-11-23 20:10:45,713 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=bd693606 provider=groq candidates_in=5 included=5 duplicates_removed=0 truncated=False latency_ms=1.22
2026-11-23 20:10:47,134 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:10:47,137 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1423.60 input_tokens=2290 output_tokens=368 total_tokens=2658
2026-11-23 20:10:47,138 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=5 context_tokens=1767 latency_ms=1423.60
2026-11-23 20:10:47,138 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=bd693606 provider=groq latency_ms=1425.09 attempts=1 context_chunks=5 context_tokens=1767 abstained=False
2026-11-23 20:10:48,082 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:10:48,088 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=948.47 task_type=RETRIEVAL_QUERY dimensions=768 text_length=40
2026-11-23 20:10:53,931 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5843.27 results=7 limit=20 filtered=False
2026-11-23 20:10:59,904 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5972.68 results=7 limit=20 filtered=False
2026-11-23 20:10:59,905 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=21711d39 provider=groq results=7 pool=10 latency_ms=12765.68
2026-11-23 20:10:59,906 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=3 top_k=5 latency_ms=0.98
2026-11-23 20:10:59,906 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=21711d39 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.45
2026-11-23 20:10:59,908 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=5 duplicates_removed=0 truncated=False total_tokens=1767 max_tokens=2000 latency_ms=1.23
2026-11-23 20:10:59,908 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=21711d39 provider=groq candidates_in=5 included=5 duplicates_removed=0 truncated=False latency_ms=1.78
2026-11-23 20:11:01,095 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:11:01,100 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1191.45 input_tokens=2297 output_tokens=304 total_tokens=2601
2026-11-23 20:11:01,104 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=2 context_chunks=5 context_tokens=1767 latency_ms=1191.45
2026-11-23 20:11:01,136 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=21711d39 provider=groq latency_ms=1227.22 attempts=1 context_chunks=5 context_tokens=1767 abstained=False
2026-11-23 20:11:01,682 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:11:01,689 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=547.17 task_type=RETRIEVAL_QUERY dimensions=768 text_length=55
2026-11-23 20:11:07,557 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5862.44 results=7 limit=20 filtered=False
2026-11-23 20:11:13,425 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5867.08 results=7 limit=20 filtered=False
2026-11-23 20:11:13,426 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=1ad18d46 provider=groq results=7 pool=10 latency_ms=12284.27
2026-11-23 20:11:13,427 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=6 top_k=5 latency_ms=0.90
2026-11-23 20:11:13,427 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=1ad18d46 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.21
2026-11-23 20:11:13,428 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=5 duplicates_removed=0 truncated=False total_tokens=1932 max_tokens=2000 latency_ms=0.94
2026-11-23 20:11:13,429 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=1ad18d46 provider=groq candidates_in=5 included=5 duplicates_removed=0 truncated=False latency_ms=1.16
2026-11-23 20:11:13,600 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
2026-11-23 20:11:13,602 INFO [groq._base_client] Retrying request to /openai/v1/chat/completions in 2.000000 seconds
2026-11-23 20:11:17,810 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:11:17,813 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=4384.35 input_tokens=2462 output_tokens=174 total_tokens=2636
2026-11-23 20:11:17,814 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=5 context_tokens=1932 latency_ms=4384.35
2026-11-23 20:11:17,815 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=1ad18d46 provider=groq latency_ms=4385.71 attempts=1 context_chunks=5 context_tokens=1932 abstained=False
2026-11-23 20:11:18,310 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:11:18,317 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=501.07 task_type=RETRIEVAL_QUERY dimensions=768 text_length=47
2026-11-23 20:11:24,121 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5803.51 results=7 limit=20 filtered=False
2026-11-23 20:11:29,824 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5702.44 results=7 limit=20 filtered=False
2026-11-23 20:11:29,824 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=6fc588d8 provider=groq results=7 pool=10 latency_ms=12008.91
2026-11-23 20:11:29,826 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=5 top_k=5 latency_ms=0.96
2026-11-23 20:11:29,826 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=6fc588d8 provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.24
2026-11-23 20:11:29,827 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1694 max_tokens=2000 latency_ms=1.12
2026-11-23 20:11:29,828 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=6fc588d8 provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.40
2026-11-23 20:11:29,959 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
2026-11-23 20:11:29,960 INFO [groq._base_client] Retrying request to /openai/v1/chat/completions in 1.000000 seconds
2026-11-23 20:11:31,474 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:11:31,477 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=1648.92 input_tokens=2199 output_tokens=89 total_tokens=2288
2026-11-23 20:11:31,478 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=1 context_chunks=4 context_tokens=1694 latency_ms=1648.92
2026-11-23 20:11:31,479 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=6fc588d8 provider=groq latency_ms=1650.41 attempts=1 context_chunks=4 context_tokens=1694 abstained=False
2026-11-23 20:11:31,984 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-23 20:11:31,989 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=509.84 task_type=RETRIEVAL_QUERY dimensions=768 text_length=34
2026-11-23 20:11:37,754 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5764.11 results=7 limit=20 filtered=False
2026-11-23 20:11:43,415 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5660.24 results=7 limit=20 filtered=False
2026-11-23 20:11:43,415 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=retrieval status=success question_sha=7188ec3f provider=groq results=7 pool=10 latency_ms=11935.90
2026-11-23 20:11:43,417 INFO [app.services.reranking_service] service=reranking operation=rerank status=success candidates=7 results=5 query_terms=4 top_k=5 latency_ms=1.15
2026-11-23 20:11:43,417 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=reranking status=success question_sha=7188ec3f provider=groq enabled=True results_in=7 results_out=5 latency_ms=1.85
2026-11-23 20:11:43,419 INFO [app.services.context_engineering_service] service=context_engineering operation=assemble status=success candidates=5 included=4 duplicates_removed=0 truncated=True total_tokens=1693 max_tokens=2000 latency_ms=1.28
2026-11-23 20:11:43,419 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=context_assemble status=success question_sha=7188ec3f provider=groq candidates_in=5 included=4 duplicates_removed=0 truncated=True latency_ms=1.53
2026-11-23 20:11:45,561 INFO [httpx] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2026-11-23 20:11:45,563 INFO [app.services.groq_service] provider=groq model=openai/gpt-oss-120b status=success latency_ms=2143.17 input_tokens=2194 output_tokens=843 total_tokens=3037
2026-11-23 20:11:45,563 INFO [app.services.rag_answer_service] service=rag_answer operation=answer status=success provider=groq model=openai/gpt-oss-120b attempts=1 citations=3 context_chunks=4 context_tokens=1693 latency_ms=2143.17
2026-11-23 20:11:45,564 INFO [app.services.rag_pipeline_service] service=rag_pipeline operation=answer status=success question_sha=7188ec3f provider=groq latency_ms=2144.08 attempts=1 context_chunks=4 context_tokens=1693 abstained=False
 # | question                                      | answer                                 |  cov |  abs |     cit |   prec |  lat(ms)
---------------------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | Customers generally have 30 days from… |    1 |    0 |     1/1 |   1.00 | 14014.17
 2 | What makes a returned unit unsellable?        | A returned unit is considered unsella… |    1 |    0 |     1/2 |   0.50 | 13224.90
 3 | When does Amazon reimburse sellers for retur… | Amazon typically reimburses sellers w… |    1 |    0 |     1/2 |   0.50 | 13691.23
 4 | How do I issue a refund to a customer?        | To issue a refund, first locate the o… |    1 |    0 |     1/1 |   1.00 | 15480.29
 5 | What is an RMA number and when is it used?    | An RMA number (Return Merchandise Aut… |    1 |    0 |     1/1 |   1.00 | 13241.15
 6 | How do I close a return request?              | In the Manage Returns tool, select th… |    1 |    0 |     0/1 |   0.00 | 13321.99
 7 | How do I contact a buyer about a return?      | You can contact the buyer by sending … |    1 |    0 |     1/2 |   0.50 | 14002.37
 8 | Are return labels prepaid for seller-fulfill… | No, by default the return label for s… |    1 |    0 |     0/1 |   0.00 | 16673.77
 9 | How quickly must I respond to a return reque… | You should respond to return requests… |    1 |    0 |     1/1 |   1.00 | 13663.84
10 | How are FBA order returns handled?            | With Fulfilment by Amazon (FBA) order… |    1 |    0 |     1/3 |   0.33 | 14084.66

====================================================================================================
AGGREGATE SUMMARY
====================================================================================================
Provider: groq  |  Top-K: 5  |  Questions: 10
----------------------------------------------------------------------------------------------------
Metric                                   |           Value
----------------------------------------------------------
Evidence phrase coverage rate            |           1.000
Abstention rate                          |           0.000
Mean citation precision                  |           0.583
Fraction with >=1 expected citation      |           0.800
Mean latency (ms)                        |        14139.84
====================================================================================================
NOTE: Evidence phrase coverage is a heuristic, not a measure of factual faithfulness.
====================================================================================================

====================================================================================================
EVALUATION COMPLETE
====================================================================================================