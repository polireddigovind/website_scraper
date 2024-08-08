import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from concurrent.futures import ThreadPoolExecutor
from zenrows import ZenRowsClient 
import re
from supabase import create_client, Client
import openai
import os
from dotenv import load_dotenv
from selenium import webdriver

# driver = webdriver.Chrome()

load_dotenv()


url = os.getenv('supabase_url')
key = os.getenv('supabase_key')
zenrows_api_key = os.getenv('zenrows_api_key')
openai_api_keys = list(os.getenv('openai_api_keys').split(','))



supabase: Client = create_client(url, key)


#      Rotating OpenAI Api keys to avoid Rate Limit
def get_openai_api_key():
    while True:
        for key in openai_api_keys:
            yield key

openai_api_key_generator = get_openai_api_key()


def zenrows_webscrap(url, api_key):
    try:
        client = ZenRowsClient(api_key)
        params = {"js_render": "true","json_response": "true","premium_proxy": "true","proxy_country": "us"}
        response = client.get(url, params=params)
        html_content = response.text
        if "(AUTH004)" in html_content or "(REQS004)" in html_content or "AUTH005" in html_content or "BLK0001" in html_content or "RESP002" in html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text().replace('\n', '').replace('\t', '').replace('\r', ' ')
            return text
        except Exception as e:
            return html_content
    
    except requests.exceptions.RequestException as e:
        return html_content
    except Exception as e:
        return html_content
    
def extract_text_from_html(content: bytes) -> str:
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    return ' '.join(text.split())

def fetch_and_extract_text(url: str) -> str:
    try:
        response = requests.get(url,timeout=15)
        response.raise_for_status()
        extracted_text = extract_text_from_html(response.content)
        return extracted_text
    except requests.exceptions.RequestException as e:
        pass
    except Exception as e:
        pass
    return zenrows_webscrap(url,zenrows_api_key)

def fetch_home_content(domain):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': domain,
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    response = requests.get(domain, timeout=10, headers=headers)
    if response.status_code != 200:
        return  fetch_and_extract_text(domain)
    response.raise_for_status()  # Check if the request was successful
    
    encoding = response.encoding if 'charset' in response.headers.get('content-type', '').lower() else 'utf-8'
    soup = BeautifulSoup(response.content.decode(encoding, 'replace'), 'html.parser')
    soup = clean_soup_of_menu(soup)
    # for a in soup.find_all('a'):
    #     a.decompose()
    text = ' '.join(soup.get_text().split()).replace('\n', ' ')

    # New code to limit text to 10000 characters
    if len(text) > 10000:
        text = text[:10000]
        
    return text


def clean_soup_of_menu(soup):
    for tag in soup.find_all(['nav', 'menu', 'aside']):
        tag.decompose()
    for class_or_id in ['navbar', 'menu', 'main-nav', 'side-nav', 'top-nav']:
        for tag in soup.find_all(attrs={"class": class_or_id}) + soup.find_all(attrs={"id": class_or_id}):
            tag.decompose()
    return soup


def extract_urls(text_list):
    url_pattern = re.compile(r'https?://\S+')
    combined_text = ' '.join(text_list)
    
    urls = url_pattern.findall(combined_text)
    unique_urls = list(set(url.rstrip(' ,.;:') for url in urls))
    return unique_urls

def extract_valid_urls(data):
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        extracted_urls = []
        for item in data:
            if re.match(url_pattern, item):
                extracted_urls.append(item)
        return extracted_urls
    

def summary_for_two_pages(data_source):
    openai_api_key = next(openai_api_key_generator)
    openai.api_key = openai_api_key
    messages = [
    {"role": "system", "content": "You are a helpful assistant. Analyze the data and provide the summary of the data."},
    {"role": "user", "content": f"obtained the following data: {data_source}. Based on this, please summarise the data"}
    ]
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return completion.choices[0].message['content'].strip()
    except:
        return ""

