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