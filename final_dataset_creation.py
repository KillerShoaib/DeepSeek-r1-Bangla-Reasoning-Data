import json


#### handle validation data ####

# translated data path
validation_translation_data_path_1 = 'Data/valid_translated_data.json'
validation_translation_data_path_2 = 'Data/valid_translated_data_v2.json'
validation_translation_data_path_3 = 'Data/valid_complete_translated_data_samples_from_error_batch.json'

# loading the correct reasoning data
validation_correct_reasoning_data_path = 'Data/only_correct_reasoning_data_validation.json'


data_path = [validation_translation_data_path_1,validation_translation_data_path_2,validation_translation_data_path_3]

# loading the translated data and appending them to a list
all_validation_translated_data = []
for data_path in data_path:
    with open(data_path,'r') as file:
        data = json.load(file)
        all_validation_translated_data.extend(data)

# Load validation correct reasoning data
with open(validation_correct_reasoning_data_path, 'r') as file:
    validation_correct_data = json.load(file)


# now map the id and add question, options, formated question, answer, to the list

# Create a dictionary mapping IDs to correct reasoning data for faster lookup
validation_correct_data_dict = {item['id']: item for item in validation_correct_data}

print("Starting to map the id and add question, options, formated question, answer, to the list")
# Iterate through translated data and add matching fields from correct data
for translated_item in all_validation_translated_data:
    translated_id = translated_item['id']
    if translated_id in validation_correct_data_dict:
        correct_item = validation_correct_data_dict[translated_id]
        # Add fields from correct data to translated item
        translated_item['question'] = correct_item['question']
        translated_item['options'] = correct_item['options'] 
        translated_item['answer'] = correct_item['answer']
        translated_item['formated_question'] = correct_item['formated_question']

# now save the data
with open('Data/final_validation_translated_reasoning_data.json', 'w') as file:
    json.dump(all_validation_translated_data, file, indent=4, ensure_ascii=False)

print("Successfully saved the final validation translated reasoning data")

#### handle test data ####

# translated data path
test_translation_data_path_1 = 'Data/test_translated_data.json'
test_translation_data_path_2 = 'Data/test_translated_data_v2.json'
test_translation_data_path_3 = 'Data/test_complete_translated_data_samples_from_error_batch.json'

# loading the correct reasoning data
test_correct_reasoning_data_path = 'Data/only_correct_reasoning_data_test.json'


data_path = [test_translation_data_path_1,test_translation_data_path_2,test_translation_data_path_3]

# loading the translated data and appending them to a list
all_test_translated_data = []
for data_path in data_path:
    with open(data_path,'r') as file:
        data = json.load(file)
        all_test_translated_data.extend(data)

# Load test correct reasoning data
with open(test_correct_reasoning_data_path, 'r') as file:
    test_correct_data = json.load(file)


# now map the id and add question, options, formated question, answer, to the list

# Create a dictionary mapping IDs to correct reasoning data for faster lookup
test_correct_data_dict = {item['id']: item for item in test_correct_data}

print("Starting to map the id and add question, options, formated question, answer, to the list")

# Iterate through translated data and add matching fields from correct data
for translated_item in all_test_translated_data:
    translated_id = translated_item['id']
    if translated_id in test_correct_data_dict:
        correct_item = test_correct_data_dict[translated_id]
        # Add fields from correct data to translated item
        translated_item['question'] = correct_item['question']
        translated_item['options'] = correct_item['options'] 
        translated_item['answer'] = correct_item['answer']
        translated_item['formated_question'] = correct_item['formated_question']

# now save the data
with open('Data/final_test_translated_reasoning_data.json', 'w') as file:
    json.dump(all_test_translated_data, file, indent=4, ensure_ascii=False)


print("Successfully saved the final test translated reasoning data")