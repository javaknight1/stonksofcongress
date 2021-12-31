import csv, json, zipfile
import requests, PyPDF2, fitz

zip_file_url = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2021FD.zip"
pdf_file_url = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2021/"

congress_docs = []

r = requests.get(zip_file_url)
zipfile_name = "2021.zip"

with open(zipfile_name, "wb") as f:
    f.write(r.content)

with zipfile.ZipFile(zipfile_name) as z:
    z.extractall('.')

with open("2021FD.txt") as f:
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

# TODO: Delete zip and txt files

for doc in congress_docs:
    r = requests.get(f"{pdf_file_url}{doc['doc_id']}.pdf")

    with open(f"pdfs/{doc['doc_id']}.pdf", 'wb+') as pdf_file:
        pdf_file.write(r.content)

    doc = fitz.open(f"pdfs/{doc['doc_id']}.pdf")
    page = doc.load_page(page_id=0)

    json_data = page.get_text("json")

    for block in json_data["blocks"]:
        import pdb; pdb.set_trace()
        if "lines" in block:
            print(block)