from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StringType, TimestampType
import pymongo
import json

#client = pymongo.MongoClient("mongodb+srv://onShore:sahu9821@cluster0.a6ot5gp.mongodb.net/?retryWrites=true&w=majority")
client = pymongo.MongoClient("mongodb://localhost:27017")  
db = client.crowdManagement
qr_scans_collection = db["users"]

spark = SparkSession.builder \
    .appName("CrowdTrackingStreaming") \
    .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

kafka_bootstrap_servers = "localhost:9092"
qr_scan_topic = "qr_scans"

qr_schema = StructType() \
    .add("scan_id", StringType()) \
    .add("name", StringType()) \
    .add("phone", StringType()) \
    .add("address", StringType()) \
    .add("scan_time", TimestampType())

qr_scans_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
    .option("subscribe", qr_scan_topic) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load() \
    .selectExpr("CAST(value AS STRING)")

qr_scans_df = qr_scans_df \
    .select(from_json(col("value"), qr_schema).alias("data")) \
    .select("data.*")

def write_qr_to_mongodb(batch_df, batch_id):
    records = batch_df.toJSON().collect()
    if records:
        qr_scans_collection.insert_many([json.loads(row) for row in records])
        print(f"✅ QR Scan Data Written to MongoDB at batch {batch_id}")

qr_scans_df.writeStream \
    .foreachBatch(write_qr_to_mongodb) \
    .option("checkpointLocation", "./checkpoint/qr_scans") \
    .start()

spark.streams.awaitAnyTermination()
