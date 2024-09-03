from google.cloud import storage

def download_embeddings():
    bucket_name = "vectorstore_chatbot_g"
    path = "local/whatsappservice-417120-e2cbe90f7315.json"
    store_client = storage.Client.from_service_account_json(path) #vectorstore_chatbot_g/PdfVectorStore/faiss_index
    
    bucket=storage.Bucket(store_client,bucket_name)
    
    blob1 = bucket.blob("PdfVectorStore/faiss_index/index.faiss")
    blob2 = bucket.blob("PdfVectorStore/faiss_index/index.pkl")
    
    blob1.download_to_filename("vectorStorage/faiss_index/index.faiss")
    blob2.download_to_filename("vectorStorage/faiss_index/index.pkl")
    
    
download_embeddings()