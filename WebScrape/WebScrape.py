#!/usr/bin/env python
# coding: utf-8

# ## Using google query

# In[27]:


# import necessary libraries
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from lxml import html

# define a more inclusive regular expression pattern to capture URLs
url_pattern = r'\b(?:https?://)?(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:\s*›\s*[a-z0-9-]+)*'

# function to extract URLs from text content of each elements
def extract_urls(text):
    # Find all potential URLs
    potential_urls = re.findall(url_pattern, text, re.IGNORECASE)
    # Transform into clickable URLs if not already in complete form
    urls = []
    for url in potential_urls:
        if not url.startswith('http'):
            url = 'https://' + url
        urls.append(url.replace(' › ', '/'))
    return urls
    
# function to extrack html page source of specific google query, inject seo-pixels in it and store the html page
def google_search_and_insert_seo_pixel(query):
    options = FirefoxOptions()
    
    options.add_argument("--lang=en")
    options.add_argument("--headless")
    
    service = FirefoxService(executable_path=r'/Users/dipanshuksh/Downloads/geckodriver')
    driver = webdriver.Firefox(service=service, options=options)

    url = f"https://www.google.com/search?q={query}&hl=en&gl=AE"

    driver.get(url)

    time.sleep(5)

    # scroll 5 times in the google page
    for _ in range(5):  
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(5)
        
    # execute the initial JavaScript that sets seo-pixels
    js_code = '''
    function setSEOAttributes(element) {
        for (var i = 0; i < element.children.length; i++) {
            var child = element.children[i];
            var rect = child.getBoundingClientRect();
            var seoPixelValue = `[x:${rect.x.toFixed(2)},y:${rect.y.toFixed(2)},w:${rect.width.toFixed(2)},h:${rect.height.toFixed(2)}]`;
            child.setAttribute('seo-pixel', seoPixelValue);
            setSEOAttributes(child);
        }
        var outerHTML = element.outerHTML;
        var scrollHeight = element.scrollHeight;
    
        return {
            outerHTML: outerHTML,
            scrollHeight: scrollHeight
        };
    }
    var rootElement = document.querySelector("html");
    return setSEOAttributes(rootElement);
    '''
    result = driver.execute_script(js_code)

    # store the html content with injected seo-pixels
    html_content = result['outerHTML']

    time.sleep(3)

    # save the html content witj injected seo-pixels for later use
    with open(f'{query}-seo-pixel.html', 'w') as file:
        time.sleep(3)
        file.write(html_content)

    time.sleep(3)
    
    driver.quit()

    # parse the html content with seo-pixels with lxml
    root = html.fromstring(html_content)

    # return the parsed content
    return root

# function to get normal ad contents from the previously saved html content containing seo-pixels
def get_normal_ad_contents(root):

    df_ad = pd.DataFrame()
    
    # filtering function to get the desired normal ad contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 600 <= w <= 652 and 116 <= h < 200 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-text-ad' in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-text-ad]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
        
        ad_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                
                # extract URLs from the text
                url_data = extract_urls(all_text)
        
                ad_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'ad'
                })
        
        # filter out duplicates
        ad_seen = set()
        ad_unique_elements = []
        
        for element in ad_element_data:
            ad_identifier = (element['text'], element['y'])  # a tuple of text and y as an unique identifier
            if ad_identifier not in ad_seen:
                ad_seen.add(ad_identifier)
                ad_unique_elements.append(element)
        
        # format links
        for item in ad_unique_elements:
            item['links'] = ', '.join(item['links'])
            
        # convert to DataFrame
        df_ad = pd.DataFrame(ad_unique_elements)
        
        df_ad['size'] = df_ad['width'].astype(str) + ' x ' + df_ad['height'].astype(str)

        print("\nFound normal ad contents.\n")
        
    else:
        print("\nNo normal ad contents.\n")
        
    return df_ad

