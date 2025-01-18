from langchain_groq import ChatGroq
import time
from typing import List, Dict
import warnings
warnings.filterwarnings("ignore")
import os
import json
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup

api_key = os.getenv("API_KEY")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

class output(BaseModel):
    Job_Title: str = Field(description="This is the job title provided from the query")
    state: str = Field(description="state of the job")
    country: str = Field(description="country of the job")
    salary: str = Field(description="The Job's Salary")
    
def extract_keypoint_fnc(query:str):
    '''
    This function is used for extracting the key points from the query
    '''
    llm = ChatGroq(model="llama-3.3-70b-versatile",api_key="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")
    parser = JsonOutputParser(pydantic_object=output)

    template = """
    You are a job search assistant Created by TheSlimPrep. Your task is to check through the input: {input} which might 
    be a sentence containing the job title, location of the job(state), and country. if a country isn't found in the input, set it to USA. also note, i only need the parsed json output, nothing else
    do not involve the word 'role' in the job_title value!
    {format_instructions}
    """
    prompt_template = PromptTemplate(template=template,partial_variables={"format_instructions": parser.get_format_instructions()})

    chain = prompt_template | llm
    response = chain.invoke({"input":query})
    content = json.loads(response.content)

    job_title = content["Job_Title"]
    first_job = job_title.split(" ")[0]
    sec_job = job_title.split(" ")[1]
    state = content["state"]
    country = content["country"]

    return job_title, first_job, sec_job, state, country


def scrape_flex_jobs(search_keyword: str = "", page: int = 1) -> List[Dict[str, str]]:
    base_url = "https://www.flexjobs.com/search"
    job_data = [] 
    for page in range(1, page + 1): 
        query_params = {
            "searchkeyword": search_keyword.lower(),
            "page": page,
            "sortbyrelevance": "true"}

        url = f"{base_url}?{urlencode(query_params)}"  # noqa

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all job containers
            job_listings = soup.find_all("div", class_="sc-14nyru2-3 ijOZYM")

            for job in job_listings:
                title_tag = job.find("a", class_="sc-jv5lm6-13 fQyPIb textWrap")
                title = title_tag.text.strip() if title_tag else "N/A"
                job_url = (
                    "https://www.flexjobs.com" + title_tag["href"]
                    if title_tag
                    else "N/A"
                )

                description_tag = job.find("p", class_="sc-jv5lm6-4 dAsgtY")
                description = description_tag.text.strip() if description_tag else "N/A"

                remote_option_tag = job.find(
                    "li", id=lambda x: x and "remoteoption" in x
                )
                remote_option = (
                    remote_option_tag.text.strip() if remote_option_tag else "N/A"
                )

                schedule_tag = job.find("li", id=lambda x: x and "jobschedule" in x)
                schedule = schedule_tag.text.strip() if schedule_tag else "N/A"

                salary_tag = job.find("li", id=lambda x: x and "salartRange" in x)
                salary = salary_tag.text.strip() if salary_tag else "N/A"

                job_data.append(
                    {
                        "title": title,
                        "url": job_url,
                        "description": description,
                        "company": "N/A",
                        "salary": salary,
                        "location": "N/A",
                        "remote_option": remote_option,
                        "schedule": schedule,
                    }
                )

            print(f"Page {page} data has been added to the list.")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

        time.sleep(5)

    return job_data


def process(query):
    job_title, _, _, _, country = extract_keypoint_fnc(query=query)
    job_country = job_title + country
    data = scrape_flex_jobs(job_country)
    llm = ChatGroq(model="llama-3.3-70b-versatile",api_key="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")

    formatted_prompt = """
    You are a job search assistant Created by TheSlimPrep. Your task is to check through the input: {input}, which is a list of dictionaries containing job details.
    Your output should list each job with its details in a clear format like this:

    Title: 
    URL: 
    Salary: 
    Description:
    Remote Option: 
    Schedule:

    For every job, ensure you include all keys from the dictionary. At the end, include a messagae at the end, TheSlimPrep Wishing them. you can be creative with, just make sure TheSlimPrep is in the message."
    """
    ptm = PromptTemplate.from_template(formatted_prompt)
    chain_2 = ptm | llm
    response_ot = chain_2.invoke({"input": data})
    return (response_ot.content) # This is the final response

import streamlit as st

st.title("Job Search Assistant")
st.write("### Enter your query to find job details:")

user_input = st.text_input("Enter a job title, location, or both:")

if st.button("Search Jobs"):
    if user_input.strip(): 
        st.write("Processing your request...")
        try:
            response = process(user_input)
            st.write("### Job Search Results:")
            st.write(response)
        except Exception as e:
            st.error(f"An error occurred while processing your request: {e}")
    else:
        st.warning("Please enter a valid query!")
