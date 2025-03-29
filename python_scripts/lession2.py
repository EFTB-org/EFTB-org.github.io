import marimo

__generated_with = "0.11.20"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
