import requests
pgn = '''[Event "Test"]
1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O'''
res = requests.post('http://127.0.0.1:8000/analyze', files={'file': ('test.pgn', pgn, 'text/plain')}, data={'url':'https://lichess.org/sample'})
print('Status', res.status_code)
try:
    print(res.json())
except Exception as e:
    print('Error decoding JSON:', e)
