## Importing libraries

import re
import requests
from datasets import load_dataset
from typing import List, Tuple, Dict
from dotenv import load_dotenv
import os
import json
import argparse
import wandb
import logging
import asyncio
import aiohttp  # Import aiohttp
from datetime import datetime
load_dotenv()

# Configure logging - Now includes unique file names and logs directory
def setup_logger(set_name, start_index, end_index):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Create a unique log file name based on set_name and indices
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file_name = f"api_call_{set_name}_{start_index}_{end_index}_{timestamp}.log"

    log_file_path = os.path.join(logs_dir, log_file_name)
    
    # Create file handler with unique name
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger



DEEPSEEK_API = os.environ['DEEPSEEK_API']

# wandb loging
wandb.login(key=os.environ['WANDB_API_KEY'])


def format_question(sample: Dict) -> Dict:
    """
    A function to format the question with proper option in a clear way so that the llm have easy time understanding it without any confusion
    i.e, "Question in Bangla: নিচের কোনটিতে মেটামারিজম অনুপস্থিত?
        Options in Bangla: {"A":'সেকেন্ডারি অ্যামিন', "B":'কিটোন', "C": 'অ্যালকোহল', "D": 'ইথার'}"

    Inputs:
    sample =  A dict object containing id,question, choices and answer field

    Output:
    Dictionary object containing evarything in input dict and formated question (str)
    """

    ID = sample['id']
    question = sample['question']
    choices = sample['choices']
    answer = sample['answer']


    # formating the Question
    formated_option = {
        "A": choices[0],
        "B": choices[1],
        "C": choices[2],
        "D": choices[3],
    }

    formated_question = f"""Below there is a Bangla multiple choice question with 4 option, you need to find the correct option for the question.
    Question in Bangla: {question}
    Options in Bangla: {str(formated_option)}"""
    
    sample_with_formated_question = {
        'id':ID,
        'question': question,
        'choices': choices,
        'answer': answer,
        'formated_question': formated_question
    }

    return sample_with_formated_question


async def api_calling(sample):
    

    formated_question = sample['formated_question']
    url = "https://api.hyperbolic.xyz/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API}"
    }
    system_instruction = """You are an inteligent assistant which will help the user to answer multiple choice question. The multiple choice question is in bangla and your final answer will always be in bangla."""
    
    data = {
        "messages": [
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": formated_question
            }
        ],
        "model": "deepseek-ai/DeepSeek-R1", # change from r1 to QwQ
        # "model": "Qwen/QwQ-32B",
        "temperature": 0.1,
        "top_p": 0.2
    }
    
    # response = requests.post(url, headers=headers, json=data)
    # print("Got response from api function")
    # return response.json()

    async with aiohttp.ClientSession() as session:  # Create a session
        async with session.post(url, headers=headers, json=data) as response:
            # print("Got response from api function")

            if response.status == 502: # handling 502 error
                show_logs("Got a 502 error. Skipping this sample...")
                # await asyncio.sleep(2) # wait 2 second
                return None

            # response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return await response.json()  # Return the JSON response

async def call_with_timeout(sample,timeout):
    try:
        
        result = await asyncio.wait_for(api_calling(sample), timeout=timeout)
        return result
    except asyncio.TimeoutError:
        log_msg = f"Timeout occurred skipping this sample"
        show_logs(log_msg) ## showing and saving the log


def log_fail(sample_no:int, set_name:str, sample_id:str, log_file_name:str, run=None):

    header = "sample_no,set_name,sample_id\n"  # Include newline

    if not (os.path.exists("Failed_Logs")):
        os.makedirs("Failed_Logs")

    filename = f"Failed_Logs/{log_file_name}"
    # Check if the file exists and if it's empty.  More robust than just checking existence.
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        with open(filename, 'w') as file:  # Use 'w' to create and write the header
            file.write(header)
    
    with open(filename,'a') as file:
        log_value = f"{str(sample_no)},{set_name},{sample_id}\n"
        file.write(log_value)

    if run is not None:
        run.log(
            {
                "sample_no":sample_no,
            }
        )
    
    log_msg = f"Failed to get response for sameple no = {sample_no} in {set_name} set"
    show_logs(log_msg) ## showing and saving the log
    

def split_think_reason(response_json):
    # Use regular expression to find the content within the <think> tag
    response_string = response_json['choices'][0]['message']['content']
    try:
        think_content = re.search(r'<think>(.*?)</think>', response_string, re.DOTALL).group(0)
        
        # Remove the <think> tag and its content from the original prompt
        ans_content = re.sub(r'<think>(.*?)</think>', '', response_string, flags=re.DOTALL).strip()

        think_ans_response = {
            'think': think_content,
            'ans': ans_content
        }

        return think_ans_response
    except Exception as e:
        log_msg = f"Error occurred: {e} saving to the outlier file"
        show_logs(log_msg) ## showing and saving the log

        os.makedirs("Outlier_response",exist_ok=True)
        filename = "Outlier_response/outliers.json"
        if os.path.exists(filename):
            try:
                with open(filename,'r') as file:
                    data = json.load(file)
            except json.JSONDecodeError:
                data = []
        else:
            data = []
        
        with open(filename,'w') as file:
            data.append(response_json)
            json.dump(data,file,indent=4,ensure_ascii=False)