# function to get normal organic contents from the previously saved html content containing seo-pixels
def get_normal_organic_contents(root):

    df_organic = pd.DataFrame()
    
    # filtering function to get the desired normal organic contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if w == 652 and 116 <= h < 200 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-text-ad' not in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and not(@data-text-ad)]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
        
        organic_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                
                # extract URLs from the text
                url_data = extract_urls(all_text)
        
                organic_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'organic'
                })
        
        # filter out duplicates
        organic_seen = set()
        organic_unique_elements = []
        
        for element in organic_element_data:
            organic_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if organic_identifier not in organic_seen:
                organic_seen.add(organic_identifier)
                organic_unique_elements.append(element)
        
        # format links
        for item in organic_unique_elements:
            item['links'] = ', '.join(item['links'])
            
        # convert to DataFrame
        df_organic = pd.DataFrame(organic_unique_elements)
        
        df_organic['size'] = df_organic['width'].astype(str) + ' x ' + df_organic['height'].astype(str)

        print("\nFound normal Organic contents.\n")
    
    else:
        print("\nNo normal Organic contents.\n")
        
    return df_organic
    
# function to get card ad contents from the previously saved html content containing seo-pixels
def get_ad_card_contents(root):

    df_ad_card = pd.DataFrame()
    
    # filtering function to get the desired card ad contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 130 <= w < 160 and 350 <= h < 420 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-pla-slot-pos' in element.attrib:
                    return True
        return False
        
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-pla-slot-pos]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
            
        ad_card_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                    
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                    
                # extract URLs from the text
                url_data = extract_urls(all_text)
            
                ad_card_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'ad cards'
                })
            
        # filter out duplicates
        ad_card_seen = set()
        ad_card_unique_elements = []
            
        for element in ad_card_element_data:
            ad_card_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if ad_card_identifier not in ad_card_seen:
                ad_card_seen.add(ad_card_identifier)
                ad_card_unique_elements.append(element)
            
        # format links
        for item in ad_card_unique_elements:
            item['links'] = ', '.join(item['links'])
                
        # convert to DataFrame
        df_ad_card = pd.DataFrame(ad_card_unique_elements)
            
        df_ad_card['size'] = df_ad_card['width'].astype(str) + ' x ' + df_ad_card['height'].astype(str)
        
        print("\nFound AD Card Elements\n")
    
    else:
        print("\nNo AD Card Elements\n")
        
    return df_ad_card

# function to get card organic contents from the previously saved html content containing seo-pixels
def get_organic_card_contents(root):

    df_organic_card = pd.DataFrame()
    
    # filtering function to get the desired card organic contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 130 <= w < 170 and 350 <= h < 420 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-laoid' in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-laoid]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
            
        organic_card_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                    
                # Extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                    
                # Extract URLs from the text
                url_data = extract_urls(all_text)
            
                organic_card_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'organic cards'
                })
            
        # filter out duplicates
        organic_card_seen = set()
        organic_card_unique_elements = []
        
        for element in organic_card_element_data:
            organic_card_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if organic_card_identifier not in organic_card_seen:
                organic_card_seen.add(organic_card_identifier)
                organic_card_unique_elements.append(element)
            
        # format links
        for item in organic_card_unique_elements:
            item['links'] = ', '.join(item['links'])
                
        # convert to DataFrame
        df_organic_card = pd.DataFrame(organic_card_unique_elements)
            
        df_organic_card['size'] = df_organic_card['width'].astype(str) + ' x ' + df_organic_card['height'].astype(str)
        
        print("\nFound Organic Card Elements\n")
    
    else:
        print("\nNo Organic Card Elements\n")

    return df_organic_card
    
# function to get csv files for each type of contents
def create_csv_files(df_ad, df_organic, df_ad_card, df_organic_card, query):
    
    df_ad.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{query}_ad.csv', index = False)

    df_organic.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{query}_organic.csv', index = False)

    df_ad_card.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{query}_ad_cards.csv', index=False)

    df_organic_card.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{query}_organic_cards.csv', index=False)


def main(query):
    
    root = google_search_and_insert_seo_pixel(query)

    df_ad = get_normal_ad_contents(root)

    df_organic = get_normal_organic_contents(root)

    df_ad_card = get_ad_card_contents(root)
    
    df_organic_card = get_organic_card_contents(root)

    create_csv_files(df_ad, df_organic, df_ad_card, df_organic_card, query)

    print("\nSuccessfully executed!\n")


if __name__ == "__main__":
    main('best luggage bags in usa')


# ## Using html page

# ### Carry on Travel Luggage.html

# In[28]:


# import necessary libraries
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from lxml import html


# define a more inclusive regular expression pattern to capture URLs
url_pattern = r'\b(?:https?://)?(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:\s*›\s*[a-z0-9-]+)*'


