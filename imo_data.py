import requests
import concurrent
import re
import json
import urllib
from tqdm import tqdm  
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

# Converts HTML elements to text with specific formatting
def get_text(elems):
    texts = ''
    for elem in elems:
        # Convert bold text to Markdown format
        if elem.find_all('b'):  
            for ele in elem.find_all('b'):
                ele.replace_with(f'**{ele.string}**')
        # Convert hyperlink text to Markdown format
        if elem.find_all('a'):  
            for ele in elem.find_all('a'):
                if ele.string and 'href' in ele.attrs:
                    ele.replace_with(f'[{ele.string}]({ele["href"]})')
        # Add Markdown header format based on heading level
        for hx in 3, 4:
            if elem.name == f'h{hx}':  
                elem.string = (f'{"#" * hx} {elem.get_text()}\n')
        # Process LaTeX equation images, replace with alt text
        imgs = elem.find_all('img', class_=['latex', 'latexcenter'])  
        if imgs:
            for img in imgs:
                img.replace_with(img['alt'])
        # Get the text content
        text = elem.get_text()
        if text:
            texts += text
    return {'text': texts}

# Fetches problem data from a given URL using BeautifulSoup for parsing HTML
def get_problem(url, session):
    problem_html = session.get(url).content.decode('utf-8')
    soup = BeautifulSoup(problem_html, 'html.parser')
    inner_div = soup.find('div', class_='mw-parser-output')
    
    # Remove the table of contents section
    toc = inner_div.find('div', id='toc')
    if toc:
        toc.extract()
        
    data = {'Problem': None, 'Solutions': []}
    for h2 in inner_div.find_all('h2'):
        subtitle = h2.get_text().strip()
        if re.search(r'video', subtitle, re.I):
            continue
        content = []
        for sibling in h2.find_next_siblings():
            if sibling.name == "h2":
                break
            content.append(sibling)
        
        # Parse the HTML content to text and process it
        ret = get_text(content)
        if re.search(r'solution', subtitle, re.I):
            data['Solutions'].append(ret)
        elif re.search(r'problem', subtitle, re.I):
            data['Problem'] = ret
    return data

# Fetches and processes each problem using multithreading
def fetch_and_process_problem(url, session):
    main_page_url = r'https://artofproblemsolving.com/wiki/index.php/IMO_Problems_and_Solutions'
    year, no = re.search(r'(\d{4})_IMO_Problems/Problem_(\d+)', url).groups()
    absolute_url = urllib.parse.urljoin(main_page_url, url)
    problem_data = get_problem(absolute_url, session)
    return year, no, problem_data

# Main function to initiate the web scraping process
def main():
    main_page_url = r'https://artofproblemsolving.com/wiki/index.php/IMO_Problems_and_Solutions'
    output_filename = 'imo_data.json'

    session = requests.Session()
    main_page_html = session.get(main_page_url).text
    problem_reg = re.compile(r'(/wiki/index.php/(\d{4})_IMO_Problems/Problem_(\d+))', re.M)
    problem_urls = problem_reg.findall(main_page_html)

    # Print the total number of problems and the output file path
    print(f'Have totally {len(problem_urls)} problems')

    data = dict()
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Use ThreadPoolExecutor for concurrent requests
        futures = [executor.submit(fetch_and_process_problem, url, session) for url, _, _ in problem_urls]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            year, no, problem_data = future.result()
            if year not in data:
                data[year] = {}
            data[year][no] = problem_data

    # Write the scraped data to a JSON file
    with open(output_filename, 'w', encoding='utf-8') as fd:
        print(f'Writing to {output_filename} successfully')
        json.dump(data, fd, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
