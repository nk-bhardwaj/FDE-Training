====================================================================================================
RAG RETRIEVAL EVALUATION
====================================================================================================
Documents: 3  |  Total chunks: 7  |  Config: chunk_size=500, overlap=75  |  Top-K: 3
Sources: ['amazon_fba_return_policy', 'amazon_process_return_requests', 'amazon_seller_fulfilled_returns']
Max chunk index per source: {'amazon_fba_return_policy': 3, 'amazon_process_return_requests': 1, 'amazon_seller_fulfilled_returns': 0}
----------------------------------------------------------------------------------------------------

Evaluating 10 questions...

Running semantic_search_chunks...
2026-11-21 00:51:30,672 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:51:30,678 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=583.07 task_type=RETRIEVAL_QUERY dimensions=768 text_length=48
2026-11-21 00:51:37,431 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6752.16 results=3 limit=3 filtered=False
2026-11-21 00:51:38,281 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:51:38,283 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=851.28 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 00:51:43,936 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5652.37 results=3 limit=3 filtered=False
2026-11-21 00:51:44,442 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:51:44,445 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=508.03 task_type=RETRIEVAL_QUERY dimensions=768 text_length=54
2026-11-21 00:51:52,418 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=7973.26 results=3 limit=3 filtered=False
2026-11-21 00:51:52,914 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:51:52,916 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=497.24 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 00:51:58,713 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5796.17 results=3 limit=3 filtered=False
2026-11-21 00:51:59,235 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:51:59,240 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=526.38 task_type=RETRIEVAL_QUERY dimensions=768 text_length=42
2026-11-21 00:52:04,681 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5440.54 results=3 limit=3 filtered=False
2026-11-21 00:52:05,180 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:52:05,186 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=503.69 task_type=RETRIEVAL_QUERY dimensions=768 text_length=32
2026-11-21 00:52:10,714 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5527.29 results=3 limit=3 filtered=False
2026-11-21 00:52:11,605 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:52:11,609 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=894.79 task_type=RETRIEVAL_QUERY dimensions=768 text_length=40
2026-11-21 00:52:17,381 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5770.90 results=3 limit=3 filtered=False
2026-11-21 00:52:17,873 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:52:17,876 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=495.09 task_type=RETRIEVAL_QUERY dimensions=768 text_length=55
2026-11-21 00:52:23,376 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5499.15 results=3 limit=3 filtered=False
2026-11-21 00:52:24,185 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:52:24,187 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=810.93 task_type=RETRIEVAL_QUERY dimensions=768 text_length=47
2026-11-21 00:52:29,896 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5708.65 results=3 limit=3 filtered=False
2026-11-21 00:52:30,383 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:52:30,389 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=492.09 task_type=RETRIEVAL_QUERY dimensions=768 text_length=34
2026-11-21 00:52:35,923 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5533.59 results=3 limit=3 filtered=False
Done.

Running keyword_search_chunks...
2026-11-21 00:52:41,485 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5562.00 results=3 limit=3 filtered=False
2026-11-21 00:52:47,103 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5617.45 results=3 limit=3 filtered=False
2026-11-21 00:52:52,674 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5570.00 results=3 limit=3 filtered=False
2026-11-21 00:52:58,580 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5905.20 results=3 limit=3 filtered=False
2026-11-21 00:53:04,217 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5636.76 results=3 limit=3 filtered=False
2026-11-21 00:53:10,021 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5801.83 results=3 limit=3 filtered=False
2026-11-21 00:53:15,603 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5581.82 results=3 limit=3 filtered=False
2026-11-21 00:53:21,210 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5606.27 results=3 limit=3 filtered=False
2026-11-21 00:53:26,814 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5603.39 results=3 limit=3 filtered=False
2026-11-21 00:53:32,453 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5637.77 results=3 limit=3 filtered=False
Done.

