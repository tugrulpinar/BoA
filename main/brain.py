from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from PyPDF2 import PdfFileMerger
from cryptography.fernet import Fernet
from bs4 import BeautifulSoup
from selenium import webdriver
from pathlib import Path
import time
import requests
import re
import os
import string


uppercase_alphabets = list(string.ascii_uppercase)
my_dict = {}

for i in range(1, 27):
    my_dict[i] = uppercase_alphabets[i-1]

FAILED_TO_FIND = []


def create_tabs(path, number, description=""):
    document_path = os.path.join(path, f"{my_dict[number]}.TAB.pdf")
    canvas = Canvas(document_path, pagesize=LETTER)
    canvas.setFont("Times-Roman", 50)
    canvas.drawString(3.5 * inch, 7 * inch, f"TAB {number}")
    canvas.setFont("Times-Roman", 15)
    canvas.drawString(2.5 * inch, 6 * inch, f"{description}")
    canvas.bookmarkPage(f"TAB {number}")
    canvas.addOutlineEntry(f"TAB {number}", f"TAB {number}")
    canvas.save()


def merge_pdf_files(path):
    merger = PdfFileMerger()
    folder = Path(path)
    source_dir = folder.absolute()

    files = [str(path.absolute()) for path in folder.glob("*.pdf")]

    if not files:
        return "There is no pdf file in the directory"

    if len(files) < 2:
        return "There's only one pdf file"

    for item in files:
        merger.append(item)

    filename = "BookOfAuthorities.pdf"
    full_path = os.path.join(source_dir, filename)
    merger.write(full_path)
    merger.close()
    file_size = os.path.getsize(full_path)
    return str(round(file_size/1000000, 1)) + " Mb"


def get_case_law(text):
    # split the text into arrays
    raw_list = text.strip().split("\n")
    # clean the tabs
    cleaner = [item.replace("\r", "") for item in raw_list]
    sec_cleaner = [item.replace("\t", "") for item in cleaner]

    case_law = []
    for item in sec_cleaner:
        try:
            while not item.strip()[0].isalpha():
                item = item.replace(item[0], "").strip()
            case_law.append(item)
        except:
            pass
    return case_law


def get_names_opposer(case_law):
    names = []
    opposer = []
    idx_to_remove = []

    # parse the text
    for idx, item in enumerate(case_law):
        try:
            if " v " in item.lower():
                names.append(item.lower().split(" v ")[0].title())
                opposer.append(item.lower().split(" v ")[1].title())
            elif " v. " in item:
                names.append(item.lower().split(" v. ")[0].title())
                opposer.append(item.lower().split(" v. ")[1].title())
            else:
                idx_to_remove.append(idx)
                print(f"Text is not in correct format for {item}")
        except:
            print(f"Text is not in correct format for {item}")

    counter = 0
    for item in idx_to_remove:
        # take not of the ones we cant find. We'll use it later
        FAILED_TO_FIND.append(case_law[item-counter])
        case_law.pop(item-counter)
        counter += 1

    return names, opposer


# 4 digit number + white space + some text + white space + some more numbers
def get_code(array, names, case_law):
    temp_codes_list = []
    idx_to_clean = []

    for idx, item in enumerate(array):
        try:
            # "\d{4}\s+[a-zA-Z]+\s+\d+"
            id_code = re.findall("\d+\s+\S+\s+\d+", item)
            if id_code:
                temp_codes_list.append(id_code[0])
            else:
                id_code = re.findall("\S+\d{4}\S+", item)
                temp_codes_list.append(id_code[0])
        except:
            idx_to_clean.append(idx)
            print("Cannot find the case code")

    counter = 0
    for item in idx_to_clean:
        names.pop(item-counter)
        FAILED_TO_FIND.append(case_law[item-counter])
        case_law.pop(item-counter)
        counter += 1

    return temp_codes_list


