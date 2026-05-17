import screen_parser

print('Loading models...')
screen_parser.load_models()

print('Taking screenshot...')
result = screen_parser.find_element('Material')
print(f'Material found at: {result}')

result2 = screen_parser.find_element('Content Browser')
print(f'Content Browser found at: {result2}')
