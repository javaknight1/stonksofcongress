import csv, json, zipfile
import requests
import os, shutil
import argparse
from progress.bar import Bar

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

def main():
    args = parseargs()
    congress_docs = get_congress_people_docs("2021FD")

    os.mkdir("./pdfs")

    print(f"Found {len(congress_docs)} PDF records....")
    bar = Bar('Loading PDFs', fill='#', suffix='%(percent).1f%% (%(index)d/%(max)d) - %(eta)ds', max=len(congress_docs))

    for doc in congress_docs:
        res = requests.get(f"{PDF_FILE_URL}{doc['doc_id']}.pdf")

        with open(f"pdfs/{doc['doc_id']}.pdf", 'wb+') as pdf_file:
            pdf_file.write(res.content)
            bar.next()

        # if (res.status_code == 200):
        #     doc = fitz.open(f"pdfs/{doc['doc_id']}.pdf")
        #     page = doc.load_page(page_id=0)

        #     json_data = page.get_text("json")

        #     if "blocks" in json_data:
        #         import pdb; pdb.set_trace()
        #         for block in json_data["blocks"]:
        #             import pdb; pdb.set_trace()
        #             if "lines" in block:
        #                 print(block)
            
    bar.finish()

    print("Completed downloading PDFs")
            
    if False and os.path.isdir("./pdfs"):
        shutil.rmtree("./pdfs")

if __name__ == "__main__":
    main()