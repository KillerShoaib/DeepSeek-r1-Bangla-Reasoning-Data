import os
import json
import re
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
file_handler = logging.FileHandler('logs/translation_log.log')
console_handler = logging.StreamHandler()

# Create formatters and add it to handlers
log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def load_error_batch_data(set:str='valid'):
    error_data = []
    error_path = 'Translation_Batch_Data_Error'
    
    # Check if directory exists
    if not os.path.exists(error_path):
        logger.warning(f"Directory {error_path} does not exist")
        return error_data
        
    logger.info(f"Loading error batch data for {set} set from {error_path}")
    
    # Go through all files in the directory
    for filename in os.listdir(error_path):
        if filename.endswith('.txt') and set in filename:
            logger.info(f"Processing file: {filename}")
            file_path = os.path.join(error_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    error_data.append(content)
                logger.debug(f"Successfully read file: {filename}")
            except Exception as e:
                logger.error(f"Error reading file {filename}: {e}")
                
    return error_data


def extract_complete_samples(input_string):
    # List to store complete samples
    complete_samples = []
    
    # Find all matches of complete JSON objects
    # Pattern looks for objects starting with { and ending with }
    pattern = r'{[^{]*"id":[^}]*"reasoning_translation":[^}]*"ans_translation":[^}]*}'
    
    # Find all matches in the input string
    matches = re.finditer(pattern, input_string)
    
    for match in matches:
        try:
            # Try to parse each matched string into a dictionary
            sample_dict = json.loads(match.group())
            # Verify that all required keys are present
            if all(key in sample_dict for key in ["id", "reasoning_translation", "ans_translation"]):
                complete_samples.append(sample_dict)
        except json.JSONDecodeError:
            continue
    
    return complete_samples

def extract_complete_samples_from_list_of_strings(list_of_strings:list):
    logger.info("Starting to extract complete samples from error batch data")
    complete_samples = []
    for i, string in enumerate(list_of_strings, 1):
        extracted_samples = extract_complete_samples(string)
        complete_samples.extend(extracted_samples)
        logger.debug(f"Extracted {len(extracted_samples)} complete samples from batch {i}")
    
    logger.info(f"Total complete samples extracted: {len(complete_samples)}")
    return complete_samples

def save_complete_samples(complete_samples, output_file):
    logger.info(f"Saving {len(complete_samples)} complete samples to {output_file}")
    # Save the complete samples to a JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complete_samples, f, ensure_ascii=False, indent=4)
        logger.info(f"Successfully saved samples to {output_file}")
    except Exception as e:
        logger.error(f"Error saving samples to {output_file}: {e}")


# Processing validation set
logger.info("Starting processing of validation set error data")
error_data = load_error_batch_data(set='valid')
complete_samples = extract_complete_samples_from_list_of_strings(error_data)
save_complete_samples(complete_samples, 'Data/valid_complete_translated_data_samples_from_error_batch.json')
logger.info(f"Completed processing validation set. Total samples recovered: {len(complete_samples)}")

# Processing test set
logger.info("Starting processing of test set error data")
error_data_test = load_error_batch_data(set='test')
complete_samples_test = extract_complete_samples_from_list_of_strings(error_data_test)
save_complete_samples(complete_samples_test, 'Data/test_complete_translated_data_samples_from_error_batch.json')
logger.info(f"Completed processing test set. Total samples recovered: {len(complete_samples_test)}")