# function to extract URLs from text
def extract_urls(text):
    # Find all potential URLs
    potential_urls = re.findall(url_pattern, text, re.IGNORECASE)
    # Transform into clickable URLs if not already in complete form
    urls = []
    for url in potential_urls:
        if not url.startswith('http'):
            url = 'https://' + url
        urls.append(url.replace(' › ', '/'))
    return urls

# function to inject seo-pixels in the specific html page and store it
def insert_seo_pixel(html_file_name):
    options = FirefoxOptions()
    
    options.add_argument("--lang=en")
    options.add_argument("--headless")
    
    service = FirefoxService(executable_path=r'/Users/dipanshuksh/Downloads/geckodriver')
    
    driver = webdriver.Firefox(service=service, options=options)
    
    url = f"file:///Users/dipanshuksh/june-17/Html/{html_file_name}.html"
    
    driver.get(url)

    # execute the initial JavaScript that sets seo-pixels
    js_code = '''
    function setSEOAttributes(element) {
        for (var i = 0; i < element.children.length; i++) {
            var child = element.children[i];
            var rect = child.getBoundingClientRect();
            var seoPixelValue = `[x:${rect.x.toFixed(2)},y:${rect.y.toFixed(2)},w:${rect.width.toFixed(2)},h:${rect.height.toFixed(2)}]`;
            child.setAttribute('seo-pixel', seoPixelValue);
            setSEOAttributes(child);
        }
        var outerHTML = element.outerHTML;
        var scrollHeight = element.scrollHeight;
    
        return {
            outerHTML: outerHTML,
            scrollHeight: scrollHeight
        };
    }
    var rootElement = document.querySelector("html");
    return setSEOAttributes(rootElement);
    '''
    result = driver.execute_script(js_code)

    # store the html content with injected seo-pixels
    html_content = result['outerHTML']

    # save the html content witj injected seo-pixels for later use
    with open(f'{html_file_name}-seo-pixel.html', 'w') as file:
        file.write(html_content)
    
    driver.quit()

    # parse the content with lxml
    root = html.fromstring(html_content)
    
    return root

# function to get normal ad contents from the previously saved html content containing seo-pixels
def get_normal_ad_contents(root):

    df_ad = pd.DataFrame()
    # filtering function to get the desired normal ad contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 600 <= w <= 652 and 116 <= h < 200 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-text-ad' in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-text-ad]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
        
        ad_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                
                # extract URLs from the text
                url_data = extract_urls(all_text)
        
                ad_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'ad'
                })
        
        # filter out duplicates
        ad_seen = set()
        ad_unique_elements = []
        
        for element in ad_element_data:
            ad_identifier = (element['text'], element['y'])  # a tuple of text and y as an unique identifier
            if ad_identifier not in ad_seen:
                ad_seen.add(ad_identifier)
                ad_unique_elements.append(element)
        
        # format links
        for item in ad_unique_elements:
            item['links'] = ', '.join(item['links'])
            
        # convert to DataFrame
        df_ad = pd.DataFrame(ad_unique_elements)
        
        df_ad['size'] = df_ad['width'].astype(str) + ' x ' + df_ad['height'].astype(str)

        print("\nFound normal ad contents.\n")
        
    else:
        print("\nNo normal ad contents.\n")
        
    return df_ad

# function to get normal organic contents from the previously saved html content containing seo-pixels
def get_normal_organic_contents(root):

    df_organic = pd.DataFrame()
    
    # filtering function to get the desired normal organic contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if w == 652 and 116 <= h < 200 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-text-ad' not in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and not(@data-text-ad)]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
        
        organic_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                
                # extract URLs from the text
                url_data = extract_urls(all_text)
        
                organic_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'organic'
                })
        
        # filter out duplicates
        organic_seen = set()
        organic_unique_elements = []
        
        for element in organic_element_data:
            organic_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if organic_identifier not in organic_seen:
                organic_seen.add(organic_identifier)
                organic_unique_elements.append(element)
        
        # format links
        for item in organic_unique_elements:
            item['links'] = ', '.join(item['links'])
            
        # convert to DataFrame
        df_organic = pd.DataFrame(organic_unique_elements)
        
        df_organic['size'] = df_organic['width'].astype(str) + ' x ' + df_organic['height'].astype(str)

        print("\nFound normal Organic contents.\n")
    
    else:
        print("\nNo normal Organic contents.\n")
        
    return df_organic
    