Running hybrid_search_chunks...
2026-11-21 00:53:32,949 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:53:32,952 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=497.35 task_type=RETRIEVAL_QUERY dimensions=768 text_length=48
2026-11-21 00:53:38,944 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5992.23 results=6 limit=6 filtered=False
2026-11-21 00:53:44,817 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5872.35 results=6 limit=6 filtered=False
2026-11-21 00:53:45,318 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:53:45,322 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=504.70 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 00:53:51,218 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5895.32 results=6 limit=6 filtered=False
2026-11-21 00:53:57,069 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5849.98 results=6 limit=6 filtered=False
2026-11-21 00:53:57,886 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:53:57,889 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=818.59 task_type=RETRIEVAL_QUERY dimensions=768 text_length=54
2026-11-21 00:54:03,823 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5934.11 results=6 limit=6 filtered=False
2026-11-21 00:54:09,718 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5894.60 results=6 limit=6 filtered=False
2026-11-21 00:54:10,200 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:54:10,208 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=488.72 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 00:54:16,405 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6196.85 results=6 limit=6 filtered=False
2026-11-21 00:54:22,371 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5964.85 results=6 limit=6 filtered=False
2026-11-21 00:54:22,863 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:54:22,868 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=495.62 task_type=RETRIEVAL_QUERY dimensions=768 text_length=42
2026-11-21 00:54:28,764 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5896.22 results=6 limit=6 filtered=False
2026-11-21 00:54:34,503 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5737.72 results=3 limit=6 filtered=False
2026-11-21 00:54:35,969 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:54:35,976 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=1469.91 task_type=RETRIEVAL_QUERY dimensions=768 text_length=32
2026-11-21 00:54:41,907 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5928.46 results=6 limit=6 filtered=False
2026-11-21 00:54:47,899 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5990.77 results=6 limit=6 filtered=False
2026-11-21 00:54:48,391 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:54:48,396 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=496.05 task_type=RETRIEVAL_QUERY dimensions=768 text_length=40
2026-11-21 00:54:54,500 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6103.25 results=6 limit=6 filtered=False
2026-11-21 00:55:00,428 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5927.99 results=6 limit=6 filtered=False
2026-11-21 00:55:00,919 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:55:00,921 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=492.12 task_type=RETRIEVAL_QUERY dimensions=768 text_length=55
2026-11-21 00:55:06,796 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5874.91 results=6 limit=6 filtered=False
2026-11-21 00:55:12,956 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6159.72 results=6 limit=6 filtered=False
2026-11-21 00:55:13,450 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:55:13,455 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=498.37 task_type=RETRIEVAL_QUERY dimensions=768 text_length=47
2026-11-21 00:55:19,404 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5947.78 results=6 limit=6 filtered=False
2026-11-21 00:55:25,149 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5745.03 results=6 limit=6 filtered=False
2026-11-21 00:55:25,982 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 00:55:25,984 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=834.75 task_type=RETRIEVAL_QUERY dimensions=768 text_length=34
2026-11-21 00:55:31,917 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5932.27 results=6 limit=6 filtered=False
2026-11-21 00:55:37,924 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6005.99 results=6 limit=6 filtered=False
Done.

 # | question                                      | retrieved (src,idx)            |   P@3 |   R@3 |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,1), (… |  0.67 |  1.00 |  1.00 |      7543.19
 2 | What makes a returned unit unsellable?        | (amazon_…,0), (amazon_…,1), (… |  0.67 |  1.00 |  1.00 |      6504.88
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  0.50 |      8482.50
 4 | How do I issue a refund to a customer?        | (amazon_…,2), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      6294.58
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      5968.14
 6 | How do I close a return request?              | (amazon_…,1), (amazon_…,0), (… |  0.67 |  1.00 |  1.00 |      6032.37
 7 | How do I contact a buyer about a return?      | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  0.33 |      6666.72
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      5994.87
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      6520.21
10 | How are FBA order returns handled?            | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  0.50 |      6026.75

 # | question                                      | retrieved (src,idx)            |   P@3 |   R@3 |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,1), (… |  0.67 |  1.00 |  1.00 |      5562.48
 2 | What makes a returned unit unsellable?        | (amazon_…,1), (amazon_…,0), (… |  0.67 |  1.00 |  1.00 |      5617.85
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,2), (… |  0.33 |  1.00 |  0.33 |      5570.79
 4 | How do I issue a refund to a customer?        | (amazon_…,0), (amazon_…,1), (… |  0.00 |  0.00 |  0.00 |      5906.02
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      5638.35
 6 | How do I close a return request?              | (amazon_…,0), (amazon_…,1), (… |  0.67 |  1.00 |  1.00 |      5802.22
 7 | How do I contact a buyer about a return?      | (amazon_…,1), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      5582.34
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      5607.07
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      5604.37
10 | How are FBA order returns handled?            | (amazon_…,2), (amazon_…,0), (… |  0.33 |  1.00 |  0.50 |      5638.65

 # | question                                      | retrieved (src,idx)            |   P@3 |   R@3 |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,1), (… |  0.67 |  1.00 |  1.00 |     12363.10
 2 | What makes a returned unit unsellable?        | (amazon_…,0), (amazon_…,1), (… |  0.67 |  1.00 |  1.00 |     12252.62
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  0.50 |     12649.17
 4 | How do I issue a refund to a customer?        | (amazon_…,2), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |     12652.61
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |     12133.77
 6 | How do I close a return request?              | (amazon_…,1), (amazon_…,0), (… |  0.67 |  1.00 |  1.00 |     13394.08
 7 | How do I contact a buyer about a return?      | (amazon_…,1), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |     12529.03
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |     12527.85
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |     12192.89
10 | How are FBA order returns handled?            | (amazon_…,0), (amazon_…,2), (… |  0.33 |  1.00 |  0.33 |     12774.66

====================================================================================================
AGGREGATE SUMMARY
====================================================================================================
Strategy           |  Mean P@3 |  Mean R@3 |     MRR |  Mean Latency (ms)
-------------------------------------------------------------------------
semantic           |     0.433 |     1.000 |   0.833 |            6603.42
keyword            |     0.400 |     0.900 |   0.783 |            5653.02
hybrid             |     0.433 |     1.000 |   0.883 |           12546.98

====================================================================================================
PER-QUERY DETAILS
====================================================================================================

--- semantic ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 2)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=7543.19 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 2)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=6504.88 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@3=0.333 R@3=1.000 RR=0.500 lat=8482.50 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 2)]
    Retrieved: [('amazon_fba_return_policy', 2), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 3)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=6294.58 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 0)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=5968.14 ms
  Q6: How do I close a return request?
    Expected: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=6032.37 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1)]
    P@3=0.333 R@3=1.000 RR=0.333 lat=6666.72 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=5994.87 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=6520.21 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 2)]
    P@3=0.333 R@3=1.000 RR=0.500 lat=6026.75 ms

