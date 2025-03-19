# import json
# with open('Data/only_correct_reasoning_data_validation.json','r') as file:
#     data = json.load(file)

# print(len(data))

# a = [0,1,2,3,4,5,6,7,8,9,10]

# for i in a[9:]:
#     print(i)


import json
import os
with open('Data/valid_translated_data.json','r') as file:
    data = json.load(file)

with open('Data/test_translated_data.json','r') as file:
    data_test = json.load(file)

print(len(data))
print(len(os.listdir('Translation_Batch_Data_Error')))

print(len(data_test))