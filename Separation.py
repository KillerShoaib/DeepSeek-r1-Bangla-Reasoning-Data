import json
import os
from typing import List,Dict

def load_data(file_path:str):
    with open(file_path,'r') as f:
        data = json.load(f)
    return data

def get_false_ids(data:List[Dict]):
    false_ids = []
    for item in data:
        if item['correct'] == False:
            false_ids.append(item['id'])
    return false_ids

def separate_data(data:List[Dict],false_ids:List[str]):
    true_data = []
    for item in data:
        if item['id'] not in false_ids:
            true_data.append(item)
    return true_data

def save_data(data:List[Dict],file_path:str):
    with open(file_path,'w') as f:
        json.dump(data,f,indent=4,ensure_ascii=False)


if __name__ == "__main__":
    print("Separation of correct and incorrect reasoning data in validation set")
    reasoning_data = load_data('Data/all_in_one_reasoning_data.json')
    correct_ids_json = load_data('Data/final_correct_answer_reasoning_data.json')
    false_ids = get_false_ids(correct_ids_json)
    true_data = separate_data(reasoning_data,false_ids)
    save_data(true_data,'Data/only_correct_reasoning_data_validation.json')

    print("Separation of correct and incorrect reasoning data in test set")
    reasoning_data = load_data('Data/test_reasoning_data_till_2983.json')
    correct_ids_json = load_data('Data/test_correct_answer_reasoning_data.json')
    false_ids = get_false_ids(correct_ids_json)
    true_data = separate_data(reasoning_data,false_ids)
    save_data(true_data,'Data/only_correct_reasoning_data_test.json')







