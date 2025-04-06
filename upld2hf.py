from datasets import Dataset, DatasetDict, load_dataset
from huggingface_hub import HfApi, create_repo
import os
from dotenv import load_dotenv
import json
load_dotenv()

def load_json_dataset(file_path:str):
    # load from json file
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data


def create_hf_repo(dataset_name:str, token:str)->str:
    api = HfApi()
    repo_id = f"{dataset_name}"
    try:
        repo_url = api.create_repo(repo_id=repo_id, token=token, repo_type="dataset")
        print(f"Created repo at {repo_url}")
    except Exception as e:
        print(f"Repo creation failed: {e}")
        print(f"Make sure that the repository doesn't exist under your user or organization or you have the right permissions and API tokens")

    return repo_id

def push_to_hf_hub(dataset:Dataset, repo_id:str, token:str)->None:
    # Check if dataset is dictionary
    if isinstance(dataset, dict):
        dataset = DatasetDict(dataset)

    if not isinstance(dataset, (Dataset, DatasetDict)):
        print("The dataset is not in a Dataset or DatasetDict format. Please transform it first into a Dataset object.")
        return

    dataset.push_to_hub(repo_id=repo_id, token=token)
    print(f"Dataset has been pushed to https://huggingface.co/datasets/{repo_id}")


def split_dataset(train_data:list, test_data:list)->DatasetDict:
    # Convert to datasets
    train_dataset = Dataset.from_list(train_data)
    test_dataset = Dataset.from_list(test_data)

    # Create a DatasetDict with validation and test splits
    dataset_dict = DatasetDict({
        'train': train_dataset,
        'test': test_dataset
    })

    return dataset_dict


if __name__ == "__main__":
    train_data_path = 'Data/final_validation_translated_reasoning_data.json'
    test_data_path = 'Data/final_test_translated_reasoning_data.json'

    # loading the data
    train_data = load_json_dataset(train_data_path)
    test_data = load_json_dataset(test_data_path)

    print("Data loaded successfully, now splitting the data and converting to dataset object")
    # splitting the data and converting to dataset object
    dataset_dict = split_dataset(train_data, test_data)
    print("Data split successfully, now creating the repo")
    # creating the repo
    hf_token = os.getenv("HF_TOKEN")
    dataset_name = "DeepSeek-r1-Distill-Bangla-MMLU-Reasoning-Data"
    repo_id = create_hf_repo(dataset_name, hf_token)
    print("Repo created successfully, now pushing the dataset to the repo")
    # pushing the dataset to the repo
    push_to_hf_hub(dataset_dict, repo_id, hf_token)
    print("Dataset pushed to the repo successfully")