--- keyword ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=5562.48 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 2)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=5617.85 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 2), ('amazon_fba_return_policy', 1)]
    P@3=0.333 R@3=1.000 RR=0.333 lat=5570.79 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 2)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_process_return_requests', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@3=0.000 R@3=0.000 RR=0.000 lat=5906.02 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=5638.35 ms
  Q6: How do I close a return request?
    Expected: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1), ('amazon_fba_return_policy', 2)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=5802.22 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 2)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=5582.34 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=5607.07 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=5604.37 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_fba_return_policy', 2), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 0)]
    P@3=0.333 R@3=1.000 RR=0.500 lat=5638.65 ms

--- hybrid ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=12363.10 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 2)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=12252.62 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 2)]
    P@3=0.333 R@3=1.000 RR=0.500 lat=12649.17 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 2)]
    Retrieved: [('amazon_fba_return_policy', 2), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 0)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=12652.61 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=12133.77 ms
  Q6: How do I close a return request?
    Expected: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0)]
    P@3=0.667 R@3=1.000 RR=1.000 lat=13394.08 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=12529.03 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=12527.85 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    P@3=0.333 R@3=1.000 RR=1.000 lat=12192.89 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 2), ('amazon_seller_fulfilled_returns', 0)]
    P@3=0.333 R@3=1.000 RR=0.333 lat=12774.66 ms

====================================================================================================
EVALUATION COMPLETE
====================================================================================================








====================================================================================================
RAG RETRIEVAL EVALUATION
====================================================================================================
Documents: 3  |  Total chunks: 12  |  Config: chunk_size=300, overlap=50  |  Top-K: 3
Sources: ['amazon_fba_return_policy', 'amazon_process_return_requests', 'amazon_seller_fulfilled_returns']
----------------------------------------------------------------------------------------------------

Evaluating 10 questions...

Running semantic_search_chunks...
2026-11-21 01:36:15,515 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:36:15,522 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=555.36 task_type=RETRIEVAL_QUERY dimensions=768 text_length=48
2026-11-21 01:36:22,573 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=7050.21 results=3 limit=3 filtered=False
2026-11-21 01:36:23,363 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:36:23,369 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=796.24 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 01:36:28,806 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5435.95 results=3 limit=3 filtered=False
2026-11-21 01:36:29,627 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:36:29,632 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=826.32 task_type=RETRIEVAL_QUERY dimensions=768 text_length=54
2026-11-21 01:36:35,266 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5632.81 results=3 limit=3 filtered=False
2026-11-21 01:36:36,093 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:36:36,097 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=826.50 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 01:36:41,663 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5564.66 results=3 limit=3 filtered=False
2026-11-21 01:36:42,208 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:36:42,211 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=547.92 task_type=RETRIEVAL_QUERY dimensions=768 text_length=42
2026-11-21 01:36:47,859 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5647.93 results=3 limit=3 filtered=False
2026-11-21 01:36:48,713 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:36:48,715 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=832.84 task_type=RETRIEVAL_QUERY dimensions=768 text_length=32
2026-11-21 01:36:55,533 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6817.65 results=3 limit=3 filtered=False
2026-11-21 01:36:56,034 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:36:56,040 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=506.16 task_type=RETRIEVAL_QUERY dimensions=768 text_length=40
2026-11-21 01:37:01,959 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5918.97 results=3 limit=3 filtered=False
2026-11-21 01:37:02,434 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:37:02,436 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=475.96 task_type=RETRIEVAL_QUERY dimensions=768 text_length=55
2026-11-21 01:37:08,131 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5694.47 results=3 limit=3 filtered=False
2026-11-21 01:37:08,610 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:37:08,615 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=483.29 task_type=RETRIEVAL_QUERY dimensions=768 text_length=47
2026-11-21 01:37:14,267 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5652.02 results=3 limit=3 filtered=False
2026-11-21 01:37:14,748 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:37:14,753 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=485.17 task_type=RETRIEVAL_QUERY dimensions=768 text_length=34
2026-11-21 01:37:20,604 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5850.23 results=3 limit=3 filtered=False
Done.

Running keyword_search_chunks...
2026-11-21 01:37:26,520 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5914.38 results=3 limit=3 filtered=False
2026-11-21 01:37:32,238 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5717.12 results=3 limit=3 filtered=False
2026-11-21 01:37:38,078 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5839.15 results=3 limit=3 filtered=False
2026-11-21 01:37:43,689 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5610.42 results=3 limit=3 filtered=False
2026-11-21 01:37:49,188 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5497.77 results=3 limit=3 filtered=False
2026-11-21 01:37:54,812 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5623.70 results=3 limit=3 filtered=False
2026-11-21 01:38:00,452 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5640.20 results=3 limit=3 filtered=False
2026-11-21 01:38:05,900 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5446.96 results=3 limit=3 filtered=False
2026-11-21 01:38:11,711 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5809.89 results=3 limit=3 filtered=False
2026-11-21 01:38:17,391 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5679.42 results=3 limit=3 filtered=False
Done.

