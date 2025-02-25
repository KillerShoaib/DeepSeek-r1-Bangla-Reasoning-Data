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
load_dotenv()

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


def api_calling(sample):
    
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
        "model": "deepseek-ai/DeepSeek-R1",
        "temperature": 0.1,
        "top_p": 0.2
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()


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
    print(f"Failed to get response for sameple no = {sample_no} in {set_name} set")
    

def split_think_reason(respons_string:str):
    # Use regular expression to find the content within the <think> tag
    think_content = re.search(r'<think>(.*?)</think>', respons_string, re.DOTALL).group(0)
    
    # Remove the <think> tag and its content from the original prompt
    ans_content = re.sub(r'<think>(.*?)</think>', '', respons_string, flags=re.DOTALL).strip()

    think_ans_response = {
        'think': think_content,
        'ans': ans_content
    }

    return think_ans_response


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
    print(f"Total token for sample {sample_no} in {set_name} = {total_token}")


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
    # file_name = "reasoning_bangla_r1_synthetic_data.json"
    if not (os.path.exists("Reasoning_data")):
        os.makedirs("Reasoning_data")
    
    file_name = f"Reasoning_data/{file_name}"
    with open(file_name,'w') as file:
        try:
            json.dump(data_list,file,indent=4,ensure_ascii=False)
        except:
            print("Error while saving to json file")


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

def main(dataset,set_name,start_index,end_index,run_name=None):
    

    # Converting to int object
    start_index = int(start_index)
    end_index = int(end_index)

    print(set_name)
    print(start_index,type(start_index))
    print(end_index,type(end_index))
    print(run_name)

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
            response_json  = api_calling(format_question_sample)

            # now checking if we got the proper response from it or not
            if('choices' in response_json and isinstance(response_json['choices'], list)):
                # splitting the think and ans from the generated ans
                split_think = split_think_reason(response_json['choices'][0]['message']['content'])
                new_data_sample = create_sample_json(split_think,format_question_sample)
                all_new_data_list.append(new_data_sample) # appending to the list

                # saving the value every time
                save_new_data(all_new_data_list,json_file_name)

                # logging the token count
                log_token_count(response_json,sample_no,set_name,Token_Counter_log_csv_name,run)
            else:
                # didn't get the right response need to log
                log_fail(sample_no,set_name,format_question_sample['id'],run)
        
        except:
            # logging the error
            log_fail(sample_no,set_name,format_question_sample['id'],failed_log_csv_name,run)
    
    if run is not None:
        run.finish()
    return all_new_data_list


if __name__ == "__main__":
    # loading the dataset
    dataset = load_dataset("hishab/bangla-mmlu")

    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('-t', '--set_name', type=str, help='Name of the set', required=True)
    parser.add_argument('-r', '--run_name', type=str, help='Name of the set', required=False, default=None)
    parser.add_argument('-b', '--start_index', type=str, help='Starting Index', required=True)
    parser.add_argument('-e', '--end_index', type=str, help='Ending Index', required=True)

    # calling the function
    args = parser.parse_args()
    main(dataset,args.set_name,args.start_index,args.end_index,args.run_name)
    # stop_lightningStudio() ### only for lightning studio