# function to get card ad contents from the previously saved html content containing seo-pixels
def get_ad_card_contents(root):

    df_ad_card = pd.DataFrame()
    
    # filtering function to get the desired card ad contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 130 <= w < 160 and 350 <= h < 420 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-pla-slot-pos' in element.attrib:
                    return True
        return False
        
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-pla-slot-pos]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
            
        ad_card_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                    
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                    
                # extract URLs from the text
                url_data = extract_urls(all_text)
            
                ad_card_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'ad cards'
                })
            
        # filter out duplicates
        ad_card_seen = set()
        ad_card_unique_elements = []
            
        for element in ad_card_element_data:
            ad_card_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if ad_card_identifier not in ad_card_seen:
                ad_card_seen.add(ad_card_identifier)
                ad_card_unique_elements.append(element)
            
        # format links
        for item in ad_card_unique_elements:
            item['links'] = ', '.join(item['links'])
                
        # convert to DataFrame
        df_ad_card = pd.DataFrame(ad_card_unique_elements)
            
        df_ad_card['size'] = df_ad_card['width'].astype(str) + ' x ' + df_ad_card['height'].astype(str)
        
        print("\nFound AD Card Elements\n")
    
    else:
        print("\nNo AD Card Elements\n")
        
    return df_ad_card

# function to get card organic contents from the previously saved html content containing seo-pixels
def get_organic_card_contents(root):

    df_organic_card = pd.DataFrame()
    
    # filtering function to get the desired card organic contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 130 <= w < 170 and 350 <= h < 420 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-laoid' in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-laoid]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
            
        organic_card_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                    
                # Extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                    
                # Extract URLs from the text
                url_data = extract_urls(all_text)
            
                organic_card_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'organic cards'
                })
            
        # filter out duplicates
        organic_card_seen = set()
        organic_card_unique_elements = []
        
        for element in organic_card_element_data:
            organic_card_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if organic_card_identifier not in organic_card_seen:
                organic_card_seen.add(organic_card_identifier)
                organic_card_unique_elements.append(element)
            
        # format links
        for item in organic_card_unique_elements:
            item['links'] = ', '.join(item['links'])
                
        # convert to DataFrame
        df_organic_card = pd.DataFrame(organic_card_unique_elements)
            
        df_organic_card['size'] = df_organic_card['width'].astype(str) + ' x ' + df_organic_card['height'].astype(str)
        
        print("\nFound Organic Card Elements\n")
    
    else:
        print("\nNo Organic Card Elements\n")

    return df_organic_card

# function to get csv files for each type of contents
def create_csv_files(df_ad, df_organic, df_ad_card, df_organic_card, html_file_name):
    
    df_ad.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{html_file_name}_ad.csv', index=False)

    df_organic.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{html_file_name}_organic.csv', index=False)
            
    df_ad_card.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{html_file_name}_ad_cards.csv', index=False)

    df_organic_card.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{html_file_name}_organic_cards.csv', index=False)

def main(html_file_name):
    
    root = insert_seo_pixel(html_file_name)

    df_ad = get_normal_ad_contents(root)

    df_organic = get_normal_organic_contents(root)

    df_ad_card = get_ad_card_contents(root)

    df_organic_card = get_organic_card_contents(root)
    
    create_csv_files(df_ad, df_organic, df_ad_card, df_organic_card, html_file_name)

    print("\nSuccessfully executed!\n")

if __name__ == "__main__":
    main('carry_on_travel_luggage')


# ### Shoe.html

# In[29]:


# import necessary libraries
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from lxml import html


# define a more inclusive regular expression pattern to capture URLs
url_pattern = r'\b(?:https?://)?(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:\s*›\s*[a-z0-9-]+)*'


# function to extract URLs from text
def extract_urls(text):
    # Find all potential URLs
    potential_urls = re.findall(url_pattern, text, re.IGNORECASE)
    # Transform into clickable URLs if not already in complete form
    urls = []
    for url in potential_urls:
        if not url.startswith('http'):
            url = 'https://' + url
        urls.append(url.replace(' › ', '/'))
    return urls