def get_clean_names(names, codes_list, case_law):
    clean_names = []
    idx_to_clean = []

    for idx, name in enumerate(names):
        if name.isalpha():
            clean_names.append(name)
        else:
            try:
                clean_names.append(re.findall(
                    "[a-zA-Z]+\s*[a-zA-Z]+\s*[a-zA-Z]+\s*[a-zA-Z]+", name)[0])
            except:
                idx_to_clean.append(idx)
                print("Problem with clean names", name)

    counter = 0
    for item in idx_to_clean:
        codes_list.pop(item-counter)
        FAILED_TO_FIND.append(case_law[item-counter])
        case_law.pop(item-counter)
        counter += 1

    return clean_names


def get_url(search_term, case_law_code):
    template = 'https://www.canlii.org/en/#search/text={}'
    url_search_term = f"{search_term}&id={case_law_code}"
    url = template.format(url_search_term)
    return url


def find_click(element_id):
    variable = browser.find_element_by_id(element_id)
    variable.click()


def find_click_xpath(xpath):
    variable = browser.find_element_by_xpath(xpath)
    variable.click()


def generate_random_folder():
    pdf_folder_path = Path("./static/client/pdf")
    # create a random folder name
    key = Fernet.generate_key()
    enc_folder = key.decode()[:-1]
    # join the pdf_folder_path and random folder name
    dir_path = os.path.join(pdf_folder_path, enc_folder)
    # make a directory with this name
    os.mkdir(dir_path)
    file_folder = os.path.join(pdf_folder_path.absolute(), enc_folder)

    return file_folder, enc_folder


def collect_files(file_folder, combined):
    global browser
    browser = webdriver.Chrome()

    # define the core url
    BASE_URL = "https://www.canlii.org"

    doc_count = 0
    for name, code, case_law in combined:
        doc_count += 1
        # create the url
        url = get_url(name, code)
        browser.get(url)
        browser.implicitly_wait(20)
        time.sleep(2)

        # parse the HTML content
        parsed_page = BeautifulSoup(browser.page_source, "html.parser")
        entries = parsed_page.find_all("div", {"class": "title"})

        print(f"Parsing CANLII for {case_law}")

        link_text = [item.getText().strip() for item in entries]
        link_url = [item.a.get("href") for item in entries]

        try:
            second_link = link_url[0]
        except:
            print("Search did not match any documents")
            FAILED_TO_FIND.append(case_law)
            continue

        # usually there will be only one bold text, incase there's multiple...
        try:
            # if len(entries) > 1:
            #     doc_code = get_code(link_text)

            #     count = 0
            #     for item in doc_code:
            #         if item == code:
            #             break
            #         else:
            #             count += 1
            #     try:
            #         second_link = link_url[count]
            #     except:
            #         print("Problem in link", case_law)

            # create the url of the case page
            page_url = BASE_URL+second_link
            browser.get(page_url)
            time.sleep(1)
            parsed_second_page = BeautifulSoup(
                browser.page_source, "html.parser")

            # find the pdf url
            pdf_button = parsed_second_page.find_all(
                "div", {"class": "col-4 col-md-2 text-right"})
            pdf_url = pdf_button[0].a.get("href")
            full_pdf_url = BASE_URL + pdf_url
            r = requests.get(full_pdf_url)
            print(f"Downloading {case_law}...")

            # write the bytes content to a pdf file
            final_document_path = os.path.join(
                file_folder, f"{my_dict[doc_count]}_{name}.pdf")
            with open(final_document_path, "wb") as f:
                f.write(r.content)

            create_tabs(file_folder, doc_count, description=case_law)

        except:
            FAILED_TO_FIND.append(case_law)
            print(f"Cannot find {case_law}")

    browser.quit()
    file_size = merge_pdf_files(file_folder)
    print("FAILED TO FIND\n", FAILED_TO_FIND)
    return file_size, FAILED_TO_FIND

# text = ''''''
# case_law = get_case_law(text)
# names, opposer = get_names_opposer(case_law)
# codes_list = get_code(opposer, names, case_law)
# clean_names = get_clean_names(names, codes_list, case_law)
# combined = list(zip(clean_names, codes_list, case_law))
# file_folder, enc_folder = generate_random_folder()
# collect_files(combined)
