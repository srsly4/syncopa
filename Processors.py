import json
import random
import copy
import logging

from miditime.miditime import MIDITime

import SeedRandomizer
from MusicElements import Tone, ToneType, Note, Bar
from RepetitiveElements import SequenceSample


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
        logging.info("Primary tone: " + str(primary_tone))

        # `sadness` probability
        mol_chance = 0.15 + random.random() * 0.6

        logging.info("Sadness probability: " + str(mol_chance))

        tone_sequence = [primary_tone]

        harmonic_notes = primary_tone.get_tone_note_indexes()

        last_tone = primary_tone

        for i in range(0, 3+ random.randrange(0, 5)):
            tone_probabilities = last_tone.next_tone_probability_list(self.results.singleton_tones)
            tone_choosen = SeedRandomizer.random_from_probability_list(tone_probabilities)
            tone_sequence.append(tone_choosen["tone"])
            last_tone = tone_choosen["tone"]

        logging.info("Tone sequence:")
        for tone in tone_sequence:
            print(str(tone) + " ", end='')
        print("")
        self.results.tone_sequence = tone_sequence


class SequenceSamplesGeneratorProcessor(DefaultProcessor):
    def __init__(self, results: ProcessorResults, max_sample_count=10):
        self.max_sample_count = max_sample_count
        super(SequenceSamplesGeneratorProcessor, self).__init__(results)

    def process(self):
        sample_types = [
            {
                'length': self.results.default_bar_size // 2,
                'probability': 0.8
            },
            {
                'length': self.results.default_bar_size,
                'probability': 0.2
            }
        ]
        sample_count = random.randrange(6, self.max_sample_count)
        self.results.sequence_samples = []
        first_sample_flag = True
        logging.info("Samples:")
        for sample_ndx in range(0, sample_count):
            sample_type = SeedRandomizer.random_from_probability_list(sample_types)
            sample_length_rest = sample_length = sample_type['length']
            sample_notes = []

            # generate sample notes
            while sample_length_rest > 0:
                possible_sequences = [seq for seq in
                                      self.results.elements_rhythm_sequences if seq['length'] <= sample_length_rest]
                selected_seq = SeedRandomizer.random_from_probability_list(possible_sequences)

                for seq_note in selected_seq['notes']:
                    sample_notes.append(copy.copy(seq_note))

                sample_length_rest -= selected_seq['length']

            # now generate pitches of these notes
            previous_note = Note(self.results.default_bar_size, self.results.elements_source['atomic']['quarter'])
            previous_note.pitch = self.results.primary_tone.get_note_index_by_octave(5)
            for note in sample_notes:
                note_tone = self.results.primary_tone
                if first_sample_flag:
                    note.pitch = self.results.primary_tone.get_note_index_by_octave(5)
                    first_sample_flag = False
                elif note.silent:
                    note.finalized = True
                    continue
                elif note.harmonic_flag:  # harmonic notes
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
                    forbidden_set = note_tone.get_forbidden_note_indexes()  # wrong sounds to differentiate
                    tone_range = note_tone.get_harmonic_note_indexes()

                    probability_list = previous_note.next_note_probability_in_tone(note_tone)
                    probability_list = [note for note in probability_list
                                        if not note['note_index'] in forbidden_set
                                        and note['note_index'] in tone_range]

                    note.pitch = SeedRandomizer.random_from_probability_list(probability_list)['note_index']

                note.finalized = True
                previous_note = note

            sample = SequenceSample(self.results.primary_tone, sample_notes)
            self.results.sequence_samples.append(sample)
            logging.info(str(sample))

        # now generate `friend` connections between samples
        sample_connections = random.randrange(2, sample_count // 2)
        for sample_ndx, sample in enumerate(self.results.sequence_samples):
            shuffled = copy.copy(self.results.sequence_samples)
            random.shuffle(shuffled)
            sample_poll = [smp for smp in shuffled if smp is not sample]
            conn_count = 0
            for sample_friend in sample_poll:
                sample.friendly_samples.append({
                    'sample': sample_friend,
                    'probability': random.random()
                })
                conn_count += 1
                if conn_count >= sample_connections:
                    break
            sample.friendly_samples.append({
                'sample': sample,
                'probability': 0.4 * random.random()
            })


class BarSampleGeneratorProcessor(DefaultProcessor):
    def __init__(self, results: ProcessorResults, min_bar_count: int):
        super(BarSampleGeneratorProcessor, self).__init__(results)
        self.min_bar_count = min_bar_count

    def process(self):
        bars = list()
        first_sequence_in_all_bars = True
        previous_sequence: SequenceSample
        tone_sequence_ndx = 0
        logging.info("Bars:")
        for bar_ndx in range(0, self.min_bar_count):
            bar = Bar(self.results.default_bar_size)
            if bar_ndx == 0:
                bar.tones[0] = self.results.primary_tone
            else:
                bar.tones[0] = self.results.tone_sequence[tone_sequence_ndx]
            tone_sequence_ndx = 0 if tone_sequence_ndx >= len(self.results.tone_sequence) - 1 \
                else tone_sequence_ndx + 1

            if random.random() > 0.5:
                bar.tones[bar.bar_size / 2] = self.results.tone_sequence[tone_sequence_ndx]
                tone_sequence_ndx = 0 if tone_sequence_ndx >= len(self.results.tone_sequence) - 1 \
                    else tone_sequence_ndx + 1

            bar_rest = self.results.default_bar_size
            max_sequence_length = bar.bar_size // len(bar.tones)
            while bar_rest > 0:
                current_tone = bar.get_tone_for_note_index(bar.bar_size - bar_rest)
                if first_sequence_in_all_bars:  # if first bar get first sequence (with a primary note)
                    sequence = self.results.sequence_samples[0]
                    first_sequence_in_all_bars = False
                else:
                    # get every possible sequence
                    sequence_poll = \
                        [seq for seq in previous_sequence.friendly_samples
                         if seq['sample'].get_length() <= max_sequence_length
                            and seq['sample'].get_length() <= bar_rest]
                    if len(sequence_poll) > 0:
                        last_note: Note = previous_sequence.get_last_note()
                        next_probabilities = last_note.next_note_probability_in_tone(current_tone)

                        for seq in sequence_poll:
                            next_note: Note = seq['sample'].get_first_note()
                            found_flag = False
                            for prob_note in next_probabilities:
                                if next_note.pitch == prob_note['note_index']:
                                    seq['probability'] *= prob_note['probability']
                                    found_flag = True
                                    break
                            if not found_flag:  # if it's `strange` range jump make it almost impossible
                                seq['probability'] = 0.01

                        sequence_shot = SeedRandomizer.random_from_probability_list(sequence_poll)
                        sequence = sequence_shot['sample']
                    else:  # quite impossible-like
                        sequence = random.choice([seq for seq in self.results.sequence_samples
                                                  if seq.get_length() <= min(bar_rest, max_sequence_length)])

                sequence_transponed_notes = sequence.get_transposed_notes(current_tone)
                for note in sequence_transponed_notes:
                    bar.append_note(note)

                previous_sequence = sequence
                bar_rest = bar.get_space_left()

            bars.append(bar)
            logging.info(str(bar))
            self.results.bars = bars


class BarGeneratorProcessor(DefaultProcessor):
    def process(self):
        bars = list()

        tone_sequence_ndx = 0
        # generate bars
        first_note_in_all_bars = True
        previous_note: Note
        logging.info("Bars")
        for bar_gen_ndx in range(0, 64):
            bar = Bar(self.results.default_bar_size)
            # in each bar generate tones
            if bar_gen_ndx == 0:
                bar.tones[0] = self.results.primary_tone
            else:
                bar.tones[0] = self.results.tone_sequence[tone_sequence_ndx]
                tone_sequence_ndx = 0 if tone_sequence_ndx >= len(self.results.tone_sequence) - 1 \
                    else tone_sequence_ndx + 1

            if random.random() > 0.5:
                bar.tones[bar.bar_size / 2] = self.results.tone_sequence[tone_sequence_ndx]
                tone_sequence_ndx = 0 if tone_sequence_ndx >= len(self.results.tone_sequence) - 1 \
                    else tone_sequence_ndx + 1

            bar_rest = bar.bar_size
            while bar_rest > 0:
                possible_sequences = \
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

            logging.info(str(bar))
            bars.append(bar)
        self.results.bars = bars


class MidiGeneratorProcessor(DefaultProcessor):
    def __init__(self, results: ProcessorResults, midi_file: str, bpm: int, rich_mode=False):
        self.output_file: str = str(midi_file)
        self.bpm = bpm
        self.rich_mode = rich_mode
        super(MidiGeneratorProcessor, self).__init__(results)

    def process(self):
        logging.info("Generating MIDI...")
        bpm = self.bpm
        bar_bpm = 8
        bar_time = self.results.default_bar_size / bar_bpm

        midi = MIDITime(bpm, self.output_file)
        midi_data = []
        midi_tone_data = []

        curr_beat = 0

        for bar in self.results.bars:
            tone_beat = curr_beat
            for note_ndx, note in bar.notes.items():
                note_midi_length = bar_time * (note.length / bar.bar_size)
                if not note.silent:
                    midi_data.append([
                        curr_beat, note.pitch + (12 if self.rich_mode else 0), 127, note_midi_length
                    ])
                curr_beat += note_midi_length

            if not self.rich_mode:
                tone_length = self.results.default_bar_size // len(bar.tones.items())
                for tone_ndx, tone in bar.tones.items():
                    tone_midi_length = bar_time * (tone_length / bar.bar_size)
                    midi_tone_data.append([
                        tone_beat, tone.get_note_index_by_octave(3), 100, tone_midi_length
                    ])
                    midi_tone_data.append([
                        tone_beat, tone.get_note_index_by_octave(3)+7, 100, tone_midi_length
                    ])
                    if tone.type == ToneType.Dur:
                        midi_tone_data.append([
                            tone_beat, tone.get_note_index_by_octave(3) + 4, 100, tone_midi_length
                        ])
                    if tone.type == ToneType.Mol:
                        midi_tone_data.append([
                            tone_beat, tone.get_note_index_by_octave(3) + 3, 100, tone_midi_length
                        ])

                    tone_beat += tone_midi_length
            else:
                rich_tone_length = self.results.default_bar_size // 8
                rich_tone_real_length = bar_time * (rich_tone_length / bar.bar_size)
                tone_accomp_curr = 0
                rich_tone_seq_ndx = 0
                while tone_accomp_curr < bar.bar_size:
                    rich_tone = bar.get_tone_for_note_index(tone_accomp_curr)
                    rich_tone_seq = [
                        rich_tone.get_note_index_by_octave(3),
                        rich_tone.get_note_index_by_octave(4),
                        rich_tone.get_note_index_by_octave(4) + 4
                        if rich_tone.type == ToneType.Dur else
                        rich_tone.get_note_index_by_octave(4) + 3,
                        rich_tone.get_note_index_by_octave(4)+7,

                    ]
                    midi_tone_data.append([
                        tone_beat, rich_tone_seq[rich_tone_seq_ndx], 90,
                        rich_tone_real_length*(len(rich_tone_seq)-rich_tone_seq_ndx)
                    ])
                    rich_tone_seq_ndx = 0 if rich_tone_seq_ndx >= len(rich_tone_seq) - 1 else rich_tone_seq_ndx + 1
                    tone_beat += rich_tone_real_length
                    tone_accomp_curr += rich_tone_length

        midi.add_track(midi_data)
        midi.add_track(midi_tone_data)
        midi.save_midi()

# end of Processors.py
