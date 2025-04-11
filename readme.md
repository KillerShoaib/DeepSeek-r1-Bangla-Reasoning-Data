<div align="center"><h1>DeepSeek R1 Bangla MMLU Distil Dataset</h1></div>
<div align="center">
    <img src="https://cdn-uploads.huggingface.co/production/uploads/65ca6f0098a46a56261ac3ac/BwZyOJ_VlSXgU6w_jsC0p.png" width="300"/>
</div>

---

# Disclaimer about the codebase

1. The codebase is super messy (I'm still a noob coder. Sorry can't help it)
2. The codebase is not optimized and is not scalable.
3. Unfortunatly I'm unable to create the whole codebase as an automated pipeline due to time constraint. Most of the steps were manual.
4. `Data` Folder is missing in the repo due to file size issue. I'll try to expose an public url of wandb artifact so that anyone can download that folder. But this may take some time.
5. There maybe some bugs in the codebase.
6. There are some experimental segment in the codebase which weren't used in the final dataset generation. (i.e: I experimented with `Qwen QwQ 32B` which is also a thinking model and cost way less but the quality of the response was not good. That's why I didn't use it in the final dataset generation.)
7. Though this codebase doesn't give an automated pipeline which can later be used to generate more dataset with ease but it shows the entire process of how to generate reasoning synthetic dataset in Bangla.

---

# Contributors
1. **Shoaib** (Myself duh)
2. [**Numaer**](https://github.com/turjo-001)

---

# Some Words from the Contributors

1. Our intention is to push **Bangla** AI (specifically LLM) research so that we can have at least somewhat decent Open Source LLM/VLLM which can compete with the commercial LLMs.

2. **If we wanted we can gatekeep the dataset and try to publish a research paper**(which we can) but decided not to do so, rather **open source it to the community.**

3. What we want is more and more people **know about this dataset** and **finetune their own models** with this dataset and **publish those model to Hugging Face.**

4. You **don't have to mention our work or anything** just create **more models** and even if possible try to add **more dataset** related to this.


# Dataset Info

**Original Dataset:** [hishab/bangla-mmlu](https://huggingface.co/datasets/hishab/bangla-mmlu)

**Synthetic Reasoning Dataset:** [DeepSeek-r1-Distill-Bangla-MMLU-Reasoning-Data](https://huggingface.co/datasets/KillerShoaib/DeepSeek-r1-Distill-Bangla-MMLU-Reasoning-Data)

**Train Samples:** 17,796

**Test Samples:** 2,576

**Total API Cost:** 7K BDT


# How the Dataset was created - High Level Overview

## Step 1 - Base Dataset
I've used `bangla-mmlu` dataset released by `hisab`. Kudos to them for creating and open sourcing the dataset. Without their dataset this synthetic reasoning dataset won't exist in the first place.

## Step 2 - Select Subset
Since I'm using `DeepSeek r1` and it's not free therefore I can't generate the synthetic data for the entire base dataset. Hence I've chosen a subset from the train (actually `validation` in the base dataset, I'm calling this set as `train` in my dataset) and test.

## Step 3 - Generate Response (Synthetic Data)
After selecting the subset from the original data I've prompted the `DeepSeek r1` model with the `formated_question` in the dataset and got the response. I had used `Hyperbolic` API. They are the only provider who were providing the `DeepSeek r1` at a reasonable price. Unfortunately couldn't use official `Deepseek` api due to the credit card region issue.

## Step 4 - Separating Correct from Wrong
After getting all the response from the `Deepseek r1` now it was time to seperate the right responses from all the response. Total percentage of correct answers from `DeepSeek r1` were around 86% (combining both train and test). Instead of manually checking which answer was correct I use `Gemini flash 2.0` and automate the whole process. I pass the generated response alongside the actual ans and id of the sample and then get structure output with the id and true/false as an output. If the answer is correct then it'll be true else will be false.

## Step 5 - Translation
Since `DeepSeek r1` used GRPO technique to teach the model it's thinking process therefore the reasoning from the model is always is in English / Chinese and it can't be changed using instruction. That's why to make this dataset completely in Bangla I need to translate it. For this I've used again `Gemini flash 2.0`. Since I was using free tier of their api therefore I've to pass 5 samples in a single api call to translate. The translation was good but I found in some cases the translation was correct but the `<think>` tag was mismatched where the translation generated `<think>` tag before the actual response. I'll write more details about this in my blog post.

## Step 6 - Translating The Incomplte Samples
`Gemini 2.0 flash` can output 8k tokens in a single api call, therefore in many cases it hit the token limit before able to translate all the 5 samples. In this case I've then seperately translate those samples as a single sample in the api call.


# Code Snipet to Download the dataset from Hugging Face

Install the datasets library if you've not installed yet.
```
pip install datasets
```

Then load the dataset

```python
from datasets import load_dataset
dataset = load_dataset("KillerShoaib/DeepSeek-r1-Distill-Bangla-MMLU-Reasoning-Data")
```


# Blog
**I'll be publishing a detail blog about the entire synthetic data generation process very soon, till then adios**


# Something that is bugging me (Unrelated)
**`And one more thing, I usually do not share any political view online or anywhere but what's happening in Gaza it's truly heartbreaking. I know this is not the place to share this view but can't help myself. May Allah save the people of Palestine and punish the wrongdoers.`**