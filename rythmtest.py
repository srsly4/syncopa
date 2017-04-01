import json
import random
import copy
from miditime.miditime import MIDITime

from MusicElements import Tone, ToneType, Note, Bar
import SeedRandomizer


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


random.seed("dshsr")

# load json data
elements_f = open("rythmelements.json")
elements = json.loads(elements_f.read())

bar_size = elements['bar']['size']
atomic_keys = list(elements['atomic'].keys())

# generate note sequences from elements
rhythm_elements = elements['elements']
for re in rhythm_elements:
    re['notes'] = notes_from_element(re['sequence'], elements['atomic'])
    seq_length = 0
    for note in re['notes']:
        seq_length += note.length
    re['length'] = seq_length


# generate all tones
tones = set()
for t_ndx in range(0, 12):
    newtone = Tone(t_ndx, ToneType.Dur)
    moltone = Tone(t_ndx, ToneType.Mol)
    tones.add(newtone)
    tones.add(moltone)

primary_tone = SeedRandomizer.random_from_sorted_set(tones)

print("Primary tone: " + str(primary_tone))


# searching primary tones
# search_depth = 1
# complementary_tones = Tone.complementary(primary_tone, tones)
#
# print("Complementary tones:")
# for tone in complementary_tones:
#     print(str(tone)+" ", end='')
# print("")
#
# alternative_tones = Tone.alternatives(primary_tone, tones)
# print("Alternative tones:")
# for tone in alternative_tones:
#     print(str(tone)+" ", end='')
# print("")
#
# tone_poll = {primary_tone}
# tone_poll = tone_poll.union(alternative_tones)
# tone_poll = tone_poll.union(complementary_tones)

# tone_sequence = [primary_tone]  # start from primary
# tone_sequence_ndx = 0
# for tone_seq_ndx in range(0, random.randrange(4, 6)):
#     possible_tones = tone_poll.difference({tone_sequence[tone_sequence_ndx]})
#     tone_sequence.append(SeedRandomizer.random_from_sorted_set(possible_tones))

# `sadness`
mol_chance = 0.15 + random.random()*0.6

print("Sadness: " + str(mol_chance))

tone_sequence = [primary_tone]
tone_sequence_ndx = 0

harmonic_notes = primary_tone.get_tone_note_indexes()
harmonic_tones = {note % 12 for note in harmonic_notes}

last_tone = primary_tone

for i in range(0, 3+random.randrange(0, 5)):
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

bars = list()
# generate bars
first_note_in_all_bars = True
previous_note: Note
for bar_gen_ndx in range(0, 64):
    bar = Bar(bar_size)
    # in each bar generate tones
    if bar_gen_ndx == 0:
        bar.tones[0] = primary_tone
    else:
        bar.tones[0] = tone_sequence[tone_sequence_ndx]
        tone_sequence_ndx = 0 if tone_sequence_ndx >= len(tone_sequence)-1 else tone_sequence_ndx + 1

    if random.random() > 0.5:
        bar.tones[bar.bar_size/2] = tone_sequence[tone_sequence_ndx]
        tone_sequence_ndx = 0 if tone_sequence_ndx >= len(tone_sequence)-1 else tone_sequence_ndx + 1

    bar_rest = bar.bar_size
    while bar_rest > 0:
        possible_sequences = [seq for seq in rhythm_elements if seq['length'] <= bar_rest]
        selected_seq = SeedRandomizer.random_from_probability_list(possible_sequences)

        for seq_note in selected_seq['notes']:
            bar.append_note(copy.copy(seq_note))

        bar_rest = bar.get_space_left()

    # generate pitch of note
    for note_ndx, note in bar.notes.items():
        # first note must be primary tone note
        if first_note_in_all_bars:
            first_note_in_all_bars = False
            note.pitch = primary_tone.get_note_index_by_octave(5)
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


print("Generating MIDI...")
bpm = 120
bar_bpm = 8
bar_time = bar_size / bar_bpm

midi = MIDITime(bpm, "test.mid")
midi_data = []
midi_tone_data = []

curr_beat = 0
tone_beat = 0

for bar in bars:
    tone_beat = curr_beat
    for note_ndx, note in bar.notes.items():
        note_midi_length = bar_time * (note.length / bar.bar_size)
        if not note.silent:
            midi_data.append([
                curr_beat, note.pitch, 127, note_midi_length
            ])
        curr_beat += note_midi_length

    tone_length = bar_size // len(bar.tones.items())
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
