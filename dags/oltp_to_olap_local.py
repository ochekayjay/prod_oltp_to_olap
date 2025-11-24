"""
### DAG which produces to and consumes from a Kafka cluster
This DAG will produce messages consisting of several elements to a Kafka cluster and consume
them.
"""
from airflow.decorators import dag, task
from pendulum import datetime
from airflow.operators.python import PythonOperator
from airflow.providers.apache.kafka.operators.produce import ProduceToTopicOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.apache.kafka.operators.consume import ConsumeFromTopicOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.utils.dag_parsing_context import get_parsing_context
from confluent_kafka import Consumer, KafkaException, KafkaError
from airflow.utils.log.logging_mixin import LoggingMixin
from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, ExecutionConfig,RenderConfig
from cosmos.profiles import PostgresUserPasswordProfileMapping
from cosmos.constants import ExecutionMode


from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateTableOperator,BigQueryCreateEmptyDatasetOperator,BigQueryCreateExternalTableOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from google.cloud import bigquery
from io import BytesIO
import pandas as pd
    

import json
import random
YOUR_NAME = "Igoche"
YOUR_PET_NAME = "<your (imaginary) pet name>"
NUMBER_OF_TREATS = 5
KAFKA_TOPIC = "topic4"
log = LoggingMixin().log

project_config = ProjectConfig(
    dbt_project_path="/opt/airflow/dbt/customer_insights"
)

profile_config = ProfileConfig(
    profile_name="user_analytics",
    target_name="dev",
    profile_mapping= PostgresUserPasswordProfileMapping(
        conn_id="postgres_default",  # Airflow connection to your Postgres
        profile_args={"schema": "prod_oltp_to_olap_schema"}
    )
)


render_config = RenderConfig(
    select=["path:models/staging/prod_client_stratification.sql", "tag:client_aggregation_reports"], # Run specific model and models with 'daily_reports' tag
    exclude=["path:models/example/*","path:models/debug/*","path:models/staging/customer_aggregation.sql"] # Exclude a specific archived model
)

# how dbt is executed (e.g. local CLI or docker)
execution_config = ExecutionConfig(
    execution_mode= ExecutionMode.LOCAL
)




def process_message_batch(messages):
    """
    Example callback to process a batch of Kafka messages.
    """
    cleanedVal = []
    for msg in messages:
        if msg is None:
            continue
        if msg.error():
            print(f"Error: {msg.error()}")
        else:
            #print(f"Consumed from {msg.topic()} [{msg.partition()}] @ {msg.offset()}: {msg.value().decode('utf-8')}")
            cleanedVal.append(json.loads(msg.value().decode('utf-8')))
    #print(cleanedVal)
    log.info("Consumed message: %s", cleanedVal)
    return cleanedVal


@task
def consume_messages(ti):
    # Consumer configuration
    conf = {
        'bootstrap.servers': 'kafka1:9092,kafka2:9093,kafka3:9094',
        'group.id': 'my_consumer_group',         # Consumer group id
        'auto.offset.reset': 'earliest'          # Where to start if no offset is committed
    }

    consumer = Consumer(conf)

    topics = ["topic4", "topic5"]
    consumer.subscribe(topics)

    poll_timeout = 10   # seconds
    max_messages = 50
    max_batch_size = 10

    messages = []
    refinedVal = []

    try:
        while len(messages) < max_messages:
            msg = consumer.poll(poll_timeout)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue  # End of partition event
                else:
                    raise KafkaException(msg.error())

            messages.append(msg)

            # Process when batch size is reached
            if len(messages) == max_messages:
                refinedVal = process_message_batch(messages)
                ti.xcom_push(key="my_data",value=refinedVal)
               
            else:
                print(len(messages))

            #

        # process any leftover messages
        if messages:
            refinedVal = process_message_batch(messages)
            return refinedVal

    finally:
        consumer.close()
        




