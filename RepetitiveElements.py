import copy
from MusicElements import Bar, Note, Tone, ToneType


class SequenceSample:
    def __init__(self, sequence_tone: Tone, notes: list):
        self.tone = sequence_tone
        self.notes = notes
        self.friendly_samples = []

    def get_length(self):
        return sum([note.length for note in self.notes])

    def get_transposed_notes(self, tone: Tone):
        copied_notes = []
        for note in self.notes:
            copied_note: Note = copy.copy(note)
            copied_note.transpose_note(self.tone, tone)
            copied_notes.append(copied_note)
        return copied_notes

    def __hash__(self, *args, **kwargs):
        return hash(sum(str(note) for note in self.notes))
# end RepetitiveElements.py
