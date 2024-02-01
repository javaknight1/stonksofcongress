import csv, json, zipfile
from dotenv import load_dotenv
import requests
import os, shutil
import argparse
from progress.bar import Bar
from PyPDF2 import PdfReader
from pathlib import Path
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.callbacks import get_openai_callback

PDF_FILE_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2021/"

def parseargs():
    parser = argparse.ArgumentParser(description="Downloads and extracts all the data about the publci trades that people from US Congress have been trading.")
    parser.add_argument('-pdf', '--pdf', action='store_true', help="Directory that holds all the PDFs you want to read.")
    parser.add_argument('-d', '--downloadonly', action='store_true', help="Only download the requried PDFs")  
    return parser.parse_args()

def download_and_extract_zip_file(zipfile_name, path_to_save='.', delete_zip=True):
    zip_file_url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{zipfile_name}"
    r = requests.get(zip_file_url)

    with open(zipfile_name, "wb") as f:
        f.write(r.content)

    with zipfile.ZipFile(zipfile_name) as z:
        z.extractall(path_to_save)

    if delete_zip and os.path.exists(zipfile_name):
        os.remove(zipfile_name)

def extract_congress_people_file(filename):
    congress_docs = []

    with open(filename) as f:
        for line in csv.reader(f, delimiter='\t'):

            # skip the first line
            if (line[8] == "DocID"):
                continue

            title = line[0]
            last_name = line[1]
            first_name = line[2]
            suffix = line[3]
            filing_type = line[4]
            state_dst = line[5]
            year = line[6]
            date = line[7]
            doc_id = line[8]

            congress_docs.append({
                "title": title,
                "last_name": last_name,
                "first_name": first_name,
                "suffix": suffix,
                "filing_type": filing_type,
                "state_dst": state_dst,
                "year": year,
                "filing_date": date,
                "doc_id": doc_id
            })
    return congress_docs

def get_congress_people_docs(name, delete_files=True):

    download_and_extract_zip_file(f"{name}.zip", f"./{name}", delete_files)
    congress_docs = extract_congress_people_file(f"{name}/{name}.txt")

    if delete_files and os.path.isdir(f"{name}"):
        shutil.rmtree(f"{name}")

    return congress_docs

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        pdf_reader = PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def process_text(text):
    # Split the text into chunks using Langchain's CharacterTextSplitter
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    
    # Convert the chunks of text into embeddings to form a knowledge base
    embeddings = OpenAIEmbeddings()
    knowledgeBase = FAISS.from_texts(chunks, embeddings)
    
    return knowledgeBase

def main():
    args = parseargs()
    congress_docs = get_congress_people_docs("2021FD")
    pdf_dir = "pdfs"

    if not os.path.exists(f"{pdf_dir}"):
        os.mkdir(f"{pdf_dir}")

    print(f"Found {len(congress_docs)} PDF records....")

    if not args.pdf:
        bar = Bar('Downloading PDFs', fill='#', suffix='%(percent).1f%% (%(index)d/%(max)d) - %(eta)ds', max=len(congress_docs))
        for doc in congress_docs:
            res = requests.get(f"{PDF_FILE_URL}{doc['doc_id']}.pdf")

            if (res.status_code == 200):
                with open(f"{pdf_dir}/{doc['doc_id']}.pdf", 'wb+') as pdf_file:
                    pdf_file.write(res.content)
                    bar.next()
            
        bar.finish()
        print("Completed downloading PDFs")

    pdf_files = Path(f"./{pdf_dir}").glob("*.pdf")
    if not args.downloadonly:
        for pdf_file in pdf_files:
            pdf_text = extract_text_from_pdf(f"{pdf_file}")

            knowledgeBase = process_text(pdf_text)

            print(f"knowledgeBase: {knowledgeBase}")

            query = input('Ask a question to the PDF\n')
            docs = knowledgeBase.similarity_search(query)

            llm = OpenAI()
            chain = load_qa_chain(llm, chain_type='stuff')
            
            with get_openai_callback() as cost:
                response = chain.run(input_documents=docs, question=query)
                print(cost)
                
            print(response)

            # client = OpenAI()

            # response = client.chat.completions.create(
            #     model="gpt-3.5-turbo-1106",
            #     response_format={ "type": "json_object" },
            #     messages=[
            #         {"role": "system", "content": f"Extracted from the PDF: {pdf_text}."},
            #         {"role": "user", "content": "Can you get the list of stock trades and export it as a json?"}
            #     ]
            # )
            # print(response.choices[0].message.content)
            
    if False and os.path.exists(f"{pdf_dir}") and os.path.isdir(f"{pdf_dir}"):
        shutil.rmtree(f"{pdf_dir}")

load_dotenv()

if __name__ == "__main__":
    main()