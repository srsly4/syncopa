import json
import random
import copy
from miditime.miditime import MIDITime

import SeedRandomizer
from MusicElements import Tone, ToneType, Note, Bar


class ProcessorResults:
    def __init__(self):
        self.elements_source = {}
        self.default_bar_size = 32
        self.elements_atomic_keys = []
        self.elements_rhythm_sequences = []
        self.bars = []
        self.singleton_tones = []
        self.primary_tone = None
        self.tone_sequence = []
        self.sequence_samples = []


class DefaultProcessor:
    def __init__(self, results: ProcessorResults):
        self.results = results

    def process(self):
        raise NotImplementedError("Object is a default processor")


class ElementsParserProcessor(DefaultProcessor):
    def __init__(self, results: ProcessorResults, json_file: str):
        super().__init__(results)
        self.json_source = json_file

    @staticmethod
    def notes_from_element(element: str, atomic: dict):
        notes = list()
        for note_atomic_ndx in element.split(","):
            is_harmonic = note_atomic_ndx[0] == '*'
            is_silent = note_atomic_ndx[0] == "#"
            if is_harmonic or is_silent:
                note_atomic_ndx = note_atomic_ndx[1:]
            note_atomic = atomic[note_atomic_ndx]
            cur_note = Note(note_atomic['length'], note_atomic)
            cur_note.harmonic_flag = is_harmonic
            cur_note.silent = is_silent
            notes.append(cur_note)
        return notes

    def process(self):
        elements_f = open(self.json_source)
        elements = json.loads(elements_f.read())
        self.results.elements_source = elements

        self.results.default_bar_size = elements['bar']['size']
        self.results.elements_atomic_keys = list(elements['atomic'].keys())

        # generate note sequences from elements
        rhythm_elements = elements['elements']
        for re in rhythm_elements:
            re['notes'] = self.notes_from_element(re['sequence'], elements['atomic'])
            seq_length = 0
            for note in re['notes']:
                seq_length += note.length
            re['length'] = seq_length

        self.results.elements_rhythm_sequences = rhythm_elements


class ToneGeneratorProcessor(DefaultProcessor):
    def process(self):
        # generate all tones
        tones = set()
        for t_ndx in range(0, 12):
            newtone = Tone(t_ndx, ToneType.Dur)
            moltone = Tone(t_ndx, ToneType.Mol)
            tones.add(newtone)
            tones.add(moltone)

        self.results.singleton_tones = tones
        primary_tone = SeedRandomizer.random_from_sorted_set(tones)
        self.results.primary_tone = primary_tone
        print("Primary tone: " + str(primary_tone))

        # `sadness` probability
        mol_chance = 0.15 + random.random() * 0.6

        print("Sadness: " + str(mol_chance))

        tone_sequence = [primary_tone]

        harmonic_notes = primary_tone.get_tone_note_indexes()
        harmonic_tones = {note % 12 for note in harmonic_notes}

        last_tone = primary_tone

        for i in range(0, 3 + random.randrange(0, 5)):
            tmp_poll = {tone for tone in harmonic_tones if tone != last_tone.index}
            tone_shot = SeedRandomizer.random_from_sorted_set(tmp_poll)
            tone_type_shoot = ToneType.Mol if random.random() < mol_chance else ToneType.Dur
            selected = list({tone for tone in tones if tone.index == tone_shot and tone.type == tone_type_shoot})[0]
            tone_sequence.append(selected)
            last_tone = selected

        print("Tone sequence:")
        for tone in tone_sequence:
            print(str(tone) + " ", end='')
        print("")
        self.results.tone_sequence = tone_sequence


