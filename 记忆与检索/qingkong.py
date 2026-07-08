from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv
load_dotenv()

client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
client.delete_collection("test")  # 旧 memory collection
client.delete_collection("hello_agents_rag_vectors")