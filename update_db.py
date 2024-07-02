import chromadb
import pickle

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./")

# Check if the collection already exists
collections = chroma_client.list_collections()
collection_names = [collection.name for collection in collections]

if "case_collection" in collection_names:
    collection = chroma_client.get_collection(name="case_collection")
else:
    collection = chroma_client.create_collection(name="case_collection")

# Load the data from the pickle file
with open('case_update.pkl', 'rb') as f:
    data_to_upsert = pickle.load(f)

# Upsert the data into the collection
for data in data_to_upsert:
    collection.upsert(
        documents=[data['summary']],  # Adding the summary as a document
        ids=[data['file_id']],  # Using extracted file_id as identifiers
        metadatas=[data['case_details']]  # Adding metadata
    )
    print(f"Case {data['file_id']} updated successfully.")

print("Database updated successfully.")
