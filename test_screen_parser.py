import screen_parser
import time

print('Starting server...')
screen_parser.start_server()

timeout = 300
start = time.time()
while not screen_parser._server_ready:
    if time.time() - start > timeout:
        print('Timeout')
        exit()
    time.sleep(1)

print('Server ready. Open UE5 and right-click in Content Browser to show context menu.')
print('Press Enter when the context menu is visible...')
input()

print('Searching for Material...')
result = screen_parser.find_element('Material')
print(f'Material: {result}')

print('Searching for Content Browser...')
result2 = screen_parser.find_element('Content Browser')
print(f'Content Browser: {result2}')

print('Searching for Blueprint Class...')
result3 = screen_parser.find_element('Blueprint Class')
print(f'Blueprint Class: {result3}')