class BarGeneratorProcessor(DefaultProcessor):
    def process(self):
        bars = list()

        tone_sequence_ndx = 0
        # generate bars
        first_note_in_all_bars = True
        previous_note: Note
        for bar_gen_ndx in range(0, 64):
            bar = Bar(self.results.default_bar_size)
            # in each bar generate tones
            if bar_gen_ndx == 0:
                bar.tones[0] = self.results.primary_tone
            else:
                bar.tones[0] = self.results.tone_sequence[tone_sequence_ndx]
                tone_sequence_ndx = 0 if tone_sequence_ndx >= len(self.results.tone_sequence) - 1\
                    else tone_sequence_ndx + 1

            if random.random() > 0.5:
                bar.tones[bar.bar_size / 2] = self.results.tone_sequence[tone_sequence_ndx]
                tone_sequence_ndx = 0 if tone_sequence_ndx >= len(self.results.tone_sequence) - 1\
                    else tone_sequence_ndx + 1

            bar_rest = bar.bar_size
            while bar_rest > 0:
                possible_sequences =\
                    [seq for seq in self.results.elements_rhythm_sequences if seq['length'] <= bar_rest]
                selected_seq = SeedRandomizer.random_from_probability_list(possible_sequences)

                for seq_note in selected_seq['notes']:
                    bar.append_note(copy.copy(seq_note))

                bar_rest = bar.get_space_left()

            # generate pitch of note
            for note_ndx, note in bar.notes.items():
                # first note must be primary tone note
                if first_note_in_all_bars:
                    first_note_in_all_bars = False
                    note.pitch = self.results.primary_tone.get_note_index_by_octave(5)
                elif note.silent:
                    note.finalized = True
                    continue
                elif note.harmonic_flag:  # harmonic notes
                    note_tone = bar.get_tone_for_note_index(note_ndx)
                    harmonic_range = note_tone.get_harmonic_note_indexes()
                    note_neighbours = previous_note.get_neighbours(note_tone, top_border=84, gap=12)
                    tone_range = note_tone.get_harmonic_note_indexes()

                    probability_list = previous_note.next_note_probability_in_tone(note_tone)
                    probability_list = [note for note in probability_list
                                        if note['note_index'] in harmonic_range
                                        and note['note_index'] in note_neighbours
                                        and note['note_index'] in tone_range]
                    if len(probability_list) == 0:
                        # set the primary note of note tone
                        note.pitch = note_tone.get_note_index_by_octave(5)
                    else:
                        note.pitch = SeedRandomizer.random_from_probability_list(probability_list)['note_index']

                else:  # non-harmonic notes
                    note_tone = bar.get_tone_for_note_index(note_ndx)  # current tone
                    forbidden_set = note_tone.get_forbidden_note_indexes()  # wrong sounds to differentiate
                    tone_range = note_tone.get_harmonic_note_indexes()

                    probability_list = previous_note.next_note_probability_in_tone(note_tone)
                    probability_list = [note for note in probability_list
                                        if not note['note_index'] in forbidden_set
                                        and note['note_index'] in tone_range]

                    note.pitch = SeedRandomizer.random_from_probability_list(probability_list)['note_index']

                note.finalized = True
                previous_note = note

            print(str(bar))
            bars.append(bar)


class MidiGeneratorProcessor(DefaultProcessor):
    def __init__(self, results: ProcessorResults, midi_file: str, bpm: int):
        self.midi_file = midi_file,
        self.bpm = bpm
        super(MidiGeneratorProcessor, self).__init__(results)

    def process(self):
        print("Generating MIDI...")
        bpm = 120
        bar_bpm = 8
        bar_time = self.results.default_bar_size / bar_bpm

        midi = MIDITime(bpm, "test.mid")
        midi_data = []
        midi_tone_data = []

        curr_beat = 0
        tone_beat = 0

        for bar in self.results.bars:
            tone_beat = curr_beat
            for note_ndx, note in bar.notes.items():
                note_midi_length = bar_time * (note.length / bar.bar_size)
                if not note.silent:
                    midi_data.append([
                        curr_beat, note.pitch, 127, note_midi_length
                    ])
                curr_beat += note_midi_length

            tone_length = self.results.default_bar_size // len(bar.tones.items())
            for tone_ndx, tone in bar.tones.items():
                tone_midi_length = bar_time * (tone_length / bar.bar_size)
                midi_tone_data.append([
                    tone_beat, tone.get_note_index_by_octave(3), 100, tone_midi_length
                ])
                # midi_tone_data.append([
                #     tone_beat, tone.get_note_index_by_octave(4)+7, 100, tone_midi_length
                # ])
                # if tone.type == ToneType.Dur:
                #     midi_tone_data.append([
                #         tone_beat, tone.get_note_index_by_octave(4) + 4, 100, tone_midi_length
                #     ])
                # if tone.type == ToneType.Mol:
                #     midi_tone_data.append([
                #         tone_beat, tone.get_note_index_by_octave(4) + 3, 100, tone_midi_length
                #     ])
                tone_beat += tone_midi_length

        midi.add_track(midi_data)
        midi.add_track(midi_tone_data)
        midi.save_midi()

# end of Processors.py