@task
def insert_into_postgres(ti):
    
    # ✅ pull contentList from previous task
    #contentList = ti.xcom_pull(task_ids="consume_events")
    contentList = ti.xcom_pull(task_ids='consume_messages', key='return_value')
    
    log.info("postgres-bound messages: %s", contentList)
    hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = hook.get_conn()
    cur = conn.cursor()

    insert_query = """
        INSERT INTO local_oltp_raw_data (
            brand, nameOfClient, clientLocation, paymentMethod,
            dayTime, item, count, cost, customerFeedBack, unique_row_id
        )
        VALUES (
            %s, %s, %s, %s, CAST(%s AS TIMESTAMP),
            %s, %s, %s, %s,
            MD5(
                CONCAT(
                    COALESCE(%s::TEXT, ''),
                    COALESCE(%s::TEXT, ''),
                    COALESCE(%s::TEXT, ''), -- Cast dayTime explicitly
                    COALESCE(%s::TEXT, '')  -- Cast cost explicitly
                )
            )
        )
    """

    for row in contentList:
        cur.execute(
            insert_query,
            (
                row.get('brand'),
                row.get('nameOfClient'),
                row.get('clientLocation'),
                row.get('paymentMethod'),
                row.get('dayTime'),
                row.get('item'),
                row.get('count'),
                row.get('cost'),
                row.get('customerFeedBack'),
                # fields used for MD5 uniqueness
                row.get('brand'),
                row.get('nameOfClient'),
                row.get('dayTime'),
                row.get('cost')
            )
        )

    conn.commit()
    cur.close()
    conn.close()
    log.info("✅ Insert completed successfully.")



@task 
def purge_staging_table():
    hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = hook.get_conn()
    cur = conn.cursor()

    cur.execute("""
                DROP TABLE local_oltp_raw_data
                """)
    conn.commit()
    cur.close()
    conn.close()



@task 
def purge_stratify_table():
    hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = hook.get_conn()
    cur = conn.cursor()

    cur.execute("""
                DROP TABLE prod_oltp_to_olap_schema.prod_client_stratification
                """)
    conn.commit()
    cur.close()
    conn.close()


 
