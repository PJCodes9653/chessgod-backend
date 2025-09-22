from analysis.analyzer import analyze_game

pgn = '''[Event "Test"]
1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O'''

if __name__ == '__main__':
    print('Running analyzer test')
    res = analyze_game(pgn)
    print('White accuracy:', res['white']['accuracy'])
    print('Black accuracy:', res['black']['accuracy'])
    print('White counts:', res['white']['counts'])
    print('White moves (great):', res['white']['moves'].get('great'))