# function to inject seo-pixels in the specific html page and store it
def insert_seo_pixel(html_file_name):
    options = FirefoxOptions()
    
    options.add_argument("--lang=en")
    options.add_argument("--headless")
    
    service = FirefoxService(executable_path=r'/Users/dipanshuksh/Downloads/geckodriver')
    
    driver = webdriver.Firefox(service=service, options=options)
    
    url = f"file:///Users/dipanshuksh/june-17/Html/{html_file_name}.html"
    
    driver.get(url)

    # execute the initial JavaScript that sets seo-pixels
    js_code = '''
    function setSEOAttributes(element) {
        for (var i = 0; i < element.children.length; i++) {
            var child = element.children[i];
            var rect = child.getBoundingClientRect();
            var seoPixelValue = `[x:${rect.x.toFixed(2)},y:${rect.y.toFixed(2)},w:${rect.width.toFixed(2)},h:${rect.height.toFixed(2)}]`;
            child.setAttribute('seo-pixel', seoPixelValue);
            setSEOAttributes(child);
        }
        var outerHTML = element.outerHTML;
        var scrollHeight = element.scrollHeight;
    
        return {
            outerHTML: outerHTML,
            scrollHeight: scrollHeight
        };
    }
    var rootElement = document.querySelector("html");
    return setSEOAttributes(rootElement);
    '''
    result = driver.execute_script(js_code)

    # store the html content with injected seo-pixels
    html_content = result['outerHTML']

    # save the html content witj injected seo-pixels for later use
    with open(f'{html_file_name}-seo-pixel.html', 'w') as file:
        file.write(html_content)
    
    driver.quit()

    # parse the content with lxml
    root = html.fromstring(html_content)
    
    return root


# function to get normal ad contents from the previously saved html content containing seo-pixels
def get_normal_ad_contents(root):

    df_ad = pd.DataFrame()
    
    # filtering function to get the desired normal ad contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 600 <= w <= 652 and 116 <= h < 200 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-text-ad' in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-text-ad]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
        
        ad_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                
                # extract URLs from the text
                url_data = extract_urls(all_text)
        
                ad_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'ad'
                })
        
        # filter out duplicates
        ad_seen = set()
        ad_unique_elements = []
        
        for element in ad_element_data:
            ad_identifier = (element['text'], element['y'])  # a tuple of text and y as an unique identifier
            if ad_identifier not in ad_seen:
                ad_seen.add(ad_identifier)
                ad_unique_elements.append(element)
        
        # format links
        for item in ad_unique_elements:
            item['links'] = ', '.join(item['links'])
            
        # convert to DataFrame
        df_ad = pd.DataFrame(ad_unique_elements)
        
        df_ad['size'] = df_ad['width'].astype(str) + ' x ' + df_ad['height'].astype(str)

        print("\nFound normal ad contents.\n")
        
    else:
        print("\nNo normal ad contents.\n")
        
    return df_ad

# function to get normal organic contents from the previously saved html content containing seo-pixels
def get_normal_organic_contents(root):

    df_organic = pd.DataFrame()
    
    # filtering function to get the desired normal organic contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if w == 652 and 116 <= h < 200 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-text-ad' not in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and not(@data-text-ad)]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
        
        organic_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                
                # extract URLs from the text
                url_data = extract_urls(all_text)
        
                organic_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'organic'
                })
        
        # filter out duplicates
        organic_seen = set()
        organic_unique_elements = []
        
        for element in organic_element_data:
            organic_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if organic_identifier not in organic_seen:
                organic_seen.add(organic_identifier)
                organic_unique_elements.append(element)
        
        # format links
        for item in organic_unique_elements:
            item['links'] = ', '.join(item['links'])
            
        # convert to DataFrame
        df_organic = pd.DataFrame(organic_unique_elements)
        
        df_organic['size'] = df_organic['width'].astype(str) + ' x ' + df_organic['height'].astype(str)

        print("\nFound normal Organic contents.\n")
    
    else:
        print("\nNo normal Organic contents.\n")
        
    return df_organic
    
