# EFTB-org.github.io Copilot Instructions

## Project Architecture

This is a **Hugo-based static site** for English For The Blind (EFTB) with a sophisticated **audio processing pipeline**. Key components:

- **Hugo site** with Doks theme (`@thulite/doks-core`) for accessible English learning content
- **Python audio processing scripts** (`python_scripts/`) that generate TTS audio from lesson content
- **Custom Hugo shortcodes** (`custom_layouts/shortcodes/`) for embedded audio players
- **Structured lesson content** in Markdown with vocabulary tables and audio integration

## Critical Development Workflows

### Python Scripts (Audio Processing)
**Always use `uv` for Python execution** - never call `python` or `pip` directly:
```bash
cd python_scripts
uv run <script.py> [args...]
uv add <package>  # Add dependencies
```

Key scripts:
- `make_audios.py` - Batch TTS generation using Kokoro pipeline
- `generate_eng_audio.py` - Groq TTS for English (requires `GROQ_API_KEY`)
- `generate_vie_audio.py` - Google Translate TTS for Vietnamese
- Audio processing utilities: `louder.py`, `pad_audio.py`, `mp3_to_wav.py`, `wav_to_mp3.py`

### Hugo Development
```bash
pnpm install              # Install Node.js dependencies
hugo server               # Local development (port 1313)
npm run dev               # Alternative dev command
hugo --minify --gc        # Production build
```

### Content Structure
- `content/docs/` - Main lesson content in Markdown
- `python_scripts/lesson_md/` - Source lesson files for audio generation
- `static/audio/` - Generated audio files served directly
- Lessons follow vocabulary table format with IPA pronunciation and Vietnamese translations

## Project-Specific Patterns

### Audio Integration
Custom shortcode pattern for embedded audio players:
```markdown
{{< audio-player src="/audio/lesson1_vocab.mp3" >}}
```
- Generates unique IDs for multiple players per page
- Includes loading spinners and play/pause states
- Uses `preload="none"` for performance

### Hugo Configuration
- **Multi-environment setup**: `config/_default/`, `config/production/`, `config/next/`
- **Custom output formats**: `searchIndex` (JSON), `SITEMAP` (XML)
- **Doks theme customization** via `params.toml` with sticky navbar and FlexSearch
- **Asset pipeline**: SCSS in `assets/scss/`, compiled via Hugo Pipes

### Lesson Content Format
Structured Markdown with:
- Vocabulary tables with IPA pronunciation: `| Word | /IPA/ | Vietnamese |`
- Language booster sections with phrase patterns
- Audio script integration for TTS generation
- Custom shortcodes for interactive elements

### Deployment
- **Netlify deployment** with Hugo 0.125.1 and Node 20.11.0
- Build command: `npm run build` (runs `hugo --minify --gc`)
- Static files published from `public/` directory
- Audio files must be pre-generated and committed to `static/audio/`

## Key Integration Points

### Audio Generation Workflow
1. Edit lesson content in `python_scripts/lesson_md/`
2. Run TTS scripts to generate audio: `uv run make_audios.py`
3. Audio outputs to `static/audio/` for Hugo to serve
4. Reference in content via `audio-player` shortcode

### Hugo Theme Extension
- Custom layouts in `custom_layouts/` override theme defaults
- Shortcodes in `custom_layouts/shortcodes/` for audio, scripts, tables
- Theme uses Bootstrap-based Doks with accessibility focus

### Content Dependencies
- Lesson audio files must exist in `static/audio/` before Hugo build
- Search index generation requires content to be properly structured
- Vietnamese translations in vocabulary tables drive TTS generation

## Common Gotchas

- **Python execution**: Must use `uv` from `python_scripts/` directory
- **Audio paths**: Use `/audio/` prefix in shortcodes (served from `static/audio/`)
- **Hugo modules**: Theme loaded via `config/_default/module.toml`, not git submodules
- **Build order**: Generate audio first, then run Hugo build for deployment
