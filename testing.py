import os
import json

def count_json_objects(directory):
    total_count = 0
    
    # Iterate over all files in the specified directory
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                # Assuming each JSON file contains a list
                print(f'Number of objects in {filename}: {len(data)}')
                total_count += len(data)
    
    return total_count

# Specify the directory containing JSON files
directory_path = 'Reasoning_data'
result = count_json_objects(directory_path)
print(f'Total count of objects in JSON files: {result}')
print(f'Total validation count of objects in JSON files: {result-2979}')
print(f'Total test count of objects in JSON files: {2979}')

# dic_a = {
#     "key": "value",
#     "key2": "value2"
# }

# dic_b = {
#     "key3": "value3",
#     "key4": "value4"
# }

# if os.path.exists("some_value.json"):
#     try:
#         with open("some_value.json",'r') as file:
#             data = json.load(file)
#     except json.JSONDecodeError:
#         data = []
# else:
#     data = []


# with open("some_value.json",'a') as file:
#     data.append(dic_a)
#     json.dump(data,file,indent=4)



# import requests
# from dotenv import load_dotenv
# import os
# load_dotenv()

# DEEPSEEK_API = os.environ['DEEPSEEK_API']

# print("Below there is a Bangla multiple choice question with 4 option, you need to find the correct option for the question.\n    Question in Bangla: নাইট্রিক এসিডের ব্যবহার নয় কোনটি?\n    Options in Bangla: {'A': 'কৃত্রিম রং তৈরিতে', 'B': 'বিস্ফোরক তৈরিতে', 'C': 'স্বর্ন থেকে খাদ দূর করতে', 'D': 'দিয়াশলাই তৈরিতে'}")