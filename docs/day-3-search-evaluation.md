# Day 3 — Search Method Evaluation Report

## Evaluation Objective

Evaluate and compare the semantic search and keyword search implementations.

## Technology Stack

- Gemini `gemini-embedding-001`.
- Embedding dimensions: 768.
- Neon PostgreSQL with pgvector.
- PostgreSQL full-text search for keyword search.

## Dataset

- 30 sample documents across 10 categories.

## Methodology

- Compared semantic and keyword search using 10 evaluation queries.
- Returned top-3 results per method per query.
- Top-1 accuracy compares the expected category with the top-1 returned category.
- Top-3 accuracy checks whether the expected category appears in the top-3 returned categories.
- Similarity and rank values are not compared numerically because scoring systems differ.

## Results

| # | Expected Category | Semantic Top-1 | Keyword Top-1 | Semantic Top-3 Categories | Keyword Top-3 Categories | Semantic Latency (ms) | Keyword Latency (ms) |
|---|--------------------|----------------|---------------|---------------------------|--------------------------|----------------------|----------------------|
| 1 | order_tracking | order_tracking | cancellations | order_tracking, order_tracking, deliver… | cancellations, shipping_charges, accoun… |        8224.61 |          5846.99 |
| 2 | delivery_delays | delivery_delays | delivery_delays | delivery_delays, delivery_delays, deliv… | delivery_delays, delivery_delays, order… |        6044.20 |          5521.44 |
| 3 | returns_refunds | returns_refunds | returns_refunds | returns_refunds, returns_refunds, excha… | returns_refunds, damaged_products, retu… |        6629.57 |          5794.23 |
| 4 | cancellations | cancellations | cancellations | cancellations, cancellations, exchanges | cancellations, damaged_products, order_… |        6560.13 |          5814.47 |
| 5 | payment_failures | payment_failures | payment_failures | payment_failures, payment_failures, shi… | payment_failures, shipping_charges, pay… |        6325.07 |          5641.99 |
| 6 | damaged_products | damaged_products | damaged_products | damaged_products, damaged_products, ret… | damaged_products, damaged_products, ret… |        6697.79 |          5788.90 |
| 7 | account_login_issues | account_login_iss… | account_login_iss… | account_login_issues, account_login_iss… | account_login_issues, exchanges, delive… |        6735.09 |          5928.85 |
| 8 | shipping_charges | shipping_charges | shipping_charges | shipping_charges, shipping_charges, shi… | shipping_charges, shipping_charges, dam… |        6481.60 |          5566.06 |
| 9 | exchanges | exchanges | shipping_charges | exchanges, exchanges, shipping_charges | shipping_charges, cancellations, exchan… |        6244.02 |          5700.48 |
| 10 | customer_support | customer_support | customer_support | customer_support, customer_support, dam… | customer_support, customer_support, dam… |        6463.10 |          5848.79 |

## Summary Metrics

| Metric | Semantic Search | Keyword Search |
|---|---|---|
| Top-1 Accuracy | 100.0% | 80.0% |
| Top-3 Accuracy | 100.0% | 90.0% |
| Average Latency | 6640.52 ms | 5745.22 ms |

## Observations and Limitations

- Failed searches are reported as failed and are excluded from latency averages.
- Queries where keyword search returned no results are treated as incorrect.
- Semantic similarity and keyword rank are not compared numerically.

