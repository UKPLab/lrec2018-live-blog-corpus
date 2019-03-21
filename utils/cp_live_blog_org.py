import os
import shutil
import argparse
import pathlib


def get_paths(path):
    print(path)
    train_paths = [ f for f in os.listdir(path + '/train') if os.path.isfile(path + '/train/' + f)]
    valid_paths = [ f for f in os.listdir(path + '/valid') if os.path.isfile(path + '/valid/' + f)]
    test_paths = [ f for f in os.listdir(path + '/test') if os.path.isfile(path + '/test/' + f)]
    return train_paths, valid_paths, test_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--get_splits", type=pathlib.Path, required=False,
                        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/processed/liveblogs"))
    parser.add_argument("--raw_data", type=pathlib.Path, required=False,
                        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/raw/liveblogs"))
    parser.add_argument("--data_dir", type=pathlib.Path, required=True,
                        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/processed/liveblogs_unp"))

    args = parser.parse_args()

    for corpus in ['guardian', 'bbc']:

        data_path = str(args.get_splits.joinpath(corpus, "inputs"))
        paths = [ file for file in os.listdir(data_path) if os.path.isfile(data_path + "/" + file)]
        train_paths, valid_paths, test_paths = get_paths(data_path)

        raw_path = args.raw_data.joinpath(corpus)

        for c_type, f_paths in zip(["train", "valid", "test"], [train_paths, valid_paths, test_paths]):
            unprocessed_path = args.data_dir.joinpath(corpus, c_type)
            print(unprocessed_path, str(unprocessed_path))
            if not os.path.isdir(str(unprocessed_path)):
                os.makedirs(str(unprocessed_path))

            for fname in f_paths:
                shutil.copy(str(raw_path.joinpath(fname)), str(unprocessed_path.joinpath(fname)))




