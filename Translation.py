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
        logging.FileHandler('logs/translation_log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


## pydantic model for structure output
class item(BaseModel):
    id: str = Field(description="The unique id of the object which given for each sample.")
    # correct: bool = Field(description="A binary value representing if the sample's generated ans and given corrected answer are same. If same then the value is True otherwise it's False")
    reasoning_translation: str = Field(description="The bangla translation of the reasoning process or delimitated by <think> and </think>")
    ans_translation: str = Field(description="The bangla translation of the answer outside of the '<think> and </think>' tag")

class Sample(BaseModel):
    all_samples: List[item] = Field(description="A list of objects containing the id, reasoning_translation and ans_translation for each sample.")


prompt = """
You're an expert at translating text from English to Bangla. You're given 10 samples (delimitated <samples></samples>) , each sample contain an unique id (string value), a reasoning text and a final answer text. Now follow the below steps to translate the given text for each samples:

1. Translate the english in bangla in a way so that the semantic meaning of the overall text remain same.
2. Do not translate those words that is given in the question or option. 
3. Do not translate any English words which are quoted ("")
4. Do not translate scientific or mathmetical words (such as name of a molecule, or a variable in math)
5. Do not translate special characters like LaTex symbol.
6. Do not translate math terminologies, Keep them as it is.
7. Those words which are already in Bangla don't change them, keep them as it is.
8. Do not translate the options letter, Here are the given options ["A", "B", "C", "D"]
9. Finally return the values in a structure format that is given to you.

Now based on the above instruction translate both the reasoning text and the final answer text.


<samples>
{top_10_formatted}
</samples>
"""

# global variables
client = genai.Client(api_key=os.environ['GOOGLE_API'])
model = 'gemini-2.0-flash'

config = {
    'response_mime_type': 'application/json',
    'response_schema': Sample,
    "temperature": 0,
    "top_p": 0.2,
    "top_k": 20,
}





def format_top_10(top_10:List[Dict]): # later use top 5 instead of top 10 but didn't change the name. Long way to go for me to become a senior python dev
    formated_data = []
    for sample in top_10:
        format_dict = {
            'id': sample['id'],
            'question': sample['question'],
            'options': sample['options'],
            'reasoning': sample['reason'],
            'ans': sample['gen_ans']
        }
        formated_data.append(format_dict)
    return formated_data


def get_batch_data(data:List[Dict],batch_size:int=5):
    logger.info(f"Starting batch processing with batch size {batch_size}")
    for i in range(0,len(data),batch_size):
        logger.debug(f"Processing batch {i//batch_size + 1}")
        formatted_data = format_top_10(data[i:i+batch_size])
        yield formatted_data


def handle_token_limit(response:str,batch_no:int,set:str='valid'):
    logger.info(f"Token limit exceeded, Therefore {batch_no}th batch can't be processed in a Json file, Saving it as a txt")
    os.makedirs('Translation_Batch_Data_Error',exist_ok=True)
    with open(f'Translation_Batch_Data_Error/{set}_translated_data_{batch_no}.txt','w') as file:
        file.write(response)
   

def save_response(response:List[Dict],file_name:str='valid_translated_data.json'):
    logger.info(f"Saving response data to {file_name} in the Data folder")
    os.makedirs('Data',exist_ok=True)
    file_name = os.path.join('Data',file_name)
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

def make_api_call(prompt_data,batch_no:int,set:str='valid', retry_count=0, max_retries=5):
    """Helper function to make API calls with retry logic"""
    global client
    logger.debug(f"Making API call (attempt {retry_count + 1})")
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt_data,
            config=config
        )
        ## if the response is a proper json then there is not token limit exceeded
        try:
            response_json = json.loads(response.text)
            return response_json['all_samples']
        except:
            # this is handling the token limit exceeded error
            handle_token_limit(response.text,batch_no,set)
    
    except Exception as e:
        if hasattr(e, 'code') and e.code == 429:
            if retry_count >= max_retries:
                # Switch API keys in sequence
                current_api = os.environ.get('CURRENT_API', 'PRIMARY')
                
                if current_api == 'PRIMARY':
                    logger.warning(f"Switching to secondary API key after {max_retries} retries")
                    client = genai.Client(api_key=os.environ['GOOGLE_API_SECONDARY'])
                    os.environ['CURRENT_API'] = 'SECONDARY'
                    return make_api_call(prompt_data,batch_no=batch_no,set=set, retry_count=0)
                    
                elif current_api == 'SECONDARY':
                    logger.warning(f"Switching to V2 API key after {max_retries} retries")
                    client = genai.Client(api_key=os.environ['GOOGLE_API_V2'])
                    os.environ['CURRENT_API'] = 'V2'
                    return make_api_call(prompt_data,batch_no=batch_no,set=set, retry_count=0)
                    
                else:  # V2 is also exhausted
                    logger.error("All API keys exhausted after maximum retries")
                    raise
            
            logger.warning(f"Resource Exhausted. Pausing for 60 seconds (attempt {retry_count + 1})")
            time.sleep(60)
            return make_api_call(prompt_data,batch_no=batch_no,set=set, retry_count=retry_count + 1)
        else:
            raise

