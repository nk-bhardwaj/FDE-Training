FROM apache/airflow:3.4.0-python3.12

RUN python -m pip install --no-cache-dir \
    "apache-airflow==3.4.0" \
    "pandas>=3.1.1" \
    "psycopg[binary]>=3.2,<4.0" \
    "python-dotenv>=1.0,<2.0" \
 && python -m pip check