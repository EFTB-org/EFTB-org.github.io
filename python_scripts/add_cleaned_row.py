import argparse

import mdpd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")

    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = f.read()

    data = mdpd.from_md(data)
    data["cleaned"] = data["**Sentence**"]
    data.to_markdown(args.input.replace(".md", "_cleaned.md"), index=False)


if __name__ == "__main__":
    main()
