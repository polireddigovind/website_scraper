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

load_dotenv()

socketio = None

def set_socketio_instance(instance):
    global socketio
    socketio = instance

url = os.getenv('supabase_url')
key = os.getenv('supabase_key')
zenrows_api_key = os.getenv('zenrows_api_key')
openai_api_keys = list(os.getenv('openai_api_keys').split(','))

supabase: Client = create_client(url, key)


def get_openai_api_key():
    while True:
        for key in openai_api_keys:
            yield key

openai_api_key_generator = get_openai_api_key()


def scrape_website_2(url, api_key):
    try:
        client = ZenRowsClient(api_key)
        params = {"js_render": "true","json_response": "true","premium_proxy": "true","proxy_country": "us"}
        response = client.get(url, params=params)
        html_content = response.text

        if "(AUTH004)" in html_content or "(REQS004)" in html_content or "AUTH005" in html_content or "BLK0001" in html_content:
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

def fetch_and_extract_text_1(url: str) -> str:
    try:
        response = requests.get(url)
        response.raise_for_status()
        extracted_text = extract_text_from_html(response.content)
        return extracted_text
    except requests.exceptions.RequestException as e:
        return scrape_website_2(url, zenrows_api_key)
    except Exception as e:
        return response
    
       
def fetch_and_extract_text(url: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': url,
        'Accept-Language': 'en-US,en;q=0.9'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 503: 
            response = fetch_and_extract_text_1(url)
        response.raise_for_status()
        encoding = response.encoding if 'charset' in response.headers.get('content-type', '').lower() else 'utf-8'
        soup = BeautifulSoup(response.content.decode(encoding, 'replace'), 'html.parser')
        extracted_text = extract_text_from_html(response.content)
        extracted_text = extracted_text + fetch_relevant_content(soup, url, headers)
        return extracted_text
    except requests.exceptions.RequestException as e:
        return fetch_and_extract_text_1(url)
        # response =  fetch_and_extract_text_1(url)
        # extracted_text = extract_text_from_html(response.content)
        # extracted_text = extracted_text + fetch_relevant_content(soup, url, headers)
        # return extracted_text
    except Exception as e:
        # return f"An error occurred while processing {url}: {e}"
        return fetch_and_extract_text_1(url)

def fetch_home_content(domain,headers):
    try:
        response = requests.get(domain, timeout=15, headers=headers)
        response.raise_for_status()  # Check if the request was successful
    except requests.RequestException as e:
        text =  fetch_and_extract_text_1(domain)
    
    encoding = response.encoding if 'charset' in response.headers.get('content-type', '').lower() else 'utf-8'
    soup = BeautifulSoup(response.content.decode(encoding, 'replace'), 'html.parser')
    soup = clean_soup_of_menu(soup)
    for a in soup.find_all('a'):
        a.decompose()
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


def extract_urls(text):
    url_pattern = re.compile(r'https?://\S+')
    urls = url_pattern.findall(text)
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
    
def fetch_relevant_content(soup):
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
        batch = extracted_urls[0:min(len(extracted_urls),20)]
        ex_urls = extract_urls(batch)
    text = ""
    summary_data_for_two_pages = ""
    count_of_two_pages=0
    for url in ex_urls:
        count_of_two_pages+=1
        response = supabase.table("links").select("website, data").eq("website", url).execute()
        check = response.data
        if check and len(check) > 0:
            summary_data_for_two_pages += check[0]["data"]
        else:
            fetch_data = fetch_home_content(url)
            if len(fetch_data) > 0:
                response = supabase.table("links").insert({"website": url, "data": fetch_data}).execute()
                summary_data_for_two_pages += fetch_data

        if count_of_two_pages==2 and len(summary_data_for_two_pages)>0:
            text+=summary_for_two_pages(summary_data_for_two_pages)
            summary_data_for_two_pages = ""

        if count_of_two_pages==2:
            count_of_two_pages=0
    if len(summary_data_for_two_pages)>0:
        text+=summary_data_for_two_pages
    return text

def scrape_website(row):
    index, domain = row
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    retries = 3
    consecutive_errors = 0  # Initialize the counter for consecutive errors
    website_data = supabase.table("website_database").select("website_url, data").eq("website_url", domain).execute()
    check = website_data.data
    if len(check) > 0:
        return index,check[0]["data"]
    
    for attempt in range(retries):
        try:
            print(f"Processing row {index + 1} - Domain {domain} - Attempt {attempt + 1}")
            response = requests.get(domain, timeout=15, headers=headers)
            if response.status_code == 429:
                print("Encountered 429 error. Waiting for 60 seconds...")
                # time.sleep(60)
                continue
            elif response.status_code == 406:
                print("Encountered 406 Not Acceptable error. Adjusting request headers...")
                headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                response = requests.get(domain, timeout=15, headers=headers)
                if response.status_code != 200:
                    print(f"Retrying after 406 error still failed for {domain}")
                    if consecutive_errors >= 10:
                        print("10 consecutive errors encountered, taking a 2-minute break.")
                        # time.sleep(120)  # 5-minute break
                        consecutive_errors = 0
                    continue
            elif response.status_code != 200:
                if attempt == 2:
                    return index,fetch_and_extract_text_1(domain)
                print(f"Unexpected status code {response.status_code} for {domain}.")
                if consecutive_errors >= 10:
                    print("10 consecutive errors encountered, taking a 2-minute break.")
                    # time.sleep(120)  # 5-minute break
                    consecutive_errors = 0
                continue

            # Successful request
            consecutive_errors = 0
            encoding = response.encoding if 'charset' in response.headers.get('content-type', '').lower() else 'utf-8'
            soup = BeautifulSoup(response.content.decode(encoding, 'replace'), 'html.parser')
            home_content = extract_text_from_html(response.content)
            inner_content = home_content + fetch_relevant_content(soup, domain, headers)
            print(f"Succeeded{index}")
            return  index,inner_content


        except requests.Timeout:
            print(f"Timeout error on {domain}.")
            inner_content = scrape_website_2(domain, zenrows_api_key)
            return index , inner_content
        except requests.RequestException as e:
            inner_content = fetch_and_extract_text_1(domain)
            return index , inner_content
        except Exception as e:
            inner_content = fetch_and_extract_text_1(domain)
            return index , inner_content

    # If all retries failed
    inner_content = fetch_and_extract_text(domain)
    return index , inner_content

# Global counter for records processed
records_processed = 0
#---------------------------   storing the data in postgres   ---------------------------
def store_data_postgres(index,data, title):
    if len(data)>0:
        supabase.table("full_data").insert({"record_index": index, "title": title, "data": data}).execute()

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
        store_data_postgres(index,inner_content, df.at[index, 'Website'])
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
    
def summary_Openai_model(data,count):
    openai_api_key = next(openai_api_key_generator)
    openai.api_key = openai_api_key
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Analyze the data and respond according to the textPrompt_openai.The response should be exactly 90 percent accuracy"},
        {"role": "user", "content": f"Please analyze the following data: {data}"},
        {"role": "user", "content": f"{textPrompt_openai}"}
    ]
    try:
        completion = openai.ChatCompletion.create(
            model=Openai_model,
            messages=messages
        )
        return completion.choices[0].message['content'].strip()
    except:
        count-=1
        if count<=0:
            return "API limit exceeded. Unable to generate data after multiple attempts."
        print("Rate limit exceeded. Rotating API key and retrying...")
        time.sleep(30) 
        return summary_Openai_model(data,count)
    
