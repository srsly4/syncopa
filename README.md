# Syncopa
Narcotic melody generator.

Generator uses tone-balanced sample creation for building harmonic and repeatable music.

Requires installed library miditime (by pip): https://pypi.python.org/pypi/miditime

## Usage
`main.py [-h] [-s SEED] [-o OUTPUT] [-b BARS] [--bpm BPM] [--continuous]
               [--rich] [-v]`

Optional arguments:
* `-h, --help ` show this help message and exit
* `-s SEED, --seed SEED` A seed to melody generation process
* `-o OUTPUT, --output OUTPUT` Output file name
* `-b BARS, --bars BARS` Count of generated bars
* `-t TONES, --tones TONES` Force tone sequence (format: `C,Gm,Hbm,Fs`)
* `--bpm BPM` Beats per minute (tempo)
* `--continuous` Generates melody using continuous sample creation
* `--rich` Another implementation of accompaniment
* `-v, --verbose` Retrieves text transcription of generated melody

## Good examples:
* `qwerty` (with rich mode enabled)
* `01b525321a3e` (with rich mode enabled)
* `mementomori` (witch rich mode enabled)
* `64adf9f13e41`
* `seed`
* `rawr`
* `return`
* `-t D,Hm,A,G -s 15d07a69ed4a`

# Orignal task content

Uporczywe narkotyczne melodie potrafią czasem na długo przylgnąć do umysłu.
Napisz program, który generuje narkotyczne melodie. Program powinien generować różne melodie w zależności od tego, jakie użytkownik poda opcje. Użytkownik będzie tak długo modyfikował opcje programu aż wygenerowana melodia utkwi mu na stałe w głowie.

Melodie te powinny być generowane w postaci plików midi i zapisywane na dysku twardym, przy czym użytkownik powinien mieć możliwość podania lokalizacji. Obsługa karty dźwiękowej w celu odtworzenia wygenerowanej melodii nie jest konieczna. Można użyć dowolnej biblioteki do obslugi formatu midi, przykladowo https://pypi.python.org/pypi/miditime


Program ten powinien wykorzystywać następujące elementy:
 - klasy
 - funkcje
 - parsowanie argumentów linii poleceń za pomocą modułu argparse ze standardowej biblioteki
 - zewnętrzna biblioteka do obsługi formatu midi

Tresc zadania w Google Drive: https://goo.gl/dbfwo3

Termin oddania zadania: 3 kwietnia 2017, 20:00
