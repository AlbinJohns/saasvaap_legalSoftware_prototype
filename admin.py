import google.generativeai as genai
import pickle
import pdfplumber
import os
import re

# Configure generative AI model

genai.configure(api_key='YOUR_API_KEY')
model = genai.GenerativeModel('gemini-1.5-flash')

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
    return text

# Function to extract case details from text
def extract_case_details(text):
    filing_no_pattern = re.compile(r'Filing Number (.+?) Filing Date')
    filing_date_pattern = re.compile(r'Filing Date (\d{2}-\d{2}-\d{4})')
    disposed_date_pattern = re.compile(r'Disposed date (\d{2}-\d{2}-\d{4})')
    case_type_pattern = re.compile(r'Case Type (.+?) Case Status')
    case_status_pattern = re.compile(r'Case Status (\w+)')

    filing_no = filing_no_pattern.search(text).group(1).strip() if filing_no_pattern.search(text) else ""
    filing_date = filing_date_pattern.search(text).group(1).strip() if filing_date_pattern.search(text) else ""
    disposed_date_match = disposed_date_pattern.search(text)
    disposed_date = disposed_date_match.group(1).strip() if disposed_date_match else ""
    case_type = case_type_pattern.search(text).group(1).strip() if case_type_pattern.search(text) else ""
    case_status = case_status_pattern.search(text).group(1).strip() if case_status_pattern.search(text) else ""

    if case_status.upper() == 'PENDING':
        disposed_date = ""

    case_details = {
        "Filing_no": filing_no,
        "filing_date": filing_date,
        "disposed_date": disposed_date,
        "case_type": case_type,
        "case_status": case_status
    }

    return case_details

# Function to process case files and return text data
def process_case_files(cases_folder, case_id):
    pdf_text, pdf_int, pdf_jud = "", "", ""

    print(f"Processing case: {case_id}")

    general_details_path = os.path.join(cases_folder, f'case_{case_id}.pdf')
    if os.path.exists(general_details_path):
        pdf_text = extract_text_from_pdf(general_details_path)
        print(f"Extracted general details from {general_details_path}")

    other_documents = []
    for filename in os.listdir(cases_folder):
        if filename.startswith(f'case_{case_id}_int') and filename.endswith('.pdf'):
            file_path = os.path.join(cases_folder, filename)
            other_documents.append(extract_text_from_pdf(file_path))
            print(f"Extracted interim document from {file_path}")
    pdf_int = "".join(other_documents)

    judgment_path = os.path.join(cases_folder, f'case_{case_id}_jud.pdf')
    if os.path.exists(judgment_path):
        pdf_jud = extract_text_from_pdf(judgment_path)
        print(f"Extracted judgment from {judgment_path}")

    return pdf_text, pdf_int, pdf_jud

# Function to start case chat and save history
def start_case_chat(case_id, pdf_text, pdf_int, pdf_jud, output_folder):
    chat = model.start_chat(history=[])

    case_details = f"""
    Here are the details of the case:
    General details: {pdf_text}

    Other documents: {pdf_int}

    Judgment: {pdf_jud}. Don't answer anything else other than what is in the document from now on.
    """

    response = chat.send_message(case_details)
    history = chat.history

    os.makedirs(output_folder, exist_ok=True)

    output_path = os.path.join(output_folder, f"{case_id}_history.pkl")
    with open(output_path, "wb") as f:
        pickle.dump(history, f)
    print(f"Saved history to {output_path}")

    return chat

# Function to process all cases in the folder and generate both history and update data
def process_all_cases(cases_folder, output_folder):
    if not os.path.exists(cases_folder):
        print(f"Cases folder {cases_folder} does not exist.")
        return
    if not os.path.isdir(cases_folder):
        print(f"{cases_folder} is not a directory.")
        return

    print(f"Processing all cases in folder: {cases_folder}")
    processed_cases = set()
    data_to_pickle = []

    for filename in os.listdir(cases_folder):
        if filename.startswith('case_') and filename.endswith('.pdf'):
            case_id = filename.split('_')[1].split('.')[0]
            if case_id not in processed_cases:
                processed_cases.add(case_id)
                try:
                    pdf_text, pdf_int, pdf_jud = process_case_files(cases_folder, case_id)
                    if pdf_text or pdf_int or pdf_jud:  # Proceed only if there's some data extracted
                        chat = start_case_chat(case_id, pdf_text, pdf_int, pdf_jud, output_folder)

                        # Extract case details and generate update data
                        case_details = extract_case_details(pdf_text)
                        prompt = f"Give me a paragraph summary of the following legal document with every important detail (such as filing number of the case, by whom and against whom, all the advocates and judges involved, and type of bench):\n{pdf_text}"
                        response = model.generate_content(prompt)
                        summary = response.text

                        data_to_pickle.append({
                            "summary": summary,
                            "file_id": case_id,
                            "case_details": case_details
                        })

                        print(f"Processed case {case_id}")
                    else:
                        print(f"No data extracted for case {case_id}")
                except Exception as e:
                    print(f"Error processing case {case_id}: {e}")

    # Save the update data to a pickle file in the working directory
    update_output_path = 'case_update.pkl'
    with open(update_output_path, 'wb') as f:
        pickle.dump(data_to_pickle, f)
    print(f"Saved update data to {update_output_path}")

# Path to the folder containing all cases
cases_folder = './cases'
# Path to the folder where pickle files will be saved
output_folder = './history'

# Process all cases in the folder
process_all_cases(cases_folder, output_folder)
