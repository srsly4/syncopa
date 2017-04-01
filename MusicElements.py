from enum import Enum


class ToneType(Enum):
    Dur = 1
    Mol = 2


class Tone:
    def __init__(self, tone_index: int, tone_type: ToneType):
        self.index = tone_index
        self.type = tone_type

    def __str__(self, *args, **kwargs):
        tone_objects = [
            "C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "G♯", "A", "B♭", "H"
        ]
        ret = tone_objects[self.index % 12]
        if self.type == ToneType.Mol:
            ret += "m"
        return ret

    def __eq__(self, other):
        return self.index == other.index and self.type == other.type

    def __lt__(self, other):
        return hash(self) < hash(other)

    def _tone_type_hash(self):
        if self.type == ToneType.Dur:
            return 1
        if self.type == ToneType.Mol:
            return 2
        else:
            return 0

    def __hash__(self):
        return 10*self.index + (self._tone_type_hash())

    def get_note_index_by_octave(self, octave) -> int:
        return octave*12 + self.index

    def get_harmonic_tone_indexes(self) -> set:
        harmonic_set = set()
        harmonic_set.add(self.index)
        harmonic_set.add((self.index+7) % 12)
        if self.type == ToneType.Dur:
            harmonic_set.add((self.index + 4) % 12)
        if self.type == ToneType.Mol:
            harmonic_set.add((self.index + 3) % 12)
        return harmonic_set

    def get_harmonic_note_indexes(self) -> set:
        harmonic_set = set()
        for ndx in range(0, 100, 12):
            harmonic_set.add(ndx + self.index)
            harmonic_set.add(ndx + self.index + 7)
            if self.type == ToneType.Dur:
                harmonic_set.add(ndx + self.index + 4)
            if self.type == ToneType.Mol:
                harmonic_set.add(ndx + self.index + 3)
        return harmonic_set

    def get_forbidden_note_indexes(self) -> set:
        h_set = self.get_harmonic_tone_indexes()
        f_set = set()
        for h_note in h_set:
            curr_ndx = h_note - 1
            while curr_ndx < 160:
                f_set.add(curr_ndx)
                curr_ndx += 12
            curr_ndx = h_note + 1
            while curr_ndx < 160:
                f_set.add(curr_ndx)
                curr_ndx += 12
        return f_set

    def get_tone_note_indexes(self) -> set:
        ret = set()
        for octave in range(0, 8):
            primary = self.index + octave*12
            ret = ret.union({primary, primary + 2, primary + 5, primary + 7, primary + 11})
            if self.type == ToneType.Dur:
                ret.add(primary+4)
                ret.add(primary+9)
            if self.type == ToneType.Mol:  # harmonic mol range !!!
                ret.add(primary+3)
                ret.add(primary+8)
        return ret

    def next_tone_probability_list(self, tones: list):
        complementaries = self.complementary(self, tones)
        alternatives = self.alternatives(self, tones)
        prob_list = []
        for t in complementaries:
            prob_list.append({
                'tone': t,
                'probability': 1
            })
        for t in alternatives:
            prob_list.append({
                'tone': t,
                'probability': 0.75
            })
        return prob_list

    @staticmethod
    def complementary(current, tones: set) -> set:
        compl = {tone for tone in tones
                 if (tone.index == (current.index + 4) % 12
                     and current.type == ToneType.Dur)  # C -> E
                 or (tone.index == (current.index + 4) % 12
                     and current.type == ToneType.Dur)  # Cadd -> D
                 or (tone.index == (current.index + 7) % 12)  # C -> G
                 or (tone.index == (current.index + 3) % 12
                     and current.type == ToneType.Mol)  # C -> Em
                 }
        return compl

    @staticmethod
    def alternatives(to_tone, tones: set) -> set:
        alt_set = set()
        for tone in tones:
            tone_compl = Tone.complementary(tone, tones)
            if to_tone in tone_compl:
                alt_set.add(tone)
        return alt_set


