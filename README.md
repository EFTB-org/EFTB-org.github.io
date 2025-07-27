# EFTB-org.github.io

A static website for the English For The Blind (EFTB) organization, built with [Hugo](https://gohugo.io/) and custom Python scripts for audio processing. The site provides accessible English learning resources, including audio lessons, documentation, and special events.

## Features
- **Accessible English lessons** with audio content
- **Documentation** and resources for learners and contributors
- **Custom Hugo theme** and layouts
- **Audio processing scripts** in Python for lesson preparation
- **Modern asset pipeline** (SCSS, JS, images)

## Project Structure
- `content/` — Markdown content for the site (lessons, docs, etc.)
- `assets/` — Source assets (SCSS, JS, images, SVGs)
- `layouts/` — Hugo templates and partials
- `static/` — Static files served as-is (audio, images, fonts)
- `python_scripts/` — Python scripts for audio processing and lesson preparation
- `config/` — Hugo configuration files (TOML)
- `public/` — Generated static site output (do not edit directly)

## Getting Started

### Prerequisites
- [Hugo](https://gohugo.io/getting-started/installing/) (extended version recommended)
- [Node.js](https://nodejs.org/) and [pnpm](https://pnpm.io/) for asset building
- Python 3.8+ (for audio scripts)

### Install dependencies
```sh
pnpm install
```

### Run the site locally
```sh
hugo server
```

### Build the site
```sh
hugo
```

### Audio Processing Scripts
Navigate to `python_scripts/` and run scripts as needed. Example:
```sh
cd python_scripts
python3 make_audios.py
```
See `python_scripts/README.md` for details on each script.

## Contributing
Contributions are welcome! Please open issues or pull requests.

## License
See [LICENSE](LICENSE) for details.