@dag(
    start_date=datetime(2025, 9, 23),
    schedule=None,   # run on demand
    catchup=False,
)
def local_oltp_to_olap_dag_call():

    #consume_task = consume_messages()

    create_postgres_table_task = SQLExecuteQueryOperator(
        task_id="create_table",
        conn_id="postgres_default",    # defined in Airflow Connections
        sql= """
                CREATE TABLE IF NOT EXISTS local_oltp_raw_data(
                    brand TEXT,
                    nameOfClient TEXT,
                    clientLocation TEXT,
                    paymentMethod TEXT,
                    dayTime TIMESTAMP,
                    item TEXT,
                    count INTEGER,
                    cost BIGINT,
                    customerFeedBack TEXT,
                    unique_row_id TEXT
                )
            """
                   # size per poll batch
    )



    create_data_wh_table_task = BigQueryCreateTableOperator(
        task_id="create_data_wh_table_task",
        dataset_id="bq_airflow_dbt_db",
        table_id="client_daily_aggregation",
        gcp_conn_id='google_cloud_default',
        table_resource={
            "schema": {
                "fields": [
                    {"name": "brand", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "nameOfClient", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "clientLocation", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "paymentMethod", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "dayTime", "type": "DATETIME", "mode": "NULLABLE"},
                    {"name": "item", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "count", "type": "INTEGER", "mode": "NULLABLE"},
                    {"name": "cost", "type": "INTEGER", "mode": "NULLABLE"},
                    {"name": "customerFeedBack", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "unique_row_id", "type": "STRING", "mode": "NULLABLE"},
                ],
            },
            "labels": {
                "env": "development",
                "owner": "data-team"
            },
            "description": "A table containing selar transaction breakdown.",
        }
        

    )


    create_client_timerank_table = BigQueryCreateTableOperator(
        task_id="create_client_agg_table_task",
        dataset_id="bq_airflow_dbt_db",
        table_id="client_time_ranking",
        gcp_conn_id='google_cloud_default',
        table_resource={
            "schema": {
                "fields": [
                    {"name": "brand", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "daytime", "type": "DATETIME", "mode": "NULLABLE"},
                    {"name": "time_window", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "items_sold", "type": "INTEGER", "mode": "NULLABLE"},
                    {"name": "sales_rank", "type": "INTEGER", "mode": "NULLABLE"},
                ],
            },
            "labels": {
                "env": "development",
                "owner": "data-team"
            },
            "description": "A table containing selar transaction breakdown.",
        }
        

    )



    dbt_transformations = DbtTaskGroup(
            group_id="dbt_transformations",
            project_config=project_config,
            profile_config= profile_config,
            execution_config=execution_config,
            default_args={"retries": 2},
            render_config=render_config,
        )
    
   
    @task
    def insert_into_central_data_warehouse():

        hook = PostgresHook(postgres_conn_id="postgres_default")
        conn = hook.get_conn()
        cur = conn.cursor()

        cur.execute("""
                    SELECT brand,
                    nameOfClient,
                    clientLocation,
                    paymentMethod,
                    dayTime,
                    item,
                    count,
                    cost,
                    customerFeedBack,
                    unique_row_id
                    FROM local_oltp_raw_data 
                    """)
        tabColList = [element[0] for element in cur.description]
        queryData = cur.fetchall()
        stagingNewDf = pd.DataFrame(queryData,columns=tabColList)

        bq_hook = BigQueryHook(gcp_conn_id='google_cloud_default')
    
        # 2. Get the authenticated credentials from the hook
        credentials = bq_hook.get_credentials()
        project_id = bq_hook.project_id


        client = bigquery.Client(project='airflow-soln-project', credentials=credentials)

        #bq_hook = BigQueryHook(gcp_conn_id="cloud-storage-default", use_legacy_sql=False)


        table_full_id = "airflow-soln-project.bq_airflow_dbt_db.client_daily_aggregation"

        job_config = bigquery.LoadJobConfig(
            # Optional: Specify schema if you want to enforce it, otherwise BigQuery infers
            # schema=[
            #     bigquery.SchemaField("col1", "INTEGER"),
            #     bigquery.SchemaField("col2", "STRING"),
            # ]
        )

        #job_config=job_config
        load_job = client.load_table_from_dataframe(
            stagingNewDf, table_full_id
        )
        load_job.result()


        

        cur.close()
        conn.close()


    

    @task
    def insert_into_client_rank_table():

        hook = PostgresHook(postgres_conn_id="postgres_default")
        conn = hook.get_conn()
        cur = conn.cursor()

        cur.execute("""
                    SELECT 
                    brand,
                    daytime,
                    time_window,
                    items_sold,
                    sales_rank
                    FROM prod_oltp_to_olap_schema.prod_client_stratification 
                    ORDER BY brand ASC
                    """)
        tabColList = [element[0] for element in cur.description]
        queryData = cur.fetchall()
        stagingNewDf = pd.DataFrame(queryData,columns=tabColList)
        stagingNewDf['time_window'] = stagingNewDf['time_window'].astype(str)

        bq_hook = BigQueryHook(gcp_conn_id='google_cloud_default')
    
        # 2. Get the authenticated credentials from the hook
        credentials = bq_hook.get_credentials()
        project_id = bq_hook.project_id


        client = bigquery.Client(project='airflow-soln-project', credentials=credentials)

        #bq_hook = BigQueryHook(gcp_conn_id="cloud-storage-default", use_legacy_sql=False)

        table_full_id = "airflow-soln-project.bq_airflow_dbt_db.client_time_ranking"

        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("brand", "STRING"),
                bigquery.SchemaField("daytime", "DATETIME"), # Adjust types as needed for your actual data
                bigquery.SchemaField("time_window", "STRING"),
                bigquery.SchemaField("items_sold", "INT64"),
                bigquery.SchemaField("sales_rank", "INT64"),
                ],
                # Optionally specify write disposition
                # write_disposition="WRITE_TRUNCATE", 
        )

        #job_config=job_config
        load_job = client.load_table_from_dataframe(
            stagingNewDf, table_full_id,job_config=job_config
        )
        load_job.result()



        

        cur.close()
        conn.close()



    

    insert_into_pg = insert_into_postgres()
    consume_from_kafka = consume_messages()
    insert_into_central_bq = insert_into_central_data_warehouse()
    insert_into_rank_table = insert_into_client_rank_table()
    purge_table = purge_staging_table()
    purge_stratifying_table = purge_stratify_table()



    

    consume_from_kafka>>create_postgres_table_task>>create_data_wh_table_task>>create_client_timerank_table>>insert_into_pg>>dbt_transformations>>insert_into_central_bq>>insert_into_rank_table>>purge_table>>purge_stratifying_table
      
     
 

local_oltp_to_olap_dag_call()

#create_table_task >> consume_task >> p_con_data >> insert_data_task

"""

query_table = SQLExecuteQueryOperator(
        task_id="query_table",
        conn_id="postgres_default",    # defined in Airflow Connections
        sql= 
                SELECT * FROM postgresDb.marketing_insights.client_aggregation
            
                   # size per poll batch
    )

"""


"""
    dbt_transformations = DbtTaskGroup(
            group_id="dbt_transformations",
            project_config=project_config,
            profile_config= profile_config,
            execution_config=execution_config,
            default_args={"retries": 2},
            render_config=render_config,
        )
"""