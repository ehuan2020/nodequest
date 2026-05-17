from huggingface_hub import hf_hub_download
import os

files = ['config.json', 'generation_config.json', 'model.safetensors']
for f in files:
    path = hf_hub_download('microsoft/OmniParser-v2.0', f'icon_caption/{f}', local_dir='weights')
    print(f'Downloaded: {path}')
print('Done')