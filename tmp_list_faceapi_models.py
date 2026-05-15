import requests

paths = ['weights', 'dist/models', 'model']
for path in paths:
    url = f'https://api.github.com/repos/justadudewhohacks/face-api.js/contents/{path}'
    r = requests.get(url, timeout=30)
    print('PATH', path, 'STATUS', r.status_code)
    if r.status_code == 200:
        data = r.json()
        print([item['name'] for item in data][:50])
    else:
        print(r.text[:400])
