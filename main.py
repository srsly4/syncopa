import random
import Processors

print("Narcotic melody generator by srsly_4")

random.seed("quatar")

results = Processors.ProcessorResults()

processors = [
    Processors.ElementsParserProcessor(results, "rhythmelements.json"),
    Processors.ToneGeneratorProcessor(results),
    Processors.BarGeneratorProcessor(results),
    Processors.MidiGeneratorProcessor(results, "output.mid", 120)
]

for processor in processors:
    processor.process()