def log_token_count(usage:Dict,sample_no:int,set_name:str,file_name:str,run=None):
    input_token = usage['usage']['prompt_tokens']
    output_token = usage['usage']['completion_tokens']
    total_token = usage['usage']['total_tokens']

    if not (os.path.exists("Token_Count")):
        os.makedirs("Token_Count")

    header = "sample_no,set_name,input_token,output_token,total_token\n"  # Include newline
    filename = f"Token_Count/{file_name}"
    # Check if the file exists and if it's empty.  More robust than just checking existence.
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        with open(filename, 'w') as file:  # Use 'w' to create and write the header
            file.write(header)

    with open(filename,'a') as file:
        value = f"{sample_no},{set_name},{input_token},{output_token},{total_token}\n"
        file.write(value)

    ## logging to wandb
    if run is not None:
        run.log(
            {
                "sample_no":sample_no,
                "input_token":input_token,
                "output_token":output_token,
                "total_token":total_token
            }
        )
    
    ## calling the log function
    logging_msg = f"Total token for sample {sample_no} in {set_name} = {total_token}"
    show_logs(logging_msg)


def create_sample_json(think_response:Dict, formated_question:Dict):
    think = think_response['think']
    gen_ans = think_response['ans']
    
    question = formated_question['question']
    options = formated_question['choices']
    actual_ans = formated_question['answer']
    formated_question_only = formated_question['formated_question']
    id = formated_question['id']

    return {
        "id":id,
        "question": question,
        "options": options,
        "answer": actual_ans,
        "formated_question": formated_question_only,
        "reason": think,
        "gen_ans": gen_ans,
    }

def save_new_data(data_list:List, file_name:str):
    if not (os.path.exists("Reasoning_data")): # added qwq prefix for all qwq synthetic data
        os.makedirs("Reasoning_data")
    
    file_name = f"Reasoning_data/{file_name}"
    with open(file_name,'w') as file:
        try:
            json.dump(data_list,file,indent=4,ensure_ascii=False)
        except:
            show_logs("Error while saving to json file")

    # if not (os.path.exists("Reasoning_data_qwq")): # added qwq prefix for all qwq synthetic data
    #     os.makedirs("Reasoning_data_qwq")
    
    # file_name = f"Reasoning_data_qwq/{file_name}"
    # with open(file_name,'w') as file:
    #     try:
    #         json.dump(data_list,file,indent=4,ensure_ascii=False)
    #     except:
    #         show_logs("Error while saving to json file")

# logging function
def show_logs(msg:str):
    logging.info(msg)


# only for lignting studio

# use this only for lightning studio
def stop_lightningStudio()-> None:
    """
    Stops Lightning Studio if it is currently running.

    This function should be used in conjunction with main() to ensure that
    Lightning Studio is stopped after the script is finished running.

    Parameters:
    None

    Returns:
    None
    """
    from lightning_sdk import Studio
    print("Stopping Lightning Studio")
    s = Studio()
    s.stop()


## building the main pipeline

async def main(dataset,set_name,start_index,end_index,run_name=None):
    

    # Converting to int object
    start_index = int(start_index)
    end_index = int(end_index)

    # making the logger global variable so that show log can access it
    global logger

    # Setup the logger with unique file name
    logger = setup_logger(set_name, start_index, end_index)

    # wandb run start if necessary
    if run_name is not None:
        run = wandb.init(project="DeepSeek-r1-bangla-reasoning-data",name=run_name)
    else:
        run = None

    data_from_a_specific_set = dataset[set_name].to_list() # converting to list object
    all_new_data_list = []
    json_file_name = f"{set_name}_{start_index}_{end_index}.json" 
    failed_log_csv_name = f"{set_name}_{start_index}_{end_index}.csv" 
    Token_Counter_log_csv_name = f"Token_counter_{set_name}_{start_index}_{end_index}.csv" 

    # now looping each item manually
    for sample_no,sample in enumerate(data_from_a_specific_set[start_index:end_index],start=start_index):
        # first formate the question
        format_question_sample =  format_question(sample)

        # now calling the api
        try:
            response_json  = await call_with_timeout(format_question_sample,timeout=15*60) # 15min timeout period

            if response_json is None:
                continue

            # print("got response from api")

            # now checking if we got the proper response from it or not
            if('choices' in response_json and isinstance(response_json['choices'], list)):
                # splitting the think and ans from the generated ans
                split_think = split_think_reason(response_json)
                new_data_sample = create_sample_json(split_think,format_question_sample)
                all_new_data_list.append(new_data_sample) # appending to the list

                # saving the value every time
                save_new_data(all_new_data_list,json_file_name)

                # logging the token count
                log_token_count(response_json,sample_no,set_name,Token_Counter_log_csv_name,run)
            else:
                log_msg = f"Didn't get the right response for this json {response_json}"
                show_logs(log_msg)
                # didn't get the right response need to log
                log_fail(sample_no,set_name,format_question_sample['id'],failed_log_csv_name,run)
        
        except Exception as e:
            # logging the error
            log_msg = f"Error occurred: {e}"
            show_logs(log_msg) ## showing and saving the log
            log_fail(sample_no,set_name,format_question_sample['id'],failed_log_csv_name,run)
    
    if run is not None:
        run.finish()
    return all_new_data_list


if __name__ == "__main__":
    # loading the dataset
    dataset = load_dataset("hishab/bangla-mmlu")

    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('-t', '--set_name', type=str, help='Name of the set', required=True)
    parser.add_argument('-r', '--run_name', type=str, help='Wandb run name (optional)', required=False, default=None)
    parser.add_argument('-b', '--start_index', type=str, help='Starting Index', required=True)
    parser.add_argument('-e', '--end_index', type=str, help='Ending Index', required=True)

    # calling the function
    # python Reasoning_collection.py --set_name "test" --start_index 20 --end_index 200
    args = parser.parse_args()
    asyncio.run(main(dataset,args.set_name,args.start_index,args.end_index,args.run_name))
    # stop_lightningStudio() ### only for lightning studio