def fetch_relevant_content(soup,domain):
    links = soup.find_all('a')
    extracted_links = []
    for link in links:
        href = link.get('href')
        if href:
            extracted_links.append(href)

    # Extract valid URLs from the data list
    extracted_urls = extract_valid_urls(extracted_links)
    ex_urls = []
    if len(extracted_urls)>0 :
        batch = extracted_urls[0:min(len(extracted_urls),10)]
        ex_urls = extract_urls(batch)

    text = ""
    summary_data_for_two_pages = ""
    count_of_two_pages=0
    inner_links_of_website = ""
    for url in ex_urls:
        response = supabase.table("links").select("website, data").eq("website", url).execute()
        check = response.data
        if check and len(check) > 0:
            fetch_data= check[0]["data"]
        else :
            fetch_data = fetch_home_content(url)
            if len(fetch_data) > 0:
                supabase.table("links").insert({"website": url,"data": fetch_data}).execute()
        count_of_two_pages+=1
        inner_links_of_website += url
        inner_links_of_website += "  ,  "
        if len(fetch_data) > 0:
            summary_data_for_two_pages += fetch_data

        if count_of_two_pages==2 and len(summary_data_for_two_pages)>0:
            text+=summary_for_two_pages(summary_data_for_two_pages)
            summary_data_for_two_pages = ""

        if count_of_two_pages==2:
            count_of_two_pages=0
    if len(summary_data_for_two_pages)>0:
        text+=summary_data_for_two_pages
    if len(inner_links_of_website)>0:
        supabase.table("website_links").insert({"website_url": domain,"urls": inner_links_of_website}).execute()
    return text


def scrape_website(row):
    index, domain = row
    headers_1 = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    headers_2 = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': domain,
        'Accept-Language': 'en-US,en;q=0.9'
    }
    website_data = supabase.table("website_database").select("website_url, data").eq("website_url", domain).execute()
    check = website_data.data
    if len(check) > 0:
        return index,check[0]["data"]
    
    response_1 = requests.get(domain, headers=headers_1,timeout=15)
    if response_1.status_code != 200:
        response_2 = requests.get(domain,headers=headers_2,timeout=15)
        if response_2.status_code != 200:
            response_3 = requests.get(domain,timeout=15)
            if response_3.status_code!= 200:
                return index,fetch_and_extract_text(domain,timeout=15)
    print(f"success---{index}---{domain}")
    if response_1.status_code == 200:
        encoding = response_1.encoding if 'charset' in response_1.headers.get('content-type', '').lower() else 'utf-8'
        soup = BeautifulSoup(response_1.content.decode(encoding, 'replace'), 'html.parser')
        home_content = extract_text_from_html(response_1.content)
        # if "please enable JS to make this app work" in home_content:
        #     driver = webdriver.Chrome()
        #     driver.get('http://example.com')
        #     time.sleep(5) 
        #     page_source = driver.page_source
        #     soup = BeautifulSoup(page_source, 'html.parser')
        #     driver.quit()
        #     home_content = extract_text_from_html(page_source)
        inner_content = home_content + fetch_relevant_content(soup,domain)
        return index, inner_content
    if response_2.status_code == 200:
        encoding = response_2.encoding if 'charset' in response_2.headers.get('content-type', '').lower() else 'utf-8'
        soup = BeautifulSoup(response_2.content.decode(encoding, 'replace'), 'html.parser')
        home_content = extract_text_from_html(response_2.content)
        inner_content = home_content + fetch_relevant_content(soup,domain)
        return index, inner_content
    if response_3.status_code ==200:
        soup = BeautifulSoup(response_3.content, 'html.parser')
        home_content = extract_text_from_html(response_3.content)
        inner_content = home_content + fetch_relevant_content(soup,domain)
        return index, inner_content


# Global counter for records processed
records_processed = 0
#---------------------------   storing the data in postgres   ---------------------------
def store_data_supabase(index,data, title):
    if len(data) > 0:
        supabase.table("sample_data").insert({"record_index": index, "title": title, "data": data}).execute()

def process_rows(row):
    global records_processed  # Make the counter accessible within the function
    try:
        if records_processed >= 2000:
            print("Processed 2000 records, taking a 5-minute break...")
            time.sleep(300)  # Wait for 5 minutes
            records_processed = 0  # Reset the counter
        result = scrape_website(row)
        records_processed += 1  # Increment records processed

        # Assuming 'result' is unpacked correctly here and 'df' is defined globally
        index, inner_content = result
        if len(inner_content) > 10000:
            inner_content = inner_content[:10000]
        website_data = supabase.table("website_database").select("website_url, data").eq("website_url", df.at[index, 'Website']).execute()
        if len(website_data.data)==0 and len(inner_content) > 0:
            supabase.table("website_database").insert({"website_url": df.at[index, 'Website'], "data": inner_content}).execute()
        store_data_supabase(index,inner_content, df.at[index, 'Website'])
    except Exception as e:
        pass