Running hybrid_search_chunks...
2026-11-21 01:38:17,917 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:38:17,919 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=527.00 task_type=RETRIEVAL_QUERY dimensions=768 text_length=48
2026-11-21 01:38:23,887 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5968.00 results=6 limit=6 filtered=False
2026-11-21 01:38:29,843 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5955.41 results=6 limit=6 filtered=False
2026-11-21 01:38:30,685 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:38:30,694 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=828.87 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 01:38:36,729 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5999.94 results=6 limit=6 filtered=False
2026-11-21 01:38:42,728 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5998.28 results=6 limit=6 filtered=False
2026-11-21 01:38:43,523 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:38:43,525 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=796.24 task_type=RETRIEVAL_QUERY dimensions=768 text_length=54
2026-11-21 01:38:49,583 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6057.30 results=6 limit=6 filtered=False
2026-11-21 01:38:55,488 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5904.08 results=6 limit=6 filtered=False
2026-11-21 01:38:55,979 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:38:55,983 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=494.64 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 01:39:01,726 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5742.95 results=6 limit=6 filtered=False
2026-11-21 01:39:07,541 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5814.08 results=6 limit=6 filtered=False
2026-11-21 01:39:08,375 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:39:08,379 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=837.20 task_type=RETRIEVAL_QUERY dimensions=768 text_length=42
2026-11-21 01:39:14,322 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5942.02 results=6 limit=6 filtered=False
2026-11-21 01:39:19,802 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5479.14 results=4 limit=6 filtered=False
2026-11-21 01:39:20,343 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:39:20,346 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=543.81 task_type=RETRIEVAL_QUERY dimensions=768 text_length=32
2026-11-21 01:39:25,959 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5611.94 results=6 limit=6 filtered=False
2026-11-21 01:39:31,818 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5859.35 results=6 limit=6 filtered=False
2026-11-21 01:39:32,325 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:39:32,332 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=509.04 task_type=RETRIEVAL_QUERY dimensions=768 text_length=40
2026-11-21 01:39:38,286 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5952.71 results=6 limit=6 filtered=False
2026-11-21 01:39:44,235 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5948.44 results=6 limit=6 filtered=False
2026-11-21 01:39:44,763 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:39:44,766 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=529.94 task_type=RETRIEVAL_QUERY dimensions=768 text_length=55
2026-11-21 01:39:50,558 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5760.99 results=6 limit=6 filtered=False
2026-11-21 01:39:56,415 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5857.04 results=6 limit=6 filtered=False
2026-11-21 01:39:56,889 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:39:56,894 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=477.68 task_type=RETRIEVAL_QUERY dimensions=768 text_length=47
2026-11-21 01:40:02,818 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5922.97 results=6 limit=6 filtered=False
2026-11-21 01:40:08,803 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5985.00 results=6 limit=6 filtered=False
2026-11-21 01:40:09,309 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:40:09,315 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=511.01 task_type=RETRIEVAL_QUERY dimensions=768 text_length=34
2026-11-21 01:40:15,179 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5863.84 results=6 limit=6 filtered=False
2026-11-21 01:40:20,879 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5700.30 results=6 limit=6 filtered=False
Done.

 # | question                                      | retrieved (src,idx)            |   P@k |   R@k |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,3), (… |  0.33 |  0.50 |  1.00 |      7839.48
 2 | What makes a returned unit unsellable?        | (amazon_…,1), (amazon_…,2), (… |  0.67 |  1.00 |  1.00 |      6232.98
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,2), (… |  0.33 |  1.00 |  1.00 |      6464.88
 4 | How do I issue a refund to a customer?        | (amazon_…,4), (amazon_…,1), (… |  0.33 |  0.33 |  1.00 |      6392.21
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |      6218.90
 6 | How do I close a return request?              | (amazon_…,1), (amazon_…,0), (… |  0.00 |  0.00 |  0.00 |      7651.46
 7 | How do I contact a buyer about a return?      | (amazon_…,1), (amazon_…,0), (… |  0.33 |  0.50 |  0.33 |      6426.41
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,1), (… |  0.00 |  0.00 |  0.00 |      6171.40
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      6136.52
10 | How are FBA order returns handled?            | (amazon_…,0), (amazon_…,0), (… |  0.33 |  0.50 |  1.00 |      6336.95

 # | question                                      | retrieved (src,idx)            |   P@k |   R@k |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,3), (… |  0.33 |  0.50 |  1.00 |      5915.61
 2 | What makes a returned unit unsellable?        | (amazon_…,2), (amazon_…,3), (… |  0.33 |  0.50 |  0.33 |      5717.92
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,3), (… |  0.33 |  1.00 |  1.00 |      5839.88
 4 | How do I issue a refund to a customer?        | (amazon_…,0), (amazon_…,2), (… |  0.67 |  0.67 |  1.00 |      5610.82
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |      5498.28
 6 | How do I close a return request?              | (amazon_…,1), (amazon_…,2), (… |  0.00 |  0.00 |  0.00 |      5624.07
 7 | How do I contact a buyer about a return?      | (amazon_…,2), (amazon_…,0), (… |  0.33 |  0.50 |  1.00 |      5640.99
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,1), (… |  0.00 |  0.00 |  0.00 |      5447.83
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      5810.24
10 | How are FBA order returns handled?            | (amazon_…,3), (amazon_…,0), (… |  0.33 |  0.50 |  1.00 |      5680.02

 # | question                                      | retrieved (src,idx)            |   P@k |   R@k |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,3), (… |  0.33 |  0.50 |  1.00 |     12472.97
 2 | What makes a returned unit unsellable?        | (amazon_…,2), (amazon_…,1), (… |  0.67 |  1.00 |  0.50 |     12863.87
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,3), (… |  0.33 |  1.00 |  1.00 |     12759.40
 4 | How do I issue a refund to a customer?        | (amazon_…,4), (amazon_…,1), (… |  0.33 |  0.33 |  1.00 |     12053.99
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |     12260.18
 6 | How do I close a return request?              | (amazon_…,1), (amazon_…,0), (… |  0.00 |  0.00 |  0.00 |     12020.92
 7 | How do I contact a buyer about a return?      | (amazon_…,2), (amazon_…,0), (… |  0.33 |  0.50 |  1.00 |     12412.32
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,1), (… |  0.00 |  0.00 |  0.00 |     12180.30
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |     12387.39
10 | How are FBA order returns handled?            | (amazon_…,0), (amazon_…,0), (… |  0.33 |  0.50 |  0.50 |     12076.86

====================================================================================================
AGGREGATE SUMMARY
====================================================================================================
Strategy           |  Mean P@k |  Mean R@k |     MRR |  Mean Latency (ms)
-------------------------------------------------------------------------
semantic           |     0.300 |     0.583 |   0.733 |            6587.12
keyword            |     0.300 |     0.567 |   0.733 |            5678.57
hybrid             |     0.300 |     0.583 |   0.700 |           12348.82

====================================================================================================
PER-QUERY DETAILS
====================================================================================================

--- semantic ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 2)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_process_return_requests', 3), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=0.500 RR=1.000 lat=7839.48 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 2), ('amazon_fba_return_policy', 0)]
    P@k=0.667 R@k=1.000 RR=1.000 lat=6232.98 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 2), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=6464.88 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 4), ('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_fba_return_policy', 4), ('amazon_seller_fulfilled_returns', 1), ('amazon_fba_return_policy', 5)]
    P@k=0.333 R@k=0.333 RR=1.000 lat=6392.21 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1), ('amazon_process_return_requests', 3)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=6218.90 ms
  Q6: How do I close a return request?
    Expected: [('amazon_fba_return_policy', 5)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_process_return_requests', 0), ('amazon_process_return_requests', 3)]
    P@k=0.000 R@k=0.000 RR=0.000 lat=7651.46 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 2)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 2)]
    P@k=0.333 R@k=0.500 RR=0.333 lat=6426.41 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1), ('amazon_process_return_requests', 2)]
    P@k=0.000 R@k=0.000 RR=0.000 lat=6171.40 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=6136.52 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 3)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=0.500 RR=1.000 lat=6336.95 ms

--- keyword ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 2)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 3), ('amazon_fba_return_policy', 1)]
    P@k=0.333 R@k=0.500 RR=1.000 lat=5915.61 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 2), ('amazon_fba_return_policy', 3), ('amazon_fba_return_policy', 1)]
    P@k=0.333 R@k=0.500 RR=0.333 lat=5717.92 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 3), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=5839.88 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 4), ('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_process_return_requests', 2), ('amazon_fba_return_policy', 4)]
    P@k=0.667 R@k=0.667 RR=1.000 lat=5610.82 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=5498.28 ms
  Q6: How do I close a return request?
    Expected: [('amazon_fba_return_policy', 5)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_process_return_requests', 2), ('amazon_process_return_requests', 0)]
    P@k=0.000 R@k=0.000 RR=0.000 lat=5624.07 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 2)]
    Retrieved: [('amazon_process_return_requests', 2), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 5)]
    P@k=0.333 R@k=0.500 RR=1.000 lat=5640.99 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1), ('amazon_fba_return_policy', 0)]
    P@k=0.000 R@k=0.000 RR=0.000 lat=5447.83 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=5810.24 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 3)]
    Retrieved: [('amazon_fba_return_policy', 3), ('amazon_seller_fulfilled_returns', 0), ('amazon_seller_fulfilled_returns', 1)]
    P@k=0.333 R@k=0.500 RR=1.000 lat=5680.02 ms