def website_summary():
    rows = []
    try:
        response = supabase.table("full_data").select("record_index, title, data").execute()
        rows = response.data
        supabase.table('full_data').delete().execute()
    except Exception as e:
        print(f"Error during Supabase operations: {e}")
    temp=0
    for row in rows:
        index=row["record_index"]
        row_count=f"model processing on row {temp} "
        if socketio:
            socketio.emit('value_update', {'value': row_count})
        summary_data = summary_openai_prompt_1(row["data"],3)
        print(temp)
        if textPrompt_openai != '':
            summary_data = summary_Openai_model(summary_data,3)
        temp+=1
        df.at[index, 'Output_data'] = summary_data


#---------------------------   Main input    ---------------------------
def scrap_fillurls_file(prompt,model,prompt2,openaimodel):
    global df  # Declare df as global as it's being accessed within process_rows
    global rows_to_process  # Similarly declare rows_to_process as global
    global input_prompt
    global model_name
    global textPrompt_openai
    global Openai_model
    global row_count
    row_count=""
    df = pd.read_csv('./uploads/scrap.csv')
    if 'Website' not in df.columns:
        return "no such column"
    position = df.columns.get_loc('Website') + 1
    if 'Output_data' not in df.columns:
        df.insert(position, 'Output_data', '')
    print(len(df)+1)
    input_prompt = prompt
    model_name = model
    Openai_model =openaimodel
    textPrompt_openai=prompt2
    rows_to_process = [(i, row['Website']) for i, row in df.iloc[0:len(df)+1].iterrows()]

    # ------------------create table if not exist to store the data for every link scraped----------------------------------------

    supabase.table('full_data').delete().execute()

    row_count="started scraping of urls"
    if socketio:
        socketio.emit('value_update', {'value': row_count})

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_rows, rows_to_process)

    print("------------------------------------------------Processing of data from database---------------------------------------------------------")

    row_count="scraped the urls successfully"
    if socketio:
        socketio.emit('value_update', {'value': row_count})

    website_summary()
    supabase.table('full_data').delete().execute()
    row_count="Task completed successfully"
    if socketio:
        socketio.emit('value_update', {'value': row_count})
    print(f"Done! Results saved in ")
    return df


