import json
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ValidationError
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()


class item(BaseModel):
    id: str = Field(description="The unique id of the object which given for each sample.")
    correct: bool = Field(description="A binary value representing if the sample's generated ans and given corrected answer are same. If same then the value is True otherwise it's False")

class Sample(BaseModel):
    all_samples: List[item] = Field(description="A list of objects containing the id and correct value for each sample.")



list_dir = os.listdir('Reasoning_data')

# file_name = os.path.join('Reasoning_data',list_dir[0])
# print(file_name)

file_name = 'Reasoning_data/validation_1001_2001.json'
with open(file_name,'r') as file:
    data = json.load(file)

top_10 = data[10:21]

def format_top_10(top_10:List[Dict]):
    formatted_data = []
    for sample in top_10:
        formatted_data.append({
            'id': sample['id'],
            'generated_ans': sample['gen_ans'],
            'correct_ans': sample['answer']
        })
    return formatted_data

top_10_formatted = format_top_10(top_10)
print(top_10_formatted[0])

prompt = f"""
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



client = genai.Client(api_key=os.environ['GOOGLE_API'])
model = 'gemini-2.0-pro-exp-02-05'

response = client.models.generate_content(
    model=model,
    contents=prompt,
    config={
        'response_mime_type': 'application/json',
        'response_schema': Sample,
        "temperature": 0,
        "top_p": 0.2,
        "top_k": 20,
    }
)

response_json = json.loads(response.text)
print(response_json)


with open('testing_correct.json' , 'a') as file:
    json.dump(response_json, file, indent=4, ensure_ascii=False)



    