--- hybrid ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 2)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 3), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=0.500 RR=1.000 lat=12472.97 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 2), ('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 0)]
    P@k=0.667 R@k=1.000 RR=0.500 lat=12863.87 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 3), ('amazon_fba_return_policy', 2)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=12759.40 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 4), ('amazon_process_return_requests', 1)]
    Retrieved: [('amazon_fba_return_policy', 4), ('amazon_seller_fulfilled_returns', 1), ('amazon_process_return_requests', 2)]
    P@k=0.333 R@k=0.333 RR=1.000 lat=12053.99 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1), ('amazon_fba_return_policy', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=12260.18 ms
  Q6: How do I close a return request?
    Expected: [('amazon_fba_return_policy', 5)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_process_return_requests', 0), ('amazon_process_return_requests', 2)]
    P@k=0.000 R@k=0.000 RR=0.000 lat=12020.92 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 2)]
    Retrieved: [('amazon_process_return_requests', 2), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=0.500 RR=1.000 lat=12412.32 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1), ('amazon_fba_return_policy', 0)]
    P@k=0.000 R@k=0.000 RR=0.000 lat=12180.30 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=12387.39 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 3)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 0), ('amazon_seller_fulfilled_returns', 1)]
    P@k=0.333 R@k=0.500 RR=0.500 lat=12076.86 ms

