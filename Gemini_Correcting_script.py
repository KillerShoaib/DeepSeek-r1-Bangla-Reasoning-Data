import json
from typing import List, Dict
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from google import genai
import time
from datetime import datetime
import logging
load_dotenv()

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/correct_answer_separation_using_gemini_log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)



## pydantic model for structure output
class item(BaseModel):
    id: str = Field(description="The unique id of the object which given for each sample.")
    correct: bool = Field(description="A binary value representing if the sample's generated ans and given corrected answer are same. If same then the value is True otherwise it's False")

class Sample(BaseModel):
    all_samples: List[item] = Field(description="A list of objects containing the id and correct value for each sample.")

prompt = """
You're given 10 samples (delimitated <samples></samples>) , each sample contain an unique id (string value), a generated ans and correct ans

1. First look each sample one by one
2. Then check if the generated ans is correct or not.
3. Generated answer is verbose (contain explanation) while the correct answer contains only the correct option either A or B or C or D
4. Match if the option in the correct answer and option in the generated answer are same
5. Finally return the values that is given to you.

<samples>
{top_10_formatted}
</samples>
"""

# global variables
client = genai.Client(api_key=os.environ['GOOGLE_API'])
# model = 'gemini-2.0-pro-exp-02-05'
model = 'gemini-2.0-flash'


config = {
    'response_mime_type': 'application/json',
    'response_schema': Sample,
    "temperature": 0,
    "top_p": 0.2,
    "top_k": 20,
}

# a function to load the all the reasoning data
def loadReasoningData(file_name:str):
    """
    This function loads the reasoning data from the given file name.
    If the file name is not found that means the file is not generated yet. It'll combine all the reasoning data json file and generate the all in one file
    """
    logger.info(f"Loading reasoning data from {file_name}")
    if os.path.exists(file_name):
        with open(file_name,'r') as file:
            data = json.load(file)
        logger.info(f"Successfully loaded data from existing file {file_name}. Reasoning data length: {len(data)}")
        return data
    else:
        logger.info("File not found. Combining data from multiple reasoning files...")
        dirs = [dir for dir in os.listdir('Reasoning_data') if dir.startswith('validation')]
        data = []
        for dir in dirs:
            file_name = os.path.join('Reasoning_data',dir)
            with open(file_name,'r') as file:
                data.extend(json.load(file))
        with open('Data/all_in_one_reasoning_data.json','w') as file:
            json.dump(data,file,indent=4,ensure_ascii=False)
        logger.info(f"Successfully created and saved combined data file. Reasoning data length: {len(data)}")
        return data

def format_top_10(top_10:List[Dict]):
    logger.debug(f"Formatting batch of {len(top_10)} samples")
    formatted_data = []
    for sample in top_10:
        formatted_data.append({
            'id': sample['id'],
            'generated_ans': sample['gen_ans'],
            'correct_ans': sample['answer']
        })
    return formatted_data

def get_batch_data(data:List[Dict],batch_size:int=10):
    logger.info(f"Starting batch processing with batch size {batch_size}")
    for i in range(0,len(data),batch_size):
        logger.debug(f"Processing batch {i//batch_size + 1}")
        formatted_data = format_top_10(data[i:i+batch_size])
        yield formatted_data


def save_response(response:List[Dict],file_name:str='final_correct_answer_reasoning_data.json'):
    logger.info(f"Saving response data to {file_name}")
    if not os.path.exists(file_name):
        with open(file_name,'w') as file:
            json.dump(response,file,indent=4,ensure_ascii=False)
        logger.info("Created new file and saved response")
    else:
        with open(file_name,'r') as file:
            data = json.load(file)
        data.extend(response)
        with open(file_name,'w') as file:
            json.dump(data,file,indent=4,ensure_ascii=False)
        logger.info("Appended response to existing file")


def make_api_call(prompt_data, retry_count=0, max_retries=5):
    """Helper function to make API calls with retry logic"""
    global client
    logger.debug(f"Making API call (attempt {retry_count + 1})")
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt_data,
            config=config
        )
        response_json = json.loads(response.text)
        return response_json['all_samples']
    
    except Exception as e:
        if hasattr(e, 'code') and e.code == 429:
            if retry_count >= max_retries:
                # Switch API key
                if os.environ.get('CURRENT_API') != 'SECONDARY':
                    logger.warning(f"Switching to secondary API key after {max_retries} retries")
                    client = genai.Client(api_key=os.environ['GOOGLE_API_SECONDARY'])
                    os.environ['CURRENT_API'] = 'SECONDARY'
                    # Reset retry count and try again with new key
                    return make_api_call(prompt_data, retry_count=0)
                else:
                    logger.error("Both API keys exhausted after maximum retries")
                    raise
            
            logger.warning(f"Resource Exhausted. Pausing for 60 seconds (attempt {retry_count + 1})")
            time.sleep(60)
            return make_api_call(prompt_data, retry_count + 1)
        else:
            raise

def correct_answer_pipeline(data:List[Dict],start_index=None,end_index=None,file_name:str='final_correct_answer_reasoning_data.json'):
    logger.info("Starting correct answer pipeline")
    api_call_count_in_a_minute = 0
    api_call_count_total = 0
    current_batch = 0

    start_index = 0 if start_index is None else int(start_index) ## if start index is not provided then it'll be 0
    end_index = len(data) if end_index is None else int(end_index) ## if end index is not provided then it'll be the length of the data

    data = data[start_index:end_index]
    total_batches = len(data) // 10 + (1 if len(data) % 10 else 0)

    for batch in get_batch_data(data):
        current_batch += 1
        logger.info(f"Processing batch {current_batch}/{total_batches}")

        api_call_count_in_a_minute += 1
        api_call_count_total += 1
        start_time = datetime.now()
        
        # checking if the api call count is more than 10 in less than 1 min
        if api_call_count_in_a_minute >= 10:
            elapsed_time = (datetime.now() - start_time).total_seconds()

            if elapsed_time < 60:
                logger.warning("Rate limit reached. Pausing for 60 seconds")
                time.sleep(60)
                logger.info("Resuming after rate limit pause")

                api_call_count_in_a_minute = 0
                start_time = datetime.now()
        
        # checking if the api call count is more than 1400 in total then will switch to the secondary api key
        if api_call_count_total == 1000:
            global client ## getting the global client variable
            client = genai.Client(api_key=os.environ['GOOGLE_API_SECONDARY'])
            logger.info("Reached the limit of 1400 API calls. Switched to secondary API key")

        prompt_data = prompt.format(top_10_formatted=json.dumps(batch)) # formatting the prompt data directtly dumping the batch data as json so that it can handle the special characters
        logger.debug("Making API call to Gemini")

        try:
            struct_data_list_values = make_api_call(prompt_data)
            save_response(struct_data_list_values,file_name=file_name)
            logger.debug(f"Successfully processed and saved batch response for batch {current_batch}/{total_batches} or till {current_batch*10} samples")
        except Exception as e:
            logger.error(f"Error in processing batch {current_batch}: {e}")

    logger.info("Completed correct answer pipeline")


if __name__ == "__main__":
    data = loadReasoningData('Data/test_reasoning_data_till_2983.json')
    correct_answer_pipeline(data,file_name='Data/test_correct_answer_reasoning_data.json')



    