from flask import Flask, request, render_template, jsonify
import chromadb
import google.generativeai as genai
import textwrap
import pickle

app = Flask(__name__)

# Initialize ChromaDB client with the SQLite database file
chroma_client = chromadb.PersistentClient(path="./")

# Assuming the collection is named "case_collection"
collection = chroma_client.get_collection(name="case_collection")

# Placeholder for Google API key (manually enter your API key here)
GOOGLE_API_KEY = "YOUR_API_KEY"

# Configure Google Generative AI
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def to_markdown(text):
    text = text.replace('•', '  *')
    return textwrap.indent(text, '> ', predicate=lambda _: True)

def load_case_chat(case_id):
    try:
        with open(f"history/{case_id}_history.pkl", "rb") as f:
            history = pickle.load(f)
    except FileNotFoundError:
        print(f"No history found for case {case_id}.")
        return None

    chat = model.start_chat(history=history)
    return chat

def send_case_query(case_id, query):
    chat = load_case_chat(case_id)
    if not chat:
        return "No history found."
    response = chat.send_message(query)
    return response.text  # Return the plain response text

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    results = collection.query(
        query_texts=[query],
        n_results=3  # Change to return top 3 results
    )
    return jsonify(results)

@app.route('/chat/<case_id>', methods=['GET', 'POST'])
def chat(case_id):
    if request.method == 'POST':
        query = request.form['query']
        response = send_case_query(case_id, query)
        return jsonify({'response': response})
    return render_template('chat.html', case_id=case_id)

@app.route('/case/<case_id>', methods=['GET'])
def get_case(case_id):
    # Fetch the specific case_id
    results = collection.get(ids=[case_id])
    
    # Check if the case was found
    if 'documents' in results and results['documents']:
        document = results['documents'][0]  # Fetch the document content
        return jsonify({'document': document})
    else:
        return jsonify({'error': 'Case not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