def translation_pipeline(data:List[Dict],set:str='valid',start_index=None,end_index=None,file_name:str='final_correct_answer_reasoning_data.json'):
    logger.info(f"Starting {set} translation pipeline")
    api_call_count_total = 0
    
    # For rate limiting
    api_calls = []  # List to store timestamps of API calls
    
    # getting the global client variable
    global client # going to use the global client variable

    start_index = 0 if start_index is None else int(start_index)
    end_index = len(data) if end_index is None else int(end_index)

    if start_index == 0:
        current_batch = 0
    else:
        current_batch = (start_index // 5)

    data = data[start_index:end_index]
    total_batches = (len(data) // 5 + (1 if len(data) % 5 else 0)) + current_batch

    for batch in get_batch_data(data,batch_size=5):
        current_batch += 1
        logger.info(f"Processing batch {current_batch}/{total_batches}")

        # Rate limiting check
        current_time = datetime.now()
        # Remove timestamps older than 60 seconds
        api_calls = [call_time for call_time in api_calls 
                    if (current_time - call_time).total_seconds() < 60]
        
        # If we've made 10 calls in the last minute, wait
        if len(api_calls) >= 10:
            sleep_time = 60 - (current_time - api_calls[0]).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Pausing for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                api_calls = []  # Reset the calls list after waiting
        
        # Add current API call timestamp
        api_calls.append(current_time)
        api_call_count_total += 1
        
        # API key rotation based on total calls
        if api_call_count_total == 1400:
            client = genai.Client(api_key=os.environ['GOOGLE_API_SECONDARY'])
            logger.info("Reached the limit of 1400 API calls. Switched to secondary API key")
        elif api_call_count_total == 2800:
            client = genai.Client(api_key=os.environ['GOOGLE_API_V2'])
            logger.info("Reached the limit of 2800 API calls. Switched to V2 API key")

        prompt_data = prompt.format(top_10_formatted=json.dumps(batch,ensure_ascii=False,indent=4))
        logger.debug("Making API call to Gemini")

        try:
            struct_data_list_values = make_api_call(prompt_data,batch_no=current_batch,set=set)
            save_response(struct_data_list_values,file_name=file_name)
            logger.debug(f"Successfully processed and saved batch response for batch {current_batch}/{total_batches}")
        except Exception as e:
            logger.error(f"Error in processing batch {current_batch}: {e}")

    logger.info(f"Completed {set} translation pipeline")


if __name__ == "__main__":
    with open('Data/only_correct_reasoning_data_test.json','r') as file:
        data = json.load(file)
    translation_pipeline(data,set='test',file_name='test_translated_data.json')







