import logging
import subprocess

SUPPORTED_FORMAT = {
    'bin': "binary",
    'ihex': 'ihex',
    'srec': 'srec'
}


def transform_elf_basic(format, in_file, out_file, objcopy=None):
    """Use objcopy to transform ELF to specific format.

    Default use "arm-none-eabi-objcopy"
    Supported formats: bin, ihex, srec.

    Arguments:
        format {str} -- which format you want to convert.
        in_file {str} -- path to elf file.
        out_file {str} -- output file
        objcopy {str} -- default it is "arm-none-eabi-objcopy"

    Returns:
        bool
    """

    if format not in SUPPORTED_FORMAT:
        raise ValueError(f"unknown type, valid choices are: {str(SUPPORTED_FORMAT)}")

    if objcopy is None:
        objcopy = "arm-none-eabi-objcopy"

    format = SUPPORTED_FORMAT.get(format, format)
    cmds = f'\"{objcopy}\" -O {format} {in_file} {out_file}'

    logging.info(cmds)
    return subprocess.call(cmds, shell=True) == 0
