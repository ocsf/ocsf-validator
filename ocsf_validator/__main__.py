from argparse import ArgumentParser

from ocsf_validator.reader import FileReader, ReaderOptions
from ocsf_validator.runner import ValidationRunner, ValidatorOptions

parser = ArgumentParser(prog="ocsf-validator", description="OCSF Schema Validation")
parser.add_argument("path", help="The OCSF schema root directory", action="store")
args = parser.parse_args()

opts = ValidatorOptions(base_path=args.path)

validator = ValidationRunner(opts)

validator.validate()