#---------------------------   website Summary from LLM   ---------------------------
def summary_openai_prompt_1(data,count):
    openai_api_key = next(openai_api_key_generator)
    openai.api_key = openai_api_key
    messages = [
    {"role": "system", "content": "You are a helpful assistant. Analyze the data and respond according to the input prompt precisely. The response should be exactly 90 percent accuracy"},
    {"role": "user", "content": f"We have scraped data for a website and obtained the following summary: {data}. Based on this, please provide a response to this prompt: {input_prompt}"}
    ]
    try:
        completion = openai.ChatCompletion.create(
            model=model_name,
            messages=messages,
            temperature=0, 
        )
        return completion.choices[0].message['content'].strip()
    except Exception as e:
        count-=1
        if count<=0:
            return data
        print(f"Rate limit exceeded. Rotating API key and retrying...{e}")
        time.sleep(30) 
        return summary_openai_prompt_1(data,count)

def summary_Openai_model(website,data,count):
    openai_api_key = next(openai_api_key_generator)
    openai.api_key = openai_api_key
    messages = [
    {"role": "system", "content": "You are a helpful assistant. Analyze the data and respond according to the input prompt precisely. The response should be exactly 90 percent accuracy"},
    {"role": "user", "content": f"We have scraped data for {website} and obtained the following summary: {data}. Based on this, please provide a response to this prompt: {textPrompt_openai}"}
    ]


    try:
        completion = openai.ChatCompletion.create(
            model=openai_model,
            messages=messages,
            temperature=0, 
        )
        return completion.choices[0].message['content'].strip()
    except:
        count-=1
        print(count)
        if count<=0:
            return "API limit exceeded. Unable to generate data after multiple attempts."
        print("Rate limit exceeded. Rotating API key and retrying...")
        time.sleep(30) 
        return summary_Openai_model(website,data,count)

def website_summary():
    rows = []
    try:
        response = supabase.table("sample_data").select("record_index, title, data").execute()
        rows = response.data
        supabase.table('sample_data').delete().execute()
    except Exception as e:
        print(f"Error during Supabase operations: {e}")

    cnt=0
    for row in rows:
        print(cnt)
        if cnt ==5:
            break
        summary_data = summary_openai_prompt_1(row["data"],3)
        if textPrompt_openai != '':
            openai_summary_data = summary_Openai_model(row["title"],summary_data,3)
            openai_list_data.append({'title': row["title"], 'data': openai_summary_data})

        global_list_data.append({'title': row["title"], 'data': summary_data})
        cnt+=1

#---------------------------   Main input    ---------------------------
def scrap_sample_data(prompt,model,prompt2,openaimodel,urls,filename):
    global df  # Declare df as global as it's being accessed within process_rows
    global rows_to_process  # Similarly declare rows_to_process as global
    global input_prompt
    global global_list_data
    global openai_list_data
    global model_name
    global textPrompt_openai
    global openai_model
    df = pd.read_csv('./uploads/scrap.csv')
    if len(filename) == 0:
        df = pd.DataFrame(urls, columns=['Website'])
    model_name = model
    openai_model=openaimodel
    textPrompt_openai=prompt2
    global_list_data = []
    openai_list_data = []
    input_prompt = prompt
    if 'Website' not in df.columns:
        return [{'title': "no such column", 'data': "wrong column name"}]
    
    rows_to_process = [(i, row['Website']) for i, row in df.iloc[0:10].iterrows()]
    

    supabase.table('sample_data').delete().execute()
         # ------------------create table if not exist to store the data for every link scraped----------------------------------------
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_rows, rows_to_process)
    
    print("-----------------------------------------------------------------------------------------")
    website_summary()
    supabase.table('sample_data').delete().execute()
    print("Data Scraping completed")
    if len(openai_list_data)>0:
        global_list_data.extend(openai_list_data)

    return global_list_data