class Note:
    def __init__(self, length, atomic):
        self.silent = False
        self.pitch = 60  # C5 as default by MIDI standard
        self.velocity = 128  # we consider all sounds to be equally-loud
        self.length = length
        self.atomic = atomic
        self.harmonic_flag = False
        self.finalized = False

    def get_tone_index(self):
        return self.pitch % 12

    def get_tone_from(self, tones: set):
        return next((t for t in tones if t.index == self.pitch % 12))

    def get_neighbours(self, tone: Tone, bottom_border=52, top_border=84, gap=12):
        neighbours_set = set()
        bottom_border = max(bottom_border, self.pitch-gap)
        top_border = min(top_border, self.pitch+gap)
        for note_ndx in range(bottom_border, top_border):
            neighbours_set.add(note_ndx)
        return neighbours_set.intersection(tone.get_tone_note_indexes())

    def get_tone_neighbours(self, tone: Tone, bottom_border=52, top_border=84):
        neighbours = self.get_neighbours(tone, bottom_border, top_border)
        harmonic = tone.get_harmonic_note_indexes()
        return neighbours.intersection(harmonic)

    def next_note_probability_in_tone(self, tone: Tone):
        last_note = self
        range_note_list: list = sorted(list(tone.get_tone_note_indexes()))
        try:
            last_note_range_ndx = range_note_list.index(last_note.pitch)
        except ValueError:
            return [{
                "note_index": tone.get_note_index_by_octave(6),
                "probability": 1
            }]

        probability_list = list()
        for key, note in enumerate(range_note_list):
            probability_list.append({
                "note_index": note,
                "probability": 0,
                "range_delta": abs(last_note_range_ndx - key),
                "range_dir": 1 if key > last_note_range_ndx else -1
            })

        probability_list = [note for note in probability_list if note['range_delta'] <= 8]

        range_probabilities = {
            0: 0.5,  # pryma
            1: 2,  # sekunda
            2: 0.2,  # tercja
            3: 0.5,  # kwarta
            4: 0.5,  # kwinta
            5: 0.1,  # seksta
            6: 0.1,  # septyma

        }
        for key, note in enumerate(probability_list):
            if note['range_delta'] in range_probabilities.keys():
                note['probability'] = range_probabilities[note['range_delta']]

        return [note for note in probability_list if note['probability'] > 0]

    def transpose_note(self, from_tone: Tone, to_tone: Tone):
        delta_tone = to_tone.get_note_index_by_octave(5) - from_tone.get_note_index_by_octave(5)
        primary_note_index = to_tone.get_note_index_by_octave(5) % 12
        self.pitch += delta_tone
        # Mol -> Dur case
        delta_note_index = self.pitch % 12 - primary_note_index
        if (from_tone.type == ToneType.Mol and to_tone.type == ToneType.Dur
                and (delta_note_index == 8 or delta_note_index == 3)):
            self.pitch += 1
        # Dur -> Mol case
        if (from_tone.type == ToneType.Dur and to_tone.type == ToneType.Mol
                and (delta_note_index == 9 or delta_note_index == 4)):
            self.pitch -= 1

    def __str__(self):
        note_representations = [
            "C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "G♯", "A", "B♭", "H"
        ]
        representation = self.atomic['representation'] + note_representations[self.get_tone_index()]
        representation += str((self.pitch // 12) + 1)
        return representation


class Bar:
    def __init__(self, size: int):
        self.tones = dict()
        self.notes = dict()
        self.bar_size = size

    def __str__(self):
        bar_str = "| "
        for note_index, note in self.notes.items():
            bar_str += str(note) + " "

        bar_str += "/".join([str(x) for x in self.tones.values()])
        bar_str += "|"
        return bar_str

    def append_note(self, note: Note):
        space_left = self.get_space_left()
        if note.length > space_left:
            raise ValueError("Can not fit that note into bar (incorrect size).")
        new_ndx = self.bar_size - space_left
        self.notes[new_ndx] = note

    def get_space_left(self) -> int:
        if len(self.notes) == 0:
            return self.bar_size
        max_key = max(self.notes.keys())
        last_note = self.notes[max_key]
        return self.bar_size - (max_key + last_note.length)

    def get_tone_for_note_index(self, index) -> Tone:
        if len(self.tones) == 0:
            raise ValueError("There are not any tones in this bar.")
        if index in self.tones:
            return self.tones[index]
        else:
            curr_tone_ndx = 0
            curr_tone = self.tones[0]
            while curr_tone_ndx <= index:
                if curr_tone_ndx in self.tones:
                    curr_tone = self.tones[curr_tone_ndx]
                curr_tone_ndx += 1
            return curr_tone

    def get_note_for_index(self, index) -> Note:
        if len(self.notes) == 0:
            raise ValueError("There are not any notes in this bar.")
        if index in self.notes:
            return self.notes[index]
        else:
            # find the first note after given index
            keys = [k for k in self.notes.keys() if k > index]
            if len(keys) == 0:
                raise ValueError("Note not found in bar.")
            return self.notes[keys[0]]
