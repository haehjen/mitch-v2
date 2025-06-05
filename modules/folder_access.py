# modules/folder_access.py
import os
import logging

logger = logging.getLogger("FolderAccess")

class FolderAccessModule:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def list_folder(self, path):
        try:
            if not os.path.isdir(path):
                logger.error(f"Path {path} is not a valid directory.")
                self.event_bus.emit("speak", f"Error: {path} is not a valid directory.")
                return None

            contents = os.listdir(path)
            logger.info(f"Contents of {path}: {contents}")
            return contents

        except Exception as e:
            logger.error(f"Failed to list folder: {e}")
            self.event_bus.emit("speak", f"Failed to list folder: {str(e)}")
            return None

    def create_folder(self, path):
        try:
            if not os.path.exists(path):
                os.makedirs(path)
                logger.info(f"Created folder: {path}")
                self.event_bus.emit("speak", f"Folder {path} created.")
                return True
            else:
                logger.warning(f"Folder already exists: {path}")
                self.event_bus.emit("speak", f"Folder {path} already exists.")
                return False
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            self.event_bus.emit("speak", f"Failed to create folder: {str(e)}")
            return False

    def read_file(self, path):
        try:
            if not os.path.isfile(path):
                logger.error(f"Path {path} is not a valid file.")
                self.event_bus.emit("speak", f"Error: {path} is not a valid file.")
                return None

            with open(path, 'r') as f:
                content = f.read()
                logger.info(f"Read from {path}: {len(content)} characters")
                return content

        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            self.event_bus.emit("speak", f"Failed to read file: {str(e)}")
            return None
