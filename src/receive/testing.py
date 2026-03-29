import hashlib
import json
from pathlib import Path

from src.config import logger, settings

# TODO <editor-fold desc="REMOVE TEST IN PROD">
def test_and_reset(processor):
    error = False
    logger.info("Verifying file integrity, and checking for missing packets")
    info_file = Path(settings.output_folder) / "info.json"
    info = json.loads(info_file.read_text())
    info_file.unlink()
    for file in info:
        file_id = bytes.fromhex(info[file]["id"])
        if file_id not in processor.processing:
            logger.error(f"File is completely missing {file} [{file_id}]")
            error = True
        else:
            if processor.processing[file_id].complete:
                path = Path(settings.output_folder) / file
                checksum = hashlib.sha256(path.read_bytes()).digest().hex()
                if checksum != info[file]["checksum"]:
                    logger.error(f"File is malformed {file} [{file_id}]: {checksum} != {info[file]['checksum']}")
                    error = True
                path.unlink()
            else:
                logger.error(f"Packets are missing {file} {processor.processing[file_id]}")
                error = True
            processor.processing.pop(file_id)
    if error:
        logger.error(f"Test failed")
    else:
        logger.success(f"All files arrived fully!")
# TODO </editor-fold>