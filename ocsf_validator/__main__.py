from argparse import ArgumentParser

from ocsf_validator.runner import ValidationRunner, ValidatorOptions

parser = ArgumentParser(prog="ocsf-validator", description="OCSF Schema Validation")
parser.add_argument("path", help="The OCSF schema root directory")
parser.add_argument(
    "-m",
    "--metaschema_path",
    help="The OCSF schema's metaschema"
    " (default: metaschema subdirectory of schema root)",
)
args = parser.parse_args()

opts = ValidatorOptions(base_path=args.path, metaschema_path=args.metaschema_path)

validator = ValidationRunner(opts)

validator.validate()
