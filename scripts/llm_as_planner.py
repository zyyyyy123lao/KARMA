import openai
import json
import os

API_KEY = "sk-rcEwLLwcwvD53Ffvi87E9HhLEL3yuSLey3zh4HZL3pKPldj9"
BASE_URL = "https://api.chatanywhere.tech/v1"
MODEL_NAME = "gpt-4o-mini-2024-07-18"

# 定义基础路径
BASE_PATH = '/root/autodl-tmp/KARMA'

similarity_flag_path = os.path.join(BASE_PATH, 'logs/similarity_flag.json')
messages_path = os.path.join(BASE_PATH, 'logs/messages.json')

def load_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# def insert_code_into_file(api_generated_code, target_file_path, line_number):
#     with open(target_file_path, 'r') as file:
#         file_content = file.readlines()
    
#     insert_index = line_number - 1
    
#     if insert_index > len(file_content):
#         insert_index = len(file_content)
    
#     file_content.insert(insert_index, api_generated_code + '\n')
    
#     with open(target_file_path, 'w') as file:
#         file.writelines(file_content)

def insert_code_into_file(new_code, target_file_path, line_number):
    with open(target_file_path, 'r') as file:
        lines = file.readlines()
    
    # 保留插入行号之前的内容
    before_lines = lines[:line_number - 1]
    
    # 组合新的文件内容：插入之前的内容 + 新代码
    new_lines = before_lines + new_code.splitlines(keepends=True)
    
    # 写回文件
    with open(target_file_path, 'w') as file:
        file.writelines(new_lines)

# example
api_generated_code = '''
def new_function():
    print("This is a new function")
'''
target_file_path = os.path.join(BASE_PATH, 'scripts/task_functions.py')
line_number = 6
insert_code_into_file(api_generated_code, target_file_path, line_number)

def write_to_file(file_path, content):
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(content + '\n')

def load_similarity_flag():
    try:
        with open(similarity_flag_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data.get("similarity_flag", False)
    except FileNotFoundError:
        return False

use_short_term_memory = load_similarity_flag()
       
skills = load_file(os.path.join(BASE_PATH, 'prompts/skills.txt'))
skills_ex = load_file(os.path.join(BASE_PATH, 'resources/actions.py'))
role = load_file(os.path.join(BASE_PATH, 'prompts/role.txt'))
examples = load_file(os.path.join(BASE_PATH, 'prompts/examples.txt'))
emphasize = load_file(os.path.join(BASE_PATH, 'prompts/emphasize.txt'))
instruction = load_file(os.path.join(BASE_PATH, 'prompts/instruction.txt'))
short_term_memory = load_file(os.path.join(BASE_PATH, 'prompts/short_term_memory.txt'))
long_term_memory = load_file(os.path.join(BASE_PATH, 'prompts/long_term_memory.txt'))


messages = [
    {"role": "user", "content": skills},
    {"role": "user", "content": skills_ex},
    {"role": "system", "content": role},
    {"role": "user", "content": examples},
    {"role": "user", "content": emphasize},
    {"role": "user", "content": long_term_memory},
    {"role": "user", "content": instruction}
]

if use_short_term_memory:
    messages.insert(5, {"role": "user", "content": short_term_memory})

with open(messages_path, 'w', encoding='utf-8') as file:
    json.dump(messages, file, ensure_ascii=False, indent=4)    

if API_KEY and BASE_URL:
    openai.api_key = API_KEY
    openai.api_base = BASE_URL

response = openai.ChatCompletion.create(
    model=MODEL_NAME,
    messages=messages,
    max_tokens=4096,
    temperature=0,
    stop=None
)

response_content = response.choices[0].message['content'].strip()

lines = response_content.split('\n')
code_lines = []
recording = False
function_name = None

for line in lines:
    if line.strip().startswith("def "):
        recording = True
        function_name = line.split('(')[0].split()[1]
    if recording:
        if line.strip() == '```':
            continue
        code_lines.append(line)

api_generated_code = '\n'.join(code_lines).strip()

print(api_generated_code)

target_file_path = os.path.join(BASE_PATH, 'scripts/task_functions.py')
line_number = 6 # 插入代码的行号
insert_code_into_file(api_generated_code, target_file_path, line_number)

# Save the function name to a file for later use
file_path = os.path.join(BASE_PATH, 'logs/generated_function_name.json')
with open(file_path, 'w') as file:
    json.dump({"function_name": function_name}, file)





