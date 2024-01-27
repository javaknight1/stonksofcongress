import csv, json, zipfile
import requests
import os, shutil
import argparse
from progress.bar import Bar
from PyPDF2 import PdfReader
from openai import OpenAI

OPENAI_API_KEY = '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'
PDF_FILE_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2021/"

def parseargs():
    parser = argparse.ArgumentParser(description="Downloads and extracts all the data about the publci trades that people from US Congress have been trading.")
    # parser.add_argument("infile", help="File that has mlb schedules")
    
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
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
    return text

def main():
    args = parseargs()
    congress_docs = get_congress_people_docs("2021FD")
    pdf_dir = "pdfs"

    if not os.path.exists(f"{pdf_dir}"):
        os.mkdir(f"{pdf_dir}")

    print(f"Found {len(congress_docs)} PDF records....")
    bar = Bar('Loading PDFs', fill='#', suffix='%(percent).1f%% (%(index)d/%(max)d) - %(eta)ds', max=len(congress_docs))

    for doc in congress_docs:
        res = requests.get(f"{PDF_FILE_URL}{doc['doc_id']}.pdf")

        if (res.status_code == 200):
            with open(f"{pdf_dir}/{doc['doc_id']}.pdf", 'wb+') as pdf_file:
                pdf_file.write(res.content)
                bar.next()

            pdf_text = extract_text_from_pdf(f"{pdf_dir}/{doc['doc_id']}.pdf")

            client = OpenAI()

            response = client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": f"Extracted from the PDF: {pdf_text}."},
                    {"role": "user", "content": "Can you get the list of stock trades and export it as a json?"}
                ]
            )
            print(response.choices[0].message.content)
            
    bar.finish()

    print("Completed downloading PDFs")
            
    if False and os.path.exists(f"{pdf_dir}") and os.path.isdir(f"{pdf_dir}"):
        shutil.rmtree(f"{pdf_dir}")

if __name__ == "__main__":
    main()