====================================================================================================
EVALUATION COMPLETE
====================================================================================================





====================================================================================================
RAG RETRIEVAL EVALUATION
====================================================================================================
Documents: 3  |  Total chunks: 5  |  Config: chunk_size=800, overlap=100  |  Top-K: 3
Sources: ['amazon_fba_return_policy', 'amazon_process_return_requests', 'amazon_seller_fulfilled_returns']
----------------------------------------------------------------------------------------------------

Evaluating 10 questions...

Running semantic_search_chunks...
2026-11-21 01:46:12,743 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:46:12,753 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=933.09 task_type=RETRIEVAL_QUERY dimensions=768 text_length=48
2026-11-21 01:46:18,640 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5886.61 results=3 limit=3 filtered=False
2026-11-21 01:46:19,485 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:46:19,495 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=854.88 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 01:46:25,281 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5785.80 results=3 limit=3 filtered=False
2026-11-21 01:46:25,755 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:46:25,759 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=476.53 task_type=RETRIEVAL_QUERY dimensions=768 text_length=54
2026-11-21 01:46:31,498 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5738.82 results=3 limit=3 filtered=False
2026-11-21 01:46:31,998 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:46:32,004 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=504.93 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 01:46:38,069 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6064.35 results=3 limit=3 filtered=False
2026-11-21 01:46:38,860 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:46:38,866 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=796.60 task_type=RETRIEVAL_QUERY dimensions=768 text_length=42
2026-11-21 01:46:44,734 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5868.31 results=3 limit=3 filtered=False
2026-11-21 01:46:45,227 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:46:45,229 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=494.55 task_type=RETRIEVAL_QUERY dimensions=768 text_length=32
2026-11-21 01:46:50,871 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5641.11 results=3 limit=3 filtered=False
2026-11-21 01:46:51,367 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:46:51,373 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=501.11 task_type=RETRIEVAL_QUERY dimensions=768 text_length=40
2026-11-21 01:46:57,302 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5928.63 results=3 limit=3 filtered=False
2026-11-21 01:46:58,095 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:46:58,097 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=794.43 task_type=RETRIEVAL_QUERY dimensions=768 text_length=55
2026-11-21 01:47:04,185 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6087.96 results=3 limit=3 filtered=False
2026-11-21 01:47:04,702 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:47:04,707 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=520.86 task_type=RETRIEVAL_QUERY dimensions=768 text_length=47
2026-11-21 01:47:10,170 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5462.53 results=3 limit=3 filtered=False
2026-11-21 01:47:11,016 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:47:11,020 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=849.15 task_type=RETRIEVAL_QUERY dimensions=768 text_length=34
2026-11-21 01:47:16,886 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5864.83 results=3 limit=3 filtered=False
Done.

Running keyword_search_chunks...
2026-11-21 01:47:22,643 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5755.65 results=3 limit=3 filtered=False
2026-11-21 01:47:28,501 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5857.21 results=3 limit=3 filtered=False
2026-11-21 01:47:34,422 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5920.80 results=3 limit=3 filtered=False
2026-11-21 01:47:40,317 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5894.17 results=3 limit=3 filtered=False
2026-11-21 01:47:45,865 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5546.56 results=2 limit=3 filtered=False
2026-11-21 01:47:51,636 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5770.40 results=3 limit=3 filtered=False
2026-11-21 01:47:57,639 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6001.41 results=3 limit=3 filtered=False
2026-11-21 01:48:03,479 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5839.48 results=3 limit=3 filtered=False
2026-11-21 01:48:09,225 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5744.75 results=3 limit=3 filtered=False
2026-11-21 01:48:15,113 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5887.37 results=3 limit=3 filtered=False
Done.