# function to get card ad contents from the previously saved html content containing seo-pixels
def get_ad_card_contents(root):

    df_ad_card = pd.DataFrame()
    
    # filtering function to get the desired card ad contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 130 <= w < 160 and 350 <= h < 420 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-pla-slot-pos' in element.attrib:
                    return True
        return False
        
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-pla-slot-pos]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
            
        ad_card_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                    
                # extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                    
                # extract URLs from the text
                url_data = extract_urls(all_text)
            
                ad_card_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'ad cards'
                })
            
        # filter out duplicates
        ad_card_seen = set()
        ad_card_unique_elements = []
            
        for element in ad_card_element_data:
            ad_card_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if ad_card_identifier not in ad_card_seen:
                ad_card_seen.add(ad_card_identifier)
                ad_card_unique_elements.append(element)
            
        # format links
        for item in ad_card_unique_elements:
            item['links'] = ', '.join(item['links'])
                
        # convert to DataFrame
        df_ad_card = pd.DataFrame(ad_card_unique_elements)
            
        df_ad_card['size'] = df_ad_card['width'].astype(str) + ' x ' + df_ad_card['height'].astype(str)
        
        print("\nFound AD Card Elements\n")
    
    else:
        print("\nNo AD Card Elements\n")
        
    return df_ad_card

# function to get card organic contents from the previously saved html content containing seo-pixels
def get_organic_card_contents(root):

    df_organic_card = pd.DataFrame()
    
    # filtering function to get the desired card organic contents
    def is_target_div(element):
        seo_pixel = element.get('seo-pixel')
        if seo_pixel:
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', seo_pixel)
            if match:
                x, y, w, h = map(float, match.groups())
                if 130 <= w < 170 and 350 <= h < 420 and not (x == 0 and y == 0 and w == 0 and h == 0) and 'data-laoid' in element.attrib:
                    return True
        return False
    
    # find all div elements that meet the criteria
    target_divs = root.xpath('//div[@seo-pixel and @data-laoid]')

    # make sure the elements match our criteria in filtering function
    target_divs = [div for div in target_divs if is_target_div(div)]

    # if even an element is found, enter this loop
    if target_divs:
            
        organic_card_element_data = []

        # loop through each elements to get their inner contents
        for element in target_divs:
            rect = element.get('seo-pixel')
            match = re.match(r'\[x:(\d+(?:\.\d+)?),y:(\d+(?:\.\d+)?),w:(\d+(?:\.\d+)?),h:(\d+(?:\.\d+)?)\]', rect)
            if match:
                x, y, w, h = map(float, match.groups())
                    
                # Extract all text within the element
                all_text = ' '.join(element.xpath('.//text()')).strip()
                    
                # Extract URLs from the text
                url_data = extract_urls(all_text)
            
                organic_card_element_data.append({
                    'tag': element.tag,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'text': all_text,
                    'links': url_data,
                    'content_type': 'organic cards'
                })
            
        # filter out duplicates
        organic_card_seen = set()
        organic_card_unique_elements = []
        
        for element in organic_card_element_data:
            organic_card_identifier = (element['text'], element['y'])  # use a tuple of text and y as an identifier
            if organic_card_identifier not in organic_card_seen:
                organic_card_seen.add(organic_card_identifier)
                organic_card_unique_elements.append(element)
            
        # format links
        for item in organic_card_unique_elements:
            item['links'] = ', '.join(item['links'])
                
        # convert to DataFrame
        df_organic_card = pd.DataFrame(organic_card_unique_elements)
            
        df_organic_card['size'] = df_organic_card['width'].astype(str) + ' x ' + df_organic_card['height'].astype(str)

        print("\nFound Organic Card Elements\n")
    
    else:
        print("\nNo Organic Card Elements\n")

    return df_organic_card

# function to get csv files for each type of contents
def create_csv_files(df_ad, df_organic, df_ad_card, df_organic_card, html_file_name):
    
    df_ad.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{html_file_name}_ad.csv', index=False)

    df_organic.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{html_file_name}_organic.csv', index=False)
            
    df_ad_card.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{html_file_name}_ad_cards.csv', index=False)

    df_organic_card.to_csv(f'/Users/dipanshuksh/June-17/CSVs/{html_file_name}_organic_cards.csv', index=False)

def main(html_file_name):
    
    root = insert_seo_pixel(html_file_name)

    df_ad = get_normal_ad_contents(root)

    df_organic = get_normal_organic_contents(root)

    df_ad_card = get_ad_card_contents(root)

    df_organic_card = get_organic_card_contents(root)
    
    create_csv_files(df_ad, df_organic, df_ad_card, df_organic_card, html_file_name)

    print("\nSuccessfully executed!\n")

if __name__ == "__main__":
    main('shoe')


# In[ ]:




