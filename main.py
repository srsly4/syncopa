import random
import Processors

print("Narcotic melody generator by srsly_4")

random.seed("pies")

results = Processors.ProcessorResults()

processors = [
    Processors.ElementsParserProcessor(results, "rhythmelements.json"),
    Processors.ToneGeneratorProcessor(results),
    Processors.SequenceSamplesGeneratorProcessor(results),
    Processors.BarSampleGeneratorProcessor(results, 64),
    # Processors.BarGeneratorProcessor(results),
    Processors.MidiGeneratorProcessor(results, "output.mid", 120)
]

for processor in processors:
    processor.process()

