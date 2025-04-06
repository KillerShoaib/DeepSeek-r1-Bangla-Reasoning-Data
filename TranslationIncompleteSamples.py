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

# pydantic model for structure output
class item(BaseModel):
    id: str = Field(description="The unique id of the object which given for each sample.")
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
{sample_data}
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

def format_sample(sample: Dict):
    return {
        'id': sample['id'],
        'question': sample['question'],
        'options': sample['options'],
        'reasoning': sample['reason'],
        'ans': sample['gen_ans']
    }

def save_response(response: List[Dict], file_name: str = 'valid_translated_data.json'):
    logger.info(f"Saving response data to {file_name} in the Data folder")
    os.makedirs('Data', exist_ok=True)
    file_name = os.path.join('Data', file_name)
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(response, file, indent=4, ensure_ascii=False)
        logger.info("Created new file and saved response")
    else:
        with open(file_name, 'r', encoding='utf-8') as file:
            data = json.load(file)
        data.extend(response)
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
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
                current_api = os.environ.get('CURRENT_API', 'PRIMARY')
                
                if current_api == 'PRIMARY':
                    logger.warning(f"Switching to secondary API key after {max_retries} retries")
                    client = genai.Client(api_key=os.environ['GOOGLE_API_SECONDARY'])
                    os.environ['CURRENT_API'] = 'SECONDARY'
                    return make_api_call(prompt_data, retry_count=0)
                    
                elif current_api == 'SECONDARY':
                    logger.warning(f"Switching to V2 API key after {max_retries} retries")
                    client = genai.Client(api_key=os.environ['GOOGLE_API_V2'])
                    os.environ['CURRENT_API'] = 'V2'
                    return make_api_call(prompt_data, retry_count=0)
                    
                else:  # V2 is also exhausted
                    logger.error("All API keys exhausted after maximum retries")
                    raise
            
            logger.warning(f"Resource Exhausted. Pausing for 60 seconds (attempt {retry_count + 1})")
            time.sleep(60)
            return make_api_call(prompt_data, retry_count=retry_count + 1)
        else:
            raise

def translation_pipeline(data: List[Dict], incomplete_ids: List[str], set: str = 'valid',file_name:str='valid_translated_data.json'):
    logger.info(f"Starting {set} translation pipeline for {len(incomplete_ids)} samples")
    
    # Filter data to only include samples with incomplete IDs
    filtered_data = [sample for sample in data if sample['id'] in incomplete_ids]
    
    for i, sample in enumerate(filtered_data, 1):
        logger.info(f"Processing sample {i}/{len(filtered_data)} with ID: {sample['id']}")
        
        formatted_sample = format_sample(sample)
        prompt_data = prompt.format(sample_data=json.dumps(formatted_sample, ensure_ascii=False, indent=4))
        
        try:
            response = make_api_call(prompt_data)
            save_response(response, file_name=file_name)
            logger.debug(f"Successfully processed and saved response for sample {i}")
            
            # Add delay between requests to avoid rate limiting
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error in processing sample {i} with ID {sample['id']}: {e}")
    
    logger.info(f"Completed {set} translation pipeline")


def get_incomplete_ids():
    logger.info(f"Getting incomplete IDs")
    correct_data_valdation_file_path = 'Data/only_correct_reasoning_data_validation.json'
    correct_data_test_file_path = 'Data/only_correct_reasoning_data_test.json'

    valid_translated_data_file_path = 'Data/valid_translated_data.json'
    test_translated_data_file_path = 'Data/test_translated_data.json'

    correct_data_validation_translated_file_path2 = 'Data/valid_complete_translated_data_samples_from_error_batch.json'
    correct_data_test_translated_file_path2 = 'Data/test_complete_translated_data_samples_from_error_batch.json'


    # Load validation and test data
    with open(correct_data_valdation_file_path, 'r') as f:
        correct_data_validation = json.load(f)

    with open(correct_data_test_file_path, 'r') as f:
        correct_data_test = json.load(f)

    with open(valid_translated_data_file_path, 'r') as f:
        valid_translated_data = json.load(f)

    with open(test_translated_data_file_path, 'r') as f:
        test_translated_data = json.load(f)

    with open(correct_data_validation_translated_file_path2, 'r') as f:
        correct_data_validation_translated = json.load(f)

    with open(correct_data_test_translated_file_path2, 'r') as f:
        correct_data_test_translated = json.load(f)

    # Get sets of IDs from correct data
    validation_ids = [item['id'] for item in correct_data_validation]
    test_ids = [item['id'] for item in correct_data_test]


    # Get sets of IDs from translated data 
    translated_validation_ids = [item['id'] for item in valid_translated_data]
    translated_test_ids = [item['id'] for item in test_translated_data]

    # get ids from translated data 2
    translated_validation_ids2 = [item['id'] for item in correct_data_validation_translated]
    translated_test_ids2 = [item['id'] for item in correct_data_test_translated]

    # merge ids from translated data 2
    translated_validation_ids.extend(translated_validation_ids2)
    translated_test_ids.extend(translated_test_ids2)

    incomplete_validation_ids = [id for id in validation_ids if id not in translated_validation_ids]
    incomplete_test_ids = [id for id in test_ids if id not in translated_test_ids]

    logger.info(f"Incomplete validation IDs: {len(incomplete_validation_ids)}")
    logger.info(f"Incomplete test IDs: {len(incomplete_test_ids)}")

    return incomplete_validation_ids, incomplete_test_ids


if __name__ == "__main__":
    # Load the original data and incomplete IDs
    with open('Data/only_correct_reasoning_data_validation.json', 'r') as f:
        validation_data = json.load(f)
    
    with open('Data/only_correct_reasoning_data_test.json', 'r') as f:
        test_data = json.load(f)
        
    incomplete_validation_ids, incomplete_test_ids = get_incomplete_ids()
    
    logger.info(f"Processing validation data")

    # Process validation data
    translation_pipeline(validation_data, incomplete_validation_ids, set='valid', file_name='valid_translated_data_v2.json')
    
    logger.info(f"Processing test data")
    # Process test data
    translation_pipeline(test_data, incomplete_test_ids, set='test', file_name='test_translated_data_v2.json')