Running hybrid_search_chunks...
2026-11-21 01:48:15,631 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:48:15,637 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=522.93 task_type=RETRIEVAL_QUERY dimensions=768 text_length=48
2026-11-21 01:48:21,725 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6087.99 results=5 limit=6 filtered=False
2026-11-21 01:48:27,964 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6238.08 results=5 limit=6 filtered=False
2026-11-21 01:48:28,444 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:48:28,449 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=483.76 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 01:48:34,381 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5930.89 results=5 limit=6 filtered=False
2026-11-21 01:48:40,060 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5678.65 results=5 limit=6 filtered=False
2026-11-21 01:48:40,881 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:48:40,883 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=821.90 task_type=RETRIEVAL_QUERY dimensions=768 text_length=54
2026-11-21 01:48:46,757 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5874.48 results=5 limit=6 filtered=False
2026-11-21 01:48:52,926 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6168.03 results=5 limit=6 filtered=False
2026-11-21 01:48:53,426 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:48:53,432 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=504.23 task_type=RETRIEVAL_QUERY dimensions=768 text_length=38
2026-11-21 01:48:59,423 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5991.23 results=5 limit=6 filtered=False
2026-11-21 01:49:05,496 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6071.69 results=5 limit=6 filtered=False
2026-11-21 01:49:05,972 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:49:05,978 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=480.94 task_type=RETRIEVAL_QUERY dimensions=768 text_length=42
2026-11-21 01:49:12,050 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6071.99 results=5 limit=6 filtered=False
2026-11-21 01:49:17,634 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5583.22 results=2 limit=6 filtered=False
2026-11-21 01:49:18,468 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:49:18,470 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=834.94 task_type=RETRIEVAL_QUERY dimensions=768 text_length=32
2026-11-21 01:49:24,545 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=6074.42 results=5 limit=6 filtered=False
2026-11-21 01:49:30,435 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5889.61 results=5 limit=6 filtered=False
2026-11-21 01:49:31,231 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:49:31,233 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=796.76 task_type=RETRIEVAL_QUERY dimensions=768 text_length=40
2026-11-21 01:49:36,964 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5730.64 results=5 limit=6 filtered=False
2026-11-21 01:49:42,965 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6000.29 results=5 limit=6 filtered=False
2026-11-21 01:49:43,767 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:49:43,770 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=803.35 task_type=RETRIEVAL_QUERY dimensions=768 text_length=55
2026-11-21 01:49:49,669 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5898.75 results=5 limit=6 filtered=False
2026-11-21 01:49:55,391 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5721.51 results=5 limit=6 filtered=False
2026-11-21 01:49:55,873 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:49:55,878 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=485.88 task_type=RETRIEVAL_QUERY dimensions=768 text_length=47
2026-11-21 01:50:01,646 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5767.03 results=5 limit=6 filtered=False
2026-11-21 01:50:07,407 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=5761.26 results=5 limit=6 filtered=False
2026-11-21 01:50:08,218 INFO [httpx2] HTTP Request: POST https://generativelanguage.googleapis.com/v1/models/gemini-embedding-001:batchEmbedContents "HTTP/1.1 200 OK"
2026-11-21 01:50:08,223 INFO [app.services.embedding_service] provider=gemini model=gemini-embedding-001 status=success latency_ms=814.96 task_type=RETRIEVAL_QUERY dimensions=768 text_length=34
2026-11-21 01:50:13,959 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=semantic_search status=success latency_ms=5735.56 results=5 limit=6 filtered=False
2026-11-21 01:50:20,001 INFO [app.services.rag_retrieval_service] store=rag_retrieval operation=keyword_search status=success latency_ms=6040.98 results=5 limit=6 filtered=False
Done.

 # | question                                      | retrieved (src,idx)            |   P@k |   R@k |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      7008.93
 2 | What makes a returned unit unsellable?        | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |      6641.73
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      6216.86
 4 | How do I issue a refund to a customer?        | (amazon_…,0), (amazon_…,1), (… |  0.67 |  0.67 |  1.00 |      6570.08
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      6665.79
 6 | How do I close a return request?              | (amazon_…,0), (amazon_…,1), (… |  0.00 |  0.00 |  0.00 |      6136.83
 7 | How do I contact a buyer about a return?      | (amazon_…,1), (amazon_…,0), (… |  0.33 |  1.00 |  0.50 |      6430.55
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  0.50 |      6883.77
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  0.50 |      5984.98
10 | How are FBA order returns handled?            | (amazon_…,0), (amazon_…,0), (… |  0.67 |  1.00 |  1.00 |      6715.55

 # | question                                      | retrieved (src,idx)            |   P@k |   R@k |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |      5756.37
 2 | What makes a returned unit unsellable?        | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |      5857.67
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |      5921.59
 4 | How do I issue a refund to a customer?        | (amazon_…,1), (amazon_…,0), (… |  1.00 |  1.00 |  1.00 |      5895.01
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,0)     |  0.33 |  1.00 |  1.00 |      5547.47
 6 | How do I close a return request?              | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  0.50 |      5771.23
 7 | How do I contact a buyer about a return?      | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      6002.29
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  0.33 |      5840.36
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |      5745.53
10 | How are FBA order returns handled?            | (amazon_…,1), (amazon_…,0), (… |  0.33 |  0.50 |  1.00 |      5888.03

 # | question                                      | retrieved (src,idx)            |   P@k |   R@k |    RR | latency (ms)
--------------------------------------------------------------------------------------------------------------------------
 1 | How long does a customer have to return an i… | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |     12851.30
 2 | What makes a returned unit unsellable?        | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |     12095.33
 3 | When does Amazon reimburse sellers for retur… | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |     12866.56
 4 | How do I issue a refund to a customer?        | (amazon_…,1), (amazon_…,0), (… |  1.00 |  1.00 |  1.00 |     12569.44
 5 | What is an RMA number and when is it used?    | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  1.00 |     12138.37
 6 | How do I close a return request?              | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  0.50 |     12801.08
 7 | How do I contact a buyer about a return?      | (amazon_…,0), (amazon_…,1), (… |  0.33 |  1.00 |  1.00 |     12529.99
 8 | Are return labels prepaid for seller-fulfill… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  0.50 |     12425.80
 9 | How quickly must I respond to a return reque… | (amazon_…,0), (amazon_…,0), (… |  0.33 |  1.00 |  0.50 |     12016.17
10 | How are FBA order returns handled?            | (amazon_…,1), (amazon_…,0), (… |  0.67 |  1.00 |  1.00 |     12593.30

====================================================================================================
AGGREGATE SUMMARY
====================================================================================================
Strategy           |  Mean P@k |  Mean R@k |     MRR |  Mean Latency (ms)
-------------------------------------------------------------------------
semantic           |     0.367 |     0.867 |   0.750 |            6525.51
keyword            |     0.400 |     0.950 |   0.883 |            5822.56
hybrid             |     0.433 |     1.000 |   0.850 |           12488.73

====================================================================================================
PER-QUERY DETAILS
====================================================================================================

--- semantic ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=7008.93 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_process_return_requests', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=6641.73 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=6216.86 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.667 R@k=0.667 RR=1.000 lat=6570.08 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=6665.79 ms
  Q6: How do I close a return request?
    Expected: [('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.000 R@k=0.000 RR=0.000 lat=6136.83 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 1), ('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=0.500 lat=6430.55 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0)]
    P@k=0.333 R@k=1.000 RR=0.500 lat=6883.77 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=1.000 RR=0.500 lat=5984.98 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 1)]
    P@k=0.667 R@k=1.000 RR=1.000 lat=6715.55 ms

--- keyword ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_process_return_requests', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=5756.37 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_process_return_requests', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=5857.67 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_process_return_requests', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=5921.59 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_fba_return_policy', 1), ('amazon_fba_return_policy', 0), ('amazon_process_return_requests', 0)]
    P@k=1.000 R@k=1.000 RR=1.000 lat=5895.01 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=5547.47 ms
  Q6: How do I close a return request?
    Expected: [('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=0.500 lat=5771.23 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=6002.29 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 0), ('amazon_process_return_requests', 0)]
    P@k=0.333 R@k=1.000 RR=0.333 lat=5840.36 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=5745.53 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0)]
    P@k=0.333 R@k=0.500 RR=1.000 lat=5888.03 ms

--- hybrid ---
  Q1: How long does a customer have to return an item?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=12851.30 ms
  Q2: What makes a returned unit unsellable?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_process_return_requests', 1), ('amazon_fba_return_policy', 1)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=12095.33 ms
  Q3: When does Amazon reimburse sellers for returned items?
    Expected: [('amazon_fba_return_policy', 0)]
    Retrieved: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=12866.56 ms
  Q4: How do I issue a refund to a customer?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1), ('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_fba_return_policy', 1), ('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0)]
    P@k=1.000 R@k=1.000 RR=1.000 lat=12569.44 ms
  Q5: What is an RMA number and when is it used?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=12138.37 ms
  Q6: How do I close a return request?
    Expected: [('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=0.500 lat=12801.08 ms
  Q7: How do I contact a buyer about a return?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_process_return_requests', 1), ('amazon_seller_fulfilled_returns', 0)]
    P@k=0.333 R@k=1.000 RR=1.000 lat=12529.99 ms
  Q8: Are return labels prepaid for seller-fulfilled returns?
    Expected: [('amazon_process_return_requests', 0)]
    Retrieved: [('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 0), ('amazon_fba_return_policy', 0)]
    P@k=0.333 R@k=1.000 RR=0.500 lat=12425.80 ms
  Q9: How quickly must I respond to a return request?
    Expected: [('amazon_seller_fulfilled_returns', 0)]
    Retrieved: [('amazon_process_return_requests', 0), ('amazon_seller_fulfilled_returns', 0), ('amazon_process_return_requests', 1)]
    P@k=0.333 R@k=1.000 RR=0.500 lat=12016.17 ms
  Q10: How are FBA order returns handled?
    Expected: [('amazon_fba_return_policy', 0), ('amazon_fba_return_policy', 1)]
    Retrieved: [('amazon_fba_return_policy', 1), ('amazon_seller_fulfilled_returns', 0), ('amazon_fba_return_policy', 0)]
    P@k=0.667 R@k=1.000 RR=1.000 lat=12593.30 ms

====================================================================================================
EVALUATION COMPLETE
====================================================================================================