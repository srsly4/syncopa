import random
import argparse
import logging
import SeedRandomizer

import Processors

elements_file = "rhythmelements.json"

print("Narcotic melody generator by srsly_4 / Szymon Piechaczek, 2017")

parser = argparse.ArgumentParser(description="Narcotic melody generator")
parser.add_argument("-s", "--seed", type=str, help="A seed to melody generation process",
                    default=SeedRandomizer.generate_seed())
parser.add_argument("-o", "--output", type=str,
                    help="Output file name", default="output.mid")
parser.add_argument("-b", "--bars", type=int,
                    default=32,
                    help="Count of generated bars")
parser.add_argument("--bpm", type=int, default=120, help="Beats per minute (tempo)")
parser.add_argument("--continuous", help="Generates melody using continuous sample creation", action="store_true")
parser.add_argument("-v", "--verbose", help="Retrieves text transcription of generated melody", action="store_true")
args = parser.parse_args()

if args.verbose:
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.WARNING)

seed = args.seed
print("Seed: " + seed)
random.seed(seed)

results = Processors.ProcessorResults()
output_file = args.output
processors = [
    Processors.ElementsParserProcessor(results, elements_file),
    Processors.ToneGeneratorProcessor(results),
    Processors.SequenceSamplesGeneratorProcessor(results),
    Processors.BarSampleGeneratorProcessor(results, args.bars)
    if not args.continuous else Processors.BarGeneratorProcessor(results),
    Processors.MidiGeneratorProcessor(results, output_file, args.bpm)
]

for processor in processors:
    processor.process()

