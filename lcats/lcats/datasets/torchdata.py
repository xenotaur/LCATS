"""Basic JSON dataset loader."""

import os
import json
from torch.utils.data import Dataset


# TODO(centaur): Do this in a more principled way.
DEFAULT_ROOT_DIR = "data"


class JsonDataset(Dataset):
    def __init__(self, root_dir=DEFAULT_ROOT_DIR, subdirectory=None):
        # Gather data in the subdirectory or the specified root.
        if subdirectory:
            self.data_dir = os.path.join(root_dir, subdirectory)
        else:
            self.data_dir = root_dir

        # Gather all json files in the specified directory and its subdirectories
        self.file_paths = []
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    self.file_paths.append(file_path)

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        file_path = self.file_paths[idx]
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
